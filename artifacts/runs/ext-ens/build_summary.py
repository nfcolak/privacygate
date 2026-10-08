#!/usr/bin/env python3
"""Value-free summary.md for ext-ens from committed aggregate metrics (counts and rates only)."""
import json
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1]
ENS, V6, S1 = RUNS / 'ext-ens', RUNS / 'ext-v6', RUNS / 'ext-step1'
ARMS = ('v5 + step-1', 'v6 + chosen', 'v5v6 chosen')


def load(path):
    return json.loads(Path(path).read_text())


def arms(name):
    """Return {arm label: gretel/second-style report} for a set directory name."""
    ens = load(ENS / name / 'metrics.json')['arms']['v5v6-chosen']
    if name == 'gretel-test':
        v5 = load(S1 / name / 'metrics.json')
    else:
        v5 = load(V6 / name / 'metrics.json')['arms']['v5-step1']
    v6 = load(V6 / name / 'metrics.json')['arms']['v6-chosen']
    return dict(zip(ARMS, (v5, v6, ens)))


def cell(r):
    return '{:.2f} / {:.2f} / {:,}'.format(r['coverage_pct'], r['excess_pct'], r['rows_exposed'])


def v7_arms():
    ens = load(ENS / 'v7-dev' / 'metrics.json')['arms']['v5v6-chosen']
    v5 = load(S1 / 'v7-dev' / 'metrics.json')
    v6 = load(V6 / 'v7-dev' / 'metrics.json')['arms']['v6-chosen']
    return dict(zip(ARMS, (v5, v6, ens)))


