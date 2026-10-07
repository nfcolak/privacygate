# ext-v6 summary: region-v6 on Gretel TEST, Nemotron-PII, ai4privacy and v7 dev

Value-free: counts, rates and shapes only. Every arm was scored once; v5 Gretel rows are the earlier measurements (not rerun).
Coverage = personal letters/digits covered %; excess = masked chars outside all source annotations / non-annotated chars (upper bound on false masks); rows = rows with exposed letters/digits.

v6 chosen options (EXT-DEV only, `ext-dev-grid.md`): name_threshold 0.1, name_propagation_ext off, ensemble off.
Propagation tied coverage (96.5249) and cost +0.08 point excess, so the rule picked it off. v6 base on EXT-DEV: 94.83 / 1.18.

| set | v5 base | v5 + step-1 | v6 base | v6 + chosen |
|---|---|---|---|---|
| Gretel TEST (4,696 rows) | 88.71 / 4.42 / 883 | 89.67 / 4.83 / 805 | 94.79 / 1.08 / 431 | 96.47 / 1.32 / 328 |
| Nemotron-PII (5,000 docs) | 95.77 / 1.26 / 683 | 96.91 / 1.37 / 545 | 90.91 / 0.23 / 1,423 | 92.03 / 0.28 / 1,308 |
| ai4privacy (5 x 1,000 rows) | 85.43 / 2.37 / 1,092 | 86.55 / 2.60 / 1,006 | 86.98 / 1.42 / 1,113 | 88.77 / 1.60 / 976 |

Cells are coverage % / excess % / rows exposed.

v7 development (not blind; same harness reproduces v5 + step-1 = 19/300 and 334):

| | v4 | v5 (and v5 + step-1) | v6 base | v6 + chosen |
|---|---|---|---|---|
| clean rows masked | 21/300 | 19/300 | 19/300 | 19/300 |
| exposed letters/digits | 111 | 334 | 4,809 | 4,747 |
| gold alnum coverage | | 99.13% (v5 + step-1) | 87.49% | 87.65% |

## Read this first

1. Gretel TEST is not independent for v6. train-v6 contains 23,279 Gretel-train rows (23,272 exact text matches with Gretel train, same generator and templates; none with TEST or EXT-DEV). The Gretel jump (88.7 to 94.8/96.5, excess 4.4 to 1.1/1.3) is in-distribution and is not evidence of generalisation. train-v5 has no Gretel-family rows (32,000 rows).
2. The two new sets have 0 exact-text overlap with train-v6, its dev file, EXT-DEV and Gretel train (`overlap.json`; ai4privacy sample has 4,996 distinct texts of 5,000).
3. On independent text v6 is mixed. Nemotron: coverage -4.9 points (v6 base vs v5 base, and v6 chosen vs v5 + step-1: 92.03 vs 96.91) with about 5x lower excess (0.28 vs 1.37). ai4privacy: +1.6 (base) / +2.2 (chosen vs v5 + step-1) points coverage and lower excess. v7 dev: large regression (exposed letters/digits 334 to 4,747).
4. The chosen v6 option (name_threshold 0.1) raises v6 coverage on every set by +1.1 to +1.8 points for +0.05 to +0.24 excess; clean rows masked on v7 unchanged.

## Out-of-scope masking (alnum chars annotated out of scope and not in-scope gold; not scored as recall or excess)

| set | out-of-scope alnum chars | v5 base | v5 + step-1 | v6 base | v6 + chosen |
|---|---|---|---|---|---|
| Nemotron | 340,600 | 44.6% masked | 47.4% | 5.0% | 6.1% |
| ai4privacy | 21,667 | 47.8% | 49.8% | 26.3% | 30.2% |

v5 base masks far more of what the policy calls out of scope. Nemotron v5 base: url 42%, company_name 42%, date 56%, date_time 65%, http_cookie 63%, api_key 59%; v6 chosen: 0.2%, 3.7%, 1.1%, 0%, 0.1%, 0.4% (occupation 1.6% to 5.1%).
ai4privacy v6 chosen masks CITY 37% (v5 base 57%), ZIPCODE 40% (63%), DATE 19% (48%), TITLE 66% (60%).
Per-label out-of-scope detail is in each `second-*/metrics.json` (`out_of_scope.per_label`).

## v6 top misses (exposed letters/digits; shapes from `shapes.py`, receipts of the v6 + chosen arm)

