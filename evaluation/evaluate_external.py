#!/usr/bin/env python3
"""Offline, value-free Gretel scoring and EXT-DEV-only inference selection.

No training, downloads or raw-text artifacts. TEST is opened for text hashes only
while reserving EXT-DEV; its annotations are not accessed until the selected
single measurement. Probability caches contain offsets/probabilities, no values.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacygate import pipeline, mbert_data
from privacygate.model import hybrid, inference
from privacygate.masking_metrics import interval_union, intersection, count_chars, count_alnum
from evaluation.masking_eval import quiet_libraries

DATA = ROOT / 'data/local/external/gretel-finance-7b844d1'
MODELS = ROOT / 'models'
CACHE = ROOT / '.cache/ext-step1-probabilities'
LANGUAGES = ('English', 'France', 'German', 'Italian', 'Spanish')
MAPPING = {
    'name': 'PERSONNAME', 'first_name': 'PERSONNAME', 'last_name': 'PERSONNAME',
    'street_address': 'ADDRESS', 'phone_number': 'TELEPHONENUM', 'email': 'EMAIL',
    'date_of_birth': 'DATEOFBIRTH', 'ssn': 'SOCIALNUM', 'passport_number': 'PASSPORTNUM',
    'driver_license_number': 'DRIVERLICENSENUM', 'credit_card_number': 'CREDITCARDNUMBER',
    'iban': 'IBAN', 'bban': 'ACCOUNTNUM', 'user_name': 'USERNAME',
    'customer_id': 'PERSONALREF', 'employee_id': 'PERSONALREF',
}
OUT = {'company', 'date', 'time', 'date_time', 'swift_bic_code', 'bank_routing_number',
       'local_latlng', 'ipv4', 'ipv6', 'api_key', 'password', 'account_pin', 'credit_card_security_code'}
TRAIN_SHA = {
    'English': '2858af81ec59d8528f81059facb099ac33e6b47caf2501da3eac113bccfee9c7',
    'France': 'a8303598dce1a6af58840d6e69ca31667f85da2abcad06b38c0cc8e296802825',
    'German': 'e7534ae69a3f2009bfa0e56af5f0d14d4a59e7138d5cf400e56ea81a7862a404',
    'Italian': 'd24d97511a933269e36ea36e591415f319cb61201838b586cf6e760cd5584082',
    'Spanish': '39954d0931f3d3771af1200f0255016bbe29905dcd0fec539864d3b01ea63b7b',
}
TEST_SHA = {
    'English': 'c02b06d3c5b7c375525136d6f74acc52ab8fc07fa863d0aa50734910ec0ef2ad',
    'France': '39fc2777822bbecab2d89bb23cbed40d9825ff4117897b8b025c02287f4ba845',
    'German': 'bfc64380bc24453f3460ffee6afbd7a3442b60dd26d5341c9fe0f1cca43216c3',
    'Italian': 'f9e8681604bf96ed03d7b275ea5259b1a6ab3e2d7a3dfdbcc27571a608dda30d',
    'Spanish': '89ff0e5b6cfd14119d299a17ce08d4bc46ce69b32cfb3740ec3bdef64de1f427',
}
TEST_ROWS = {'English': 2891, 'France': 443, 'German': 453, 'Italian': 448, 'Spanish': 461}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    pending.replace(path)


def merge_per_label(spans):
    groups = defaultdict(list)
    for span in spans:
        groups[span['label']].append((span['start'], span['end']))
    result = []
    for label, pairs in groups.items():
        merged = []
        for a, b in sorted(pairs):
            if merged and a < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        result.extend(dict(start=a, end=b, label=label) for a, b in merged)
    return sorted(result, key=lambda s: (s['start'], s['end'], s['label']))


def convert(language, ordinal, row):
    text = row['generated_text']
    assert isinstance(text, str) and row['language'] == language
    spans = json.loads(row['pii_spans'])
    assert isinstance(spans, list)
    for s in spans:
        assert s['label'] in set(MAPPING) | OUT
        assert type(s['start']) is int and type(s['end']) is int
        assert 0 <= s['start'] < s['end'] <= len(text)
    gold = merge_per_label([dict(start=s['start'], end=s['end'], label=MAPPING[s['label']])
                            for s in spans if s['label'] in MAPPING])
    return dict(language=language, ordinal=ordinal, text=text, text_sha256=text_sha(text),
                gold=gold, all_annotations=spans)


def load_data(split, data=DATA):
    import pyarrow.parquet as pq
    data = Path(data)
    hashes = {}
    # EXT-DEV reads only this column of TEST, never labels or other metadata.
    test_text_hashes = set()
    for language in LANGUAGES:
        path = data / (language + '_test.parquet')
        hashes[path.name] = sha(path)
        assert hashes[path.name] == TEST_SHA[language]
        table = pq.read_table(path, columns=['generated_text'])
        assert table.num_rows == TEST_ROWS[language]
        test_text_hashes.update(text_sha(t) for t in table['generated_text'].to_pylist())
    rows, reservation = [], {}
    for language in LANGUAGES:
        path = data / (language + ('_test.parquet' if split == 'test' else '_train.parquet'))
        hashes[path.name] = sha(path)
        assert hashes[path.name] == (TEST_SHA if split == 'test' else TRAIN_SHA)[language]
        table = pq.read_table(path, columns=['generated_text', 'pii_spans', 'language'])
        source = table.to_pylist()
        if split == 'ext-dev':
            eligible = [(text_sha(r['generated_text']), i, r) for i, r in enumerate(source)
                        if text_sha(r['generated_text']) not in test_text_hashes]
            eligible.sort(key=lambda r: (r[0], r[1]))
            chosen = eligible[:200]
            assert len(chosen) == 200
            reservation[language] = {'train_rows': len(source), 'test_duplicates_dropped': len(source) - len(eligible),
                                     'reserved_rows': 200, 'selected_text_hashes': [r[0] for r in chosen],
                                     'selected_ordinals': [r[1] for r in chosen]}
            rows.extend(convert(language, i, r) for _, i, r in chosen)
        else:
            rows.extend(convert(language, i, r) for i, r in enumerate(source))
    assert len(rows) == (1000 if split == 'ext-dev' else 4696)
    return rows, {'split': split, 'data_sha256s': hashes, 'reservation': reservation,
                  'rows': len(rows), 'dataset_revision': '7b844d16738527a04264f50214cb426a4cea0897',
                  'license': 'Apache-2.0', 'synthetic': True}


def model_paths(model, options, models=MODELS):
    if model in ('v4', 'region-v4-2ep'):
        paths = [Path(models) / 'region-v4-2ep']
    elif model in ('v5', 'region-v5-2ep'):
        paths = [Path(models) / 'region-v5-2ep']
    elif model == 'ensemble':
        paths = [Path(models) / 'region-v4-2ep']
    else:
        paths = [Path(model).resolve()]
    if model == 'ensemble' or options.get('ensemble'):
        paths.append(pipeline.ensemble_peer(paths[0]))
    return paths


class ProbabilityCache:
    """Float32 NPZ keyed by document hash, weights/config/tokenizer/code hashes.

    All probabilities are stored, not just argmax/name mass. Replaying thresholds
    and both propagation modes never runs the neural model. No pickle or text.
    """
    def __init__(self, paths, cache=CACHE):
        self.paths = paths
        self.cache = Path(cache)
        self.bindings, self.labels, self.dirs = {}, {}, {}
        tokenizer = Path(os.environ['HF_HOME']) / 'hub/models--google-bert--bert-base-multilingual-cased/snapshots' / mbert_data.MODEL_REVISION
        tok_hashes = {p.name: sha(p) for p in sorted(tokenizer.iterdir()) if p.is_file()}
        for path in paths:
            binding = {'weights': sha(path / 'model.safetensors'), 'config': sha(path / 'config.json'),
                       'tokenizer': tok_hashes, 'probability_code': sha(Path(hybrid.__file__)), 'schema': 1}
            key = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
            self.bindings[str(path)] = binding
            self.labels[str(path)] = {int(k): v for k, v in json.loads((path / 'config.json').read_text())['id2label'].items()}
            self.dirs[str(path)] = self.cache / key
            self.dirs[str(path)].mkdir(parents=True, exist_ok=True)
        assert all(labels == self.labels[str(paths[0])] for labels in self.labels.values())

    def file(self, path, row):
        return self.dirs[str(path)] / (row['text_sha256'] + '.npz')

    def prepare(self, rows):
        import numpy as np
        import torch
        for path in self.paths:
            missing = {r['text_sha256']: r for r in rows if not self.file(path, r).is_file()}
            pending = list(missing.values())
            if not pending:
                print('CACHE_HIT model={} docs={}'.format(path.name, len(rows)), flush=True)
                continue
            with quiet_libraries():
                model = hybrid.Mbert(path)
                for begin in range(0, len(pending), 16):
                    chunk = pending[begin:begin + 16]
                    outputs = model.raw_probabilities([r['text'] for r in chunk])
                    for row, windows in zip(chunk, outputs):
                        lengths = np.array([len(offs) for offs, _ in windows], dtype=np.int32)
                        offsets = np.array([(-1, -1) if o is None else o for offs, _ in windows for o in offs], dtype=np.int32)
                        probabilities = np.concatenate([p for _, p in windows])
                        target = self.file(path, row)
                        with target.with_suffix('.pending').open('wb') as handle:
                            np.savez_compressed(handle, offsets=offsets, lengths=lengths, probabilities=probabilities)
                        target.with_suffix('.pending').replace(target)
                    if begin % 128 == 0 or begin + len(chunk) == len(pending):
                        print('PROBABILITIES model={} complete={}/{}'.format(path.name, begin + len(chunk), len(pending)), flush=True)
                del model
            import gc
            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

    def windows(self, path, row):
        import numpy as np
        result, pos = [], 0
        with np.load(self.file(path, row), allow_pickle=False) as saved:
            offsets, probabilities = saved['offsets'], saved['probabilities']
            for length in saved['lengths']:
                length = int(length)
                offs = [None if int(a) == -1 else (int(a), int(b)) for a, b in offsets[pos:pos + length]]
                result.append((offs, probabilities[pos:pos + length]))
                pos += length
            assert pos == len(offsets) == len(probabilities)
        return result

    def predict(self, row, model, options, windows=None):
        paths = model_paths(model, options, self.paths[0].parent)
        windows = windows or {str(p): self.windows(p, row) for p in paths}
        probs = windows[str(paths[0])]
        if len(paths) == 2:
            probs = hybrid.Mbert.average_probabilities(probs, windows[str(paths[1])])
        raw = hybrid.Mbert.decode_probabilities(probs, self.labels[str(paths[0])], options.get('name_threshold'))
        adapter = SimpleNamespace(spans_with_scores=hybrid.Mbert.spans_with_scores)
        batch = inference.mbert_candidates(row['text'], _mbert=adapter, _raw=raw)
        stages = pipeline._stages('full')
        result = pipeline._finish(row['text'], batch, stages, pipeline._modules(stages), options)
        assert result['status'] == 'ok'
        return result


def span_counts(text, gold, mask):
    n = len(text)
    union = interval_union([(s['start'], s['end']) for s in gold], n)
    hits = intersection(union, mask, n)
    c = Counter(gold_spans=len(gold), positive_rows=bool(gold))
    c['gold_chars'], c['covered_gold_chars'] = count_chars(union, n), count_chars(hits, n)
    c['exposed_gold_chars'] = c['gold_chars'] - c['covered_gold_chars']
    c['gold_alnum_chars'], c['covered_gold_alnum_chars'] = count_alnum(text, union), count_alnum(text, hits)
    c['exposed_gold_alnum_chars'] = c['gold_alnum_chars'] - c['covered_gold_alnum_chars']
    c['rows_with_exposed_alnum'] = c['exposed_gold_alnum_chars'] > 0
    for kind, test in [('letters', str.isalpha), ('digits', str.isdigit)]:
        c['gold_' + kind] = sum(test(text[i]) for a, b in union for i in range(a, b))
        c['covered_gold_' + kind] = sum(test(text[i]) for a, b in hits for i in range(a, b))
        c['exposed_gold_' + kind] = c['gold_' + kind] - c['covered_gold_' + kind]
    for s in gold:
        hit = count_chars(intersection([(s['start'], s['end'])], mask, n), n)
        c['complete_spans' if hit == s['end'] - s['start'] else 'partial_spans' if hit else 'untouched_spans'] += 1
    return c


def score(row, result):
    text, n = row['text'], len(row['text'])
    mask = interval_union([(s['start'], s['end']) for s in result['entities']], n)
    ann = interval_union([(s['start'], s['end']) for s in row['all_annotations']], n)
    base = Counter(rows=1, text_chars=n, masked_chars=count_chars(mask, n), blocked_rows=result['status'] == 'blocked',
                   non_annotated_chars=n - count_chars(ann, n),
                   excess_masked_chars=count_chars(mask, n) - count_chars(intersection(mask, ann, n), n))
    base['rows_with_excess'] = base['excess_masked_chars'] > 0
    base['all_annotation_empty_rows'] = not row['all_annotations']
    base['all_annotation_empty_masked_rows'] = not row['all_annotations'] and bool(mask)
    base['empty_in_scope_gold_rows'] = not row['gold']
    base['empty_in_scope_gold_masked_rows'] = not row['gold'] and bool(mask)
    total = span_counts(text, row['gold'], mask) + base
    labels = {label: span_counts(text, [s for s in row['gold'] if s['label'] == label], mask) + base
              for label in {s['label'] for s in row['gold']}}
    return total, labels


def describe(c):
    assert c['covered_gold_alnum_chars'] + c['exposed_gold_alnum_chars'] == c['gold_alnum_chars']
    assert c['complete_spans'] + c['partial_spans'] + c['untouched_spans'] == c['gold_spans']
    assert c['excess_masked_chars'] <= c['non_annotated_chars']
    def pct(a, b):
        return 100 * c[a] / c[b] if c[b] else None
    return {**dict(c), 'coverage_pct': pct('covered_gold_alnum_chars', 'gold_alnum_chars'),
            'excess_pct': pct('excess_masked_chars', 'non_annotated_chars'),
            'rows_exposed': c['rows_with_exposed_alnum']}


class Aggregate:
    def __init__(self):
        self.overall, self.languages, self.labels = Counter(), defaultdict(Counter), defaultdict(Counter)

    def add(self, row, result):
        c, labels = score(row, result)
        self.overall.update(c)
        self.languages[row['language']].update(c)
        for label, counts in labels.items():
            self.labels[label].update(counts)

    def report(self):
        labels = json.loads((ROOT / 'configs/privacy-policy-v1.json').read_text())['labels']
        return {**describe(self.overall), 'per_language': {k: describe(v) for k, v in sorted(self.languages.items())},
                'per_label': {k: describe(self.labels[k]) for k in sorted(labels)}}


def provenance(cache, binding):
    code = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    return {**binding, 'model_sha256s': {Path(k).name: v['weights'] for k, v in cache.bindings.items()},
            'model_bindings': {Path(k).name: v for k, v in cache.bindings.items()}, 'code_commit': code,
            'code_sha256s': {str(p.relative_to(ROOT)): sha(p) for p in
                            [Path(__file__), Path(pipeline.__file__), Path(hybrid.__file__), Path(inference.__file__),
                             ROOT / 'privacygate/assemblers/names.py']},
            'mapping': MAPPING, 'out_of_scope_labels': sorted(OUT),
            'definitions': {'coverage_pct': 'Unicode str.isalnum union coverage of in-scope mapped annotations, class-agnostic final mask.',
                            'excess_pct': 'Masked chars outside ALL source annotations / all non-annotated chars; upper bound, not adjudicated false positives.',
                            'per_label': 'Label gold counts; whole-row excess repeats for each supported label (non-additive).'},
            'training': False, 'offline': True}


def evaluate(rows, cache, model, options, receipts=None):
    aggregate = Aggregate()
    started = time.perf_counter()
    handle = Path(receipts).open('x') if receipts else None
    try:
        for i, row in enumerate(rows):
            result = cache.predict(row, model, options)
            aggregate.add(row, result)
            if handle:
                handle.write(json.dumps({'row': i, 'entities': result['entities'], 'status': result['status']}) + '\n')
            if (i + 1) % 500 == 0:
                print('SCORED docs={}/{}'.format(i + 1, len(rows)), flush=True)
    finally:
        if handle:
            handle.close()
    report = aggregate.report()
    if receipts:
        verified = Aggregate()
        saved = [json.loads(line) for line in Path(receipts).read_text().splitlines()]
        assert len(saved) == len(rows)
        for i, (row, result) in enumerate(zip(rows, saved)):
            assert result['row'] == i
            verified.add(row, result)
        assert verified.report() == report
        report['receipt_verification'] = True
    return {**report, 'model': model, 'options': options, 'wall_seconds': time.perf_counter() - started}


def grid(args):
    assert args.split == 'ext-dev'
    rows, binding = load_data('ext-dev', args.data)
    paths = model_paths('ensemble', {}, args.models)
    cache = ProbabilityCache(paths, args.cache)
    cache.prepare(rows)
    settings = [(model, {'name_threshold': threshold, 'name_propagation_ext': prop, 'ensemble': model == 'ensemble'})
                for model in ('v4', 'v5', 'ensemble') for threshold in (None, 0.4, 0.3, 0.2, 0.1) for prop in (False, True)]
    aggregates = [Aggregate() for _ in settings]
    for i, row in enumerate(rows):
        windows = {str(p): cache.windows(p, row) for p in paths}
        for (model, options), aggregate in zip(settings, aggregates):
            aggregate.add(row, cache.predict(row, model, options, windows))
        if (i + 1) % 100 == 0:
            print('GRID docs={}/{} settings={}'.format(i + 1, len(rows), len(settings)), flush=True)
    results = [{**a.report(), 'model': m, 'options': o} for (m, o), a in zip(settings, aggregates)]
    baselines = {r['model']: r for r in results if r['options']['name_threshold'] is None and not r['options']['name_propagation_ext']}
    for result in results:
        result['baseline_excess_pct'] = baselines[result['model']]['excess_pct']
        result['eligible'] = result['excess_pct'] <= result['baseline_excess_pct'] + 1.0
    eligible = [r for r in results if r['eligible']]
    # Predetermined neutral tie break: lower excess, then stable grid order.
    chosen = max(eligible, key=lambda r: (r['coverage_pct'], -r['excess_pct']))
    out = Path(args.out)
    save(out, {**provenance(cache, binding), 'selection_rule': 'Highest coverage subject to same-model all-options-off baseline excess + 1.0 percentage point; ties lower excess then grid order.',
               'ensemble_baseline': 'Probability-averaged ensemble with threshold and propagation off.',
               'results': results, 'chosen': chosen})
    lines = ['# EXT-DEV inference-only grid', '', 'Selection only: 200 text-hash-sorted, TEST-deduplicated train rows per language; no training.',
             'Same-model excess budget = baseline + 1.0 percentage point. Ensemble baseline averages v4/v5; name options off.', '',
             '| model | name threshold | propagation ext | coverage % | excess % | rows exposed | excess cap % | eligible |',
             '|---|---|---|---:|---:|---:|---:|---|']
    for r in results:
        lines.append('| {} | {} | {} | {:.4f} | {:.4f} | {} | {:.4f} | {} |'.format(r['model'], r['options']['name_threshold'], r['options']['name_propagation_ext'],
                     r['coverage_pct'], r['excess_pct'], r['rows_exposed'], r['baseline_excess_pct'] + 1, r['eligible']))
    lines.extend(['', 'Chosen: ' + chosen['model'] + ' ' + json.dumps(chosen['options'], sort_keys=True),
                  'TEST is not used for selection; its text hashes are used only to exclude duplicates.', ''])
    out.with_suffix('.md').write_text('\n'.join(lines))
    print('SELECTED ' + json.dumps({k: chosen[k] for k in ('model', 'options', 'coverage_pct', 'excess_pct')}, sort_keys=True), flush=True)


def v7(args, model, options):
    # Reuse the actual v7 validator and evaluate_pipeline aggregate scorer,
    # without its blind custody, now that the user designates v7 development.
    from evaluation import evaluate_pipeline as runner
    from evaluation import masking_eval as ev
    from evaluation.checks.verify_frozen import V7_DATA
    rows, binding = runner.load_v7_dataset(V7_DATA)
    original = rows
    adapted = [dict(text=r['text'], text_sha256=text_sha(r['text'])) for r in original]
    cache = ProbabilityCache(model_paths(model, options, args.models), args.cache)
    cache.prepare(adapted)
    aggregate = ev.EvaluationAggregate()
    for row, adapted_row in zip(original, adapted):
        aggregate.add(row, cache.predict(adapted_row, model, options))
    report = {**aggregate.report(), **provenance(cache, {'data_sha256s': {'masking-stress-v7.jsonl': binding['sha256']}}),
              'model': model, 'options': options, 'development': True, 'blind': False, 'dataset_version': 'v7',
              'baseline_context': {'v4': {'clean_rows_masked': 21, 'clean_rows': 300, 'exposed_alnum': 111},
                                   'v5': {'clean_rows_masked': 19, 'clean_rows': 300, 'exposed_alnum': 334}}}
    save(args.v7_out / 'metrics.json', report)
    overall = report['overall']
    lines = ['# v7 development check (not blind)', '',
             'Chosen model: ' + model, 'Options: ' + json.dumps(options, sort_keys=True),
             'Clean rows masked: {}/{}; v4 baseline 21/300; v5 baseline 19/300.'.format(overall['clean_controls']['masked_rows'], overall['clean_controls']['rows']),
             'Exposed letters/digits: {}; v4 baseline 111; v5 baseline 334.'.format(overall['leaked_gold_alnum_chars']),
             'Scoring: evaluate_pipeline.py EvaluationAggregate, unchanged v7 validator; no blind-v7 artifact/custody writes.', '']
    (args.v7_out / 'summary.md').write_text('\n'.join(lines))
    print('V7_COMPLETE clean_masked={} exposed_alnum={}'.format(overall['clean_controls']['masked_rows'], overall['leaked_gold_alnum_chars']), flush=True)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('external_arguments') from None


def main():
    parser = SafeParser(description=__doc__)
    parser.add_argument('--split', choices=('test', 'ext-dev'), required=True)
    parser.add_argument('--model', default='v4')
    parser.add_argument('--options', default='{}', help='JSON object; all three switches default off')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--models', type=Path, default=MODELS)
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--grid', action='store_true')
    parser.add_argument('--selection', type=Path, help='Use chosen entry from an EXT-DEV grid, without re-selection')
    parser.add_argument('--v7-out', type=Path, help='Optional chosen-setting v7 development check before TEST')
    args = parser.parse_args()
    assert os.environ.get('HF_HUB_OFFLINE') == '1' and os.environ.get('HF_HOME')
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    if args.grid:
        grid(args)
        return 0
    model, options = args.model, json.loads(args.options)
    pipeline.normalize_options(options)
    if model == 'ensemble':
        options['ensemble'] = True
    if args.selection:
        selection = json.loads(args.selection.read_text())
        assert selection['split'] == 'ext-dev'
        model, options = selection['chosen']['model'], selection['chosen']['options']
    if args.v7_out:
        assert 'blind-v7' not in args.v7_out.parts
        v7(args, model, options)
    if args.split == 'test':
        assert args.selection, 'test_requires_locked_ext_dev_selection'
        assert not args.out.exists()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive start receipt refuses accidental remeasurement even on failure.
        with args.out.with_suffix('.STARTED').open('x') as handle:
            json.dump({'model': model, 'options': options, 'selection_sha256': sha(args.selection)}, handle)
    rows, binding = load_data(args.split, args.data)
    cache = ProbabilityCache(model_paths(model, options, args.models), args.cache)
    cache.prepare(rows)
    report = evaluate(rows, cache, model, options, args.out.parent / 'receipts.jsonl')
    save(args.out, {**provenance(cache, binding), **report, 'runs': 1, 'selection_sha256': sha(args.selection) if args.selection else None})
    print('EXTERNAL_COMPLETE ' + json.dumps({k: report[k] for k in ('model', 'options', 'coverage_pct', 'excess_pct', 'rows_exposed')}, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as error:
        import traceback
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                  for f in traceback.extract_tb(error.__traceback__)]
        print('EXTERNAL_FAILED type={} frames={}'.format(type(error).__name__, json.dumps(frames)), file=sys.stderr)
        raise SystemExit(2)
