"""Gold label/population construction only; never filters prediction offsets.

Whole-row alignment is mandatory. Windows may omit outside spans, but a row
is retained only when every span has a complete, correctly labelled window.
Derived from the frozen diagnose_alignment.candidate; not a long-text scorer.
"""
from privacygate import mbert_data as md

ALIGNMENT_POLICY = "whole-row-gate-contained-bio-crossing-ignore-full-coverage-v1"
ALIGNMENT_SOURCE_VERSION = "window-alignment-v1"
EXCLUSION_REASONS = (
    "whole_row_broken_boundary", "whole_row_lost_span", "overlapping_gold",
    "incomplete_gold_coverage",
)


def whole_offsets(tok, text):
    """Untruncated offsets, using the same special-token convention as encode."""
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=True,
              truncation=False, verbose=False)
    return [None if a == b == 0 else (a, b) for a, b in enc["offset_mapping"]]


def window_geometry(offsets, spans):
    real = [o for o in offsets if o is not None]
    if not real:
        return [], list(range(len(spans))), []
    lo, hi = min(o[0] for o in real), max(o[1] for o in real)
    inside, outside, crossing = [], [], []
    for j, (start, end, _) in enumerate(spans):
        if end <= lo or start >= hi:
            outside.append(j)
        elif start >= lo and end <= hi:
            inside.append(j)
        else:
            crossing.append(j)
    return inside, outside, crossing


def align_windows(whole, windows, spans):
    """Return label names and source window indices, or value-free row reasons.

    Whole-row broken/lost gates are preserved. Partial crossing tokens are
    ignored for loss only. Coverage is proved from actual BIO labels, not just
    containment geometry. Discarding a bad window never bypasses full coverage.
    Reasons may co-occur (whole-row broken and lost); counts are reason events.
    """
    _, broken, lost = md.align(whole, spans)
    reasons = []
    if broken:
        reasons.append("whole_row_broken_boundary")
    if lost:
        reasons.append("whole_row_lost_span")
    ordered = sorted(spans)
    if not reasons and any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        reasons.append("overlapping_gold")
    if reasons:
        return {"retained": False, "reasons": reasons, "windows": [],
                "covered": set(), "windows_discarded_alignment": 0}

    retained, covered, discarded = [], set(), 0
    for window_index, offsets in enumerate(windows):
        inside, outside, crossing = window_geometry(offsets, spans)
        labels, wb, wl = md.align(offsets, [spans[j] for j in inside])
        if wb or wl:
            discarded += 1
            continue
        ignored = set()
        for j in crossing:
            start, end, _ = spans[j]
            for i, off in enumerate(offsets):
                if off is not None and off[0] < end and off[1] > start:
                    labels[i] = None
                    ignored.add(i)
        effective_inside = set()
        for j in inside:
            start, end, lab = spans[j]
            idx = [i for i, off in enumerate(offsets)
                   if off is not None and off[0] < end and off[1] > start]
            expected = [("B-" if k == 0 else "I-") + lab for k in range(len(idx))]
            if idx and [labels[i] for i in idx] == expected:
                effective_inside.add(j)
        covered.update(effective_inside)
        retained.append({"labels": labels, "inside": effective_inside,
                         "outside": outside, "crossing": crossing,
                         "ignored_crossing_tokens": len(ignored),
                         "source_window_index": window_index})
    if not retained or len(covered) != len(spans):
        return {"retained": False, "reasons": ["incomplete_gold_coverage"],
                "windows": [], "covered": covered,
                "windows_discarded_alignment": discarded}
    return {"retained": True, "reasons": [], "windows": retained,
            "covered": covered, "windows_discarded_alignment": discarded}


def empty_stats():
    return {"rows_excluded_by_reason": {reason: 0 for reason in EXCLUSION_REASONS},
            "windows_discarded_alignment": 0, "gold_spans_retained": 0,
            "gold_spans_fully_covered": 0, "ignored_crossing_tokens_retained": 0}
