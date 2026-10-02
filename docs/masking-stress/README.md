# Synthetic literal-masking development stress fixtures

Status: templates/rules frozen before any model predictions. This independent STRESS task did not load a tokenizer or model, call a detector, inspect a corpus/held-out split, train, tune thresholds or score masking. These fixtures are development diagnostics only, never training input or a held-out final test.

## Artifacts and counts

- Generator: `scripts/make_masking_stress.py` (Python standard library only).
- Ignored dataset: `data/augmentation/masking-stress-dev.jsonl`.
- Aggregate binding and family/language/label matrix: `manifest.json`.
- 110 rows: 100 positive and 10 deliberately impersonal clean controls.
- EN/DE/FR/IT/ES: 22 rows each. Eleven families: 10 rows each, with two variants per family/language.
- 370 gold spans, 9,130 original gold characters and 7,854 Unicode alphanumeric gold characters.
- Dataset: 137,089 UTF-8 bytes; SHA256 `b901873cbdd3715aaae2c78477193fecb3fd47410344fdb240ce75abdbfb6cbf`.

Families: `names`, `phone`, `identity`, `full_address`, `username`, `account`, `personalref`, `multiple_entities`, `repeated_values`, `long_text`, `clean`.

Names include accents, hyphens and repeated occurrences. Phones include international/local-looking punctuation and extensions, with the whole formatted phone/extension annotated. Identity cards, passports and driving licences include separators. Explicitly person-linked usernames, membership accounts and delivery references remain positive irrespective of checksum. Fifteen personal-reference occurrences are intentionally IBAN-shaped and checksum-invalid; this does not justify exposing them. Multiple-entity cases mix adjacent punctuation and several labels; repeated-value cases annotate every occurrence, not just the first.

## Gold and schema

Exact row keys: `case_id`, `language`, `family`, `text`, `gold`, `split`. `split` is always `dev`. Each gold entry has exactly `start`, `end`, `label`; offsets are Python Unicode character positions, half-open, sorted, non-overlapping and in bounds. Boolean offsets are rejected. `gold=[]` occurs only in clean controls.

Slots are annotated during concatenation; no substring search recovers offsets. Every inserted personal slot includes the owner name when present. `PERSONNAME` is a contiguous full-name diagnostic label; `ADDRESS` is one contiguous full-address region containing street, building, apartment, postcode, locality, country and internal separators. Outside owner names are separate non-overlapping spans. The address is not decomposed into overlapping components. Diagnostic labels need not be trained classes: missing checkpoint support is not a negative-example admission rule.

Unmasked whitespace, punctuation or separators inside a gold region can fail all-character complete-span masking even when all Unicode alphanumeric characters are masked. The integrator must use original masked-interval union, independent of predicted labels, and report both measures separately. Alphanumeric coverage and disappearance of a substring are not privacy guarantees. Clean rows require separate false-positive counts, not trivial complete-PII successes.

## Long-text and clean-control construction

Ten long rows have an early owner plus five later personal placements. Lengths are 8,341–8,752 characters, below the 12,000-character cap. Two different character-target schedules spread phone, full address, reference, username and repeated owner slots throughout impersonal filler. Actual later slot starts range from 1,069 to 8,544. Character targets are not tokenizer boundaries. Cached-tokenizer sliding-window boundary/crossing verification remains pending; neither tokenizer nor model was loaded here. These rows probe long-context placement but do not prove an entity crosses any actual inference window.

The clean controls and long filler discuss only abstract geometry/optics/material properties, without personal narrative, identifiers, address-like slots, possessions or unresolved reference codes. Clean cases are authored as impersonal prose, not selected by detector silence. Generic ambiguous codes are excluded from this clean pool rather than asserted harmless.

## Freeze and source-only independence checks

Generation is deterministic, without random seeds or detector-dependent case selection. The manifest binds the generator, ignored dataset, template set and inspected existing generator source hashes. Exact new skeletons and rendered texts are compared to string literals in `make_positives.py`, `make_challenge.py`, `make_negatives.py` and `negative_data.py`; IDs are compared to those literals and 175 positive-template IDs reconstructed from source. The new ID prefix is absent from existing generator-source literals. No existing generated dataset or frozen split was read. These lexical checks cannot establish semantic, translation or generation-family independence; exact corpus-level text disjointness remains unproven.

## Generate and verify offline

From the worktree root:

    env -u PYTHONPATH HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.cache/hf python3 scripts/make_masking_stress.py
    env -u PYTHONPATH python3 scripts/make_masking_stress.py --verify

Generation refuses existing artifacts. `--verify` regenerates in memory, compares exact dataset bytes/SHA256 and the complete deterministic manifest, parses the stored rows and validates schema, offsets, language/family coverage, unique IDs/exact texts and positive/clean presence. One compact sanity group checks Unicode slot accounting and rejects eight malformed-structure variants. Output/errors contain only aggregate counts, hashes and fixed codes, never text/values or prediction fragments.

After METRICS integration, the final integrator can regenerate this ignored dataset in its delivery worktree and pass it to `scripts/measure_masking.py --dataset data/augmentation/masking-stress-dev.jsonl --format stress --model-dir models/pos-neg-alignment-pilot-1002 --out-dir <new-output-directory>`. This task supplies no duplicate scorer and waits for no other agent.

## Limits

All inserted values are invented compositions. Accidental collisions with real names, addresses, codes or numbers are possible; no number is verified unassigned. Country names are public place names, while street/locality spellings and formats are artificial. Identity/telephone/address formats are not nationally validated. Limited authored templates are not representative of real personal information. Automated offset completeness covers the inserted slots, not all possible semantic omissions. No production, compliance or privacy guarantee follows from these fixtures or any later aggregate result.
