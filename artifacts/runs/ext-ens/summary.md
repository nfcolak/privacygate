# ext-ens summary: v5 + v6 combination (`ensemble_pair`) on the independent sets

Value-free: counts, rates and shapes only. The v5v6 arm was measured once per set after the choice was frozen and committed (`dev-grid.{json,md}`, commit 98e4c07). Coverage = personal letters/digits covered %; excess = masked chars outside all source annotations / non-annotated chars; rows = rows with exposed letters/digits. v5 + step-1 and v6 + chosen are the earlier measurements from `ext-step1/` and `ext-v6/` (not rerun).

Chosen on Gretel EXT-DEV and v7 dev only: `ensemble_pair` = union, name_threshold 0.1, name_propagation_ext off.
Rule: fewest exposed letters/digits over EXT-DEV + v7 dev, v7 clean rows masked <= 21/300, EXT-DEV excess <= v5 + step-1 EXT-DEV excess + 1.0 (5.89).
EXT-DEV (coverage / excess / rows exposed): v5 + step-1 87.99 / 4.89 / 190; v5v6 chosen 97.60 / 5.20 / 46. Union with name_threshold 0.1 won; propagation tied on exposed (1,350) and cost +0.07 point excess, so the rule picked it off. Every mean-mode setting was eligible but exposed 4,727 or more.

| set | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---|---|---|
| Gretel TEST (4,696 rows; in-distribution for v6, not a selection set) | 89.67 / 4.83 / 805 | 96.47 / 1.32 / 328 | 97.63 / 5.06 / 213 |
| Nemotron-PII (5,000 docs) | 96.91 / 1.37 / 545 | 92.03 / 0.28 / 1,308 | 98.99 / 1.41 / 246 |
| ai4privacy (5 x 1,000 rows) | 86.55 / 2.60 / 1,006 | 88.77 / 1.60 / 976 | 93.75 / 2.84 / 568 |

Cells are coverage % / excess % / rows exposed.

v7 development (not blind):

| | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---|---|---|
| clean rows masked | 19/300 | 19/300 | 19/300 |
| exposed letters/digits | 334 | 4,747 | 306 |
| gold alnum coverage % | 99.13 | 87.66 | 99.20 |

## Read this first

1. On the two independent sets v5v6 beats both single models on coverage: Nemotron 98.99 vs 96.91 (v5 + step-1) and 92.03 (v6); ai4privacy 93.75 vs 86.55 and 88.77. Rows exposed drop to 246 (from 545) and 568 (from 1,006).
2. Excess is the v5 level, not the v6 level: Nemotron 1.41 (v5 + step-1 1.37, v6 0.28), ai4privacy 2.84 (2.60, 1.60). Out-of-scope masking stays at the v5 level or above (Nemotron 48.0%, ai4privacy 54.5%; v6 6.1% and 30.2%). The union takes v6 recall and keeps v5 over-masking.
3. v7 dev: clean rows masked 19/300 (unchanged), exposed letters/digits 306 (v5 + step-1 334, v6 4,747); the union restores v5-level v7 behaviour that v6 lost.
4. Gretel TEST is in-distribution for v6 and was not used for any choice. v5v6 97.63 / 5.06 there; its excess is v5-like (4.83), well above v6 alone (1.32).
5. Mean mode (probability average) was eligible but weak on dev (exposed 4,727 or more, mostly v7), so the union was chosen on dev, not on the independent sets.

## Per label (coverage % / exposed letters+digits)

Gretel TEST (4,696 rows; in-distribution for v6, not a selection set)

| label | gold alnum | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---:|---|---|---|
| ACCOUNTNUM | 2,594 | 87.8 / 317 | 98.5 / 40 | 99.2 / 22 |
| ADDRESS | 81,008 | 91.5 / 6,917 | 96.1 / 3,188 | 98.0 / 1,641 |
| CREDITCARDNUMBER | 1,911 | 89.1 / 208 | 99.9 / 1 | 100.0 / 0 |
| DATEOFBIRTH | 2,139 | 86.0 / 299 | 92.5 / 160 | 94.5 / 117 |
| DRIVERLICENSENUM | 1,114 | 93.4 / 74 | 100.0 / 0 | 100.0 / 0 |
| EMAIL | 10,478 | 95.2 / 504 | 96.4 / 373 | 96.9 / 330 |
| IBAN | 3,390 | 96.8 / 110 | 96.0 / 136 | 97.4 / 88 |
| PASSPORTNUM | 1,157 | 91.0 / 104 | 90.2 / 113 | 96.5 / 41 |
| PERSONALREF | 3,144 | 79.6 / 640 | 99.2 / 26 | 99.5 / 17 |
| PERSONNAME | 84,632 | 86.9 / 11,047 | 96.8 / 2,729 | 97.4 / 2,237 |
| SOCIALNUM | 1,259 | 91.0 / 113 | 94.0 / 75 | 98.7 / 16 |
| TELEPHONENUM | 8,457 | 95.8 / 353 | 96.5 / 292 | 96.7 / 278 |
| USERNAME | 544 | 69.7 / 165 | 100.0 / 0 | 100.0 / 0 |

