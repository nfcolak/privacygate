# Stage 1 dataset audit verdict

Verdict: AUDITED_NOT_TRAINING_READY. This is a full-row structural/lexical audit and provisional split selection, not a semantic quality certification, synthetic-provenance proof, performance result or training authorization.

## Frozen source and scope

Candidate: `ai4privacy/openpii-masking-mini-10k`, revision `ad851605dfd3c1a3fefe51c8d8f1cc0e4a6853d0`. `source.json` freezes source identity, pinned metadata endpoint, retrieval date, claimed CC BY 4.0 license and SHA256/size of the subset README and both Parquet files. The pinned API returned this exact revision before download. No upstream million-row files, model artifacts or user/private-company data were accessed; candidate synthetic provenance remains unresolved. Historical card counts were hypotheses; measurements below come from both complete local Parquet files.

Raw source, annotation values and token strings stayed local in ignored `data/raw`. Reports contain categories, aggregate counts and SHA256 identifiers, never source rows or entity values. No downloaded content was submitted to any service. Only public pinned GET requests and one isolated dependency install were used; no paid APIs.

## Measured full population

- Physical files: 9,000 train and 1,000 validation; all 10,000 rows examined.
- 23 language codes, 19 span labels; 81,471 spans and 1,331,891 supplied tokens.
- Zero empty source strings, empty annotation lists, all-label target-free rows or empty token sequences. EMAIL-free rows are not all-label clean negatives. No IBAN label is present.
- All supplied character spans have valid, nonoverlapping Python Unicode-code-point half-open bounds and exactly match their locally compared annotation values. Zero span-value, label-index, masked-text reconstruction, token/class length, BIO grammar or per-row BIO-entity-count failures.
- Every embedded `split` field says `train`, including the 1,000 physical validation rows. This is a metadata warning, not a reason to rewrite rows. Physical file identity remains authoritative.
- No duplicate `uid` hashes, exact source strings or normalized entity-masked templates, within or across physical splits.

## Token alignment gate

Supplied token arrays do not include offsets or a frozen tokenizer/vocabulary revision. All rows received length, legal-label, BIO-transition and B-label/entity-count checks. Local literal WordPiece reconstruction (remove `##`, skip only Unicode whitespace, require consecutive exact matches) supported original-text position inference for 5,202 rows; 4,798 could not be inferred. The latter comprise 4,789 rows where inference first stopped at `[UNK]` and 9 literal reconstruction failures; 4,794 rows contain `[UNK]` in total because some fail earlier. These rows are unverified, not silently repaired or declared malformed.

On exactly reconstructable rows, 123 rows have inferred BIO entity-boundary discrepancies; 19 rows have token/span-boundary crossings and 2 rows have token/span-label discrepancies. These findings are structural warnings under the disclosed inference method, not semantic annotation judgments. All 123 affected rows are quarantined from allocation. In the five-language selection, this excludes 54 rows, including the 3 boundary-crossing and 1 label-discrepancy rows (overlapping reasons). Hash-only excluded manifests preserve reasons. No source annotation or token label was changed. Unsupported inference by itself does not exclude a row; this is why the remaining manifests are provisional, not certified aligned token-classification data.

## Lexical leakage method and limits

Exact source key: SHA256 of original UTF-8 source. Template key: replace annotated spans with typed, index-free `[LABEL]` markers; normalize NFKC, casefold and collapse whitespace; SHA256 the result. No raw template is emitted.

Near matching uses set Jaccard over unique character 5-grams of these templates, with a predeclared threshold 85/100 and a minimum of 20 unique shingles. Complete prefix-filter candidates use globally frequency-sorted shingles and a length-ratio filter; all candidate pairs receive exact integer Jaccard comparison. This is not a sampled preview or model-based comparison. All 10,000 unique templates qualify; 46,132 candidate pairs were checked, with zero matches and zero cross-official-split matches. The algorithm's minimum-length and lexical threshold remain limits even though no rows were too short in this revision.

Zero measured lexical overlap is not proof of semantic, translation, latent generation-family or real-world independence. Unannotated values are not masked by the template algorithm. No similarity threshold was tuned from labels or performance. Matching pairs, if present on a rerun, are unioned transitively before allocation, and transitive endpoints need not meet the pairwise threshold.

## Five-language manifests and split decision

Official validation is not retained as final. This is a conservative decision despite zero measured leakage: the publisher describes row-level shuffle/splitting, not generation-family grouping, and literal similarity checks cannot prove source-family independence. Reassignment provides explicit measured exact/template/near-group disjointness; it does not create unobserved semantic independence.

Selection contains 4,272 rows (3,837 physical train + 435 physical validation). 54 target-language rows are excluded for observed inference discrepancies, leaving 4,218 provisional allocated rows. 5,728 non-target-language rows are outside the selection. Groups are constructed over all 10,000 rows before language selection or quality exclusions.

| Language | Selected | Excluded | Train | Dev | Test |
|---|---:|---:|---:|---:|---:|
| EN | 1256 | 13 | 991 | 135 | 117 |
| DE | 841 | 5 | 679 | 84 | 73 |
| FR | 918 | 4 | 739 | 76 | 99 |
| IT | 625 | 11 | 487 | 69 | 58 |
| ES | 632 | 21 | 481 | 53 | 77 |
| Total | 4272 | 54 | 3377 | 417 | 424 |

Every one of the 19 observed labels has nonzero entity support in every language of each allocated split. Full entity counts and rows-with-label counts are saved by language, source split and assigned split in `audit.json` and `data/manifests/split-policy.json`. Small support is not evidence of statistically sufficient evaluation: the minimum entity support for a language/label cell is 9 in dev and test.

Seed: `privacygate-stage1-20260930`. Group membership is the transitive union of exact source hashes, masked-template hashes and measured near matches. Group ID is SHA256 of `group:` followed by sorted hashed row IDs, colon-delimited. Assign `floor(100 * int(SHA256(seed + ':' + group_id), 16) / 2**256)` buckets 0..79 to train, 80..89 to dev and 90..99 to test. No label stratification, support-based retries, threshold tuning or performance feedback. Manifest entries sort by hashed row ID. Desired 80/10/10 proportions are probabilistic, not exact quotas. In this revision all full-population groups are singletons.

The generator programmatically verifies zero train/dev/test overlap for row IDs, exact hashes, template hashes and transitive group IDs. It also verifies that allocated plus excluded row IDs partition the selection exactly. `--offline --verify` recomputes every row, group, audit and manifest and byte-compares all outputs, including output hashes. `output-hashes.json` freezes generated evidence file bytes, excluding itself.

## Reproducibility and remaining gates

Commands and environment setup are in the repository README. Recorded execution: Python 3.9.6, PyArrow 21.0.0, macOS arm64; only PyArrow is an additional runtime dependency. A failed initial install of unavailable PyArrow 23.0.1 was corrected to the successfully installed pinned 21.0.0. Exact audit JSON comparison includes runtime/schema metadata, so use the recorded environment for byte-identical full-report verification; row-ID and allocation logic does not depend on Python random state.

Before any training: resolve publisher synthetic-provenance wording, decide semantic annotation review and unknown-token/offset handling, and authorize the next stage explicitly. Ambiguous subset wording does not prove that actual people's data is present; structural validity cannot establish synthetic provenance either. Provenance research is separately owned (`provenance.md` and `provenance-sources.json`) and untouched by this audit branch. No model, training, evaluation, detector, UI or remote repository changes were made.
