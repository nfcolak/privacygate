"""Exclusive output creation and read-only byte-for-byte deterministic replay."""
from collections import Counter
import hashlib
import json
import random
import sys

from .convert import conversion_stats, convert, require, scorer_constants
from .spec import (DATA, ENGLISH_CAP, EXT_DEV_PER_LANGUAGE, LANGUAGES, MANIFEST, OUTPUTS,
                   POLICY, REVISION, ROOT, SCORER, SEED, SYNTHETIC_ROWS, TRAIN_HASHES, V5,
                   V5_HASH, V5_ROWS)
from .synthetic import build_synthetic

sys.path.insert(0, str(ROOT))
from privacygate.data import region_data as rd


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def encode(row):
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'


def file_record(path, relative=False):
    return {'path': str(path.relative_to(ROOT) if relative else path),
            'sha256': sha256(path), 'bytes': path.stat().st_size}


def frozen_inputs():
    mapping, outside, test_hashes = scorer_constants(SCORER)
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    require(set(mapping.values()) <= set(policy['labels']) == set(rd.REGION_LABELS), 'policy_mapping_mismatch')
    require(not set(mapping) & outside, 'mapping_scope_overlap')
    records = {'policy': file_record(POLICY, True), 'scorer': file_record(SCORER), 'train_v5': file_record(V5)}
    require(records['train_v5']['sha256'] == V5_HASH, 'train_v_five_hash_mismatch')
    for language in LANGUAGES:
        for split, expected in (('train', TRAIN_HASHES[language]), ('test', test_hashes[language])):
            path = DATA / (language + '_' + split + '.parquet')
            record = file_record(path)
            require(record['sha256'] == expected, 'gretel_input_hash_mismatch')
            records[language + '_' + split] = record
    code_paths = [ROOT / 'scripts/make_train_v6.py', *sorted((ROOT / 'scripts/train_v6').glob('*.py'))]
    code_paths += [ROOT / 'privacygate/data/region_data.py', ROOT / 'privacygate/data/window_alignment.py',
                   ROOT / 'privacygate/mbert_data.py']
    code_records = {str(path.relative_to(ROOT)): file_record(path, True) for path in code_paths}
    return mapping, outside, records, code_records


