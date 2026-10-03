# Blind v4: frozen old-model arms and GLiNER2-PII

Blind, one sweep per arm, no tuning. Synthetic, annotation-relative diagnostics only; not a privacy guarantee.
No training, downloads, installs, corpus test split access, row-level inspection, or raw-text/value/row-id/offset evidence.
Only aggregate reports were inspected. The new region model arm will be added later after training.

## Frozen bindings

Starting commit: `8cca06013d6997e891fe5f75be9b3e9a9bdf3f8f`.
Old checkpoint: `models/pos-neg-alignment-pilot-1002`; model.safetensors sha256: `0058a5c93c2ef14c5f65daf8ae8afc061851acf8d5cf5d52ba0342f578d9cac9`.
Pipeline profiles: `legacy_union_refined` and `full`, unchanged from the committed `configs/pipeline-v1.json`; both use the actual pipeline entrypoint.
Dataset: `data/augmentation/masking-stress-v4.jsonl`; sha256: `b0b21ae034fa54eb8949e7444c882f44fa53070bb927a00485dc252056f1821e`.
Frozen six-field schema and SHA binding: `docs/masking-stress-v4/manifest.json`; 500 rows, 300 positive, 200 clean, 830 gold spans.
GLiNER2-PII: `fastino/gliner2-privacy-filter-PII-multi`, revision `1cb4166094dc58fa8d836429f060d6c95f62b495`; pinned isolated runtime, offline, MPS.
All 42 pinned-card labels, threshold 0.5, 64-word-token overlap, chunk planning, prediction mapping, merging and historical coverage scorer unchanged.
The only external data-loader adaptations are manifest-bound v4 loading, DATEOFBIRTH → DATE for the historical scorer allowlist, and omission of external v4 family grouping (the historical scorer only admits legacy families). Gold intervals and text remain unchanged; this summary restores the canonical DATEOFBIRTH label. Label-exact diagnostics are not used for cross-model comparison.
All code/config fingerprints were frozen before the first sweep and verified unchanged after all three sweeps.

## Overall aggregates

Cells with intervals show evaluator-emitted Wilson 95% row-rate intervals. GLiNER2’s historical evaluator emits no Wilson intervals; none were added.
Complete means every original gold character is masked, not merely its alphanumeric characters. Exposed counts use Unicode alphanumeric characters. Excess counts are masked characters outside all annotated gold, including clean controls.

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows; Wilson 95% | excess chars | clean rows masked; Wilson 95% | clean masked chars |
|---|---|---|---|---|---|---|---|---|
| old-legacy_union_refined | 670/830 | 160 | 0 | 270/21611 | 169/300; 56.33% [50.68%, 61.83%] | 2260 | 168/200; 84.00% [78.29%, 88.43%] | 2252/17204 |
| old-full | 810/830 | 20 | 0 | 60/21611 | 281/300; 93.67% [90.32%, 95.91%] | 2441 | 152/200; 76.00% [69.63%, 81.39%] | 2199/17204 |
| gliner2_pii | 498/830 | 262 | 70 | 4973/21611 | 132/300; CI not emitted | 1566 | 105/200; CI not emitted | 1549/17204 |

Both old-model arms released 500/500 rows; blocked rows and execution-uncovered characters were zero. Blocked positive rows would count as fully-masked-row failures.
Additional evaluator-emitted overall Wilson 95% intervals (no span/character independence assumption):

- old-legacy_union_refined: released_fully_masked_positive_rows: 169/300; 56.33% [50.68%, 61.83%]; clean_ok_rows: 200/200; 100.00% [98.12%, 100.00%]; ok_rows: 500/500; 100.00% [99.24%, 100.00%]; blocked_rows: 0/500; 0.00% [0.00%, 0.76%]; rows_with_uncovered_chars: 0/500; 0.00% [0.00%, 0.76%].
- old-full: released_fully_masked_positive_rows: 281/300; 93.67% [90.32%, 95.91%]; clean_ok_rows: 200/200; 100.00% [98.12%, 100.00%]; ok_rows: 500/500; 100.00% [99.24%, 100.00%]; blocked_rows: 0/500; 0.00% [0.00%, 0.76%]; rows_with_uncovered_chars: 0/500; 0.00% [0.00%, 0.76%].

