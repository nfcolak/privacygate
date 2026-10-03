# PrivacyGate

Research prototype (initialized from a local proposal note; see Provenance). Goal: compare regex, mBERT BIO classifier and hybrid PII detection/masking on synthetic multilingual text (EN, DE, FR, IT, ES).

## Status
Regex baseline, mBERT BIO classifier and regex+mBERT hybrid policies are all implemented, and the CLI exposes all three (`--engine`). **The all-personal-information masking target (names, phones, identity numbers, addresses, ...) is NOT achieved**: no engine is assured to mask every personal value, and measured limitations are listed below. Synthetic research only; no privacy guarantee. Stage 1 and Stage 2 audited the public candidate datasets locally and produced value-free manifests; the data is **not training-ready** (provenance and annotation-quality gates open). Raw artifacts are ignored, not included in Git.

Current development masking evidence (2026-10-03): [name/separator refinement summary](docs/runs/masking-coverage/refine-1003-summary.md). On synthetic dev sets only, `hybrid_union_refined` completely masks 369/370 v1 spans (0/7854 exposed alnum chars, 99/100 fully masked positive rows) and 130/130 v2 spans (0/2827 exposed, 60/60 rows). Remaining v2 false masks affect 5/20 clean rows (46 chars); pooled window-cut crossings remain 93/100 complete with 12/2180 alnum chars exposed. These sets are NOT blind: rules were written while looking at their failures; the blind v3 check will be run later by the integrator. The all-personal-information masking target is NOT achieved; no privacy or legal guarantee. No training or test-split evaluation; provenance, semantic-quality and final split gates remain open.

## Limitations (regex-only)
- Detects only emails and IBANs with a valid mod-97 checksum. Names, addresses, phones, etc. are **not** detected.
- Conservative patterns: unusual formats will be missed. Not a privacy guarantee; no production or legal claims.
- Use synthetic data only.

## Usage
Default engine `regex` is standard library only (Python >=3.9, no torch import).
```
echo "Mail anna.test@example.org und DE89370400440532013000" | env -u PYTHONPATH python3 -m privacygate
env -u PYTHONPATH python3 -m privacygate --help
env -u PYTHONPATH python3 smoke.py
```
Output JSON: `masked_text` and `entities` (`start`, `end` offsets into the original text, `label`). Original values and confidences are never output. Overlapping detections are merged into their union before masking, so every character of every chosen detection is masked.

### Engines
```
--engine regex|mbert|hybrid     default regex
--model-dir PATH                local mBERT directory (default: models/full-1 in the repo); mbert/hybrid only
--hybrid-policy union|rules_first|rules_first_thr   default union (keeps overlapping coverage; not a claim of calibrated superiority)
--confidence F                  mBERT minimum confidence in [0,1] (default 0.0; rules_first_thr default 0.5)
```
mbert/hybrid need the training environment (torch, transformers; see Stage 3) and run fully offline: `HF_HUB_OFFLINE=1`, a local model directory and a pre-populated local Hugging Face cache for the pinned tokenizer. Nothing is downloaded. A missing model/cache or load failure exits 1 with a generic message; there is no silent fallback to regex. Errors never echo input.
```
export HF_HUB_OFFLINE=1 HF_HOME=<local-hf-cache>
echo "<synthetic text>" | env -u PYTHONPATH <train-venv>/bin/python -m privacygate --engine hybrid --model-dir <model-dir> --hybrid-policy union
```

### Measured limitations
- regex: only EMAIL and checksum-valid IBAN; names, phones, addresses, identity numbers are not detected (Micro dev strict F1 0.128 over 19 labels).
- mBERT `full-1`: Micro dev strict F1 0.949 (dev only, single seed), but IBAN recall 0.000 and 100% decoy / 43% clean-sentence false positives on the synthetic challenge dev set; weakest on SURNAME, GIVENNAME, DRIVERLICENSENUM, IDCARDNUM. Quick synthetic CLI checks also showed missed items (e.g. a phone number and an email by mBERT alone), so span misses must be expected.
- Code-like strings (order, tracking, reference codes) are not assumed safe or unsafe by format; no evaluation covers them.
- Micro data is synthetic and provisional; results do not transfer to real text. Test splits were not evaluated. See `docs/runs/compare-dev/summary.md`.

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

## Integration status (2026-10-02): measured pilots vs ready code/data
Measured: the ONE negative-only `neg-pilot-1002` completed on original source `e69fcd8`, original alignment and `run-identity-v1`.
It used 1,979 retained Micro + 1,000 negative train rows/windows, 187 optimizer steps, and 495 retained dev rows;
strict dev F1 0.71760710553814, wall time 155.975368625 s. This is a small wiring/timing pilot, not an improvement claim.
No expanded positive labels or alignment correction were included. Evidence: `docs/runs/neg-pilot-1002/`.
The checkpoint/results were copied byte-identically into this worktree's `models/neg-pilot-1002` and `results/neg-pilot-1002`;
`artifact-location.json` records relocation only. Old metadata keeps the original execution path and is NOT resumable under current code.

