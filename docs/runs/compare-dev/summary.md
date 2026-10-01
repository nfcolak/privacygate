# Hybrid comparison on dev data

Micro dev rows: 3796 (excluded for broken wordpiece boundary: 39); challenge dev rows: 1200. mBERT = full-1. rules_first_thr uses mBERT confidence >= 0.5 (tuned on dev).

| arm | Micro strict F1 | Micro EMAIL F1 | Micro char P | Micro char R | IBAN recall strict | IBAN recall any-label | decoy FP | clean FP | overmask chars |
|---|---|---|---|---|---|---|---|---|---|
| regex | 0.128 | 0.964 | 0.996 | 0.108 | 1.000 | 1.000 | 0.000 | 0.000 | 0.0000 |
| mbert | 0.949 | 0.999 | 0.996 | 0.998 | 0.000 | 0.774 | 1.000 | 0.432 | 0.1244 |
| union | 0.948 | 0.997 | 0.996 | 0.998 | 1.000 | 1.000 | 1.000 | 0.432 | 0.1244 |
| rules_first | 0.946 | 0.967 | 0.996 | 0.997 | 1.000 | 1.000 | 1.000 | 0.432 | 0.1244 |
| rules_first_thr | 0.946 | 0.967 | 0.996 | 0.995 | 1.000 | 1.000 | 1.000 | 0.430 | 0.1232 |

Threshold sweep (rules_first, dev): threshold -> Micro F1 / clean FP / decoy FP
  0.0: 0.946 / 0.432 / 1.000
  0.5: 0.946 / 0.430 / 1.000
  0.7: 0.938 / 0.388 / 1.000
  0.8: 0.930 / 0.348 / 0.995
  0.9: 0.912 / 0.280 / 0.975
  0.95: 0.891 / 0.204 / 0.965
  0.99: 0.830 / 0.020 / 0.860

Findings (see metrics.json):
- mBERT has no IBAN label: strict IBAN recall 0, and only part of IBAN characters are masked under other labels. Regex and both hybrids reach full IBAN recall on this synthetic set.
- On Micro dev, mBERT and the hybrids are within about 0.003 strict F1; union is closest to mBERT, rules_first loses a little because regex EMAIL spans differ from gold boundaries.
- EMAIL-only strict F1 on Micro dev: regex is lower than mBERT; rules_first is lower than union because regex wins on overlap.
- Regex has zero false positives on decoys and clean text (decoys were built to be negatives for the regex, so this is by construction, not evidence of robustness).
- mBERT (and all hybrids using it) flags many clean and decoy sentences, because it was trained on Micro, which has no clean negatives; decoy codes look like ID-like PII to it. Whether masking decoys with some label is an error depends on the use.
- The confidence threshold trades Micro recall for fewer false positives: see sweep. Chosen value is dev-tuned and optimistic.

Limitations: dev data only (tests frozen), single seed and single model, synthetic data, challenge templates are few and simple; the label sets differ (regex 2 labels vs mBERT 19), so general strict F1 is not a fair regex comparison, use the EMAIL-only column.
