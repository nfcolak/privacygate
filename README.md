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

## Repository assets

Machine policy and pipeline configuration are in `configs/`. Aggregate metrics, manifests, verification files and blind-evaluation custody records are in `artifacts/`. Dataset rows and model weights are ignored rather than committed. Evaluators retain JSON outputs and print aggregate summaries; they do not create repository notes.
