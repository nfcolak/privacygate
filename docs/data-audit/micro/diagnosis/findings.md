# Offline alignment diagnosis (2026-10-02)

## Scope and execution

This is a local structural diagnosis of the existing provisional Micro train/dev manifests, based on `privacygate-prep-1002` at `e69fcd8`. It is not training, model evaluation, held-out test inspection, human annotation review, or evidence that all personal information is masked.

Executed once from the alignment worktree:

```sh
env -u PYTHONPATH HF_HUB_OFFLINE=1 HF_HOME=/Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.cache/hf /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.venv-train/bin/python scripts/diagnose_alignment.py
```

Actual result: exit 0, aggregate JSON only, 13/13 hand-built offset/span fixture checks passed, both splits `reproduced_and_explained`, all candidate invariants true, and read-only input hashes unchanged. No fallback cache copy was needed. After that execution, two output fields were renamed consistently in source and the saved JSON to distinguish window-extent crossings from genuine internal cuts; no corpus rerun was performed.

The script defaults to both manifests and accepts only `--split train` and/or `--split dev`. It uses `mbert_data.load_rows` and its existing main raw directory, validates the pinned source artifact hashes and sizes, and loads tokenizer assets directly from the cached snapshot with `local_files_only=True`. No test manifest is opened. The existing helper scans the pinned shared raw source files to locate requested IDs; only requested train/dev rows are parsed by that helper. Scanning those shared files is not a test-manifest lookup or model scoring.

`check_alignment.py` was inspected and its whole-row tokenization/alignment checks replayed inside this new script; it was not launched separately because it would overwrite historical `alignment.json`. The unchanged production `train_mbert.build_windows` was actually invoked per requested row for original-exclusion replay. `compare.py` was inspected, not executed; no model weights were loaded.

## Historical counts reproduced, not inferred

| Evidence | Train | Dev |
| --- | ---: | ---: |
| Requested manifest rows | 30,404 | 3,835 |
| Whole-row boundary-affected spans | 364 | 39 |
| Whole-row boundary-affected rows / exclusions | 362 | 38 |
| Whole-row lost spans | 0 | 0 |
| Original sliding-window excluded rows | 375 | 39 |
| Original retained rows | 30,029 | 3,796 |
| Original retained windows | 30,029 | 3,796 |
| Additional sliding-window exclusions | 13 | 1 |
| Rows longer than 512 tokens, including specials | 13 | 1 |
| Additional exclusions with an outside-window span | 13 | 1 |
| Additional exclusions also with a cut-crossing span | 5 | 1 |
| Additional exclusions with outside spans but no cut crossing | 8 | 0 |
| Additional exclusions with crossing but no outside span | 0 | 0 |
| Outside-window span/window events | 183 | 13 |
| Unexplained extra exclusions | 0 | 0 |
| Whole-row exclusions unexpectedly retained by original code | 0 | 0 |

Every reproduced count compared with historical `alignment.json`, full-1 config/metrics, and compare-dev exclusion/retention counts has delta zero. Original dev gold support also reproduces exactly at 27,083, without generating predictions or scores.

The hashed bindings for `original_extra_excluded`, `long`, `outside_any_window`, `extra_excluded_with_outside`, and `original_window_lost` are identical within each split. This establishes local row-set identity rather than assuming the cause from matching counts. Both original and whole-row exclusions were computed for each requested row; individual IDs and values were not persisted.

Actual mechanism:

1. `check_alignment.row_stats` aligns all spans against an untruncated whole-row tokenization. It finds 362/38 boundary-affected rows, and no lost spans.
2. `train_mbert.build_windows` calls `md.align` on each window while still passing the full row's span list. `md.align` treats every span with no overlapping token in that window as lost, including spans wholly outside that window. A partially visible span also fails its endpoint equality check and is called broken.
3. The production helper rejects the entire row if any window has either condition. All 13/1 additional exclusions have outside-window spans; 5/1 also have actual cut crossings. Each whole-row-alignable window's broken/lost counts were checked against its outside/crossing geometry, with zero residual unexplained window errors.
4. `compare.py` calls the same helper before forming its Micro dev population, explaining why compare-dev and full-1 both retain 3,796 rows. The field names describing all exclusions as broken boundaries are therefore too broad.

No historical artifacts or production code were repaired.

## Window geometry definitions

`crossing_window_extent_any` (12 train rows, 3 dev rows) and `window_extent_crossing_span_events` (13/4 events) include crossings of the outer tokenized extent, including already whole-row-broken short rows. They must not be described as pure internal-cut statistics. The whole-row-valid additional-exclusion intersection, `extra_excluded_with_crossing`, is the separate actual-cut row set: 5 train and 1 dev. For those rows full-row boundaries are valid, so the crossing arises inside sliding-window cuts, not a whole-row fringe mismatch. The broad geometry fields were renamed after execution to make that distinction explicit.

