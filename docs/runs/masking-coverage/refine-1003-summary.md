# Name/separator refinement and narrow AGE filtering (1003)

Synthetic development diagnostic only, for `hybrid_union_refined` at confidence 0.0 with the same frozen checkpoint and unchanged `masking-union-v2` scorer. The all-personal-information masking target is **NOT achieved**; these results are not a privacy or legal guarantee.

**v1, v2 and window-cut are NOT blind:** the new rules were written while looking at their failures. The blind check is v3, to be run later by the integrator; no v3 result is included here. No training or test-split evaluation was performed.

## Evidence binding

Before: committed [`refine-v1/metrics.json`](refine-v1/metrics.json), [`refine-v2/metrics.json`](refine-v2/metrics.json) and [`window-cut/metrics.json`](window-cut/metrics.json). After: restored [`refine-v1-1003/metrics.json`](refine-v1-1003/metrics.json), [`refine-v2-1003/metrics.json`](refine-v2-1003/metrics.json) and [`window-cut-1003/metrics.json`](window-cut-1003/metrics.json). All table numbers below were extracted programmatically from those metrics, not inferred from historical summaries.

The restored `privacygate/refine.py` SHA256 is `5fcfa1e688140e0ba72c3980523c5114df98a97fe8329a4dcee51abb9d6dfdaf`, matching all three after-run manifests; all their recorded source bindings also match this worktree. The recovery archive checksums passed. No measurement was repeated because the measured source was restored byte-identically and the CLI coverage check passed.

Complete spans require every original character, including separators, to be covered by the final masking union. Exposed alnum chars count Unicode letters/numbers only. Fully masked positive rows require all annotated spans to be complete. Excess chars are masked characters outside the gold annotation union across all evaluated rows, including clean rows; this is annotation-relative, not proof that the excess is harmless text. Clean-row completeness is N/A. Window-cut mid-window controls contain annotated positives and are not clean controls; `0/0` clean rows below means no clean controls were present.

## v1

| State | Complete spans | Exposed alnum chars | Fully masked positive rows | Clean rows masked | Clean masked chars | Excess chars |
|---|---:|---:|---:|---:|---:|---:|
| Before | 201/370 | 3/7854 | 0/100 | 0/10 | 0 | 0 |
| After | 369/370 | 0/7854 | 99/100 | 0/10 | 0 | 0 |

## v2

| State | Complete spans | Exposed alnum chars | Fully masked positive rows | Clean rows masked | Clean masked chars | Excess chars |
|---|---:|---:|---:|---:|---:|---:|
| Before | 70/130 | 0/2827 | 0/60 | 9/20 | 56 | 56 |
| After | 130/130 | 0/2827 | 60/60 | 5/20 | 46 | 46 |

Remaining v2 false masks: **5/20 clean rows, 46 characters**. Complete coverage of the annotated positives on this synthetic dev set does not establish complete masking of real personal information.

## window-cut (all rows)

| State | Complete spans | Exposed alnum chars | Fully masked positive rows | Clean rows masked | Clean masked chars | Excess chars |
|---|---:|---:|---:|---:|---:|---:|
| Before | 138/200 | 24/4360 | 47/80 | 0/0 | 0 | 0 |
| After | 187/200 | 24/4360 | 67/80 | 0/0 | 0 | 0 |

### Window-cut pooled groups

These rows sum the disjoint `cut_*` or `mid_*` group metrics for the same arm, keeping crossing spans separate from matched positive controls.

| State | Complete spans | Exposed alnum chars | Fully masked positive rows | Clean rows masked | Clean masked chars | Excess chars |
|---|---:|---:|---:|---:|---:|---:|
| Cut before | 70/100 | 12/2180 | 24/40 | 0/0 | 0 | 0 |
| Cut after | 93/100 | 12/2180 | 33/40 | 0/0 | 0 | 0 |
| Mid-window controls before | 68/100 | 12/2180 | 23/40 | 0/0 | 0 | 0 |
| Mid-window controls after | 94/100 | 12/2180 | 34/40 | 0/0 | 0 | 0 |

## New rules

**d. Name gaps.** Join name-labelled pieces (`GIVENNAME`, `SURNAME`, `MIDDLENAME`, `TITLE`, `PERSONNAME`) across bounded whitespace, hyphens, apostrophes or the listed name particles. The merged span covers the gap. Gaps are capped at 40 characters, blank lines block joining, and non-name pieces are never joined by this rule.

**e. Value gaps.** Join separator-only gaps of at most three characters within the same value family. Identity-document labels share a family, while phone, account, card, reference, email and username families remain separate. A full stop followed by whitespace blocks joining as a sentence boundary. An attached username-style `@` sigil is included for eligible `USERNAME`/`EMAIL` spans only under the bounded lexical guard.

**f. AGE near-miss filter.** Discard only one- or two-digit, mBERT-sourced `AGE` pieces that lack multilingual age context within 40 characters on either side and are not connected to another value-family piece. Adjacent or overlapping value pieces are retained to avoid dropping fragments of identifiers. The measured exposed-alnum count does not increase on any of these dev sets; remaining clean false masks are not eliminated.

## Verification

`env -u PYTHONPATH python3 smoke.py`: `SMOKE OK`. The required synthetic CLI check ran offline with the frozen checkpoint: the whole name was one exact masked span, the whole phone was one exact masked span, and label-placeholder replacement matched the reported spans. Only aggregate check results were printed; no input values or entity offsets were logged.
