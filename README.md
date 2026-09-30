# PrivacyGate

Research prototype (initialized from a local proposal note; see Provenance). Goal: compare regex, mBERT BIO classifier and hybrid PII detection/masking on synthetic multilingual text (EN, DE, FR, IT, ES).

## Status
Only the **regex-only baseline** exists. mBERT, hybrid and evaluation are **not implemented**. No dataset is included; proposed dataset details have not been audited.

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

## Future milestones
1. Synthetic multilingual dataset (audited).
2. mBERT BIO classifier.
3. Hybrid regex + mBERT.
4. Evaluation: entity precision/recall/F1 and character masking.

## Provenance
Local source note: `/Users/necatifurkancolak/AI-Workplace/Obsidian Vaults/NecatiOS/wiki/sources/privacygate-future-project-idea.md`.
