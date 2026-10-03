# Frozen blind synthetic stress v3
Purpose: one new synthetic development masking diagnostic for the batch integrator; not training or the corpus test split.
The fixed-seed, stdlib-only generator creates 150 rows: 110 positive and 40 clean, with 155 whole-value gold spans across EN/DE/FR/IT/ES.
Formats cover particles, initials and titles; routed/PO-box addresses; extended phones; separated identifiers/accounts; running-text online contacts; five long texts.
Blind status: generated before any model or rule saw v3; no detector, refinement implementation, failure diagnostics or model predictions were consulted.
Prior generator sources were read only to avoid reuse; requested stress categories and the shared batch problem description were known.
Generate once with `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 scripts/make_masking_stress_v3.py`; existing dataset or manifest files are never overwritten.
Verify with `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 scripts/make_masking_stress_v3.py --verify`; the exact stress validator is AST-extracted without model-bearing imports.
JSONL stays git-ignored; the committed manifest binds bytes, hashes, aggregate coverage and source novelty. The integrator alone owns the single blind measurement; no privacy guarantee is made.