Measured: one expanded corrected-alignment pilot trained on 1,979 retained Micro + 630 positive + 1,000 negative rows (3,609 total retained; 226 steps; 171.878921125 s wall time), with 495 Micro dev rows and a separate 280-row positive-dev evaluation. Micro strict exact-span+label F1: 0.7429782723900371; separate positive-dev F1: 0.7545271629778673. On positive-dev, ACCOUNTNUM and PERSONALREF each had strict exact-span+correct-label TP=0/support=40; USERNAME TP=24/support=40. These strict class-specific misses alone do NOT establish literal exposure. The later [class-agnostic masking diagnostic](docs/runs/masking-coverage/summary.md) keeps original easy positive dev and frozen stress dev separate. Results: `docs/runs/pos-neg-alignment-pilot-1002/`; relocation-only receipt: `artifact-location.json` there. The original output identity remains bound to the source path, so the delivered checkpoint is not resumable at the delivery path.
These synthetic pilot results do not demonstrate readiness or improvement over unmatched historical runs. Full training, final-test evaluation, matched incumbent comparison, and semantic-quality, provenance, and split gates remain pending.

Exercised in the bounded expanded pilot (not evidence of reliable learning): the following inputs/policies were included; this is not new evidence of readiness or reliable model quality:
- `docs/scope/` ([masking-policy](docs/scope/masking-policy.md), [coverage](docs/scope/coverage.md), [gates](docs/scope/gates.md)): what "all personal information" would cover, historical checkpoint/rule coverage (19 entity / 39 BIO / 2 rule labels), and open provenance, semantic quality and final split gates. Unsupported/new unknown categories remain unknown; no all-PII guarantee.
- `docs/augmentation/`: existing train-only synthetic `neg-v2` negatives, unchanged (1,000 rows), bounded fail-closed loading.
- `docs/positive-data/`: 630 train / 280 separate dev positives; TRAIN-only label discovery, separate Micro/positive-dev metrics, strict split/overlap guards. USERNAME, ACCOUNTNUM and PERSONALREF are proposed classes in new wiring, NOT learned by an existing checkpoint. Offline cached-tokenizer checks on synthetic positives retain all rows, with all 1,980 train / 920 dev gold spans fully represented across 13 labels; this is structural coverage, not semantic review or scoring.
- `privacygate/window_alignment.py`: whole-row broken/lost gate; outside spans ignored per window; cut-crossing gold tokens IGNORE, not O; every gold span must have complete BIO coverage in a retained window or the row is excluded explicitly. New train/dev construction uses this policy. See `docs/data-audit/micro/diagnosis/implementation.md`; saved original diagnosis remains unchanged and original replay uses an explicit legacy helper.
- `run-identity-v3` binds alignment policy/source version as well as separate positive bindings and final TRAIN label inventory. v1 negative pilot and v2 positive-wiring identities fail closed; no checkpoint migration.
- Decoding/scoring remains strict window span union and uses predictions at original offsets, never gold ignore masks. Partial/duplicate span errors remain possible; this does NOT solve general long-text masking. Changed training population makes historical `full-1` an unmatched baseline. Any later authorized comparison must score BOTH models on identical retained dev IDs using the SAME scorer/preprocessing; no new model scoring was done here.
- `--engine hybrid` does not establish complete masking. Historical phone/email misses, mBERT IBAN recall 0.000 and high decoy/clean false positives are unchanged.

One explicitly UNRUN next bounded pilot command, including positives/negatives, is in `docs/positive-data/README.md`; execution needs new authorization.
The negative-pilot compute estimate applies only to old alignment/negative-only assumptions, NOT expanded labels or changed alignment, and is not a full-training budget.
Full runs, held-out inspection/scoring, human semantic review, publisher provenance verification and final split freeze remain unauthorized/open.
Historical Stage 3/4 commands and metrics below describe their original source/populations, not commands to rerun current code against old run names.

## Future milestones
1. Chosen dataset: `ai4privacy/openpii-masking-micro-100k` (EN/DE/FR/IT/ES), pinned and audited in Stage 2; a dataset choice, not training authorization. The Mini 10K pilot audit stays as recorded.
2. Implemented (see Stages 3-4): mBERT BIO classifier and hybrid regex + mBERT, dev comparison only.
3. Open: reach and measure the all-personal-information masking target (phones, identity numbers, addresses, names, code-like identifiers), final test evaluation, and the data provenance/annotation gates. Not authorized yet.

## Provenance
Local source note: `privacygate-future-project-idea.md` in the author's private notes (path omitted).

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
