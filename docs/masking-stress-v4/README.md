# Frozen blind masking stress v4

Policy: privacy-policy-v1. Synthetic development diagnostic only; not training data, not the corpus test split, and not a privacy or legal guarantee.

## Composition

- 500 rows: 300 positives and 200 unambiguous non-personal controls.
- EN/DE/FR/IT/ES: 100 rows each, comprising 60 positives and 40 controls.
- 150 positives (50%) use the reserved families: form-style records, chat lines, email signatures, mixed-language country formats, and OCR-like separator noise. Each family has 30 rows.
- Remaining positives cover all 16 canonical labels, whole names/addresses/phone extensions, identity and banking values, private references, online contacts, birth dates, ages, and 10 long letters of 3,000–6,000 characters with repeated values.
- 60 clean near-miss twins reuse annotated positive values in explicitly non-personal product-code, calendar-date or quantity contexts. They are authored before detection, never selected by results.

Every row has exactly `case_id`, `family`, `gold`, `language`, `split`, `text`. Gold is ordered, non-overlapping, and uses half-open original Python string offsets. Whole values include internal separators, attached name titles, complete postal routing and phone extension phrases. Salutations and surrounding prose/punctuation remain outside gold. Postal recipients belong to the one ADDRESS region rather than overlapping name spans.

## Freeze and verification

Run from this worktree, using stdlib Python and no network:

```sh
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 scripts/make_masking_stress_v4.py
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 scripts/make_masking_stress_v4.py --verify
```

Generation refuses if either the JSONL or manifest already exists. Verification writes nothing: it validates frozen rows, deterministically regenerates in memory, checks exact dataset bytes, and checks the complete manifest including generator and schema-validator hashes. Output is aggregate-only; errors never echo input.

The ignored artifact is `data/augmentation/masking-stress-v4.jsonl`. Commit the generator, manifest and this README only. The integrator copies the JSONL from the custodian worktree without displaying its rows. Verification on a different checkout requires the identical generator and `privacygate/masking_metrics.py` source.

The permitted span-validator functions are AST-extracted without importing the package. Their label namespace is the canonical policy-v1 allowlist, including DATEOFBIRTH; the legacy scorer label/family allowlists are not the new dataset contract. No scorer or detector is run by generation/verification.

## Independence and custody

The author read only the shared contract/policy, the v3 manifest (category descriptions, not templates/rows), and the allowed schema-validator source. Detector modules, training generators/data, research reports, predictions and measurements were not consulted. New templates and value pools were authored independently; exact literal disjointness from v3 cannot be proved because the permitted manifest does not contain its templates or values. This limitation is explicit in the manifest.

Measure once per profile+model; never tune on v4. The integrator owns measurements. Do not use v4 rows or results to select rules, thresholds, profiles, training examples, or checkpoints. Keep results aggregate-only. Training must exclude the five reserved format families. Future tuning requires a separate non-blind development set; further blind claims require a freshly authored held-out version.
