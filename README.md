# PrivacyGate

Offline multilingual PII masking research prototype for English, German, French, Italian and Spanish (EN/DE/FR/IT/ES). It combines an mBERT region model with deterministic rules to mask personal information while limiting unnecessary masking.

Synthetic data only. This is not a production privacy control and provides no privacy or legal guarantee. The external evaluation—not the near-perfect internal scores—is the honest headline: **87.09–88.71% of annotated personal letters/digits masked**, with **4.04–4.42% excess masking on non-annotated text**.

## How it works

The full pipeline keeps candidate spans in original-text coordinates:

```text
mBERT region model → regex + structured detectors → context gate
→ address/name assemblers → refinement + coverage union → render
```

The model proposes regions; rules detect and validate structured values; the context gate distinguishes personal from operational uses. Assemblers extend address/name regions and propagate supported name mentions within a document. Refinement and union combine accepted spans before rendering placeholders. Required-stage or inference failures return a blocked result rather than silently falling back to regex.

Four profiles are supported:

- `full`: all stages; default for `privacygate.pipeline.run_pipeline`.
- `structured`: model, regex and structured detection without context/assemblers.
- `structured_address_names`: structured detection plus address/name assemblers, without the context gate.
- `legacy_union_refined`: retained legacy hybrid union/refinement behavior.

`full_calibrated` is retired; historical results remain in the artifacts. The CLI still defaults to the regex engine, not the full pipeline.

## Repository layout

```text
privacygate/
├── cli.py, __main__.py           # stdin → JSON interface
├── pipeline.py                  # staged orchestration; stable public API
├── model/                       # inference, hybrid policies, training guards
├── rules/                       # structured detection, context, refinement
├── assemblers/                  # addresses and names
├── data/                        # spans, window alignment, training-data adapters
├── evaluation/                  # masking evaluation and blind-run custody
└── detect.py, mbert_data.py, positive_data.py,
    negative_data.py, masking_metrics.py  # five fixed canonical modules
scripts/
├── checks/                      # regression checks and frozen verification
├── audit/                       # data, coverage and alignment audits
├── evaluation/                  # pipeline scoring and comparisons
├── training/                    # current mBERT trainer
├── make_*.py                    # frozen synthetic generators
└── train_v2/ … train_v5/         # frozen generator implementations, not trainers
configs/                         # machine policy and pipeline configuration
artifacts/                       # aggregate metrics, manifests and receipts
└── figures/results.png
smoke.py                         # deterministic CLI smoke test
```

The frozen generators and the five flat canonical modules are intentional fixed paths, not compatibility shims: manifests bind their source bytes and frozen callers depend on them. Do not relocate or rewrite them. `scripts/checks/verify_frozen.py` adapts historical paths at runtime without changing source bytes or historical hashes. Seven retired files are archived outside the repository.

Models and datasets are not committed. Project notes, protocols and reports live outside the repository in ProjectOS project `10-Projects/privacygate`; only the root README and AGENTS are repository notes.

## Evaluation method

Each internal round used a fresh synthetic blind set, separate from development data. Each model/profile arm was measured once, with hash-bound manifests and custody receipts preventing repeat scoring. Later rounds used revised models/rules, so their results are not a controlled comparison on one common test set. Previously scored sets are no longer blind.

The primary masking metric is the share of annotated personal letters/digits covered by the final mask, independent of the predicted label. It is not exact-span F1 or the percentage of documents fully protected. A clean row counts as masked if any text is masked.

The external test used a synthetic dataset **we did not generate**, with one measurement per arm and no training on that test. Excess masking is masked characters outside all source annotations divided by all non-annotated characters. This character rate is not directly comparable to the internal clean-row rate; missing annotations can also inflate it.

## Results

![Internal blind-set coverage and clean-row masking, with external test coverage and excess masking](artifacts/figures/results.png)

### Internal blind sets

Best setup per round, with the region-v5 challenger shown separately:

| Blind set | Setup (`full`) | Personal letters/digits masked | Clean rows masked |
|---|---|---:|---:|
| v4 | region-v2 | 100.00% | 76/200 |
| v5 | region-v3 | 95.85% | 50/300 |
| v6 | region-v4 | 99.41% | 58/300 |
| v7 | region-v4, round-4 rules | 99.71% | 21/300 (7.0%) |
| v7 challenger | region-v5, round-4 rules | 99.13% | 19/300 |

Aggregate records and receipts are in `artifacts/runs/blind-v4/` through `blind-v7/`. These internal blind sets **overstate quality** relative to external text.

