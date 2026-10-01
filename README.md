# PrivacyGate

Research prototype (initialized from a local proposal note; see Provenance). Goal: compare regex, mBERT BIO classifier and hybrid PII detection/masking on synthetic multilingual text (EN, DE, FR, IT, ES).

## Status
The regex-only baseline and mBERT BIO classifier are implemented; hybrid comparison remains unimplemented. Stage 1 audited all 10,000 rows of a pinned public candidate locally and produced value-free manifests. The data is **not training-ready**: synthetic provenance and annotation-quality gates remain open. Stage 2 audited the Micro 100K dataset (provisional manifests, also **not training-ready**). Raw artifacts are ignored, not included in Git.

## Limitations (regex-only)
- Detects only emails and IBANs with a valid mod-97 checksum. Names, addresses, phones, etc. are **not** detected.
- Conservative patterns: unusual formats will be missed. Not a privacy guarantee; no production or legal claims.
- Use synthetic data only.

## Usage
Standard library only, Python >=3.9.
```
echo "Mail anna.test@example.org und DE89370400440532013000" | env -u PYTHONPATH python3 -m privacygate
env -u PYTHONPATH python3 -m privacygate --help
env -u PYTHONPATH python3 smoke.py
```
Output JSON: `masked_text` and `entities` (`start`, `end` offsets into the original text, `label`). Original values are never output. Overlaps: earlier start wins, then longer span.

## Stage 1 dataset audit (no model or training)

From the repository/worktree root:

```sh
env -u PYTHONPATH python3 -m venv .venv
env -u PYTHONPATH .venv/bin/python -m pip install --no-cache-dir -r docs/data-audit/requirements.txt
env -u PYTHONPATH .venv/bin/python scripts/audit_dataset.py --help
env -u PYTHONPATH .venv/bin/python scripts/audit_dataset.py
env -u PYTHONPATH .venv/bin/python scripts/audit_dataset.py --offline --verify
```

The full audit downloads only missing frozen public subset artifacts from the exact revision in `docs/data-audit/source.json`, then validates their sizes and SHA256 hashes before reading every row. A cached artifact with a mismatched hash fails; it is never silently replaced. Initial metadata/Parquet inspection occurred before implementing the schema checks. No upstream corpus or tokenizer/model downloads occur.

For a disconnected full re-run, use `env -u PYTHONPATH .venv/bin/python scripts/audit_dataset.py --offline`. Verification is always offline, recomputes the complete dataset and group assignments, checks row/exact/template/group disjointness and partition coverage, and byte-compares the saved JSON/manifests. A missing artifact or differing output fails. Dependencies must already be installed for offline use. Exact full-report verification uses the recorded Python 3.9.6 / PyArrow 21.0.0 environment; runtime/schema metadata can differ on another interpreter even when manifests agree.

Evidence: `docs/data-audit/audit.json`, `source.json`, `output-hashes.json`, `verdict.md`, and `data/manifests/{selected,excluded,train,dev,test}.jsonl` plus `split-policy.json`. Only aggregate counts, category metadata and SHA256 IDs are committed. Raw files and the isolated environment are ignored. No entity values, rows or templates are logged or sent remotely.

Measured: 10,000 rows; 4,272 EN/DE/FR/IT/ES selected; 54 quarantined for inferred token/span discrepancies; 3,377 train / 417 dev / 424 test. No observed exact/template duplicates or near matches under the disclosed lexical method. Official validation was conservatively replaced by deterministic group allocation, not treated as independently certified final data. Unsupported token-position inference remains a warning, not an automatic repair or exclusion.

Remaining gate: clarify the conflicting synthetic-provenance wording and resolve semantic annotation quality / unsupported token alignment before training. Structural checks do not prove provenance, completeness, real-world independence or production privacy. No clean all-label negatives or IBAN annotations were found. No training, evaluation results or threshold tuning are included. See `docs/data-audit/verdict.md` for the seed, algorithm, limitations and per-language split counts.

Verification actually run: help, complete cached pinned audit, offline full recomputation/byte verification, and the unchanged `env -u PYTHONPATH .venv/bin/python smoke.py` check. The first dependency attempt (`pyarrow==23.0.1`) was unavailable in the configured package index; pinned `pyarrow==21.0.0` installed successfully.

## Stage 2 Micro 100K audit (no model or training)

```sh
env -u PYTHONPATH .venv/bin/python scripts/audit_micro.py            # downloads pinned files if missing, hash-checked
env -u PYTHONPATH .venv/bin/python scripts/audit_micro.py --verify   # offline recompute + byte-compare
```
Pinned `ai4privacy/openpii-masking-micro-100k` @ `f95b4e1539657c3d0047d9ad3f20f26675f22c7d`. Reuses Stage 1 row checks (Mini outputs unchanged, still verify byte-identical). Measured: 100,000 rows; 38,835 EN/DE/FR/IT/ES; 442 quarantined (token/BIO/label discrepancies); 317 rows overlap Mini 10K (239 train, 34 dev, 40 test, 4 quarantined; 313 exact) and are excluded from all Micro splits; provisional 30,404 train / 3,835 dev / 3,841 test. Card says synthetic only, without Mini's internal conflict, but unverified; card label list differs from data (e.g. `TIME`). Not training-ready; see `docs/data-audit/micro/verdict.md`. Evidence in `docs/data-audit/micro/` and `data/manifests/micro/`.

