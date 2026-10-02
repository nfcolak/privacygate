# Masking coverage: two separate synthetic development populations

Measurement item1 is complete for these datasets only. No item2 repair/training is authorized or performed. The easy positive dev and the frozen stress dev are different populations, not a before/after model comparison. The same expanded checkpoint is used; no incumbent rescore, threshold selection or model/data changes.

## Original easy positive dev — preserved v1 history

Evidence: [positive-dev/metrics.json](positive-dev/metrics.json), [manifest](positive-dev/manifest.json), [receipt](positive-dev/receipt.json), [findings](positive-dev/findings.md). All five original artifacts remain byte-identical to commit `225ec00a407a44508f4937bac2a204dd264bc590`. `masking-union-v1` and its original scorer/source hashes are still valid historical bindings; these rows were not rescored under v2.

280 positive rows, 920 gold spans; no clean controls. mBERT and hybrid union each: 918/920 all-character complete spans, 278/280 fully masked positive rows, 7430/7441 covered gold characters; 11/7182 Unicode alphanumeric characters uncovered in two partial USERNAME spans, 0 untouched spans, 0 annotation-relative excess characters. Regex: 0/920 complete spans. ACCOUNTNUM and PERSONALREF were each fully masked 40/40 despite strict class-specific misses. Component address labels do not establish complete address regions.

## Frozen stress dev — one v2 measurement

Evidence: [stress metrics](stress-dev/metrics.json), [frozen scoring manifest](stress-dev/manifest.json), [receipt](stress-dev/receipt.json), [engine/language/label/family aggregates](stress-dev/summary.md), [actual command](stress-dev/scoring-command.txt), [routing](stress-dev/routing.json). Separate original generator history: [frozen generator manifest](../../masking-stress/manifest.json), unchanged.

110 rows: 100 positive, 10 impersonal clean; 370 gold spans, 9130 original gold characters, 7854 Unicode alphanumeric gold characters, 137089 dataset bytes. All rows scored once under regex, mbert confidence=0 and hybrid_union confidence=0. One checkpoint load and one completed raw-model sweep reused by both learned arms; MPS, 5.064439 seconds within the unchanged 360-second bound. No predicted fragment, row identifier, raw value or per-example record is emitted.

| Engine | Complete spans | Positive rows complete | Covered gold chars | Exposed Unicode alnum | Partial / untouched | Excess chars | Clean masked / total |
|---|---:|---:|---:|---:|---:|---:|---:|
| hybrid_union | 100/370 | 0/100 | 6898/9130 | 1609/7854 | 231 / 39 | 0 | 0/10 |
| mbert | 100/370 | 0/100 | 6898/9130 | 1609/7854 | 231 / 39 | 0 | 0/10 |
| regex | 10/370 | 0/100 | 350/9130 | 7534/7854 | 0 / 360 | 0 | 0/10 |

For each learned arm, 2232 gold characters are uncovered: 1609 Unicode letters/digits and 623 non-alphanumeric formatting characters. 114 spans expose at least one alphanumeric character; 156 additional incomplete spans have formatting-only gaps. These are separate from all-character completeness. Unmasked spaces/punctuation alone are not claimed to expose identifier content; alnum-only coverage is not a privacy guarantee. Regex leaves 8780 gold characters uncovered (7534 alnum, 1246 nonalnum).

All three arms mask 0/10 clean controls and 0/3233 clean characters. No excess beyond annotations was observed. These small authored controls and annotation-relative excess do not prove real-world false-positive safety; clean completeness is N/A, not 100%.

### Class confusion is not literal exposure

mBERT raw/final classification: 19 exact correct-label, 29 exact different-label, 52 fully covered nonexact, 231 partial, 39 untouched. Hybrid raw/final: 22 / 29 / 49 / 231 / 39. Coverage is identical, not all detection diagnostics: regex changes three EMAIL detections from combined/nonexact to exact-correct. No prediction is filtered using gold.

