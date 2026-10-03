# Phase-1 integrated pipeline: non-blind development evidence

Both v1 and v2 are **NOT blind**. These are previously exposed synthetic development diagnostics, not held-out final evaluation. No training, test-split evaluation, download, threshold selection, or blind-v4 scoring was performed.

Each of the four profiles was evaluated once per development set through `scripts/evaluate_pipeline.py`, using `models/pos-neg-alignment-pilot-1002` in the required offline environment. Every run completed end to end with zero blocked rows: 110/110 OK rows on v1 and 80/80 OK rows on v2. Each run directory contains `metrics.json`, `manifest.json`, and its own `summary.md`. All headline values below are read from the corresponding `metrics.json` overall aggregate, including its clean-controls aggregate.

## v1 — exposed synthetic development set, NOT blind

Dataset: `data/augmentation/masking-stress-dev.jsonl`.

| Profile | Complete spans | Partial | Untouched | Exposed alnum chars | Fully masked positive rows | Excess chars | Clean rows masked | Clean masked chars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy_union_refined | 369/370 | 1 | 0 | 0 | 99/100 | 0 | 0/10 | 0 |
| structured | 369/370 | 1 | 0 | 0 | 99/100 | 0 | 0/10 | 0 |
| structured_address_names | 369/370 | 1 | 0 | 0 | 99/100 | 0 | 0/10 | 0 |
| full | 369/370 | 1 | 0 | 0 | 99/100 | 0 | 0/10 | 0 |

## v2 — exposed synthetic development set, NOT blind

Dataset: `data/augmentation/masking-stress-v2-dev.jsonl`. Regenerated using the frozen generator; regenerated manifest bytes exactly matched the tracked manifest, and `scripts/make_masking_stress_v2.py --verify` passed. Dataset SHA-256: `4b52ff31718ba6dd0b7e8a9fda9637f241295f782504d456179467a6b0c2f0d2`.

| Profile | Complete spans | Partial | Untouched | Exposed alnum chars | Fully masked positive rows | Excess chars | Clean rows masked | Clean masked chars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy_union_refined | 130/130 | 0 | 0 | 0 | 60/60 | 46 | 5/20 | 46 |
| structured | 130/130 | 0 | 0 | 0 | 60/60 | 56 | 9/20 | 56 |
| structured_address_names | 130/130 | 0 | 0 | 0 | 60/60 | 56 | 9/20 | 56 |
| full | 130/130 | 0 | 0 | 0 | 60/60 | 49 | 6/20 | 49 |

The added profiles do not improve complete-span counts on these exposed sets. On v2, `full` reduces clean-control overmasking relative to `structured` and `structured_address_names`, but still exceeds the legacy baseline. Complete-span coverage and exposed-alphanumeric counts are different measurements: v1 retains one partial span despite zero exposed alphanumeric characters. These are annotation-relative synthetic results, not a privacy or legal guarantee; no human semantic review was performed.

## Integration and verification

The eight requested branches were merged with `--no-ff` in the requested order, without conflicts. The still-running training-data branch was not merged. No pipeline/module call-site fix was necessary: `structured`, `structured_address_names`, and `full` already followed the shared contract and ran successfully.

The only code adjustment was the admission-failure sub-check in `scripts/check_pipeline.py`: with specialist modules now available, it temporarily maps the structured detector to a genuinely missing module and verifies the same blocked, empty-output behavior. No specialist check was weakened.

All requested checks were executed once:

- `smoke.py`: SMOKE OK.
- `scripts/check_pipeline.py`: candidate contract PASS; stage unavailable PASS; legacy_identical=110/110; scored adapter PASS; pipeline CLI PASS; PIPELINE OK.
- `scripts/check_eval.py`: EVAL CHECK OK; v1_legacy_complete=369/370. Only its scratch output parent was redirected in memory from `_runs/pg-p1-eval` to `_runs/pg-int-p1`; its checks and repository file were unchanged.
- `scripts/check_structured.py`: struct_complete=134/134; negatives_detected=0.
- `scripts/check_address.py`: addr_complete=50/50; nonaddr_regions=0; addr_exact=50/50; address_contract_ok=1.
- `scripts/check_names.py`: name_complete=123/123; negatives_masked=0; name_mechanics=ok.
- `scripts/check_context.py`: clean_rejected=85/85; personal_rejected=0.

Blind v4 was copied into the ignored augmentation directory, made owner-writable, and subjected only to `scripts/make_masking_stress_v4.py --verify`. Verification passed with dataset SHA-256 `b0b21ae034fa54eb8949e7444c882f44fa53070bb927a00485dc252056f1821e`. No v4 rows were opened, printed, inspected, or scored by this integration task outside the authorized verifier. No file under `docs/runs/blind-v4/` was created.

The integration-fix/evidence commit includes only `scripts/check_pipeline.py` and `docs/runs/pipeline-dev-1003/`, with no data or model weights. No push was performed.
