#!/usr/bin/env python3
"""Subset pilot and full alignment/ETA accounting without modifying the existing trainer.

Usage (shared offline Python):
  -m scripts.train_v6.pilot --prepare
  -m scripts.training.train_mbert --run pilot-v6 --region-train-file
    data/augmentation/pilot-v6-train.jsonl --region-dev-file
    data/augmentation/pilot-v6-dev.jsonl --epochs 1 --batch-size 16 --out-dir models
  -m scripts.train_v6.pilot --measure

The full loader's 32,000-row bound is not bypassed for training. Full alignment
is counted in bounded read-only chunks; it is not a full fitting run.
"""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
from .convert import require
from .io import encode, sha256
from .spec import MANIFEST, OUTPUTS, ROOT
from privacygate.data import region_data as rd
from privacygate import mbert_data as md

PILOT_FILES = {split: ROOT / 'data/augmentation/pilot-v6-{}.jsonl'.format(split) for split in ('train', 'dev')}
PILOT_MANIFEST = ROOT / 'data/augmentation/pilot-v6-manifest.json'
RESULT = ROOT / 'artifacts/train-v6/pilot.json'
MODEL_INFO = ROOT / 'models/pilot-v6/train_info.json'


def bound_sources():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for split, path in OUTPUTS.items():
        require(sha256(path) == manifest['outputs'][split]['sha256'], 'source_hash_mismatch')
    return manifest


def prepare():
    bound_sources()
    require(not any(path.exists() for path in [*PILOT_FILES.values(), PILOT_MANIFEST]), 'pilot_output_exists')
    manifest = {'method': 'first rows of fixed-seed shuffled full outputs', 'outputs': {}, 'source_manifest_sha256': sha256(MANIFEST)}
    for split, count in (('train', 400), ('dev', 200)):
        selected = []
        with OUTPUTS[split].open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                rd._check_row(row, split)
                selected.append(row)
                if len(selected) == count:
                    break
        require(len(selected) == count, 'pilot_subset_too_small')
        with PILOT_FILES[split].open('x', encoding='utf-8', newline='\n') as stream:
            for row in selected:
                stream.write(encode(row))
        manifest['outputs'][split] = {'path': str(PILOT_FILES[split].relative_to(ROOT)),
            'sha256': sha256(PILOT_FILES[split]), 'rows': count,
            'full_source_sha256': sha256(OUTPUTS[split])}
    PILOT_MANIFEST.write_text(encode(manifest), encoding='utf-8')
    train, _ = rd.load_region_file(PILOT_FILES['train'], 'train', PILOT_MANIFEST)
    dev, _ = rd.load_region_file(PILOT_FILES['dev'], 'dev', PILOT_MANIFEST)
    rd.check_disjoint(train, dev)
    print('PILOT_PREPARED train=400 dev=200')


def profile_file(tok, path, split):
    from privacygate.data import window_alignment as wa
    stats = wa.empty_stats()
    stats.update(rows_available=0, rows_used=0, rows_excluded=0, clean_rows_used=0, windows=0)
    lengths, prediction_lengths, chunk = [], [], []
    start = time.perf_counter()

    def consume(rows):
        windows, observed = rd.build_windows(tok, rows)
        for key, value in observed.items():
            if isinstance(value, dict):
                for reason, count in value.items():
                    stats[key][reason] += count
            else:
                stats[key] += value
        lengths.extend(len(window[0]) for window in windows)
        if split == 'dev':
            prediction_lengths.extend(len(ids) for row in rows for ids, _ in md.encode(tok, row['text']))

    with path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            rd._check_row(row, split)
            chunk.append(row)
            if len(chunk) == 256:
                consume(chunk)
                chunk = []
        if chunk:
            consume(chunk)
    stats['alignment_seconds'] = time.perf_counter() - start
    stats['windows_per_available_row'] = stats['windows'] / stats['rows_available']
    stats['windows_per_used_row'] = stats['windows'] / stats['rows_used']
    stats['window_lengths'] = dict(sorted(Counter(lengths).items()))
    stats['prediction_windows'] = len(prediction_lengths) if split == 'dev' else None
    return stats, lengths