### External test — the headline result

`gretelai/synthetic_pii_finance_multilingual`, Apache-2.0, commit `7b844d1`; test split restricted to EN/DE/FR/IT/ES: **4,696 documents and 12,200 in-scope spans**, measured once per arm using `full`.

| Model | Personal letters/digits masked | Excess on non-annotated text |
|---|---:|---:|
| region-v4 | 87.09% | 4.04% |
| region-v5 | 88.71% | 4.42% |

Person names without cues were a major weakness (roughly 81–85% coverage); usernames were also weak. Excess masking was mostly numbers/amounts. The annotations are LLM-made, with automated validation and reported spot checks—not a fully human-adjudicated reference. External aggregates, manifests and measurement tooling are retained outside the repository under `~/AI-Workplace/Artifacts/PrivacyGate/external/gretel-results/` (`external-gretel.json`).

## Limitations

- Synthetic-only research does not establish performance on real personal data or unseen domains/languages.
- Character coverage can hide partially leaked values and fully unprotected documents. An `ok` status certifies processing, not complete PII recall.
- Names without contextual cues, usernames and ambiguous numeric fields remain failure modes. Wider masks trade recall against retained utility.
- External annotations can omit or misclassify values; some mapped labels do not establish personal linkage. Scope differences limit comparisons with internal tests.
- Provenance, annotation-quality and final split gates remain open. No deployment, anonymization or legal compliance claim is made.

## Usage and reproduction

Run commands from the repository root. The default regex engine requires only Python >=3.9 and detects EMAIL and checksum-valid IBAN values. mBERT/hybrid and the staged pipeline additionally require `requirements-train.txt`, local model weights and a populated tokenizer cache. Missing assets fail without a silent regex fallback.

Reuse an existing training environment, or prepare one from locally available dependency wheels. These instructions do not authorize downloads, training or repeat blind measurements.

```sh
# Only if an environment has not already been prepared:
env -u PYTHONPATH python3 -m venv .venv-train
# Install requirements-train.txt from your locally available wheels, without network access:
# .venv-train/bin/python -m pip install --no-index --find-links /path/to/wheels -r requirements-train.txt

export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HOME=/path/to/populated/hf-cache
PY=/path/to/existing/.venv-train/bin/python
pgpy() { env -u PYTHONPATH "$PY" "$@"; }

pgpy -m privacygate --help
pgpy smoke.py
pgpy scripts/checks/check_pipeline.py
pgpy scripts/checks/check_eval.py
pgpy scripts/checks/check_structured.py
pgpy scripts/checks/check_context.py
pgpy scripts/checks/check_address.py
pgpy scripts/checks/check_names.py
pgpy scripts/checks/verify_frozen.py all
pgpy -m scripts.training.train_mbert --help
```

The regression checks require the local synthetic development assets; pipeline/evaluation checks also require the legacy checkpoint `models/pos-neg-alignment-pilot-1002`. `verify_frozen.py all` reports missing supported datasets as skipped, not verified. Some historical verification paths also depend on the external ProjectOS policy document.

The CLI reads synthetic text from stdin and emits JSON with `masked_text` and `entities` (original-text offsets and labels, not original entity values or confidences). Staged results also include status, completion and aggregate diagnostics. Unmasked text remains in the output, so this output is not a safe-to-log privacy guarantee.

- `--engine regex|mbert|hybrid`: engine selection; default `regex`.
- `--model-dir PATH`: local checkpoint; default `models/full-1` when unspecified.
- `--hybrid-policy union|rules_first|rules_first_thr|union_refined`: hybrid combination policy.
- `--pipeline-profile full|structured|structured_address_names|legacy_union_refined`: opt into staged processing; overrides engine/policy/refinement/confidence options.
- `--refine` and `--confidence`: optional non-staged model controls; see CLI help.

```sh
# Use an existing file containing synthetic input only:
pgpy -m privacygate --pipeline-profile full \
  --model-dir models/region-v4-2ep < synthetic-input.txt

# Current scoring/audit entry points; help does not score a dataset:
pgpy scripts/evaluation/evaluate_pipeline.py --help
pgpy scripts/evaluation/compare.py --help
pgpy scripts/audit/audit_dataset.py --help
```

Evaluators retain JSON outputs and print aggregate summaries, not dataset rows. Historical blind arms must not be rerun; reproduce their reported numbers from the committed aggregates and receipts. Training requires separate authorization even though the trainer entry point is available.