Nemotron-PII (5,000 docs)

| label | gold alnum | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---:|---|---|---|
| ACCOUNTNUM | 9,936 | 98.5 / 146 | 76.2 / 2,361 | 98.9 / 107 |
| ADDRESS | 12,393 | 97.4 / 323 | 97.1 / 360 | 99.6 / 48 |
| AGE | 724 | 76.5 / 170 | 34.8 / 472 | 76.5 / 170 |
| CREDITCARDNUMBER | 9,539 | 99.6 / 40 | 99.5 / 46 | 99.8 / 19 |
| DATEOFBIRTH | 7,304 | 94.9 / 376 | 98.9 / 80 | 99.5 / 40 |
| EMAIL | 63,505 | 99.8 / 112 | 99.8 / 107 | 99.8 / 107 |
| IDCARDNUM | 1,758 | 95.3 / 83 | 63.7 / 639 | 96.1 / 68 |
| PERSONALREF | 23,982 | 96.3 / 881 | 62.9 / 8,902 | 97.8 / 518 |
| PERSONNAME | 43,191 | 93.5 / 2,806 | 94.4 / 2,407 | 98.2 / 759 |
| SOCIALNUM | 3,060 | 99.1 / 27 | 100.0 / 0 | 100.0 / 0 |
| TAXNUM | 740 | 97.0 / 22 | 73.0 / 200 | 98.2 / 13 |
| TELEPHONENUM | 14,982 | 99.9 / 10 | 99.7 / 38 | 99.9 / 10 |
| USERNAME | 8,648 | 86.4 / 1,177 | 96.3 / 319 | 98.2 / 156 |

ai4privacy (5 x 1,000 rows)

| label | gold alnum | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---:|---|---|---|
| ADDRESS | 8,901 | 77.4 / 2,009 | 70.8 / 2,601 | 80.8 / 1,713 |
| AGE | 471 | 64.1 / 169 | 32.5 / 318 | 65.0 / 165 |
| CREDITCARDNUMBER | 1,771 | 87.5 / 221 | 95.7 / 76 | 97.3 / 47 |
| DRIVERLICENSENUM | 1,131 | 78.5 / 243 | 52.1 / 542 | 83.7 / 184 |
| EMAIL | 8,612 | 100.0 / 0 | 100.0 / 0 | 100.0 / 0 |
| IDCARDNUM | 3,867 | 79.9 / 778 | 63.3 / 1,421 | 85.2 / 574 |
| PASSPORTNUM | 1,545 | 84.9 / 234 | 76.2 / 367 | 91.4 / 133 |
| PERSONNAME | 45,565 | 84.1 / 7,255 | 93.6 / 2,923 | 95.2 / 2,190 |
| SOCIALNUM | 1,339 | 88.9 / 149 | 68.8 / 418 | 92.9 / 95 |
| TAXNUM | 1,616 | 87.7 / 199 | 68.3 / 512 | 92.6 / 120 |
| TELEPHONENUM | 9,199 | 99.5 / 44 | 97.2 / 253 | 99.7 / 28 |

## Per language (coverage % / excess % / rows exposed)

Gretel TEST (4,696 rows; in-distribution for v6, not a selection set)

| language | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---|---|---|
| English | 91.37 / 4.78 / 429 | 96.73 / 1.15 / 195 | 97.83 / 4.93 / 125 |
| France | 89.14 / 4.45 / 88 | 97.13 / 1.67 / 29 | 98.26 / 4.96 / 19 |
| German | 86.68 / 4.81 / 88 | 94.49 / 1.56 / 41 | 96.41 / 5.14 / 26 |
| Italian | 88.36 / 5.36 / 92 | 96.51 / 1.68 / 30 | 97.41 / 5.66 / 20 |
| Spanish | 83.53 / 5.07 / 108 | 95.84 / 1.59 / 33 | 97.07 / 5.52 / 23 |

Nemotron-PII (5,000 docs)

| language | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---|---|---|
| English | 96.91 / 1.37 / 545 | 92.03 / 0.28 / 1,308 | 98.99 / 1.41 / 246 |

ai4privacy (5 x 1,000 rows)

| language | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---|---|---|
| de | 91.15 / 4.71 / 145 | 91.59 / 2.43 / 151 | 95.65 / 4.93 / 84 |
| en | 84.85 / 2.90 / 241 | 85.28 / 1.66 / 272 | 92.36 / 3.12 / 148 |
| es | 82.06 / 1.71 / 251 | 83.15 / 1.06 / 242 | 89.82 / 1.95 / 158 |
| fr | 89.19 / 1.39 / 170 | 90.91 / 1.06 / 165 | 95.58 / 1.58 / 84 |
| it | 85.51 / 2.46 / 199 | 92.97 / 1.84 / 146 | 95.32 / 2.77 / 94 |

## Out-of-scope masking (alnum chars annotated out of scope and not in-scope gold; not scored as recall or excess)