def build_datasets():
    import pyarrow.parquet as pq
    mapping, outside, inputs, code = frozen_inputs()
    # Standing TEST: read only generated_text, immediately reduce to hashes; never read annotations.
    test_texts, test_rows = set(), 0
    for language in LANGUAGES:
        values = pq.read_table(DATA / (language + '_test.parquet'), columns=['generated_text']).column(0).to_pylist()
        inputs[language + '_test']['rows'] = len(values)
        test_rows += len(values)
        test_texts.update(text_hash(value) for value in values)
    candidates, reservation, reserved_hashes = {}, {}, set()
    for language in LANGUAGES:
        table = pq.read_table(DATA / (language + '_train.parquet'), columns=['generated_text', 'pii_spans', 'language'])
        raw = table.to_pylist()
        inputs[language + '_train']['rows'] = len(raw)
        eligible = sorted(((text_hash(row['generated_text']), ordinal, row)
                           for ordinal, row in enumerate(raw) if text_hash(row['generated_text']) not in test_texts),
                          key=lambda record: (record[0], record[1]))
        require(len(eligible) >= EXT_DEV_PER_LANGUAGE, 'reservation_too_small')
        candidates[language] = eligible
        selected = eligible[:EXT_DEV_PER_LANGUAGE]
        reserved_hashes.update(digest for digest, _, _ in selected)
        reservation[language] = {'train_input_rows': len(raw), 'test_text_duplicates_dropped': len(raw) - len(eligible),
            'eligible_rows': len(eligible), 'reserved_rows': len(selected),
            'reservation_text_hashes_sha256': hashlib.sha256('\n'.join(x[0] for x in selected).encode()).hexdigest()}
    datasets = {'train': [], 'dev': []}
    origins = {'train': [], 'dev': []}
    conversions = {'train': {}, 'dev': {}}
    for language, eligible in candidates.items():
        dev_stats, train_stats = conversion_stats(), conversion_stats()
        for _, ordinal, raw in eligible[:EXT_DEV_PER_LANGUAGE]:
            row = convert(raw, language, 'dev', ordinal, mapping, outside, dev_stats)
            if row is not None:
                datasets['dev'].append(row)
                origins['dev'].append('gretel_ext_dev')
        rest = eligible[EXT_DEV_PER_LANGUAGE:]
        pool = [record for record in rest if record[0] not in reserved_hashes]
        reservation[language]['additional_reserved_text_duplicates_dropped'] = len(rest) - len(pool)
        reservation[language]['pool_before_cap'] = len(pool)
        if language == 'English':
            pool = pool[:ENGLISH_CAP]
        reservation[language]['pool_selected_before_conversion'] = len(pool)
        for _, ordinal, raw in pool:
            row = convert(raw, language, 'train', ordinal, mapping, outside, train_stats)
            if row is not None:
                datasets['train'].append(row)
                origins['train'].append('gretel_train_pool')
        reservation[language]['dev_rows_written'] = sum(1 for r in datasets['dev'] if r['language'] == LANGUAGES[language])
        reservation[language]['pool_rows_written'] = sum(1 for r in datasets['train'] if r['language'] == LANGUAGES[language])
        conversions['train'][language] = train_stats
        conversions['dev'][language] = dev_stats
    with V5.open(encoding='utf-8') as stream:
        v5 = [json.loads(line) for line in stream]
    require(len(v5) >= V5_ROWS, 'train_v_five_too_small')
    require(len({row['case_id'] for row in v5}) == len(v5), 'train_v_five_duplicate_id')
    selected_v5 = sorted(v5, key=lambda row: (text_hash(row['case_id']), row['case_id']))[:V5_ROWS]
    # Never resample the requested first 16,000 subset; fail if it contaminates TEST/EXT-DEV.
    require(not {text_hash(row['text']) for row in selected_v5} & (test_texts | reserved_hashes), 'internal_subset_external_overlap')
    datasets['train'].extend(selected_v5)
    origins['train'].extend(['train_v5_subset'] * len(selected_v5))
    synthetic, synthetic_stats = build_synthetic()
    require(len(synthetic) == SYNTHETIC_ROWS, 'synthetic_count')
    require(not {text_hash(row['text']) for row in synthetic} & (test_texts | reserved_hashes), 'synthetic_external_overlap')
    datasets['train'].extend(synthetic)
    origins['train'].extend(['targeted_synthetic'] * len(synthetic))
    for split in datasets:
        paired = list(zip(datasets[split], origins[split]))
        random.Random(SEED + (0 if split == 'train' else 1)).shuffle(paired)
        datasets[split] = [row for row, _ in paired]
        origins[split] = [origin for _, origin in paired]
    rd.check_disjoint(datasets['train'], datasets['dev'])
    require(not {text_hash(row['text']) for rows in datasets.values() for row in rows} & test_texts, 'output_test_overlap')
    metadata = {'inputs': inputs, 'code_inputs': code, 'mapping': mapping, 'out_of_scope_labels': sorted(outside),
        'reservation': reservation, 'conversion': conversions, 'synthetic_composition': synthetic_stats,
        'train_v5_selection': {'input_rows': len(v5), 'selected_rows': len(selected_v5),
            'ordered_case_id_hashes_sha256': hashlib.sha256('\n'.join(text_hash(r['case_id']) for r in selected_v5).encode()).hexdigest()},
        'test_deduplication': {'rows_hashed': test_rows, 'unique_text_hashes': len(test_texts),
                               'columns_read': ['generated_text'], 'annotations_read': False}}
    return datasets, origins, metadata


def summarize(rows, origins, split):
    ids, signatures = set(), {}
    counters = {key: Counter() for key in ('language', 'label', 'label_rows', 'family')}
    by_source, by_language = {}, {}
    clean, digest, size = 0, hashlib.sha256(), 0
    for row, origin in zip(rows, origins):
        rd._check_row(row, split)
        require(row['case_id'] not in ids, 'duplicate_case_id')
        ids.add(row['case_id'])
        key = text_hash(row['text'])
        signature = (row['language'], tuple((s['start'], s['end'], s['label']) for s in row['gold']))
        require(key not in signatures or signatures[key] == signature, 'conflicting_duplicate_text')
        signatures[key] = signature
        encoded = encode(row).encode('utf-8')
        require(len(encoded) <= rd.MAX_LINE_BYTES, 'region_line_too_long')
        digest.update(encoded)
        size += len(encoded)
        labels = Counter(s['label'] for s in row['gold'])
        counters['language'][row['language']] += 1
        counters['label'].update(labels)
        counters['label_rows'].update(labels.keys())
        counters['family'][row['family']] += 1
        clean += not row['gold']
        for buckets, name in ((by_source, origin), (by_language, row['language'])):
            summary = buckets.setdefault(name, {'rows': 0, 'clean_rows': 0, 'languages': Counter(),
                'label_spans': Counter(), 'label_rows': Counter()})
            summary['rows'] += 1
            summary['clean_rows'] += not row['gold']
            summary['languages'][row['language']] += 1
            summary['label_spans'].update(labels)
            summary['label_rows'].update(labels.keys())
    require(size <= rd.MAX_FILE_BYTES, 'region_file_too_large')
    return {'path': str(OUTPUTS[split].relative_to(ROOT)), 'sha256': digest.hexdigest(), 'bytes': size,
        'rows': len(rows), 'clean_rows': clean, 'clean_share': clean / len(rows), 'unique_texts': len(signatures),
        'counts': counters, 'sources': by_source, 'per_language': by_language}


