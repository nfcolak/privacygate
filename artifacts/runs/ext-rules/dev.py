#!/usr/bin/env python3
"""Value-free dev driver for ext-rules: Gretel EXT-DEV + v7 dev only, v5 + step-1 options.

Modes: prep (probability cache only), shapes (exposed ID-label shapes, no values),
select (per-detector ablation -> dev.json / dev.md). Imports evaluation/evaluate_external.py unchanged.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation import evaluate_external as ee
from evaluation import evaluate_pipeline as runner
from evaluation import masking_eval as evm
from evaluation.checks.verify_frozen import V7_DATA
from privacygate.rules import structured
from privacygate.masking_metrics import interval_union

ARM = {'name': 'v5-step1', 'model': 'v5',
       'options': {'ensemble': False, 'name_propagation_ext': True, 'name_threshold': 0.1}}
ID_LABELS = ('IDCARDNUM', 'DRIVERLICENSENUM', 'PASSPORTNUM', 'SOCIALNUM', 'TAXNUM', 'PERSONALREF')


def shape(value):
    out = []
    for ch in value:
        c = '9' if ch.isdigit() else ('A' if ch.isalpha() and ch.isupper() else 'a' if ch.isalpha() else ch)
        if not out or out[-1][0] != c or c not in '9Aa':
            out.append([c, 1])
        else:
            out[-1][1] += 1
    return ''.join(c if c not in '9Aa' else c + str(n) for c, n in out)


def load(args):
    dev, _ = ee.load_data('ext-dev')
    v7, binding = runner.load_v7_dataset(V7_DATA)
    v7a = [dict(text=r['text'], text_sha256=ee.text_sha(r['text'])) for r in v7]
    return dev, v7, v7a


def make_cache(args):
    return ee.ProbabilityCache(ee.model_paths(ARM['model'], ARM['options']), Path(args.cache))


def run_dev(cache, dev, v7, v7a, collect=False):
    agg = ee.Aggregate()
    exposed_shapes = Counter()
    for row in dev:
        result = cache.predict(row, ARM['model'], ARM['options'])
        agg.add(row, result)
        if collect:
            n = len(row['text'])
            mask = interval_union([(s['start'], s['end']) for s in result['entities']], n)
            for g in row['gold']:
                if g['label'] in ID_LABELS:
                    covered = all(any(a <= i < b for a, b in mask) for i in range(g['start'], g['end']))
                    if not covered:
                        exposed_shapes[('gretel', g['label'], shape(row['text'][g['start']:g['end']]))] += 1
    rep = agg.report()
    v7agg = evm.EvaluationAggregate()
    for row, ad in zip(v7, v7a):
        result = cache.predict(ad, ARM['model'], ARM['options'])
        v7agg.add(row, result)
        if collect:
            n = len(row['text'])
            mask = interval_union([(s['start'], s['end']) for s in result['entities']], n)
            for g in row['gold']:
                if g['label'] in ID_LABELS:
                    covered = all(any(a <= i < b for a, b in mask) for i in range(g['start'], g['end']))
                    if not covered:
                        exposed_shapes[('v7', g['label'], shape(row['text'][g['start']:g['end']]))] += 1
    v7rep = v7agg.report()
    o = v7rep['overall']
    out = {
        'gretel_dev': {'coverage_pct': rep['coverage_pct'], 'excess_pct': rep['excess_pct'],
                       'exposed_alnum': rep['exposed_gold_alnum_chars'], 'rows_exposed': rep['rows_exposed'],
                       'per_label_exposed_alnum': {k: v.get('exposed_gold_alnum_chars', 0) for k, v in rep['per_label'].items()
                                                   if k in ID_LABELS and v.get('gold_alnum_chars')}},
        'v7_dev': {'clean_rows_masked': o['clean_controls']['masked_rows'], 'clean_rows': o['clean_controls']['rows'],
                   'exposed_alnum': o['leaked_gold_alnum_chars'],
                   'per_label_exposed_alnum': {k: v['leaked_gold_alnum_chars'] for k, v in v7rep['per_gold_label'].items()
                                               if k in ID_LABELS}},
    }
    out['exposed_total'] = out['gretel_dev']['exposed_alnum'] + out['v7_dev']['exposed_alnum']
    return out, exposed_shapes


GATE = {'clean_rows_max': 21, 'excess_rise_max_pct_points': 0.3}


def merge(args):
    runs, arm = {}, None
    for path in args.inputs:
        data = json.loads(Path(path).read_text())
        arm = data['arm']
        for tag, run in data['runs'].items():
            if tag == 'off' and 'off' in runs:
                assert runs['off']['exposed_total'] == run['exposed_total'] and runs['off']['v7_dev'] == run['v7_dev']
                continue
            runs[tag] = run
    off = runs['off']
    verdicts = {}
    for tag, run in runs.items():
        if tag in ('off', 'all', 'chosen'):
            continue
        lowers = run['exposed_total'] < off['exposed_total']
        clean_ok = run['v7_dev']['clean_rows_masked'] <= GATE['clean_rows_max']
        excess_rise = run['gretel_dev']['excess_pct'] - off['gretel_dev']['excess_pct']
        excess_ok = excess_rise <= GATE['excess_rise_max_pct_points']
        verdicts[tag] = {'lowers_exposed_by': off['exposed_total'] - run['exposed_total'], 'clean_rows_masked': run['v7_dev']['clean_rows_masked'],
                         'excess_rise_points': excess_rise, 'keep': bool(lowers and clean_ok and excess_ok),
                         'reason': ('kept' if lowers and clean_ok and excess_ok else
                                    'clean rows above 21/300' if not clean_ok else
                                    'excess rise above 0.3 point' if not excess_ok else 'no exposed-character reduction on dev')}
    chosen = sorted(k for k, v in verdicts.items() if v['keep'])
    assert frozenset(chosen) == structured.DEFAULT_ENABLED, (chosen, sorted(structured.DEFAULT_ENABLED))
    out = {'arm': arm, 'gate': GATE, 'runs': runs, 'verdicts': verdicts, 'chosen': chosen,
           'data': 'Gretel EXT-DEV (1,000 rows) + v7 development (600 rows); model v5 + step-1 options; probabilities cached, rules replayed'}
    Path(ROOT / 'artifacts/runs/ext-rules/dev.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    lines = ['# ext-rules dev selection (Gretel EXT-DEV + v7 dev only)', '',
             'Model arm: v5 + step-1 options (name_threshold 0.1, name_propagation_ext on). Each detector is switched on alone against all-rules-off; value-free counts.',
             'Gate: keep only if exposed letters/digits (EXT-DEV + v7 dev) go down, v7 clean rows masked <= 21/300, EXT-DEV excess rises by <= 0.3 point.', '',
             '| run | exposed alnum (EXT-DEV + v7) | EXT-DEV coverage % | EXT-DEV excess % | v7 clean rows masked | decision |', '|---|---:|---:|---:|---:|---|']
    for tag, run in runs.items():
        decision = ('baseline' if tag == 'off' else verdicts[tag]['reason'] if tag in verdicts else 'combination of kept detectors' if tag == 'chosen' else 'all registered (reference)')
        lines.append('| {} | {} | {:.4f} | {:.4f} | {}/300 | {} |'.format(tag, run['exposed_total'], run['gretel_dev']['coverage_pct'],
                     run['gretel_dev']['excess_pct'], run['v7_dev']['clean_rows_masked'], decision))
    lines += ['', 'Chosen: ' + ', '.join(chosen) + '.',
              'Detectors with no dev effect are not kept (EXT-DEV has no valid-checksum ES/DE/GB/CH values and v7 has no ID exposure under the official alnum metric); they stay registered and unit-tested in check_structured.py.', '']
    (ROOT / 'artifacts/runs/ext-rules/dev.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('prep', 'shapes', 'select', 'cues', 'merge'))
    p.add_argument('--inputs', nargs='*', default=[])
    p.add_argument('--cache', default=str(ROOT / '.cache/ext-step1-probabilities'))
    p.add_argument('--prep-models', default='v5,v6')
    p.add_argument('--out', type=Path)
    p.add_argument('--only', default=None, help='comma list of detector names (and/or all) for select; default: every detector singly, then all')
    args = p.parse_args()
    assert os.environ.get('HF_HUB_OFFLINE') == '1' and os.environ.get('HF_HOME')
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    if args.mode == 'merge':
        merge(args)
        return
    dev, v7, v7a = load(args)
    if args.mode == 'prep':
        for model in args.prep_models.split(','):
            c = ee.ProbabilityCache(ee.model_paths(model, {}), Path(args.cache))
            c.prepare(dev)
            c.prepare(v7a)
        return
    cache = make_cache(args)
    cache.prepare(dev)
    cache.prepare(v7a)
    names = tuple(structured.ID_DETECTORS)
    if args.mode == 'shapes':
        structured.ENABLED = frozenset(args.only.split(',')) if args.only else frozenset()
        result, shapes = run_dev(cache, dev, v7, v7a, collect=True)
        print(json.dumps({k: result[k] for k in ('gretel_dev', 'v7_dev', 'exposed_total')}, sort_keys=True))
        by = Counter()
        for (src, label, sh), n in shapes.items():
            by[(src, label, sh)] += n
        for (src, label, sh), n in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1], -kv[1])):
            print(src, label, sh.replace('\n', '\\n'), n)
        return
    if args.mode == 'cues':
        # Which generic cue words (fixed vocabulary only) precede exposed ID-label gold spans.
        structured.ENABLED = frozenset()
        vocab = set('''passport passeport passaporto pasaporte reisepass pass ausweis personalausweis identity identification
            id card carte carta tarjeta identité identità licence license driver driving permis permit conduire patente
            conducir führerschein social security sécurité sociale sozialversicherung seguridad previdenza ssn nir nss
            tax steuer fiscal fiscale codice impôt number nummer numéro numero número no nr patient member membership
            customer client kunde employee mitarbeiter reference ref health insurance plan medical record account
            beneficiary policy versicherung assuré assicurazione seguro'''.split())
        found = Counter()
        for src, rows in (('gretel', dev), ('v7', v7)):
            for row in rows:
                result = (cache.predict(row, ARM['model'], ARM['options']) if src == 'gretel'
                          else cache.predict(dict(text=row['text'], text_sha256=ee.text_sha(row['text'])), ARM['model'], ARM['options']))
                n = len(row['text'])
                mask = interval_union([(s['start'], s['end']) for s in result['entities']], n)
                for g in row['gold']:
                    if g['label'] not in ID_LABELS:
                        continue
                    if all(any(a <= i < b for a, b in mask) for i in range(g['start'], g['end'])):
                        continue
                    before = row['text'][max(0, g['start'] - 70):g['start']]
                    line = before.split('\n')[-1]
                    words = tuple(w for w in re.findall(r'[^\W\d_]+', line.lower()) if w in vocab)[-3:]
                    gap = re.sub(r'[^\W\d_]+', 'w', line[-30:])
                    found[(src, g['label'], ' '.join(words), 'gap=' + shape(line[-12:]))] += 1
        for key, n in sorted(found.items()):
            print(*key, n)
        return
    runs = {}
    plan = [('off', frozenset())] + [(n, frozenset([n])) for n in names] + [('all', frozenset(names))]
    if args.only:
        plan = [('off', frozenset())] + [(n, frozenset([n])) for n in args.only.split(',') if n != 'all']
        if 'all' in args.only.split(','):
            plan.append(('all', frozenset(names)))
        if 'chosen' in args.only.split(','):
            plan = [('off', frozenset()), ('chosen', structured.DEFAULT_ENABLED)]
    for tag, enabled in plan:
        structured.ENABLED = enabled
        result, _ = run_dev(cache, dev, v7, v7a)
        runs[tag] = {'enabled': sorted(enabled), **result}
        print('RUN', tag, json.dumps({k: result[k] for k in ('exposed_total',)}),
              result['gretel_dev']['excess_pct'], result['v7_dev']['clean_rows_masked'], flush=True)
    args.out.write_text(json.dumps({'arm': ARM, 'runs': runs}, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