Gretel TEST (`gretel-test/shapes.json`):
- ADDRESS: 3,188 exposed alnum (96.1% covered); largest pieces are mixed letter+digit (75 pieces, 1,603 chars) and other/punctuated (74, 830) and lowercase (25, 308). Cause hint: the address region stops early or starts late, leaving a house-number/unit/postcode piece or lowercase street word.
- PERSONNAME: 2,729 exposed (96.8%); pieces are `other` shape (67, 787 chars: initials, hyphen/apostrophe forms), one-word capitalised (76, 603), lowercase (41, 459), uppercase (40, 364). Cause hint: cue-free single names and unusual name forms.
- DATEOFBIRTH 92.5% (160 exposed), PASSPORTNUM 90.2% (113), SOCIALNUM 94.0% (75): lowest per-label coverage; small counts.

Nemotron (`second-nemotron/shapes.json`):
- PERSONALREF 62.9% covered, 8,902 exposed: uppercase letter-prefixed codes and 5-10+ digit strings. Cause hint: my mapping adds medical-record and health-plan numbers to PERSONALREF (policy: patient/membership references); train-v6 labels PERSONALREF mainly on customer/employee-style references, so these code shapes are likely outside its training.
- ACCOUNTNUM 76.2% (2,361), IDCARDNUM 63.7%, TAXNUM 73.0%, AGE 34.8%: long digit strings with no cue word, and AGE as bare numbers.
- PERSONNAME 94.4% (2,407): one-word capitalised names.

ai4privacy (`second-ai4privacy/shapes.json`):
- PERSONNAME 93.6% (2,923): one-word capitalised names (given or surname alone), no cue.
- IDCARDNUM 63.3%, DRIVERLICENSENUM 52.1%, PASSPORTNUM 76.2%, SOCIALNUM 68.8%, TAXNUM 68.3%, AGE 32.5%: uppercase alnum codes and bare numbers; country formats differ from Gretel/train templates.
- ADDRESS 70.8% (2,601 exposed; STREET and BUILDINGNUM only): largest pieces are `other` shape (47 pieces, 960 chars) and two-word capitalised (41, 473), i.e. street names. Cause hint: the dataset has street/number fragments inside short sentences; Gretel/train addresses are whole multi-line blocks. Per language, es 83.1 and en 85.3 are the weakest.

v7 dev (`v7-dev/metrics.json`, exposed 4,747): AGE 1,204 of 1,669 exposed, ADDRESS 1,202, USERNAME 872, CREDITCARDNUMBER 383, ACCOUNTNUM 255, PERSONALREF 255, IBAN 285. Families: damaged_carbon_copies, translation_enclosures, helpdesk_turns, signoff_tiles, registration_panels. Cause hint: train-v6 has 578 AGE and 450 USERNAME gold spans versus 1,157 and 168 AGE/USERNAME in train-v5 (AGE halved), and half of its 47k rows are Gretel text that carries no AGE, IDCARDNUM or TAXNUM labels; v7's stress layouts (OCR noise, carbon copies, tiles) are absent from Gretel.

## v6 top excess shapes (masked chars outside every annotation; upper bound, not adjudicated false positives)

- Gretel: EMAIL entities over un-annotated email-like strings (14.9k alnum) are the largest group, then PERSONNAME on `other` and one-word capitalised pieces, ADDRESS on mixed letter+digit pieces, TELEPHONENUM on 10+ digit strings. Cause hint: Gretel leaves some real-looking emails, phones and addresses unannotated (its own annotation gaps), so part of this is not a model error; the old money/number/PERSONALREF excess seen with v5 does not appear in v6's top shapes.
- Nemotron: almost all PERSONNAME: lowercase, one-word capitalised and multi-word capitalised pieces. Cause hint: the 0.1 name threshold masks capitalised words and lowercase tokens that the source marks as other categories or leaves unannotated (the threshold costs +0.05 point here).
- ai4privacy: PERSONNAME on `other`, one-word capitalised and lowercase pieces; ADDRESS on lowercase pieces. Same hint: low-threshold name decisions on capitalised and lowercase words outside the annotated names.

## Files

`ext-dev-grid.{json,md}`, `gretel-test/metrics.json` (+ receipts, shapes), `second-nemotron/` and `second-ai4privacy/` (mapping.json, metrics.json, shapes.json), `v7-dev/metrics.json`, `overlap.json`, `arms-*.json`.
Code: `evaluation/evaluate_external.py` at d7770e7 (additive: v6 alias, grid model list, second-set loaders, multi-arm and v7-arms modes; Gretel scoring unchanged).
Second-set mapping caveats: the Nemotron README names no label table, so labels were read from the data (counts only); fax numbers, medical-record and health-plan numbers are my in-scope choices, and CITY/ZIPCODE/postcode/state/country are out of scope.
