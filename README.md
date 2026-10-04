# PrivacyGate

Offline research prototype for PII detection and masking on synthetic multilingual text (EN, DE, FR, IT, ES). Implements a regex baseline, an mBERT BIO classifier, hybrid policies, and an opt-in staged pipeline.

Synthetic research only: no engine is assured to mask every personal value. There is no production privacy or legal guarantee; provenance, annotation-quality and final split gates remain open.

Project notes, reports and protocols live in ProjectOS project `10-Projects/privacygate`.

## Usage

The default regex engine needs only Python >=3.9 and detects EMAIL and checksum-valid IBAN values.

```sh
env -u PYTHONPATH python3 -m privacygate --help
env -u PYTHONPATH python3 smoke.py
```

The CLI reads text from stdin and emits JSON with `masked_text` and `entities` containing original-text offsets and labels, not original entity values or confidences.

- `--engine regex|mbert|hybrid` selects the engine (default: regex).
- `--model-dir PATH` selects local mBERT weights.
- `--hybrid-policy union|rules_first|rules_first_thr|union_refined` selects the hybrid policy.
- `--pipeline-profile legacy_union_refined|structured|structured_address_names|full` opts into the staged pipeline.

mBERT/hybrid require the dependencies in `requirements-train.txt`, local model weights and a populated tokenizer cache. Set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and `HF_HOME` to that cache. Missing assets fail without a silent regex fallback. No model download or training is authorized by these instructions.

## Repository tools

Run current tools from the repository root using the offline training environment:

```sh
python scripts/checks/check_<name>.py
python scripts/checks/verify_frozen.py <set>
python scripts/evaluation/evaluate_pipeline.py ...
python scripts/evaluation/compare.py ...
python -m scripts.training.train_mbert --help
python scripts/audit/<command>.py ...
```

The trainer is the implementation in `scripts/training/`; invoking training still requires separate authorization. Mutable runtime code lives in `privacygate/rules/`, `assemblers/`, `model/`, `evaluation/` and `data/`.

Original `scripts/make_*.py` and `scripts/train_v2/` through `scripts/train_v5/` paths and bytes are frozen. The five flat `privacygate/` modules `detect.py`, `mbert_data.py`, `positive_data.py`, `negative_data.py` and `masking_metrics.py` are canonical implementations required by frozen callers, not compatibility shims. Verify legacy frozen assets through `scripts/checks/verify_frozen.py`; historical artifact paths and hashes are not rewritten.

## Repository assets

Machine policy and pipeline configuration are in `configs/`. Aggregate metrics, manifests, verification files and blind-evaluation custody records are in `artifacts/`. Dataset rows and model weights are ignored rather than committed. Evaluators retain JSON outputs and print aggregate summaries; they do not create repository notes.