## Future milestones
1. **Chosen next dataset: `ai4privacy/openpii-masking-micro-100k`** (EN/DE/FR/IT/ES), pinned and audited in Stage 2 below. This is a dataset choice, not training authorization.
2. (Done, Stage 2) Pin, audit schema/offsets/provenance/duplicates/Mini overlap. Do not automatically merge related datasets. No Nemotron or 1.5M dataset adoption is selected.
3. The Mini 10K pilot audit remains completed with its recorded results above unchanged; it is not replaced or retroactively reinterpreted by this selection.
4. mBERT BIO classifier, hybrid regex + mBERT, and evaluation remain unimplemented and unauthorized pending the relevant gates and explicit authorization.

## Provenance
Local source note: `/Users/necatifurkancolak/AI-Workplace/Obsidian Vaults/NecatiOS/wiki/sources/privacygate-future-project-idea.md`.

## Stage 3: mBERT (training pipeline; dev-only)
Approved 2026-10-01: `google-bert/bert-base-multilingual-cased`, pinned revision `3f076fdb1ab68d5b2880cb87a0886f315b8146f8`, trained on the provisional Micro train split. Test split untouched; all tuning/reporting on dev. Not a production or privacy claim.
```sh
/opt/homebrew/bin/python3.12 -m venv .venv-train
env -u PYTHONPATH .venv-train/bin/pip install torch transformers accelerate pyarrow   # resolved versions: requirements-train.txt
export HF_HOME=$PWD/.cache/hf
env -u PYTHONPATH .venv-train/bin/python scripts/check_alignment.py
env -u PYTHONPATH .venv-train/bin/python -m privacygate.train_mbert --run pilot --max-train-rows 2000 --max-dev-rows 500 --epochs 1
env -u PYTHONPATH .venv-train/bin/python -m privacygate.train_mbert --run full-1 --epochs 2
```
Alignment (`docs/data-audit/micro/alignment.json`): train 362 / dev 38 rows have a span boundary inside a wordpiece and are excluded (not repaired); 0 spans lost; 13 train / 1 dev rows exceed 512 wordpieces (sliding window, stride 128); [UNK] rate 1.03%. Labels: B-/I- on every wordpiece of a span, 39 classes.

Pilot (2,000 train rows, 1 epoch, 495 dev rows, MPS, `docs/runs/pilot/`): strict span P 0.624 / R 0.704 / F1 0.662; 0.94 steps/s (batch 16). Per-language and per-label numbers in `metrics.json`; a 1-epoch pilot on 6.5% of the data, not representative.

Full run `full-1` (single seed 13; 2 epochs, 3,754 steps, MPS, 5,009 s; 30,029 train rows used, 375 excluded for broken boundaries): dev strict entity-span P 0.944 / R 0.954 / F1 0.949 on 3,796 rows and 27,083 spans. Per-language F1: 0.945–0.953. Weakest labels: SURNAME 0.848, GIVENNAME 0.855, DRIVERLICENSENUM 0.905, IDCARDNUM 0.906. Dev only; test split untouched. No hybrid or regex comparison yet. Single seed; not a production privacy claim. Evidence: `docs/runs/full-1/`.

## Stage 4: hybrid comparison (dev)
Regex vs mBERT (`full-1`) vs hybrids on Micro dev (3,796 rows after the train_mbert boundary exclusion) and a synthetic challenge dev set (EN/DE/FR/IT/ES; 100 IBAN, 40 decoy, 100 clean sentences per language). Test splits (Micro test, challenge test) are not evaluated. No training; single seed; dev-tuned threshold.
```sh
python3 scripts/make_challenge.py            # writes data/challenge/{dev,test}.jsonl (ignored) + docs/challenge/manifest.json
python3 scripts/make_challenge.py --verify   # reproduces manifest hashes
env -u PYTHONPATH HF_HUB_OFFLINE=1 HF_HOME=$PWD/.cache/hf .venv-train/bin/python scripts/compare.py   # needs models/full-1
```
Policies in `privacygate/hybrid.py`: `union`, `rules_first`, `rules_first_thr` (rules_first with mBERT confidence >= 0.5, chosen on dev). Full table, sweep and limitations: `docs/runs/compare-dev/summary.md`.

| arm | Micro strict F1 | Micro EMAIL F1 | IBAN recall (strict) | decoy FP | clean FP |
|---|---|---|---|---|---|
| regex | 0.128 | 0.964 | 1.000 | 0.000 | 0.000 |
| mbert | 0.949 | 0.999 | 0.000 | 1.000 | 0.432 |
| union | 0.948 | 0.997 | 1.000 | 1.000 | 0.432 |
| rules_first | 0.946 | 0.967 | 1.000 | 1.000 | 0.432 |
| rules_first_thr (0.5) | 0.946 | 0.967 | 1.000 | 1.000 | 0.430 |

Regex general F1 is not comparable (2 labels vs 19); the challenge negatives are regex-negative by construction.
