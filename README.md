# PrivacyGate

Research prototype (initialized from a local proposal note; see Provenance). Goal: compare regex, mBERT BIO classifier and hybrid PII detection/masking on synthetic multilingual text (EN, DE, FR, IT, ES).

## Status
Only the **regex-only baseline** exists. mBERT, hybrid and evaluation are **not implemented**. Stage 1 audited all 10,000 rows of a pinned public candidate locally and produced value-free manifests. The data is **not training-ready**: synthetic provenance and annotation-quality gates remain open. Raw artifacts are ignored, not included in Git.

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

## Future milestones
1. **Chosen next dataset: `ai4privacy/openpii-masking-micro-100k`**, limited to EN/DE/FR/IT/ES for the planned work. The exact revision is not yet selected or pinned, and the full audit is pending. This is a dataset choice, not training authorization; no model or training work is authorized by it.
2. Pin the exact revision, then audit the five-language subset: schema, character offsets, provenance, duplicates, and overlap with the completed Mini 10K train/dev/test manifests before freezing any new splits. Do not automatically merge related datasets. No Nemotron or 1.5M dataset adoption is selected.
3. The Mini 10K pilot audit remains completed with its recorded results above unchanged; it is not replaced or retroactively reinterpreted by this selection.
4. mBERT BIO classifier, hybrid regex + mBERT, and evaluation remain unimplemented and unauthorized pending the relevant gates and explicit authorization.

## Provenance
Local source note: `/Users/necatifurkancolak/AI-Workplace/Obsidian Vaults/NecatiOS/wiki/sources/privacygate-future-project-idea.md`.
