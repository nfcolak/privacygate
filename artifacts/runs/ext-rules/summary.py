#!/usr/bin/env python3
"""Build artifacts/runs/ext-rules/summary.md from committed metrics (value-free counts only)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / 'artifacts/runs'
ID = ('IDCARDNUM', 'DRIVERLICENSENUM', 'PASSPORTNUM', 'SOCIALNUM', 'TAXNUM', 'PERSONALREF')
SETS = (('gretel-test', 'Gretel TEST (4,696 rows; in-distribution for v6, never used to choose)'),
        ('second-nemotron', 'Nemotron-PII (5,000 docs)'), ('second-ai4privacy', 'ai4privacy (5 x 1,000 rows)'))
NEW = ('v5-step1-rules', 'v6-chosen-rules')


def load(path):
    return json.loads((RUNS / path).read_text())


def baselines(key):
    """(v5 + step-1, v6 + chosen) report dicts from the earlier rounds."""
    if key == 'gretel-test':
        return load('ext-step1/gretel-test/metrics.json'), load('ext-v6/gretel-test/metrics.json')['arms']['v6-chosen']
    arms = load('ext-v6/{}/metrics.json'.format(key))['arms']
    return arms['v5-step1'], arms['v6-chosen']


def cell(r):
    return '{:.2f} / {:.2f} / {:,}'.format(r['coverage_pct'], r['excess_pct'], r['rows_exposed'])


def exposed(r, label):
    x = r['per_label'].get(label, {})
    return x.get('exposed_gold_alnum_chars', 0), x.get('gold_alnum_chars', 0), x.get('coverage_pct')


def main():
    new = {k: load('ext-rules/{}/metrics.json'.format(k))['arms'] for k, _ in SETS}
    out = ['# ext-rules summary: cue-free ID-code detectors on independent text', '',
           'Value-free: counts, rates, shapes. Each rules arm measured once per set; baselines are the ext-v6 / ext-step1 measurements (same samples, mappings, metrics, `evaluation/evaluate_external.py` unchanged).',
           'Cells are coverage % / excess % / rows exposed. Gretel TEST is reported only: train-v6 holds Gretel train rows, so it never selects anything.', '',
           'Rules enabled (chosen on Gretel EXT-DEV + v7 dev, `dev.md`): `it_codice_fiscale`, `fr_nir` (checksum-validated, cue-free). Registered but off (no dev evidence or failed gate): `es_dni_nie`, `de_steuer_idnr`, `gb_nino`, `ch_ahv`, `us_ssn` (v7 clean rows 23/300), `cued_documents`, `cued_social_tax`, `cued_personalref`.', '',
           '| set | v5 + step-1 | v5 + step-1 + rules | v6 + chosen | v6 + chosen + rules |', '|---|---|---|---|---|']
    for key, title in SETS:
        b5, b6 = baselines(key)
        out.append('| {} | {} | {} | {} | {} |'.format(title, cell(b5), cell(new[key]['v5-step1-rules']), cell(b6), cell(new[key]['v6-chosen-rules'])))
    v7 = load('ext-rules/v7-dev/metrics.json')['arms']
    b5v7 = load('ext-step1/v7-dev/metrics.json')
    b6v7 = load('ext-v6/v7-dev/metrics.json')['arms']['v6-chosen']

    def v7cell(r):
        o = r['overall']
        return '{}/300 clean rows masked, {:,} exposed alnum'.format(o['clean_controls']['masked_rows'], o['leaked_gold_alnum_chars'])
    out.append('| v7 dev (not blind) | {} | {} | {} | {} |'.format(v7cell(b5v7), v7cell(v7['v5-step1-rules']), v7cell(b6v7), v7cell(v7['v6-chosen-rules'])))
    out += ['', '## Read this first', '',
            '1. The rules arm changes almost nothing on the independent sets: Nemotron and ai4privacy are identical to the baselines at every reported digit (coverage, excess, rows exposed, per label, per language, out-of-scope). Neither set holds checksum-valid codice fiscale or NIR values in the sampled rows; ES/DE/GB/CH detectors that would fire there did not qualify on dev (no dev evidence), so they are off.',
            '2. Gretel TEST moves slightly (v5 + step-1 +0.02 point coverage, v6 + chosen +0.03, rows exposed 805 to 805 and 328 to 326, excess unchanged), almost all in SOCIALNUM (French NIR) and Spanish/German text. Gretel TEST is in-distribution for v6 and was not used for any choice.',
            '3. v7 dev is unchanged (19/300 clean rows masked; 334 and 4,747 exposed alnum), as at selection.',
            '4. The big remaining ID gaps on independent text (ai4privacy IDCARDNUM / DRIVERLICENSENUM / PASSPORTNUM / TAXNUM, Nemotron PERSONALREF) are uppercase letter-prefixed codes without checksum; the cue-bound shapes for them showed no dev gain, so a model or cue-vocabulary change would be needed, not a format rule.', '',
            '## Change on the ID labels (exposed alnum chars / gold alnum chars; coverage %)', '']
    for key, title in SETS:
        b5, b6 = baselines(key)
        out += ['### ' + title, '', '| label | v5 + step-1 | + rules | v6 + chosen | + rules |', '|---|---|---|---|---|']
        for label in ID:
            cells = []
            for r in (b5, new[key]['v5-step1-rules'], b6, new[key]['v6-chosen-rules']):
                e, g, c = exposed(r, label)
                cells.append('{:,} / {:,}; {}'.format(e, g, 'n/a' if c is None else '{:.2f}'.format(c)))
            out.append('| {} | {} |'.format(label, ' | '.join(cells)))
        out.append('')
    out += ['## Per language (coverage % / excess %)', '']
    for key, title in SETS:
        b5, b6 = baselines(key)
        out += ['### ' + title, '', '| language | v5 + step-1 | + rules | v6 + chosen | + rules |', '|---|---|---|---|---|']
        for lang in sorted(b5['per_language']):
            out.append('| {} | {} |'.format(lang, ' | '.join('{:.2f} / {:.2f}'.format(r['per_language'][lang]['coverage_pct'], r['per_language'][lang]['excess_pct'])
                                                          for r in (b5, new[key]['v5-step1-rules'], b6, new[key]['v6-chosen-rules']))))
        out.append('')
    out += ['## Out-of-scope masking (% of out-of-scope alnum chars masked)', '', '| set | v5 + step-1 | + rules | v6 + chosen | + rules |', '|---|---|---|---|---|']
    for key, title in SETS[1:]:
        b5, b6 = baselines(key)
        out.append('| {} | {} |'.format(title, ' | '.join('{:.2f}'.format(r['out_of_scope']['masked_pct']) for r in (b5, new[key]['v5-step1-rules'], b6, new[key]['v6-chosen-rules']))))
    out += ['', '## Top remaining miss shapes (rules arms; alnum chars exposed, from `shapes-*.json`)', '']
    for key, title in SETS:
        for arm in NEW:
            path = RUNS / 'ext-rules' / key / ('shapes-' + arm + '.json')
            if not path.exists():
                continue
            s = json.loads(path.read_text())
            out.append('- {} / {}: '.format(title.split(' (')[0], arm) + '; '.join('{} {} ({} pieces, {:,} chars)'.format(t['label'], t['shape'], t['pieces'], t['alnum_chars']) for t in s['top_miss_shapes'][:6]))
    out.append('')
    (RUNS / 'ext-rules/summary.md').write_text('\n'.join(out))
    print('summary written', len(out))


if __name__ == '__main__':
    main()