Wilson intervals describe row indicators under an IID assumption, not production privacy. Shared synthetic grammars, translated contexts and small strata limit population inference.

## Per canonical gold label: complete / exposed

| label | legacy complete spans | legacy exposed alnum | full complete spans | full exposed alnum | GLiNER2-PII complete spans | GLiNER2-PII exposed alnum |
|---|---|---|---|---|---|---|
| ACCOUNTNUM | 22/25 | 0/350 | 24/25 | 0/350 | 23/25 | 2/350 |
| ADDRESS | 23/120 | 259/8830 | 109/120 | 50/8830 | 0/120 | 3062/8830 |
| AGE | 25/25 | 0/50 | 25/25 | 0/50 | 0/25 | 50/50 |
| CREDITCARDNUMBER | 20/20 | 0/320 | 20/20 | 0/320 | 20/20 | 0/320 |
| DATEOFBIRTH | 30/30 | 0/240 | 30/30 | 0/240 | 30/30 | 0/240 |
| DRIVERLICENSENUM | 19/20 | 0/220 | 20/20 | 0/220 | 20/20 | 0/220 |
| EMAIL | 60/60 | 0/2482 | 60/60 | 0/2482 | 59/60 | 7/2482 |
| IBAN | 53/55 | 0/1342 | 54/55 | 0/1342 | 55/55 | 0/1342 |
| IDCARDNUM | 20/20 | 0/180 | 20/20 | 0/180 | 17/20 | 27/180 |
| PASSPORTNUM | 55/55 | 0/495 | 55/55 | 0/495 | 55/55 | 0/495 |
| PERSONALREF | 50/50 | 0/550 | 50/50 | 0/550 | 48/50 | 22/550 |
| PERSONNAME | 116/170 | 1/3169 | 164/170 | 0/3169 | 103/170 | 160/3169 |
| SOCIALNUM | 25/25 | 0/325 | 25/25 | 0/325 | 23/25 | 26/325 |
| TAXNUM | 19/20 | 0/220 | 20/20 | 0/220 | 20/20 | 0/220 |
| TELEPHONENUM | 108/110 | 10/2493 | 109/110 | 10/2493 | 0/110 | 1617/2493 |
| USERNAME | 25/25 | 0/345 | 25/25 | 0/345 | 25/25 | 0/345 |

## Per family: old-full

Families are disjoint row groups. Zero-denominator positive or clean rates are N/A, not zero success.

