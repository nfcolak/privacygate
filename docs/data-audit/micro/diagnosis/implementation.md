# Production window correction integrated (2026-10-02)

## Scope/status

The frozen `findings.md` and `aggregate.json` describe the original one-time Micro train/dev diagnosis, not a new run. They were not rewritten or rerun. `scripts/diagnose_alignment.py` now retains the e69fcd8 construction explicitly as `legacy_build_windows`, so future original-behaviour replay cannot accidentally call corrected production construction. Its diagnostic candidate is unchanged.

`privacygate/window_alignment.py` implements the demonstrated narrow gold label/population policy for NEW training/dev construction only. No training, real checkpoint evaluation, corpus diagnosis, held-out data inspection, install/download or remote operation was performed in this integration. Historical `full-1`, comparison/challenge and negative-pilot artifacts remain immutable.

## Construction and safeguards

1. Untruncated whole-row tokenization must align every gold span. Broken endpoints and wholly lost spans exclude the row, not just a window. Overlapping gold annotations also fail closed; no annotation repair.
2. Wholly outside spans are irrelevant to an individual window, not lost. Wholly contained spans receive the existing every-wordpiece B-/I- labels.
3. Every token overlapping a cut-crossing gold span receives IGNORE (-100), never O/clean. Special tokens retain IGNORE. Offsets themselves are NOT replaced or censored.
4. A window with failed contained-span alignment is discarded. Retain the row only if every gold span is completely represented with expected BIO labels in at least one retained window. Otherwise exclude with `incomplete_gold_coverage`. The lost-span safeguard is replaced by full-coverage proof at window level, not deleted.
5. Empty-gold negative rows remain valid, including normal special-token handling.

## Aggregate output compatibility

`build_windows` still returns `(windows, excluded_row_count)`; optional `alignment_stats` adds aggregates without row IDs/values.

- `rows_excluded_by_reason`: whole_row_broken_boundary, whole_row_lost_span, overlapping_gold, incomplete_gold_coverage. Both whole-row broken/lost reasons can occur on one row, so reason counts need not sum to the excluded-row total.
- `windows_discarded_alignment`: contained-span window alignment failures, counted separately from row exclusions. A discarded window is acceptable only when other retained windows prove complete coverage.
- `gold_spans_retained`, `gold_spans_fully_covered`, `ignored_crossing_tokens_retained`: structural coverage on retained rows/windows.
- New train config/info: `train_rows_excluded_by_reason`, `train_alignment_stats`; separate source included/retained/excluded counts remain in `train_row_counts`.
- Micro/positive dev calls each expose `rows_excluded_by_reason`, `alignment_stats` separately; no pooled F1.

The compatible `train_rows_excluded_broken` and `rows_excluded_broken_boundary` fields now mean ALL excluded rows, not just broken boundaries. Historical fields already included outside-window loss; their saved values/names remain unchanged. `rows_with_broken_boundary_excluded` remains true as a safeguard, not a description of every exclusion.

## Identity and conservative scoring

New identity is `run-identity-v3`, with `alignment_policy=whole-row-gate-contained-bio-crossing-ignore-full-coverage-v1` and `alignment_source_version=window-alignment-v1`, also recorded explicitly in config. Separate positive train/dev bindings, TRAIN-only discovered label inventory, bounded typed loaders, pinned tokenizer/model and fail-closed provenance remain. v1 negative-only and v2 positive-wiring identities cannot resume under these semantics. Old checkpoints are not migrated or retrained.

The scorer is NOT replaced. `evaluate` still decodes model label predictions at original offsets and unions strict exact `(start,end,label)` spans. Gold IGNORE labels affect loss/population only, never erase predictions. Partial cut spans and nonidentical duplicate spans can remain false positives/false negatives. This does not establish general long-text reconstruction/masking.

Changed training selection makes historical full-1 an UNMATCHED baseline. Any later authorized comparison must score incumbent and candidate on exactly the same retained dev population, with the same scorer and fixed preprocessing. No new model scores were generated here; the synthetic prediction test uses a deterministic stub solely to prove the uncensored offset path.

## Executed synthetic proof

- `scripts/check_positive_training.py`: original five assertion groups retained; only fake tokenizer flat/overflow API adapted.
- `scripts/check_window_alignment.py`: production helper plus build_windows on outside, genuine broken/lost, covered/uncovered crossing, oversized span, touching cut, overlapping gold, empty gold, specials, empty-window and discarded-window cases; matches the diagnostic candidate. Original diagnostic's 13 synthetic assertions pass without execute/corpus access. Stub evaluator proves ignored-gold positions still produce prediction spans. Identity checks refuse v1/v2/changed alignment versions.
- `smoke.py` ran once: SMOKE OK. Both generators --verify pass. Positive files regenerated with parent-expected hashes, negative file unchanged.
- Offline pinned cached tokenizer on SYNTHETIC positives only: 630/630 train rows/windows and 280/280 dev retained, zero exclusions; all 1,980 train / 920 dev gold spans completely covered across all 13 supplied labels. No model loaded/scored and tokenizer asset hashes unchanged. This is not human semantic quality or learned label coverage.

One window-failure fixture initially used an extent that made its gold span crossing, not contained/broken. A single cause-based fixture correction added the overlapping-end token needed to exercise contained boundary failure. Production safeguards were not changed; failed evidence is preserved. Remaining checks then passed; smoke/wiring were not rerun.

Execution/hash evidence is in `.worktrees/_runs/pg-continue-integrate-1002/` (`checks.log`, `checks-repair.log`, `checks-final.json`, `positive-retention.json`, `artifact-verification.json`); parent separately archives launcher records before cleanup.

## Measured pilot / pending gates

The one completed neg-pilot-1002 remains a tiny negative-only timing/wiring run on e69fcd8/original alignment/run-identity-v1, not on expanded labels or corrected selection. Model/results are preserved byte-identically in this delivery worktree; `docs/runs/neg-pilot-1002/artifact-location.json` alone adds relocation paths. Its original identity/output path and frozen manifest/config/metrics/summary remain historical, incompatible with current code. Its compute extrapolation does not estimate expanded positives/changed alignment.

New positive/alignment training requires fresh authorization. Publisher provenance, human semantic annotation/completeness quality, negative/positive semantic independence, taxonomy expansion and final provisional-split freeze remain unresolved. Unsupported categories stay unknown. No all-PII, production or legal guarantee. The explicitly unrun next pilot is documented once in `docs/positive-data/README.md`.