def main():
    sets = [('Gretel TEST (4,696 rows; in-distribution for v6, not a selection set)', 'gretel-test'),
            ('Nemotron-PII (5,000 docs)', 'second-nemotron'), ('ai4privacy (5 x 1,000 rows)', 'second-ai4privacy')]
    data = {name: arms(name) for _, name in sets}
    grid = load(ENS / 'dev-grid.json')
    chosen = grid['chosen']
    L = ['# ext-ens summary: v5 + v6 combination (`ensemble_pair`) on the independent sets', '',
         'Value-free: counts, rates and shapes only. The v5v6 arm was measured once per set after the choice was frozen and committed (`dev-grid.{json,md}`, commit 98e4c07). '
         'Coverage = personal letters/digits covered %; excess = masked chars outside all source annotations / non-annotated chars; rows = rows with exposed letters/digits. '
         'v5 + step-1 and v6 + chosen are the earlier measurements from `ext-step1/` and `ext-v6/` (not rerun).', '',
         'Chosen on Gretel EXT-DEV and v7 dev only: `ensemble_pair` = {}, name_threshold {}, name_propagation_ext {}.'.format(
             chosen['options']['ensemble_pair'], chosen['options']['name_threshold'],
             'on' if chosen['options']['name_propagation_ext'] else 'off'),
         'Rule: fewest exposed letters/digits over EXT-DEV + v7 dev, v7 clean rows masked <= 21/300, EXT-DEV excess <= v5 + step-1 EXT-DEV excess + 1.0 ({:.2f}).'.format(grid['excess_cap_pct']),
         'EXT-DEV (coverage / excess / rows exposed): v5 + step-1 {:.2f} / {:.2f} / {}; v5v6 chosen {:.2f} / {:.2f} / {}. '
         'Union with name_threshold 0.1 won; propagation tied on exposed (1,350) and cost +0.07 point excess, so the rule picked it off. '
         'Every mean-mode setting was eligible but exposed 4,727 or more.'.format(
             grid['v5_step1_ext_dev']['coverage_pct'], grid['v5_step1_ext_dev']['excess_pct'], grid['v5_step1_ext_dev']['rows_exposed'],
             chosen['ext_dev']['coverage_pct'], chosen['ext_dev']['excess_pct'], chosen['ext_dev']['rows_exposed']), '',
         '| set | ' + ' | '.join(ARMS) + ' |', '|---|---|---|---|']
    for title, name in sets:
        L.append('| {} | {} |'.format(title, ' | '.join(cell(data[name][a]) for a in ARMS)))
    L += ['', 'Cells are coverage % / excess % / rows exposed.', '']
    v7 = v7_arms()
    L += ['v7 development (not blind):', '', '| | ' + ' | '.join(ARMS) + ' |', '|---|---|---|---|',
          '| clean rows masked | ' + ' | '.join('{}/{}'.format(v7[a]['overall']['clean_controls']['masked_rows'], v7[a]['overall']['clean_controls']['rows']) for a in ARMS) + ' |',
          '| exposed letters/digits | ' + ' | '.join('{:,}'.format(v7[a]['overall']['leaked_gold_alnum_chars']) for a in ARMS) + ' |',
          '| gold alnum coverage % | ' + ' | '.join('{:.2f}'.format(100 * v7[a]['overall']['covered_gold_alnum_chars'] / v7[a]['overall']['gold_alnum_chars']) for a in ARMS) + ' |', '']
    L += ['## Read this first', '',
          '1. On the two independent sets v5v6 beats both single models on coverage: Nemotron 98.99 vs 96.91 (v5 + step-1) and 92.03 (v6); ai4privacy 93.75 vs 86.55 and 88.77. Rows exposed drop to 246 (from 545) and 568 (from 1,006).',
          '2. Excess is the v5 level, not the v6 level: Nemotron 1.41 (v5 + step-1 1.37, v6 0.28), ai4privacy 2.84 (2.60, 1.60). Out-of-scope masking stays at the v5 level or above (Nemotron 48.0%, ai4privacy 54.5%; v6 6.1% and 30.2%). The union takes v6 recall and keeps v5 over-masking.',
          '3. v7 dev: clean rows masked 19/300 (unchanged), exposed letters/digits 306 (v5 + step-1 334, v6 4,747); the union restores v5-level v7 behaviour that v6 lost.',
          '4. Gretel TEST is in-distribution for v6 and was not used for any choice. v5v6 97.63 / 5.06 there; its excess is v5-like (4.83), well above v6 alone (1.32).',
          '5. Mean mode (probability average) was eligible but weak on dev (exposed 4,727 or more, mostly v7), so the union was chosen on dev, not on the independent sets.', '']
    L += ['## Per label (coverage % / exposed letters+digits)', '']
    for title, name in sets:
        labels = sorted(data[name][ARMS[2]]['per_label'])
        L += [title, '', '| label | gold alnum | ' + ' | '.join(ARMS) + ' |', '|---|---:|---|---|---|']
        for label in labels:
            rows = [data[name][a]['per_label'][label] for a in ARMS]
            if not rows[2].get('gold_alnum_chars'):
                continue
            L.append('| {} | {:,} | {} |'.format(label, rows[2]['gold_alnum_chars'], ' | '.join(
                '{:.1f} / {:,}'.format(r['coverage_pct'], r.get('exposed_gold_alnum_chars', 0)) for r in rows)))
        L.append('')
    L += ['## Per language (coverage % / excess % / rows exposed)', '']
    for title, name in sets:
        langs = sorted(data[name][ARMS[2]]['per_language'])
        L += [title, '', '| language | ' + ' | '.join(ARMS) + ' |', '|---|---|---|---|']
        for lang in langs:
            L.append('| {} | {} |'.format(lang, ' | '.join(cell(data[name][a]['per_language'][lang]) for a in ARMS)))
        L.append('')
    L += ['## Out-of-scope masking (alnum chars annotated out of scope and not in-scope gold; not scored as recall or excess)', '',
          '| set | out-of-scope alnum chars | ' + ' | '.join(ARMS) + ' |', '|---|---:|---|---|---|']
    for title, name in sets[1:]:
        o = [data[name][a]['out_of_scope'] for a in ARMS]
        L.append('| {} | {:,} | {} |'.format(title.split(' (')[0], o[2]['alnum_chars'], ' | '.join('{:.1f}% masked'.format(x['masked_pct']) for x in o)))
    L.append('')
    for title, name in sets[1:]:
        per = data[name][ARMS[2]]['out_of_scope']['per_label']
        top = sorted(per, key=lambda k: -per[k]['alnum_chars'])[:6]
        L.append('{} largest out-of-scope labels (masked % for {}): '.format(title.split(' (')[0], ' | '.join(ARMS)) + '; '.join(
            '{} ({:,} chars) '.format(k, per[k]['alnum_chars']) + ' | '.join(
                '{:.1f}'.format(data[name][a]['out_of_scope']['per_label'][k]['masked_pct']) for a in ARMS) for k in top))
    L += ['', '## Top miss and excess shapes of the v5v6 arm (`shapes.py`, value-free)', '']
    for title, name in sets:
        path = ENS / name / 'shapes.json'
        if not path.is_file():
            continue
        s = load(path)
        L.append(title)
        L.append('- misses (exposed alnum): ' + '; '.join('{} {} ({} pieces, {:,} chars)'.format(
            m['label'], m['shape'], m['pieces'], m['alnum_chars']) for m in s['top_miss_shapes'][:8]))
        L.append('- excess (masked alnum outside annotations): ' + '; '.join('{} on {} ({} pieces, {:,} chars)'.format(
            m['label'], m['shape'], m['pieces'], m['alnum_chars']) for m in s['top_excess_shapes'][:6]))
        L.append('')
    L += ['## Files', '', '`dev-grid.{json,md}`, `arms.json`, `gretel-test/` (metrics, receipts, shapes), `second-nemotron/` and `second-ai4privacy/` (mapping.json copied from ext-v6, metrics.json, shapes.json), `v7-dev/metrics.json`, `shapes.py`, `build_summary.py`.',
          'Code: `ensemble_pair` in `privacygate/pipeline.py` (`combine_pair`, `ensemble_pair_peer`); `hybrid.py` is unchanged (the probability-cache key binds its sha256). `evaluate_external.py`: model name `v5v6`, `--pair-grid`.', '']
    (ENS / 'summary.md').write_text('\n'.join(L))
    print('SUMMARY_WRITTEN')


if __name__ == '__main__':
    main()
