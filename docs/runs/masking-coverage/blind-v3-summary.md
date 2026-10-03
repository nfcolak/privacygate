# Blind v3: frozen refinement measurement

Synthetic dev only; single sweep; no tuning; training false; test_evaluated false. Not a privacy guarantee. V3 was generated before any model or rule saw it; refine.py remained frozen at sha256 5fcfa1e688140e0ba72c3980523c5114df98a97fe8329a4dcee51abb9d6dfdaf. Scoring is unchanged; complete spans require full annotated-span coverage, not just alphanumeric coverage.

Source: blind-v3-1003/metrics.json and manifest.json. Dataset: 150 rows, 110 positive, 40 clean, 155 gold spans; sha256 313a477b124c5c7f9e7aeaa35f777c85291833940254ff74f4e98c39a1f8dd61. One successful measurement invocation; no retry or subsequent rule change.

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess chars | clean rows masked | clean masked chars |
|---|---|---|---|---|---|---|---|---|
| mbert | 29/155 | 126 | 0 | 662/4711 | 24/110 | 756 | 40/40 | 729 |
| hybrid_union | 37/155 | 118 | 0 | 585/4711 | 24/110 | 756 | 40/40 | 729 |
| hybrid_union_refined | 95/155 | 60 | 0 | 198/4711 | 57/110 | 845 | 40/40 | 818 |

## Hybrid_union_refined by gold label and family

| slice | complete spans | exposed alnum chars |
|---|---|---|
| label: ACCOUNTNUM | 4/5 | 0/60 |
| label: ADDRESS | 8/25 | 166/1564 |
| label: DRIVERLICENSENUM | 5/5 | 0/55 |
| label: EMAIL | 10/10 | 0/426 |
| label: IBAN | 2/5 | 0/122 |
| label: IDCARDNUM | 5/5 | 0/55 |
| label: PASSPORTNUM | 0/5 | 1/55 |
| label: PERSONALREF | 8/10 | 0/130 |
| label: PERSONNAME | 22/50 | 31/1540 |
| label: TELEPHONENUM | 26/30 | 0/611 |
| label: USERNAME | 5/5 | 0/93 |
| family: account | 10/15 | 0/338 |
| family: clean | 0/0 | 0/0 |
| family: full_address | 8/20 | 82/1175 |
| family: identity | 10/15 | 1/165 |
| family: long_text | 17/25 | 84/923 |
| family: multiple_entities | 10/10 | 0/371 |
| family: names | 7/25 | 17/763 |
| family: personalref | 3/5 | 0/65 |
| family: phone | 11/15 | 0/308 |
| family: repeated_values | 14/20 | 14/510 |
| family: username | 5/5 | 0/93 |

## Three-line comparison (hybrid_union_refined)

Non-blind refine-v1-1003: complete 369/370; exposed alnum 0/7854; fully masked positive rows 99/100; excess 0; clean masked 0/10 rows, 0 chars.
Non-blind refine-v2-1003: complete 130/130; exposed alnum 0/2827; fully masked positive rows 60/60; excess 46; clean masked 5/20 rows, 46 chars.
Blind v3: complete 95/155; exposed alnum 198/4711; fully masked positive rows 57/110; excess 845; clean masked 40/40 rows, 818 chars: lower coverage and greater overmasking on different synthetic formats; v1/v2 are tuned development evidence, not unbiased comparators.
