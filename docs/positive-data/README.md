# Synthetic positive PII augmentation (pos-v1)

Status (2026-10-02): trainer wiring is ready and checked with in-memory synthetic fixtures only. NO positive model has been
trained; no checkpoint inference/evaluation or positive-data scoring was run in this task; no test split exists for this data.
A separate existing negative pilot is outside this task. This implementation does not start or modify that run.
Synthetic research target, not a privacy guarantee. All-personal-information masking remains the target, not an achieved result.

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
  each source, so boundary exclusions cannot conceal augmentation admission.
- `run-identity-v2` binds positive train and dev separately: exact file-byte SHA256, counts, labels, languages, templates and
  split; positive schema `positive-jsonl-v1`, supported source version `pos-v1`; the ordered final label inventory; and all
  existing negative binding, Micro manifest hash, pinned model, output-path and settings fields. Source version denotes the
  supported protocol, not independently verified provenance of arbitrary input files. Cheap guards run before heavy imports;
  final inventory/classifier-map compatibility is checked after Micro train loading and before any model work or output writes.
- Reuse refuses incomplete/missing/incompatible identities, including `run-identity-v1` and historical checkpoints without
  provenance. No metadata migration. Compatible complete outputs are returned unchanged without retraining/rescoring; when
  completing a compatible checkpoint's missing outputs, existing config/metrics files are never rewritten. Use a fresh run name
  for changed bindings or settings. Malformed input/CLI errors are fixed value-free codes, not parser messages or values.

## Separate positive-development metric

`metrics.json.dev` remains the existing Micro dev result. If and only if `--positive-dev-file` is supplied,
`metrics.json.positive_dev` is a **separate** call to the unchanged strict span evaluator: overall, per-label, per-language,
rows evaluated and rows excluded for broken boundaries. The exact input binding is `positive_dev_input` in metrics and
`positive_dev` in config/identity. There is no pooled headline F1 and no invented result when the file is absent.
Positive dev rows are never concatenated into training. This generator-development metric probes authored positive-template
coverage only, not real-world generalisation, semantic independence or final-test performance. There is no final-test option.

## Code-only checks

    env -u PYTHONPATH python3 scripts/check_positive_training.py
    env -u PYTHONPATH python3 smoke.py
    env -u PYTHONPATH python3 -m privacygate.train_mbert --help

Expected: `POSITIVE TRAINING WIRING OK (synthetic only; no training/evaluation)` and `SMOKE OK`.
The wiring check uses in-memory Micro rows, loader bytes, a character-tokenizer stub, metadata existence markers and an
opaque evaluator routing spy. It neither imports torch/transformers nor reads a corpus, opens a checkpoint or emits scores.

## Next bounded pilot example — NOT run

Only after the separate negative pilot has finished, the alignment diagnosis below has evidence and is integrated, and
execution is explicitly authorized. Ensure the already prepared positive JSONL files are available at the two worktree paths
below (generated files are ignored and do not arrive with a Git branch); stop on missing files/cache/dependencies, never install
or download as a workaround. This positive-only pilot intentionally omits negatives to keep that experiment separate.
The main model/cache/venv are read-only; outputs are in this worktree. Cache access is offline. Run from this worktree:

    cd /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-positive-training-1002
    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
      HF_HOME=/Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.cache/hf \
      /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.venv-train/bin/python \
      -m privacygate.train_mbert --run pos-pilot-1002 \
      --max-train-rows 2000 --max-dev-rows 500 --epochs 1 --batch-size 16 --lr 3e-5 --seed 13 \
      --positive-train-file data/augmentation/positive-train.jsonl \
      --positive-dev-file data/augmentation/positive-dev.jsonl --out-dir "$PWD/models"

With the documented prepared artifacts this admits at most 2000 selected Micro train rows plus all 630 positive train rows,
and at most 500 selected Micro dev rows plus a separate 280-row positive dev evaluation. Retained counts may be lower under
the **unchanged** alignment exclusions. Report measured time/steps, each source's included/retained/excluded counts, Micro
`dev` and separate `positive_dev` metrics before considering a larger run. No timing or model-quality result is claimed here.

Alignment dependence: another agent is diagnosing the original alignment logic. Neither `mbert_data.py` nor `build_windows`
alignment/exclusion logic was changed in this task. Any production correction must be based on that evidence and applied only
after integration, not silently repaired during positive-data wiring.

## Limitations

Names are invented syllable compositions and may coincide with real people by chance; cities are real public place names used as address
components; phone numbers use reserved/fictional-style ranges where known but formats are artificial and not verified to be unassigned;
identity numbers are random strings with no checksum or real national format; no value is a verified real contact or identity. Low
lexical diversity (few templates, modest variants); a model trained on this may learn the template cues. Automated structural checks in
--verify are not human annotation review.
