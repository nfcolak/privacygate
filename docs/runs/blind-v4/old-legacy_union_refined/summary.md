# Pipeline masking evaluation

Synthetic annotation-relative masking only; no training or test split evaluated.
Not a privacy or legal guarantee. Wilson intervals describe row indicators under an IID assumption;
shared synthetic grammars and small strata limit population inference.

Profile: legacy_union_refined
Dataset version: v4
Dataset sha256: b0b21ae034fa54eb8949e7444c882f44fa53070bb927a00485dc252056f1821e

Complete spans: 670/830
Partial spans: 160
Untouched spans: 0
Exposed alphanumeric characters: 270/21611
Uncovered gold characters: 723
Fully masked positive rows (blocked counted as failures): 169/300
Excess masked characters: 2260
Clean rows masked: 168/200
Clean characters masked: 2252/17204
OK / blocked rows: 500 / 0
Execution uncovered characters: 0

## Row-rate Wilson 95% intervals

fully_masked_positive_rows: 169/300; 56.33% [50.68%, 61.83%]
released_fully_masked_positive_rows: 169/300; 56.33% [50.68%, 61.83%]
clean_masked_rows: 168/200; 84.00% [78.29%, 88.43%]
clean_ok_rows: 200/200; 100.00% [98.12%, 100.00%]
ok_rows: 500/500; 100.00% [99.24%, 100.00%]
blocked_rows: 0/500; 0.00% [0.00%, 0.76%]
rows_with_uncovered_chars: 0/500; 0.00% [0.00%, 0.76%]

## Per gold label

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| ACCOUNTNUM | 22/25 | 3 | 0 | 0 | 22/25 | 0/0 |
| ADDRESS | 23/120 | 97 | 0 | 259 | 23/120 | 0/0 |
| AGE | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |
| CREDITCARDNUMBER | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| DATEOFBIRTH | 30/30 | 0 | 0 | 0 | 30/30 | 0/0 |
| DRIVERLICENSENUM | 19/20 | 1 | 0 | 0 | 19/20 | 0/0 |
| EMAIL | 60/60 | 0 | 0 | 0 | 60/60 | 0/0 |
| IBAN | 53/55 | 2 | 0 | 0 | 53/55 | 0/0 |
| IDCARDNUM | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| PASSPORTNUM | 55/55 | 0 | 0 | 0 | 55/55 | 0/0 |
| PERSONALREF | 50/50 | 0 | 0 | 0 | 40/40 | 0/0 |
| PERSONNAME | 116/170 | 54 | 0 | 1 | 107/160 | 0/0 |
| SOCIALNUM | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |
| TAXNUM | 19/20 | 1 | 0 | 0 | 19/20 | 0/0 |
| TELEPHONENUM | 108/110 | 2 | 0 | 10 | 98/100 | 0/0 |
| USERNAME | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |

## Per family

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| account | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| biography | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |
| chat_lines | 88/110 | 22 | 0 | 20 | 13/30 | 0/0 |
| clean_calendar | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_catalog | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_dimensions | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_facilities | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_near_miss_twins | 0/0 | 0 | 0 | 0 | 0/0 | 50/60 |
| clean_numeric | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_organisations | 0/0 | 0 | 0 | 0 | 0/0 | 7/20 |
| clean_places | 0/0 | 0 | 0 | 0 | 0/0 | 11/20 |
| form_records | 88/110 | 22 | 0 | 20 | 13/30 | 0/0 |
| full_address | 4/20 | 16 | 0 | 48 | 4/20 | 0/0 |
| identity | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |
| long_text | 68/80 | 12 | 0 | 37 | 1/10 | 0/0 |
| mixed_language | 95/120 | 25 | 0 | 64 | 6/30 | 0/0 |
| names | 20/30 | 10 | 0 | 0 | 20/30 | 0/0 |
| ocr_noise | 95/110 | 15 | 0 | 10 | 19/30 | 0/0 |
| personalref | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |
| phone | 15/15 | 0 | 0 | 0 | 15/15 | 0/0 |
| signature_blocks | 112/150 | 38 | 0 | 71 | 3/30 | 0/0 |
| username | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |

Per-label row success concerns that label only; row-scoped excess repeats across labels and is not additive.
Human semantic review is not performed by this evaluator; that gate remains incomplete.
