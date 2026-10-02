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

Loader (`--negative-train-file`) fails closed: split=train only, languages en/de/fr/it/es, empty annotations,
unique IDs (also disjoint from Micro train/dev IDs), text <= 2000 chars, <= 20000 rows, exact duplicate guard.
Rejection prints an error code only. Rows are appended after positive selection (`--max-train-rows` applies to
Micro only); labels come from the original Micro train. Config records `negative_train` (sha256, counts). An
existing run whose recorded negative binding differs from the requested one is refused.

## Later pilot (NOT run; needs measured timing and separate approval)

    cd <worktree> && HF_HUB_OFFLINE=1 env -u PYTHONPATH <.venv-train python> -m privacygate.train_mbert \
      --run neg-pilot --max-train-rows 2000 --max-dev-rows 500 --epochs 1 \
      --negative-train-file data/augmentation/negatives-train.jsonl

Pending: bounded preflight timing (steps/sec from a small run) -> estimate -> approval. Full training needs
separate approval after the preflight; test stays closed.
