# Synthetic clean negatives (train only)

Status: code prepared; NO training run, no test split use. Synthetic research only; no privacy guarantee.

Semantics: generic impersonal statements (nature, objects, general knowledge), EN/DE/FR/IT/ES, 200 rows per
language (1000 total), 8 frame templates per language (`neg-<lang>-t0..t7`), no digits. Excluded by construction:
names, person-linked references, identifiers/order/tracking/reference codes, contact details, addresses, dates,
ambiguous sensitive context. Existing decoys are NOT used as negatives.

Limitations: low lexical diversity (6 subjects x 6 predicates x 8 frames per language); rows from one frame
share structure; independence from dev/test challenge templates is by separate authoring only (those texts were
not consulted), not proven. A model trained with them may over-learn "plain generic prose is clean".

Generate / verify (output is gitignored under data/augmentation/; manifest docs/augmentation/manifest.json is value-free):

    env -u PYTHONPATH python3 scripts/make_negatives.py
    env -u PYTHONPATH python3 scripts/make_negatives.py --verify

Generator v2 (`neg-v2`): German frames that previously combined "dass" with main-clause word order now use
colon-introduced main clauses ("Man weiß allgemein: Der Fluss ..."), which are grammatical with the same
predicates. Scope, languages, 200 rows per language and train-only behaviour are unchanged; the manifest hash
differs from `neg-v1`. No held-out test text was read to build or filter examples.

Loader (`--negative-train-file`) fails closed with a value-free code only (`ValueError("neg_...")`; no text,
keys, types or offsets are echoed): the file must be a regular file of at most 16 MiB (read is bounded before
parsing); at most 20000 non-empty lines of at most 32 KiB each, counted before any JSON parsing; every row an
object with exactly the six keys, string fields of the right type, split=train, languages en/de/fr/it/es, empty
annotation list, unique IDs (also disjoint from Micro train/dev IDs), non-blank text <= 2000 chars, no digits,
no exact duplicates. These are structural checks; they do not prove that a text is free of personal information.

Run-reuse guard (`privacygate/train_guard.py`, evaluated in `train_mbert` before importing torch or touching
any corpus/model): a new run records `run_identity` (run name, model+revision, epochs, batch size, lr, seed,
window settings, max rows, Micro manifest hash, augmentation sha256 + row/language/template counts or null, and
the resolved output directory) in `train_info.json` and `docs/runs/<run>/config.json`. An existing run is reused
only when a complete checkpoint's identity equals the requested one. Refused (exit 2, code only): incomplete
or symlinked checkpoint files, unparseable/oversized metadata, config/identity mismatch (including a different
augmentation or output path), recorded history without a checkpoint, and every pre-existing run without
`run_identity` (e.g. `pilot`, `full-1`) - historical runs are never migrated, rewritten or asserted compatible.
Negative rows are appended after positive selection (`--max-train-rows` applies to Micro only); labels come from
the original Micro train. Default runs without `--negative-train-file` keep the original training semantics (`negative_train: null`).

## Later pilot (NOT run; needs measured timing and separate approval)

    cd <worktree> && HF_HUB_OFFLINE=1 env -u PYTHONPATH <.venv-train python> -m privacygate.train_mbert \
      --run neg-pilot --max-train-rows 2000 --max-dev-rows 500 --epochs 1 \
      --negative-train-file data/augmentation/negatives-train.jsonl

Pending: bounded preflight timing (steps/sec from a small run) -> estimate -> approval. Full training needs
separate approval after the preflight; test stays closed.
