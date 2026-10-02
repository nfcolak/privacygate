# Synthetic positive PII augmentation (pos-v1)

Status (2026-10-02): positive train/dev wiring and corrected production window construction are integrated. One expanded corrected-alignment synthetic pilot has now trained: 1,979 retained Micro + 630 positive + 1,000 negative train rows; separate evaluations used 495 Micro-dev and 280 positive-dev rows. Micro strict F1 was 0.7429782723900371 and separate positive-dev strict F1 was 0.7545271629778673. ACCOUNTNUM and PERSONALREF each had strict exact-span+correct-label TP=0/support=40; USERNAME TP=24/support=40. No class-agnostic masking-coverage diagnostic was run, so these results do not show whether all characters in those spans were left visible. The copied checkpoint is relocation-only and not resumable at the delivery output path; see `../runs/pos-neg-alignment-pilot-1002/`. This is not evidence of readiness or improvement over unmatched historical runs. Full training, final-test evaluation, matched incumbent comparison, and semantic-quality, provenance and split gates remain pending. Synthetic research only, not a privacy guarantee.

Artifacts (generated JSONL is gitignored under data/augmentation/; only code and the value-free manifest are committed):
- data/augmentation/positive-train.jsonl  630 rows, 105 templates (3 per family/language, 6 variants each)
- data/augmentation/positive-dev.jsonl    280 rows,  70 templates (2 per family/language, 4 variants each); DEVELOPMENT only
- docs/positive-data/manifest.json        counts, hashes, disjointness flags, generator revision (pos-v1), template-set hash

Generate / verify:

    env -u PYTHONPATH python3 scripts/make_positives.py
    env -u PYTHONPATH python3 scripts/make_positives.py --verify

