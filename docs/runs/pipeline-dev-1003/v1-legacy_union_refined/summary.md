# Pipeline masking evaluation

Synthetic annotation-relative masking only; no training or test split evaluated.
Not a privacy or legal guarantee. Wilson intervals describe row indicators under an IID assumption;
shared synthetic grammars and small strata limit population inference.

Profile: legacy_union_refined
Dataset version: v1
Dataset sha256: b901873cbdd3715aaae2c78477193fecb3fd47410344fdb240ce75abdbfb6cbf

Complete spans: 369/370
Partial spans: 1
Untouched spans: 0
Exposed alphanumeric characters: 0/7854
Uncovered gold characters: 1
Fully masked positive rows (blocked counted as failures): 99/100
Excess masked characters: 0
Clean rows masked: 0/10
Clean characters masked: 0/3233
OK / blocked rows: 110 / 0
Execution uncovered characters: 0

## Row-rate Wilson 95% intervals

fully_masked_positive_rows: 99/100; 99.00% [94.55%, 99.82%]
released_fully_masked_positive_rows: 99/100; 99.00% [94.55%, 99.82%]
clean_masked_rows: 0/10; 0.00% [0.00%, 27.75%]
clean_ok_rows: 10/10; 100.00% [72.25%, 100.00%]
ok_rows: 110/110; 100.00% [96.63%, 100.00%]
blocked_rows: 0/110; 0.00% [0.00%, 3.37%]
rows_with_uncovered_chars: 0/110; 0.00% [0.00%, 3.37%]

## Per gold label

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| ACCOUNTNUM | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |
| ADDRESS | 30/30 | 0 | 0 | 0 | 30/30 | 0/0 |
| DRIVERLICENSENUM | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |
| EMAIL | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |
| IDCARDNUM | 20/20 | 0 | 0 | 0 | 20/20 | 0/0 |
| PASSPORTNUM | 10/10 | 0 | 0 | 0 | 10/10 | 0/0 |
| PERSONALREF | 30/30 | 0 | 0 | 0 | 30/30 | 0/0 |
| PERSONNAME | 149/150 | 1 | 0 | 0 | 99/100 | 0/0 |
| TELEPHONENUM | 50/50 | 0 | 0 | 0 | 40/40 | 0/0 |
| USERNAME | 50/50 | 0 | 0 | 0 | 40/40 | 0/0 |

## Per family

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| account | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |
| clean | 0/0 | 0 | 0 | 0 | 0/0 | 0/10 |
| full_address | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |
| identity | 40/40 | 0 | 0 | 0 | 10/10 | 0/0 |
| long_text | 59/60 | 1 | 0 | 0 | 9/10 | 0/0 |
| multiple_entities | 70/70 | 0 | 0 | 0 | 10/10 | 0/0 |
| names | 30/30 | 0 | 0 | 0 | 10/10 | 0/0 |
| personalref | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |
| phone | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |
| repeated_values | 70/70 | 0 | 0 | 0 | 10/10 | 0/0 |
| username | 20/20 | 0 | 0 | 0 | 10/10 | 0/0 |

Per-label row success concerns that label only; row-scoped excess repeats across labels and is not additive.
Human semantic review is not performed by this evaluator; that gate remains incomplete.
