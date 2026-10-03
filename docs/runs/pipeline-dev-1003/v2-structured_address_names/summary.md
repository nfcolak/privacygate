# Pipeline masking evaluation

Synthetic annotation-relative masking only; no training or test split evaluated.
Not a privacy or legal guarantee. Wilson intervals describe row indicators under an IID assumption;
shared synthetic grammars and small strata limit population inference.

Profile: structured_address_names
Dataset version: v2
Dataset sha256: 4b52ff31718ba6dd0b7e8a9fda9637f241295f782504d456179467a6b0c2f0d2

Complete spans: 130/130
Partial spans: 0
Untouched spans: 0
Exposed alphanumeric characters: 0/2827
Uncovered gold characters: 0
Fully masked positive rows (blocked counted as failures): 60/60
Excess masked characters: 56
Clean rows masked: 9/20
Clean characters masked: 56/2254
OK / blocked rows: 80 / 0
Execution uncovered characters: 0

## Row-rate Wilson 95% intervals

fully_masked_positive_rows: 60/60; 100.00% [93.98%, 100.00%]
released_fully_masked_positive_rows: 60/60; 100.00% [93.98%, 100.00%]
clean_masked_rows: 9/20; 45.00% [25.82%, 65.79%]
clean_ok_rows: 20/20; 100.00% [83.89%, 100.00%]
ok_rows: 80/80; 100.00% [95.42%, 100.00%]
blocked_rows: 0/80; 0.00% [0.00%, 4.58%]
rows_with_uncovered_chars: 0/80; 0.00% [0.00%, 4.58%]

## Per gold label

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| ADDRESS | 45/45 | 0 | 0 | 0 | 40/40 | 0/0 |
| PERSONNAME | 60/60 | 0 | 0 | 0 | 60/60 | 0/0 |
| TELEPHONENUM | 25/25 | 0 | 0 | 0 | 25/25 | 0/0 |

## Per family

| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |
|---|---|---|---|---|---|---|
| clean | 0/0 | 0 | 0 | 0 | 0/0 | 9/20 |
| full_address | 75/75 | 0 | 0 | 0 | 35/35 | 0/0 |
| long_text | 15/15 | 0 | 0 | 0 | 5/5 | 0/0 |
| phone | 40/40 | 0 | 0 | 0 | 20/20 | 0/0 |

Per-label row success concerns that label only; row-scoped excess repeats across labels and is not additive.
Human semantic review is not performed by this evaluator; that gate remains incomplete.
