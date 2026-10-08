# ext-rules summary: cue-free ID-code detectors on independent text

Value-free: counts, rates, shapes. Each rules arm measured once per set; baselines are the ext-v6 / ext-step1 measurements (same samples, mappings, metrics, `evaluation/evaluate_external.py` unchanged).
Cells are coverage % / excess % / rows exposed. Gretel TEST is reported only: train-v6 holds Gretel train rows, so it never selects anything.

Rules enabled (chosen on Gretel EXT-DEV + v7 dev, `dev.md`): `it_codice_fiscale`, `fr_nir` (checksum-validated, cue-free). Registered but off (no dev evidence or failed gate): `es_dni_nie`, `de_steuer_idnr`, `gb_nino`, `ch_ahv`, `us_ssn` (v7 clean rows 23/300), `cued_documents`, `cued_social_tax`, `cued_personalref`.

| set | v5 + step-1 | v5 + step-1 + rules | v6 + chosen | v6 + chosen + rules |
|---|---|---|---|---|
| Gretel TEST (4,696 rows; in-distribution for v6, never used to choose) | 89.67 / 4.83 / 805 | 89.69 / 4.83 / 805 | 96.47 / 1.32 / 328 | 96.50 / 1.32 / 326 |
| Nemotron-PII (5,000 docs) | 96.91 / 1.37 / 545 | 96.91 / 1.37 / 545 | 92.03 / 0.28 / 1,308 | 92.03 / 0.28 / 1,308 |
| ai4privacy (5 x 1,000 rows) | 86.55 / 2.60 / 1,006 | 86.55 / 2.60 / 1,006 | 88.77 / 1.60 / 976 | 88.77 / 1.60 / 976 |
| v7 dev (not blind) | 19/300 clean rows masked, 334 exposed alnum | 19/300 clean rows masked, 334 exposed alnum | 19/300 clean rows masked, 4,747 exposed alnum | 19/300 clean rows masked, 4,747 exposed alnum |

## Read this first

1. The rules arm changes almost nothing on the independent sets: Nemotron and ai4privacy are identical to the baselines at every reported digit (coverage, excess, rows exposed, per label, per language, out-of-scope). Neither set holds checksum-valid codice fiscale or NIR values in the sampled rows; ES/DE/GB/CH detectors that would fire there did not qualify on dev (no dev evidence), so they are off.
2. Gretel TEST moves slightly (v5 + step-1 +0.02 point coverage, v6 + chosen +0.03, rows exposed 805 to 805 and 328 to 326, excess unchanged), almost all in SOCIALNUM (French NIR) and Spanish/German text. Gretel TEST is in-distribution for v6 and was not used for any choice.
3. v7 dev is unchanged (19/300 clean rows masked; 334 and 4,747 exposed alnum), as at selection.
4. The big remaining ID gaps on independent text (ai4privacy IDCARDNUM / DRIVERLICENSENUM / PASSPORTNUM / TAXNUM, Nemotron PERSONALREF) are uppercase letter-prefixed codes without checksum; the cue-bound shapes for them showed no dev gain, so a model or cue-vocabulary change would be needed, not a format rule.

## Change on the ID labels (exposed alnum chars / gold alnum chars; coverage %)

### Gretel TEST (4,696 rows; in-distribution for v6, never used to choose)

| label | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| IDCARDNUM | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a |
| DRIVERLICENSENUM | 74 / 1,114; 93.36 | 74 / 1,114; 93.36 | 0 / 1,114; 100.00 | 0 / 1,114; 100.00 |
| PASSPORTNUM | 104 / 1,157; 91.01 | 104 / 1,157; 91.01 | 113 / 1,157; 90.23 | 113 / 1,157; 90.23 |
| SOCIALNUM | 113 / 1,259; 91.02 | 82 / 1,259; 93.49 | 75 / 1,259; 94.04 | 13 / 1,259; 98.97 |
| TAXNUM | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a |
| PERSONALREF | 640 / 3,144; 79.64 | 640 / 3,144; 79.64 | 26 / 3,144; 99.17 | 26 / 3,144; 99.17 |

### Nemotron-PII (5,000 docs)

| label | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| IDCARDNUM | 83 / 1,758; 95.28 | 83 / 1,758; 95.28 | 639 / 1,758; 63.65 | 639 / 1,758; 63.65 |
| DRIVERLICENSENUM | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a |
| PASSPORTNUM | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a |
| SOCIALNUM | 27 / 3,060; 99.12 | 27 / 3,060; 99.12 | 0 / 3,060; 100.00 | 0 / 3,060; 100.00 |
| TAXNUM | 22 / 740; 97.03 | 22 / 740; 97.03 | 200 / 740; 72.97 | 200 / 740; 72.97 |
| PERSONALREF | 881 / 23,982; 96.33 | 881 / 23,982; 96.33 | 8,902 / 23,982; 62.88 | 8,902 / 23,982; 62.88 |

### ai4privacy (5 x 1,000 rows)