def batch_shapes(lengths, batch_size=16):
    indices = list(range(len(lengths)))
    random.Random(13).shuffle(indices)
    counts = Counter()
    for start in range(0, len(indices), batch_size):
        batch = indices[start:start + batch_size]
        padded = min(md.MAX_LEN, (max(lengths[index] for index in batch) + 63) // 64 * 64)
        counts[str(padded)] += 1
    return dict(sorted(counts.items()))


def measure():
    require(not RESULT.exists(), 'pilot_measurement_exists')
    manifest = bound_sources()
    info = json.loads(MODEL_INFO.read_text(encoding='utf-8'))
    require(info['device'] == 'mps' and info['batch_size'] == 16 and info['epochs'] == 1, 'pilot_settings_mismatch')
    require(info['train_rows'] == 400 and info['dev_rows'] == 200, 'pilot_row_count_mismatch')
    pilot_binding = json.loads(PILOT_MANIFEST.read_text(encoding='utf-8'))
    for split, path in PILOT_FILES.items():
        require(sha256(path) == info['data_sha256s'][split] == pilot_binding['outputs'][split]['sha256'], 'pilot_hash_mismatch')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    md.setup_hf_home()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(md.MODEL_ID, revision=md.MODEL_REVISION, use_fast=True, local_files_only=True)
    full_train, train_lengths = profile_file(tok, OUTPUTS['train'], 'train')
    print('FULL_ALIGNMENT train_rows={} train_windows={} excluded={}'.format(
        full_train['rows_available'], full_train['windows'], full_train['rows_excluded']), flush=True)
    full_dev, _ = profile_file(tok, OUTPUTS['dev'], 'dev')
    _, pilot_train_lengths = profile_file(tok, PILOT_FILES['train'], 'train')
    steps = math.ceil(full_train['windows'] / 16)
    evaluation = info['eval_time_s'] * full_dev['prediction_windows'] / info['dev_windows']
    prep = full_train['alignment_seconds'] + full_dev['alignment_seconds']
    estimates = {}
    for epochs in (1, 2):
        training = epochs * steps / info['steps_per_sec']
        estimates[str(epochs)] = {'epochs': epochs, 'batch_size': 16, 'steps': epochs * steps,
            'train_seconds': training, 'train_hours': training / 3600,
            'dev_eval_seconds': epochs * evaluation,
            'alignment_seconds': prep, 'save_upper_seconds': epochs * info['save_time_s'],
            'train_dev_alignment_save_seconds': training + epochs * (evaluation + info['save_time_s']) + prep,
            'train_dev_alignment_save_hours': (training + epochs * (evaluation + info['save_time_s']) + prep) / 3600}
    result = {'device': info['device'], 'batch_size': 16, 'source_manifest_sha256': sha256(MANIFEST),
        'pilot_train_info_sha256': sha256(MODEL_INFO),
        'pilot': {key: info[key] for key in ('train_rows', 'dev_rows', 'train_windows', 'dev_windows',
            'train_rows_used', 'train_rows_excluded', 'train_alignment_stats', 'dev_alignment_stats',
            'steps', 'steps_per_sec', 'train_time_s', 'eval_time_s', 'save_time_s')},
        'pilot_windows_per_available_row': info['train_windows'] / info['train_rows'],
        'pilot_windows_per_used_row': info['train_windows'] / info['train_rows_used'],
        'full_train_alignment': full_train, 'full_dev_alignment': full_dev,
        'pilot_padded_batch_shapes': batch_shapes(pilot_train_lengths),
        'full_padded_batch_shapes_epoch_one': batch_shapes(train_lengths), 'eta': estimates,
        'eta_method': 'Exact full retained window count; ceil(windows/16)/measured pilot steps_per_sec. Dev scales by prediction windows. Saves conservatively once per epoch. Alignment measured. Model initialization is excluded. Estimates are not full-run measurements; MPS load and sequence lengths affect throughput.',
        'requested_pilot_cli_refusal': 'region_mode_arguments',
        'pilot_alternative': 'Unchanged trainer with materialized 400/200 subsets and no unsupported max-row flags.',
        'full_loader_rows': manifest['outputs']['train']['rows'], 'existing_loader_row_limit': rd.MAX_ROWS,
        'full_training_ready_with_existing_loader': manifest['outputs']['train']['rows'] <= rd.MAX_ROWS}
    with RESULT.open('x', encoding='utf-8') as stream:
        stream.write(encode(result))
    print('PILOT_MEASURED steps_per_sec={:.6f} pilot_windows_per_row={:.6f} full_windows_per_row={:.6f} eta_1ep_h={:.6f} eta_2ep_h={:.6f}'.format(
        info['steps_per_sec'], result['pilot_windows_per_available_row'], full_train['windows_per_available_row'],
        estimates['1']['train_hours'], estimates['2']['train_hours']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--measure', action='store_true')
    args = parser.parse_args()
    try:
        prepare() if args.prepare else measure()
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, IndexError):
        print('ERROR pilot_failed', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