## Conservative candidate (diagnostic only)

Policy implemented only in `scripts/diagnose_alignment.py`:

- Keep the whole-row broken/lost gate. Do not repair spans or silently reinterpret annotation semantics.
- Fail closed on overlapping gold spans whose token labels would be ambiguous.
- In a window, omit wholly outside spans from alignment. They are neither lost nor positive labels in that window.
- Align wholly contained spans normally with all overlapping pieces receiving B-/I- labels.
- For a span crossing a window extent, ignore every overlapping token for training labels (`None`, corresponding to `-100`), rather than marking that partial segment O/clean. Special tokens are also ignored.
- Discard a window if its wholly contained spans still fail alignment.
- Retain a row only if every gold span is completely represented with the expected labels in at least one retained window. If no full representation exists, exclude the row explicitly as incomplete coverage. Never count its missing segment as clean.

| Candidate structural result | Train | Dev |
| --- | ---: | ---: |
| Retained rows | 30,033 | 3,796 |
| Retained windows | 30,037 | 3,796 |
| Excluded rows | 371 | 39 |
| Whole-row boundary exclusions preserved | 362 | 38 |
| Additional incomplete-coverage exclusions | 9 | 1 |
| Uncovered gold spans before rejecting those rows | 12 | 1 |
| Gold spans on retained rows | 215,213 | 27,083 |
| Gold spans fully covered in retained windows | 215,213 | 27,083 |
| Ignored crossing tokens on retained windows | 4 | 0 |
| Crossing segments incorrectly treated as clean | 0 | 0 |
| Overlapping-gold rows | 0 | 0 |
| Retained candidate window-alignment failures | 0 | 0 |

This conservative policy recovers four train rows but not every long row. Nine train rows and one dev row remain outside the candidate population because full gold-span coverage was not demonstrated. The evidence does not establish that a universal long-row solution or a new production scorer is ready. No semantic annotation repair, relabeling, or model-quality conclusion follows from this result.

Synthetic checks cover outside spans, real whole-row broken boundaries, missing spans, crossing tokens ignored rather than clean, overlap-window full coverage, uncovered crossings, spans larger than all windows, boundary-touching spans, conflicting overlapping gold, empty gold, and special tokens. These are automated offset/span checks, not human annotation review.

## Small concrete recommendation for the next implementer

Change only the population/label construction part of `build_windows` in a separately authorized implementation:

1. Compute a whole-row broken/lost gate before sliding windows.
2. Align only fully contained spans in each window; omit outside spans and use ignored labels for partial crossing spans.
3. Require complete per-row gold coverage across retained windows, preserving an explicit exclusion reason for incomplete coverage. Do not simply delete the existing lost-span check without a coverage replacement.
4. Keep these exclusions separate in aggregate reporting: whole-row boundary, whole-row missing span, window-only issue, and incomplete gold coverage.

Do not copy the diagnostic as a broad production refactor. Crossing-window prediction reconstruction remains separate work: future scoring must use a deterministic offset merge/reconstruction rule tested on synthetic crossings, and must not erase predictions based on gold ignore masks. Ignored training tokens are not a declaration that a segment is clean at inference time.

Changed train row selection invalidates a direct historical F1 comparison. Although the conservative candidate dev IDs happen to equal the original dev IDs here (their hashed bindings match), that fact alone does not validate a different reconstruction/scorer. Before any future incumbent comparison, evaluate both old and new models on exactly the same retained dev IDs with the same new scorer and fixed preprocessing. Such evaluation is not authorized by this diagnosis. Preserve the historical full-1/compare results as historical evidence, not a matched control under changed selection.

Human semantic annotation quality, publisher provenance, final split/provenance gates, unsupported privacy categories, and complete personal-information masking remain open. No full training, broad sweep, or held-out test inspection/scoring was performed or authorized here.

## Evidence and bindings

- Machine-readable evidence: `aggregate.json` in this directory.
- Protected source and historical artifacts: SHA256 bindings in `bindings.protected_files_sha256`.
- Requested populations and computed row sets: count plus SHA256 of the sorted unique ID set, never an individual ID list.
- Raw source artifacts: size and SHA256 validated against the frozen source metadata, and hashes rechecked after diagnosis.
- Tokenizer: `google-bert/bert-base-multilingual-cased`, revision `3f076fdb1ab68d5b2880cb87a0886f315b8146f8`, max length 512, overlap 128; cached tokenizer asset hashes recorded.
- Dataset attribution: Ai4Privacy / Ai Suisse SA, `ai4privacy/openpii-masking-micro-100k`, revision `f95b4e1539657c3d0047d9ad3f20f26675f22c7d`; existing language-filtered provisional train/dev selection reused unchanged. Synthetic provenance is the publisher's unverified claim, not an independently established guarantee.
