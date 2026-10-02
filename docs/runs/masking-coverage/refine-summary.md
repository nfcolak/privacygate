# Rule-based span refinement: hybrid_union -> hybrid_union_refined

Synthetic development diagnostic only (training false, test evaluated false). Counts are annotated-span coverage of invented
synthetic rows; unannotated information is outside them. This is not a privacy guarantee and says nothing about real data.
Same mBERT checkpoint (sha256 0058a5c93c2ef14c5f65daf8ae8afc061851acf8d5cf5d52ba0342f578d9cac9), confidence 0.0, one forward sweep per dataset; scoring is the existing
masking_metrics union-coverage scorer, unchanged (refined ADDRESS spans are labelled STREET for scoring input only; no metric below depends on labels).

Caveat: the refinement rules were written after seeing the stress v1 failure shapes, so v1 gains are optimistic.
Stress v2 (different formats; generated before any model output on it was seen) is the fairer check, but not fully blind: the first v2 run
(rules a-c as briefed) gave ADDRESS 33/45 and 58/130 complete spans overall; value-free failure shapes (a street-type word such as 'via'/'calle'
left outside the STREET piece) then led to one added rule (street-type prefix), which is what the numbers below include.
Fully masked positive rows stay 0 because every row also carries an owner-name gold span (PERSONNAME) that this checkpoint has no label for;
refinement does not touch names. Excess on v1 comes from ZIPCODE pieces the model finds inside non-address values (e.g. username) being
merged with the real address across a short gap, which the briefed gap rules allow.

## Stress v1 (110 rows)

Overall, hybrid_union -> hybrid_union_refined (mbert arm shown for reference):

| metric | mbert | hybrid_union | hybrid_union_refined |
|---|---|---|---|
| complete spans / gold spans | 117/370 | 117/370 | 201/370 |
| partial spans | 253 | 253 | 169 |
| untouched spans | 0 | 0 | 0 |
| exposed alnum chars | 783/7854 | 783/7854 | 3/7854 |
| fully masked positive rows | 0/100 | 0/100 | 0/100 |
| clean controls with any mask | 0/10 | 0/10 | 0/10 |
| clean-control masked chars | 0 | 0 | 0 |
| excess masked chars (all rows, outside gold) | 0 | 0 | 148 |

Per gold label / family (hybrid_union -> hybrid_union_refined):

| slice | complete spans | partial | untouched | exposed alnum chars | fully masked rows | row-scoped excess chars |
|---|---|---|---|---|---|---|
| ADDRESS | 0/30 -> 30/30 | 30 -> 0 | 0 -> 0 | 435 -> 0 | 0/30 -> 30/30 | 0 -> 148 |
| TELEPHONENUM | 3/50 -> 46/50 | 47 -> 4 | 0 -> 0 | 323 -> 3 | 3/40 -> 36/40 | 0 -> 148 |
| long_text rows | 19/60 -> 38/60 | 41 -> 22 | 0 -> 0 | 210 -> 0 | 0/10 -> 0/10 | 0 -> 0 |

Clean controls: any mask 0/10 -> 0/10; masked chars 0 -> 0; excess masked chars over all rows 0 -> 148.

## Stress v2 (80 rows)

Overall, hybrid_union -> hybrid_union_refined (mbert arm shown for reference):

| metric | mbert | hybrid_union | hybrid_union_refined |
|---|---|---|---|
| complete spans / gold spans | 19/130 | 19/130 | 70/130 |
| partial spans | 111 | 111 | 60 |
| untouched spans | 0 | 0 | 0 |
| exposed alnum chars | 119/2827 | 119/2827 | 0/2827 |
| fully masked positive rows | 0/60 | 0/60 | 0/60 |
| clean controls with any mask | 9/20 | 9/20 | 9/20 |
| clean-control masked chars | 56 | 56 | 64 |
| excess masked chars (all rows, outside gold) | 56 | 56 | 64 |

Per gold label / family (hybrid_union -> hybrid_union_refined):

| slice | complete spans | partial | untouched | exposed alnum chars | fully masked rows | row-scoped excess chars |
|---|---|---|---|---|---|---|
| ADDRESS | 0/45 -> 45/45 | 45 -> 0 | 0 -> 0 | 96 -> 0 | 0/40 -> 40/40 | 0 -> 0 |
| TELEPHONENUM | 19/25 -> 25/25 | 6 -> 0 | 0 -> 0 | 23 -> 0 | 19/25 -> 25/25 | 0 -> 0 |
| long_text rows | 5/15 -> 10/15 | 10 -> 5 | 0 -> 0 | 8 -> 0 | 0/5 -> 0/5 | 0 -> 0 |

Clean controls: any mask 9/20 -> 9/20; masked chars 56 -> 64; excess masked chars over all rows 56 -> 64.

Per-slice excess is row-scoped (whole-row excess for rows containing the label) and not additive across slices.
Details: refine-v1/ and refine-v2/ (metrics.json, manifest.json, summary.md).