| label | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| IDCARDNUM | 778 / 3,867; 79.88 | 778 / 3,867; 79.88 | 1,421 / 3,867; 63.25 | 1,421 / 3,867; 63.25 |
| DRIVERLICENSENUM | 243 / 1,131; 78.51 | 243 / 1,131; 78.51 | 542 / 1,131; 52.08 | 542 / 1,131; 52.08 |
| PASSPORTNUM | 234 / 1,545; 84.85 | 234 / 1,545; 84.85 | 367 / 1,545; 76.25 | 367 / 1,545; 76.25 |
| SOCIALNUM | 149 / 1,339; 88.87 | 149 / 1,339; 88.87 | 418 / 1,339; 68.78 | 418 / 1,339; 68.78 |
| TAXNUM | 199 / 1,616; 87.69 | 199 / 1,616; 87.69 | 512 / 1,616; 68.32 | 512 / 1,616; 68.32 |
| PERSONALREF | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a | 0 / 0; n/a |

## Per language (coverage % / excess %)

### Gretel TEST (4,696 rows; in-distribution for v6, never used to choose)

| language | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| English | 91.37 / 4.78 | 91.37 / 4.78 | 96.73 / 1.15 | 96.73 / 1.15 |
| France | 89.14 / 4.45 | 89.14 / 4.45 | 97.13 / 1.67 | 97.13 / 1.67 |
| German | 86.68 / 4.81 | 86.77 / 4.81 | 94.49 / 1.56 | 94.58 / 1.56 |
| Italian | 88.36 / 5.36 | 88.36 / 5.36 | 96.51 / 1.68 | 96.51 / 1.68 |
| Spanish | 83.53 / 5.07 | 83.61 / 5.07 | 95.84 / 1.59 | 96.07 / 1.59 |

### Nemotron-PII (5,000 docs)

| language | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| English | 96.91 / 1.37 | 96.91 / 1.37 | 92.03 / 0.28 | 92.03 / 0.28 |

### ai4privacy (5 x 1,000 rows)

| language | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| de | 91.15 / 4.71 | 91.15 / 4.71 | 91.59 / 2.43 | 91.59 / 2.43 |
| en | 84.85 / 2.90 | 84.85 / 2.90 | 85.28 / 1.66 | 85.28 / 1.66 |
| es | 82.06 / 1.71 | 82.06 / 1.71 | 83.15 / 1.06 | 83.15 / 1.06 |
| fr | 89.19 / 1.39 | 89.19 / 1.39 | 90.91 / 1.06 | 90.91 / 1.06 |
| it | 85.51 / 2.46 | 85.51 / 2.46 | 92.97 / 1.84 | 92.97 / 1.84 |

## Out-of-scope masking (% of out-of-scope alnum chars masked)

| set | v5 + step-1 | + rules | v6 + chosen | + rules |
|---|---|---|---|---|
| Nemotron-PII (5,000 docs) | 47.41 | 47.41 | 6.05 | 6.05 |
| ai4privacy (5 x 1,000 rows) | 49.83 | 49.83 | 30.19 | 30.19 |

## Top remaining miss shapes (rules arms; alnum chars exposed, from `shapes-*.json`)

- Gretel TEST / v5-step1-rules: PERSONNAME other (265 pieces, 3,649 chars); ADDRESS mixed-alnum (193 pieces, 3,361 chars); PERSONNAME capitalised-words(n=1) (353 pieces, 2,388 chars); PERSONNAME capitalised-words(n=2) (144 pieces, 1,798 chars); ADDRESS other (143 pieces, 1,794 chars); PERSONNAME upper (117 pieces, 1,548 chars)
- Gretel TEST / v6-chosen-rules: ADDRESS mixed-alnum (75 pieces, 1,603 chars); ADDRESS other (74 pieces, 830 chars); PERSONNAME other (67 pieces, 787 chars); PERSONNAME capitalised-words(n=1) (76 pieces, 603 chars); PERSONNAME lower (41 pieces, 459 chars); PERSONNAME upper (40 pieces, 364 chars)
- Nemotron-PII / v5-step1-rules: PERSONNAME capitalised-words(n=1) (481 pieces, 2,730 chars); USERNAME lower (97 pieces, 952 chars); PERSONALREF upper (92 pieces, 707 chars); DATEOFBIRTH digits5-9 (47 pieces, 376 chars); ADDRESS mixed-alnum (17 pieces, 255 chars); USERNAME mixed-alnum (18 pieces, 190 chars)
- Nemotron-PII / v6-chosen-rules: PERSONALREF upper (652 pieces, 6,955 chars); PERSONNAME capitalised-words(n=1) (377 pieces, 2,334 chars); ACCOUNTNUM digits10+ (101 pieces, 1,136 chars); PERSONALREF digits10+ (105 pieces, 1,064 chars); PERSONALREF digits5-9 (116 pieces, 807 chars); ACCOUNTNUM upper (32 pieces, 685 chars)
- ai4privacy / v5-step1-rules: PERSONNAME capitalised-words(n=1) (703 pieces, 4,460 chars); PERSONNAME capitalised-words(n=2) (170 pieces, 2,152 chars); IDCARDNUM upper (80 pieces, 752 chars); ADDRESS other (37 pieces, 713 chars); PERSONNAME other (27 pieces, 371 chars); ADDRESS capitalised-words(n=1) (41 pieces, 359 chars)
- ai4privacy / v6-chosen-rules: PERSONNAME capitalised-words(n=1) (363 pieces, 2,222 chars); IDCARDNUM upper (142 pieces, 1,384 chars); ADDRESS other (47 pieces, 960 chars); PERSONNAME capitalised-words(n=2) (43 pieces, 528 chars); ADDRESS capitalised-words(n=2) (41 pieces, 473 chars); DRIVERLICENSENUM upper (36 pieces, 424 chars)