def make_manifest(datasets, origins, metadata):
    outputs = {split: summarize(rows, origins[split], split) for split, rows in datasets.items()}
    return {'manifest_version': 6, 'seed': SEED, 'schema': rd.SCHEMA_VERSION, 'policy': 'privacy-policy-v1',
        'synthetic_only': True, 'dataset': {'revision': REVISION, 'license': 'Apache-2.0', 'llm_generated_synthetic': True},
        'outputs': outputs, **metadata,
        'selection': {'external_dev': 'Drop all five TEST text duplicates, SHA256(UTF8 generated_text) hex ascending, first 200 rows per source language; ties use source ordinal.',
            'gretel_pool': 'Exclude the entire global reserved text set; English first 8000 remaining rows in the same hash order, all other eligible rows.',
            'train_v5': 'First 16000 rows ordered by SHA256(UTF8 case_id) hex; preserve all six original fields.',
            'invalid_rows': 'Validate offsets for every source annotation; merge overlapping mapped-same-label gold; drop cross-mapped-label or mapped/OUT overlaps; no refill of reserved or capped rows.',
            'shuffle': 'Independent deterministic Random(seed) train and Random(seed+1) dev permutations.'},
        'verification': {'canonical_bytes_replay': True, 'input_hashes_verified': True, 'schema_all_rows': True,
            'train_dev_text_disjoint': True, 'outputs_test_text_disjoint': True, 'ext_dev_never_trained': True,
            'no_test_annotation_read': True, 'row_ids_unique': True, 'conflicting_duplicate_text_rejected': True},
        'trainer_compatibility': {'max_rows_in_existing_loader': rd.MAX_ROWS,
            'full_train_within_row_limit': outputs['train']['rows'] <= rd.MAX_ROWS,
            'region_max_row_cli_flags_supported': False,
            'pilot_method': 'Materialize first 400 train / 200 dev shuffled rows into ignored subset files; unchanged region trainer without max-row CLI flags.',
            'full_training_requires': 'An authorized trainer/loader update outside Unit B if full_train_within_row_limit is false.'}}


def generate():
    targets = [*OUTPUTS.values(), MANIFEST]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise FileExistsError('output_exists')
    datasets, origins, metadata = build_datasets()
    manifest = make_manifest(datasets, origins, metadata)
    created = []
    try:
        for split, path in OUTPUTS.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8', newline='\n') as stream:
                created.append(path)
                for row in datasets[split]:
                    stream.write(encode(row))
            require(sha256(path) == manifest['outputs'][split]['sha256'], 'write_hash_mismatch')
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with MANIFEST.open('x', encoding='utf-8', newline='\n') as stream:
            created.append(MANIFEST)
            stream.write(encode(manifest))
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return manifest


def verify():
    require(MANIFEST.is_file() and all(path.is_file() for path in OUTPUTS.values()), 'missing_output')
    stored = json.loads(MANIFEST.read_text(encoding='utf-8'))
    require(isinstance(stored, dict), 'manifest_schema')
    datasets, origins, metadata = build_datasets()
    for split, path in OUTPUTS.items():
        require(sha256(path) == stored['outputs'][split]['sha256'], 'data_hash_mismatch')
        with path.open(encoding='utf-8', newline='') as stream:
            count = 0
            for index, line in enumerate(stream):
                require(index < len(datasets[split]), 'excess_rows')
                row = json.loads(line)
                rd._check_row(row, split)
                require(line == encode(row), 'jsonl_canonical_encoding')
                require(row == datasets[split][index], 'whole_value_replay_mismatch')
                count += 1
        require(count == len(datasets[split]), 'row_count')
        # Exercise the exact existing loader when its count bound permits it.
        if len(datasets[split]) <= rd.MAX_ROWS:
            loaded, _ = rd.load_region_file(path, split, MANIFEST)
            require(len(loaded) == count, 'loader_row_count')
    recomputed = make_manifest(datasets, origins, metadata)
    # Canonical JSON normalizes Counter objects to the same representation read from disk.
    require(stored == json.loads(encode(recomputed)), 'manifest_aggregate_mismatch')
    return recomputed