Families (EN/DE/FR/IT/ES each, present in both splits): names, phone, identity (IDCARDNUM, PASSPORTNUM, DRIVERLICENSENUM),
address (STREET, BUILDINGNUM, ZIPCODE, CITY plus the owner's name), username, account, personalref. Every name, number, address
component and code in a row is a labelled span; fixed template text contains no digits. Spans are recorded during string
assembly (no find/replace), and entries hold only start/end/label.

## Labels

Existing exact labels: GIVENNAME, SURNAME, TELEPHONENUM, IDCARDNUM, PASSPORTNUM, DRIVERLICENSENUM, STREET, BUILDINGNUM, CITY, ZIPCODE.
New, initial proposed operational labels (not a taxonomy, not a legal classification, no trained support, not exhaustive):
- USERNAME: handle/account name explicitly stated as belonging to an invented person.
- ACCOUNTNUM: non-IBAN membership/customer/loyalty/library number explicitly tied to an invented person.
- PERSONALREF: order/tracking/case reference explicitly tied to an invented person. Shapes vary; some are IBAN-shaped strings with an
  invalid checksum (23 rows) and remain positive: an invalid checksum never makes a person-linked code negative.
Generic codes without person context are NOT labelled personal here; they belong to the ambiguity pool of docs/scope/masking-policy.md.
No catch-all label is introduced for unsupported details. Health, narrative, biometric and other categories remain open.

## Split protocol

Train and dev use different template pools (template IDs and template strings disjoint) and different invented-name onsets, street stems,
cities and handle stems; code-like values already used in train are rejected in dev. The manifest records disjoint flags for template IDs,
template strings, row IDs, exact texts and the value pools. Pools are authored, not randomly split, so dev is NOT evidence of
generalisation beyond this generator: dev templates are written by the same author in the same style (semantic independence is not proven).
Do not feed dev rows to training. `load_positive_file(path, allowed_split="train")` rejects a dev file unless allowed_split="dev".

## Loader

`privacygate.positive_data.load_positive_file(path, allowed_split="train", forbid_ids=()) -> (rows, binding)`: regular file only, at most
16 MiB, 20000 lines, 32 KiB per line, 2000 chars per text, 32 annotations per row; exact six row keys and three mask keys; ints only
(bool rejected); 0 <= start < end <= len; sorted non-overlap; label allowlist; unique row IDs (and disjoint from forbid_ids); split must equal
allowed_split. Errors are fixed `pos_*` codes and never echo input. binding = sha256 of file bytes, rows, per_language, per_label, templates, split.
Trainer options are `--positive-train-file PATH` and `--positive-dev-file PATH`; admission passes the exact train/dev split
explicitly to this loader. Positive IDs must be disjoint from **all** original Micro train/dev manifest IDs, admitted negatives,
and the other positive split (checks happen before caps or model imports). Local SHA256 keys over exact source texts
(regardless of language) and template IDs refuse positive train/dev overlap; generator manifest flags are not trusted.
These checks do not prove semantic independence.

## Training wiring and provenance

- Inventory is the sorted union of labels from **all original Micro TRAIN rows** plus positive TRAIN annotations, using the
  original `O`, `B-<label>`, `I-<label>` ordering. Dev never discovers classes. Dev annotations absent from the training
  inventory are refused before fitting; unknown labels are not dropped. With no positive file the original label order remains.
- USERNAME, ACCOUNTNUM and PERSONALREF receive B/I classes when present in positive train. A fresh classifier is initialized
  from the existing pinned `google-bert/bert-base-multilingual-cased` base revision, **not** from `full-1`. This is implemented
  support, not evidence that those labels have been trained or learned. Neither `full-1` nor historical outputs are modified.
- `--max-train-rows` limits Micro only. Positive train and optional negatives are each appended once; existing batch shuffling
  handles the combined data. `micro_train_rows_available`, `micro_train_rows_selected`, `positive_train_rows_included`,
  `negative_train_rows_included` and `train_row_counts` retain separate included/retained/excluded-after-windowing counts for
  each source, so alignment/coverage exclusions cannot conceal augmentation admission.
- `run-identity-v3` binds positive train and dev separately: exact file-byte SHA256, counts, labels, languages, templates and
  split; positive schema `positive-jsonl-v1`, supported source version `pos-v1`; the ordered final label inventory;
  `alignment_policy=whole-row-gate-contained-bio-crossing-ignore-full-coverage-v1` and
  `alignment_source_version=window-alignment-v1`; and all existing negative binding, Micro manifest hash, pinned model,
  output-path and settings fields. Source versions denote supported code/protocol, not verified provenance of arbitrary inputs.
  Cheap guards run before heavy imports; final inventory/classifier-map compatibility is checked after Micro train loading
  and before any model work or output writes.
- Reuse refuses incomplete/missing/incompatible identities, including `run-identity-v1`, prior positive `run-identity-v2`,
  changed alignment versions and historical checkpoints without provenance. No metadata migration. Compatible complete
  outputs are returned unchanged without retraining/rescoring; when completing a compatible checkpoint's missing outputs,
  existing config/metrics files are never rewritten. Use a fresh run name for changed bindings/settings. Malformed input/CLI
  errors are fixed value-free codes, not parser messages or values.

## Separate positive-development metric

`metrics.json.dev` remains the existing Micro dev result. If and only if `--positive-dev-file` is supplied,
`metrics.json.positive_dev` is a **separate** call to the same strict span evaluator: overall, per-label, per-language,
rows evaluated, compatible total `rows_excluded_broken_boundary`, plus `rows_excluded_by_reason` and `alignment_stats`.
The compatible broken-boundary fields now count ALL excluded rows (whole-row broken/lost, overlapping gold, incomplete coverage);
reason events may overlap. Contained-span window failures are separately counted in `windows_discarded_alignment`.
The exact input binding is `positive_dev_input` in metrics and `positive_dev` in config/identity.
There is no pooled headline F1 and no invented result when the file is absent.
Positive dev rows are never concatenated into training. This generator-development metric probes authored positive-template
coverage only, not real-world generalisation, semantic independence or final-test performance. There is no final-test option.

## Code-only checks

    env -u PYTHONPATH python3 scripts/check_positive_training.py
    env -u PYTHONPATH python3 smoke.py
    env -u PYTHONPATH python3 -m privacygate.train_mbert --help

Expected: `POSITIVE TRAINING WIRING OK (synthetic only; no training/evaluation)` and `SMOKE OK`.
The wiring check uses in-memory Micro rows, loader bytes, a character-tokenizer stub, metadata existence markers and an
opaque evaluator routing spy. It neither imports torch/transformers nor reads a corpus, opens a checkpoint or emits scores.

## Corrected alignment and synthetic proof

New construction preserves the whole-row broken/lost gate, ignores wholly outside spans per window, uses existing BIO for
contained spans, sets crossing gold tokens to IGNORE, and requires every gold span to be fully represented in a retained window.
Otherwise the row is excluded explicitly for incomplete coverage. See `docs/data-audit/micro/diagnosis/implementation.md`.
Prediction decoding still uses original offsets and never consults gold ignore positions: partial/duplicate span errors remain.
This is NOT a general long-text masking solution or a new scorer. Historical full-1 is an unmatched baseline; a later authorized
comparison must score both models on identical retained dev IDs with the same scorer/preprocessing. No new checkpoint scoring now.

Executed integration checks: existing smoke once (SMOKE OK), original five positive-wiring assertion groups, production window
synthetic checks (including uncensored prediction offsets and old identity refusal), both generators --verify. One synthetic
contained-boundary fixture was repaired after an initial failure; no production safeguard was removed and smoke was not rerun.
Offline pinned cached-tokenizer construction on the generated SYNTHETIC positives only retained all 630 train / 280 dev rows,
all 1,980 train / 920 dev gold spans across all 13 labels; zero exclusions. This proves structural label coverage, not annotation
semantics, provenance, independence or learned model quality. No model loaded/scored, no Micro/held-out data opened in integration.

## Next bounded pilot example — executed

The expanded corrected-alignment pilot was executed once. Its exact bound command is recorded in `docs/runs/pos-neg-alignment-pilot-1002/run-manifest.json`; see also the run's `summary.md` and `artifact-location.json`. It ran from the original pilot worktree, not this delivery worktree. This is not a new run proposal: do not rerun it. The original run identity and output path remain unchanged; the copied checkpoint is not resumable at this delivery path. Synthetic results do not establish readiness or improvement over unmatched historical runs. Full training, final-test evaluation, matched incumbent comparison, and semantic-quality, provenance and split gates remain pending.


## Limitations

Names are invented syllable compositions and may coincide with real people by chance; cities are real public place names used as address
components; phone numbers use reserved/fictional-style ranges where known but formats are artificial and not verified to be unassigned;
identity numbers are random strings with no checksum or real national format; no value is a verified real contact or identity. Low
lexical diversity (few templates, modest variants); a model trained on this may learn the template cues. Automated structural checks in
--verify are not human annotation review.