ACCOUNTNUM is 10/10 literally complete despite 0 exact correct-label detections (5 exact different-label, 5 nonexact fully covered); IDCARDNUM is 20/20 complete despite 0 exact correct-label detections. PERSONALREF is 17/30 complete (9 exact different-label, 8 nonexact full), with 3 partial and 10 untouched. Confusion does not excuse actual uncovered characters. ADDRESS and PERSONNAME are explicit GOLD-only diagnostic regions, not new checkpoint prediction classes.

### Stress per-family — mBERT and hybrid have the same coverage

| Group | Complete spans | Covered gold chars | Exposed Unicode alnum | Positive rows complete | Partial / untouched | Formatting-only incomplete spans |
|---|---:|---:|---:|---:|---:|---:|
| account | 10/20 | 338/348 | 0/308 | 0/10 | 10 / 0 | 10 |
| full_address | 0/20 | 570/833 | 157/706 | 0/10 | 20 / 0 | 10 |
| identity | 20/40 | 538/558 | 0/478 | 0/10 | 20 / 0 | 20 |
| long_text | 2/60 | 476/1714 | 1036/1450 | 0/10 | 19 / 39 | 10 |
| multiple_entities | 33/70 | 1596/1926 | 197/1632 | 0/10 | 37 / 0 | 14 |
| names | 0/30 | 754/784 | 0/714 | 0/10 | 30 / 0 | 30 |
| personalref | 10/20 | 423/433 | 0/378 | 0/10 | 10 / 0 | 10 |
| phone | 1/20 | 432/521 | 64/434 | 0/10 | 19 / 0 | 10 |
| repeated_values | 14/70 | 1378/1610 | 155/1386 | 0/10 | 56 / 0 | 32 |
| username | 10/20 | 393/403 | 0/368 | 0/10 | 10 / 0 | 10 |

### Stress per-language — mBERT and hybrid have the same coverage

| Group | Complete spans | Covered gold chars | Exposed Unicode alnum | Positive rows complete | Partial / untouched | Formatting-only incomplete spans |
|---|---:|---:|---:|---:|---:|---:|
| de | 19/74 | 1338/1836 | 377/1590 | 0/20 | 47 / 8 | 32 |
| en | 19/74 | 1432/1822 | 262/1554 | 0/20 | 48 / 7 | 30 |
| es | 19/74 | 1390/1854 | 341/1602 | 0/20 | 47 / 8 | 33 |
| fr | 22/74 | 1371/1820 | 322/1562 | 0/20 | 44 / 8 | 31 |
| it | 21/74 | 1367/1798 | 307/1546 | 0/20 | 45 / 8 | 30 |

### Stress per-gold-label — mBERT and hybrid have the same coverage

| Group | Complete spans | Covered gold chars | Exposed Unicode alnum | Positive rows complete | Partial / untouched | Formatting-only incomplete spans |
|---|---:|---:|---:|---:|---:|---:|
| ACCOUNTNUM | 10/10 | 110/110 | 0/90 | 10/10 | 0 / 0 | 0 |
| ADDRESS | 0/30 | 752/1785 | 733/1464 | 0/30 | 21 / 9 | 0 |
| DRIVERLICENSENUM | 10/10 | 110/110 | 0/90 | 10/10 | 0 / 0 | 0 |
| EMAIL | 10/10 | 350/350 | 0/320 | 10/10 | 0 / 0 | 0 |
| IDCARDNUM | 20/20 | 200/200 | 0/160 | 20/20 | 0 / 0 | 0 |
| PASSPORTNUM | 0/10 | 100/110 | 0/90 | 0/10 | 10 / 0 | 10 |
| PERSONALREF | 17/30 | 383/585 | 166/480 | 17/30 | 3 / 10 | 0 |
| PERSONNAME | 0/150 | 3262/3640 | 218/3330 | 0/100 | 140 / 10 | 140 |
| TELEPHONENUM | 3/50 | 997/1415 | 323/1080 | 3/40 | 47 / 0 | 1 |
| USERNAME | 30/50 | 634/825 | 169/750 | 22/40 | 10 / 10 | 5 |