| family | rows | complete spans | partial | untouched | exposed alnum | fully masked positive rows; Wilson 95% | excess chars | clean rows masked; Wilson 95% | clean masked chars |
|---|---|---|---|---|---|---|---|---|---|
| account | 20 | 20/20 | 0 | 0 | 0/342 | 20/20; 100.00% [83.89%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| biography | 10 | 20/20 | 0 | 0 | 0/100 | 10/10; 100.00% [72.25%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| chat_lines | 30 | 109/110 | 1 | 0 | 0/2335 | 29/30; 96.67% [83.33%, 99.41%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| clean_calendar | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 200 | 20/20; 100.00% [83.89%, 100.00%] | 200/1912 |
| clean_catalog | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 664 | 20/20; 100.00% [83.89%, 100.00%] | 664/2240 |
| clean_dimensions | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 24 | 4/20; 20.00% [8.07%, 41.60%] | 24/1554 |
| clean_facilities | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 144 | 20/20; 100.00% [83.89%, 100.00%] | 144/1556 |
| clean_near_miss_twins | 60 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 658 | 50/60; 83.33% [71.97%, 90.69%] | 658/3981 |
| clean_numeric | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 278 | 20/20; 100.00% [83.89%, 100.00%] | 278/1776 |
| clean_organisations | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 107 | 7/20; 35.00% [18.12%, 56.71%] | 107/2284 |
| clean_places | 20 | 0/0 | 0 | 0 | 0/0 | 0/0; N/A (zero denominator) | 124 | 11/20; 55.00% [34.21%, 74.18%] | 124/1901 |
| form_records | 30 | 109/110 | 1 | 0 | 0/2335 | 29/30; 96.67% [83.33%, 99.41%] | 126 | 0/0; N/A (zero denominator) | 0/0 |
| full_address | 20 | 18/20 | 2 | 0 | 11/1455 | 18/20; 90.00% [69.90%, 97.21%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| identity | 25 | 25/25 | 0 | 0 | 0/265 | 25/25; 100.00% [86.68%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| long_text | 10 | 78/80 | 2 | 0 | 11/2174 | 8/10; 80.00% [49.02%, 94.33%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| mixed_language | 30 | 117/120 | 3 | 0 | 13/3901 | 27/30; 90.00% [74.38%, 96.54%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| names | 30 | 30/30 | 0 | 0 | 0/559 | 30/30; 100.00% [88.65%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| ocr_noise | 30 | 105/110 | 5 | 0 | 10/2335 | 26/30; 86.67% [70.32%, 94.69%] | 108 | 0/0; N/A (zero denominator) | 0/0 |
| personalref | 10 | 10/10 | 0 | 0 | 0/110 | 10/10; 100.00% [72.25%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| phone | 15 | 15/15 | 0 | 0 | 0/327 | 15/15; 100.00% [79.61%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |
| signature_blocks | 30 | 144/150 | 6 | 0 | 15/5102 | 24/30; 80.00% [62.69%, 90.49%] | 8 | 0/0; N/A (zero denominator) | 0/0 |
| username | 10 | 10/10 | 0 | 0 | 0/271 | 10/10; 100.00% [72.25%, 100.00%] | 0 | 0/0; N/A (zero denominator) | 0/0 |

## Execution and evidence

Each arm ran once under nohup with PYTHONPATH removed, bytecode writes disabled and both Hugging Face/Transformers offline flags set. PIDs, exact commands, environment, exit codes and aggregate-only completion logs are recorded per arm.
The old-model custody ledger contains exactly two completed receipts and two durable reservations: one each for legacy_union_refined and full with the old checkpoint SHA. GLiNER2’s separate manifest reserves and records exactly one completed sweep.

- old-legacy_union_refined: exit 0; one invocation; process wall time 9.934 seconds; `old-legacy_union_refined/metrics.json`, `old-legacy_union_refined/manifest.json`, `old-legacy_union_refined/execution.json`.
- old-full: exit 0; one invocation; process wall time 9.252 seconds; `old-full/metrics.json`, `old-full/manifest.json`, `old-full/execution.json`.
- gliner2_pii: exit 0; one invocation; process wall time 41.240 seconds; `gliner2_pii/metrics.json`, `gliner2_pii/manifest.json`, `gliner2_pii/execution.json`.

GLiNER2-PII completed within the 15-minute arm limit: 41.240 seconds total process wall time; 538 chunks; 33.968 seconds sweep time and 6.448 seconds model load. Old-model timings are process wall times, not comparable normalized scorer timings.
Verification evidence: `freeze.json`, `verification.json`, `RECEIPTS.jsonl`, `RECEIPTS.jsonl.STARTED`, and the per-arm manifests/metrics. No predictions or rows are retained.

Limits: invented values and authored synthetic contexts, annotation-relative excess, controlled OCR perturbations, repeated long-letter filler, fixed chunk boundaries, and no human semantic review. Neither synthetic completeness nor these intervals establish real-data privacy or legal compliance.