| set | out-of-scope alnum chars | v5 + step-1 | v6 + chosen | v5v6 chosen |
|---|---:|---|---|---|
| Nemotron-PII | 340,600 | 47.4% masked | 6.1% masked | 48.0% masked |
| ai4privacy | 21,667 | 49.8% masked | 30.2% masked | 54.5% masked |

Nemotron-PII largest out-of-scope labels (masked % for v5 + step-1 | v6 + chosen | v5v6 chosen): url (83,884 chars) 42.1 | 0.2 | 42.1; company_name (48,010 chars) 58.2 | 3.7 | 56.9; occupation (32,855 chars) 2.7 | 5.1 | 6.9; date (32,181 chars) 55.6 | 1.1 | 55.6; http_cookie (15,592 chars) 63.3 | 0.1 | 63.3; date_time (9,089 chars) 64.5 | 0.0 | 64.5
ai4privacy largest out-of-scope labels (masked % for v5 + step-1 | v6 + chosen | v5v6 chosen): CITY (8,885 chars) 60.5 | 37.4 | 66.3; DATE (5,827 chars) 47.8 | 19.3 | 49.3; TIME (3,051 chars) 20.0 | 6.9 | 22.6; TITLE (2,047 chars) 63.5 | 65.5 | 73.4; ZIPCODE (900 chars) 62.7 | 40.1 | 67.1; GENDER (595 chars) 12.1 | 14.8 | 17.6

## Top miss and excess shapes of the v5v6 arm (`shapes.py`, value-free)

Gretel TEST (4,696 rows; in-distribution for v6, not a selection set)
- misses (exposed alnum): PERSONNAME other (31 pieces, 507 chars); ADDRESS other (53 pieces, 497 chars); PERSONNAME lower (40 pieces, 456 chars); PERSONNAME capitalised-words(n=1) (54 pieces, 456 chars); ADDRESS mixed-alnum (19 pieces, 420 chars); ADDRESS lower (26 pieces, 309 chars); PERSONNAME upper (28 pieces, 302 chars); PERSONNAME mixed-alnum (13 pieces, 270 chars)
- excess (masked alnum outside annotations): PERSONNAME on other (2368 pieces, 26,433 chars); ADDRESS on mixed-alnum (801 pieces, 19,122 chars); PERSONNAME on capitalised-words(n=1) (2726 pieces, 19,089 chars); PERSONNAME on upper (1361 pieces, 15,701 chars); EMAIL on email-like (708 pieces, 15,307 chars); PERSONALREF on upper (1598 pieces, 13,340 chars)

Nemotron-PII (5,000 docs)
- misses (exposed alnum): PERSONNAME capitalised-words(n=1) (106 pieces, 700 chars); PERSONALREF upper (54 pieces, 412 chars); AGE digits<=4 (85 pieces, 170 chars); USERNAME lower (16 pieces, 93 chars); PERSONALREF digits5-9 (12 pieces, 78 chars); EMAIL other (5 pieces, 65 chars); USERNAME mixed-alnum (7 pieces, 63 chars); ACCOUNTNUM upper (5 pieces, 46 chars)
- excess (masked alnum outside annotations): PERSONNAME on other (891 pieces, 3,325 chars); PERSONNAME on capitalised-words(n=1) (471 pieces, 2,817 chars); PERSONALREF on upper (432 pieces, 2,282 chars); PERSONNAME on capitalised-words(n=2) (170 pieces, 2,189 chars); PERSONNAME on lower (577 pieces, 1,979 chars); ADDRESS on lower (287 pieces, 1,616 chars)

ai4privacy (5 x 1,000 rows)
- misses (exposed alnum): PERSONNAME capitalised-words(n=1) (265 pieces, 1,599 chars); ADDRESS other (32 pieces, 625 chars); IDCARDNUM upper (59 pieces, 560 chars); PERSONNAME capitalised-words(n=2) (37 pieces, 458 chars); ADDRESS capitalised-words(n=1) (36 pieces, 310 chars); ADDRESS capitalised-words(n=2) (26 pieces, 294 chars); ADDRESS digits<=4 (88 pieces, 229 chars); AGE digits<=4 (87 pieces, 165 chars)
- excess (masked alnum outside annotations): PERSONNAME on capitalised-words(n=1) (454 pieces, 2,305 chars); PERSONNAME on other (187 pieces, 2,240 chars); PERSONNAME on lower (636 pieces, 1,534 chars); ADDRESS on lower (120 pieces, 461 chars); PERSONNAME on capitalised-words(n=2) (29 pieces, 356 chars); PERSONALREF on upper (24 pieces, 318 chars)

## Files

`dev-grid.{json,md}`, `arms.json`, `gretel-test/` (metrics, receipts, shapes), `second-nemotron/` and `second-ai4privacy/` (mapping.json copied from ext-v6, metrics.json, shapes.json), `v7-dev/metrics.json`, `shapes.py`, `build_summary.py`.
Code: `ensemble_pair` in `privacygate/pipeline.py` (`combine_pair`, `ensemble_pair_peer`); `hybrid.py` is unchanged (the probability-cache key binds its sha256). `evaluate_external.py`: model name `v5v6`, `--pair-grid`.
