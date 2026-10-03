# Pipeline masking evaluation

Synthetic annotation-relative masking only; no training or test split evaluated.
Not a privacy or legal guarantee. Wilson intervals describe row indicators under an IID assumption;
shared synthetic grammars and small strata limit population inference.

Profile: full
Dataset version: v4
Dataset sha256: b0b21ae034fa54eb8949e7444c882f44fa53070bb927a00485dc252056f1821e

Complete spans: 810/830
Partial spans: 20
Untouched spans: 0
Exposed alphanumeric characters: 60/21611
Uncovered gold characters: 111
Fully masked positive rows (blocked counted as failures): 281/300
Excess masked characters: 2441
Clean rows masked: 152/200
Clean characters masked: 2199/17204
OK / blocked rows: 500 / 0
Execution uncovered characters: 0

## Row-rate Wilson 95% intervals

fully_masked_positive_rows: 281/300; 93.67% [90.32%, 95.91%]
released_fully_masked_positive_rows: 281/300; 93.67% [90.32%, 95.91%]
clean_masked_rows: 152/200; 76.00% [69.63%, 81.39%]
clean_ok_rows: 200/200; 100.00% [98.12%, 100.00%]
ok_rows: 500/500; 100.00% [99.24%, 100.00%]
blocked_rows: 0/500; 0.00% [0.00%, 0.76%]
rows_with_uncovered_chars: 0/500; 0.00% [0.00%, 0.76%]

## Per gold label

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| ACCOUNTNUM | 24/25 | 1 | 0 | 0 | 24/25 | 0/0 |
| ADDRESS | 109/120 | 11 | 0 | 50 | 109/120 | 0/0 |
| AGE | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |
| CREDITCARDNUMBER | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| DATEOFBIRTH | 30/30 | 0 | 0 | 0 | 30/30 | 0/0 |
| DRIVERLICENSENUM | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| EMAIL | 60/60 | 0 | 0 | 0 | 60/60 | 0/0 |
| IBAN | 54/55 | 1 | 0 | 0 | 54/55 | 0/0 |
| IDCARDNUM | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| PASSPORTNUM | 55/55 | 0 | 0 | 0 | 55/55 | 0/0 |
| PERSONALREF | 50/50 | 0 | 0 | 0 | 40/40 | 0/0 |
| PERSONNAME | 164/170 | 6 | 0 | 0 | 154/160 | 0/0 |
| SOCIALNUM | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |
| TAXNUM | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| TELEPHONENUM | 109/110 | 1 | 0 | 10 | 99/100 | 0/0 |
| USERNAME | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |

## Per family

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| account | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| biography | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |
| chat_lines | 109/110 | 1 | 0 | 0 | 29/30 | 0/0 |
| clean_calendar | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_catalog | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_dimensions | 0/0 | 0 | 0 | 0 | 0/0 | 4/20 |
| clean_facilities | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_near_miss_twins | 0/0 | 0 | 0 | 0 | 0/0 | 50/60 |
| clean_numeric | 0/0 | 0 | 0 | 0 | 0/0 | 20/20 |
| clean_organisations | 0/0 | 0 | 0 | 0 | 0/0 | 7/20 |
| clean_places | 0/0 | 0 | 0 | 0 | 0/0 | 11/20 |
| form_records | 109/110 | 1 | 0 | 0 | 29/30 | 0/0 |
| full_address | 18/20 | 2 | 0 | 11 | 18/20 | 0/0 |
| identity | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |
| long_text | 78/80 | 2 | 0 | 11 | 8/10 | 0/0 |
| mixed_language | 117/120 | 3 | 0 | 13 | 27/30 | 0/0 |
| names | 30/30 | 0 | 0 | 0 | 30/30 | 0/0 |
| ocr_noise | 105/110 | 5 | 0 | 10 | 26/30 | 0/0 |
| personalref | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |
| phone | 15/15 | 0 | 0 | 0 | 15/15 | 0/0 |
| signature_blocks | 144/150 | 6 | 0 | 15 | 24/30 | 0/0 |
| username | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |

Per-label row success concerns that label only; row-scoped excess repeats across labels and is not additive.
Human semantic review is not performed by this evaluator; that gate remains incomplete.