Per-gold-label row success refers only to that label, not every label on the row. Per-label excess/text/mask counts are row-scoped and not additive. Disjoint language/family aggregates are additive. Full regex and raw-versus-final label diagnostics are in the linked stress artifacts.

### Actual tokenizer boundaries and long-text failure

Evidence: [tokenization-preflight.json](stress-dev/tokenization-preflight.json), [token-offset-extent.json](stress-dev/token-offset-extent.json). Both are separate prediction-independent, hash-bound diagnoses, saved before inference; they do not revise the original generator manifest.

The cached pinned tokenizer actually returned 120 inference windows: 100 rows with one, 10 long rows with two. Long rows are 8341–8752 characters. Actual noninitial starts/nonfinal ends yield 20 internal window cuts and ZERO gold spans crossing those cuts. Therefore no cut-crossing robustness claim is supported; character-placement schedules did not establish crossings.

Long_text: 2/60 all-character complete spans, 0/10 fully masked rows, 19 partial and 39 untouched, 1036/1450 alnum characters exposed. Actual encode offsets have no overlap with 39/60 long-text gold spans; all 39 lie beyond the final encoded token end (aggregate range 2013–2553 while rows exceed 8341 characters). The same cached tokenizer with truncation=False has 1671–2202 content tokens per long row and overlaps all long-text gold spans. This is a demonstrated inference tokenization/extent failure, not a gold-span crossing failure or a proven model-quality explanation. The unchanged scorer still measured against the entire original text/gold, including those omitted spans; no rows/spans were dropped, edited or repaired.

### Remaining observed failures and unresolved gates

- Whole ADDRESS regions fail: 0/30 complete; 21 partial, 9 untouched; 733/1464 alnum characters exposed, not merely separator gaps. The dedicated full_address family exposes 157/706 alnum characters even without long text.
- Long-text later placements are not represented by the existing inference encoding: 39 untouched spans, with 1036 exposed alnum characters across the long_text family. No encoding/model fix or repair-and-rescore was performed.
- Phones: 3/50 complete, 47 partial, 323/1080 alnum exposed. USERNAME: 30/50 complete with 169/750 alnum exposed. PERSONALREF: 17/30 complete with 166/480 alnum exposed.
- PERSONNAME: 0/150 all-character complete; 140 formatting-only partials, 10 untouched with 218 alnum characters exposed. PASSPORTNUM: 0/10 all-character complete but 0/90 alnum exposed; these are formatting gaps, not evidence that all passport content remained visible.
- Human annotation quality/completeness, provenance, semantic/translation independence, final split gates and final-test authorization remain unresolved. Source-literal checks do not establish corpus-wide or real-world independence. No Micro corpus, test, real/company data, training/tuning, installation/download, remote or push was used in this task.

## Exact bindings

Checkpoint SHA256: `0058a5c93c2ef14c5f65daf8ae8afc061851acf8d5cf5d52ba0342f578d9cac9`.
Original positive-dev dataset SHA256: `7cc5c56f555021d135118e9e6b772e5fe8271cf887ddba3aa38530f3ac777a42`.
Stress-dev dataset SHA256: `b901873cbdd3715aaae2c78477193fecb3fd47410344fdb240ce75abdbfb6cbf`.
Tokenizer: `google-bert/bert-base-multilingual-cased` @ `3f076fdb1ab68d5b2880cb87a0886f315b8146f8`; exact cached asset and source hashes are in each frozen scoring manifest and the stress boundary diagnosis.
New scorer/report: `masking-union-v2`; interval-union formulas unchanged, GOLD-only diagnostic label admission, stress-only 12000-character cap, finite loader guards, and frozen-family aggregation added. Original positive limits and v1 history are unchanged.
Agent routing: `gpt-6.1-sol / openai-codex / high`, restricted launcher attempt=1, no fallback. This diagnostic establishes coverage only on these annotated synthetic development populations; no all-real-personal-data, production or privacy claim.
