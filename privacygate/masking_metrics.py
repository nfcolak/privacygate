"""Value-free, class-agnostic original-character masking diagnostics (synthetic dev only).

Intervals are half-open Python Unicode character offsets, not bytes or graphemes.
No text, identifiers, offsets or predicted fragments are returned by aggregate scoring.
"""
from collections import Counter
from typing import Any

SCORER_VERSION = "masking-union-v1"
LABELS = frozenset({
    "ACCOUNTNUM", "AGE", "BUILDINGNUM", "CITY", "CREDITCARDNUMBER", "DATE",
    "DRIVERLICENSENUM", "EMAIL", "GENDER", "GIVENNAME", "IBAN", "IDCARDNUM",
    "PASSPORTNUM", "PERSONALREF", "SEX", "SOCIALNUM", "STREET", "SURNAME",
    "TAXNUM", "TELEPHONENUM", "TITLE", "USERNAME", "ZIPCODE",
})
CLASSES = (
    "exact_correct_label", "exact_different_label", "fully_covered_nonexact",
    "partially_covered", "untouched",
)
DEFINITIONS = {
    "offsets": "Half-open [start,end) Python Unicode code-point offsets; bool/invalid/out-of-bounds rejected, never clipped.",
    "coverage": "Intersection of gold character union with final masked-original-interval union, regardless of predicted label. Adjacent and overlapping intervals count once.",
    "complete_span": "Every original character position in the gold span is in the final masking union.",
    "positive_row": "A row with nonempty gold; success requires every gold span fully covered. Clean controls never inflate completeness.",
    "alnum": "Python str.isalnum() Unicode letters/numbers only; separate from all-character coverage and not a privacy guarantee.",
    "excess": "Final predicted character union minus ALL gold character union on a row; outside annotations, not proof of non-personal content.",
    "classification_precedence": "Raw exact correct-label > raw exact different-label > final-union fully covered through larger/combined intervals > partial intersection > untouched. Mutually exclusive; exact classifications must also be fully covered.",
    "final_mask_classification": "Same precedence applied to final CLI entities rather than raw detection candidates, with the same final masking union. Labels may change during overlap merging.",
    "label_overlap": "For each touched gold span: any overlapping raw correct-label candidate versus only different-label candidates; diagnostic only, never used to filter predictions.",
    "per_label_rows": "Rows containing this gold label; fully_masked_positive_rows means all gold spans of THIS label covered, not all labels on those rows.",
    "per_label_excess": "Whole-row excess against ALL gold for rows containing this label; repeated across labels and NOT additive. Masked/text/clean row counts have the same row-scoped convention.",
    "clean": "Empty-gold controls have separate masked-row/character counts and null (N/A) completeness ratios.",
    "raw_vs_final": "Raw mBERT decoded window candidates (deduplicated by hybrid.Mbert.spans); hybrid raw candidates are regex plus mBERT. Coverage uses actual CLI overlap merging, including hybrid.union then inference.merge_spans. No substring disappearance test.",
    "historical": "Not historical strict F1: exact offsets AND label are detection correctness, not class-agnostic masking coverage. No historical artifacts changed or scorer equivalence asserted.",
    "annotation_limit": "Only annotated synthetic dev spans are measured. Unannotated personal information may exist; excess is annotation-relative. Cannot establish coverage of all real personal information or complete address/person linkage.",
}


class MaskingError(ValueError):
    """Only fixed, value-free error codes may cross the CLI boundary."""


def _integer(value):
    return type(value) is int


def _length(n):
    if not _integer(n) or n < 0:
        raise MaskingError("mask_length")


def validate_spans(spans, n, gold=False):
    _length(n)
    if not isinstance(spans, list):
        raise MaskingError("mask_span_schema")
    pairs = []
    for span in spans:
        if not isinstance(span, dict) or not {"start", "end", "label"} <= span.keys():
            raise MaskingError("mask_span_schema")
        a, b = span["start"], span["end"]
        if not _integer(a) or not _integer(b):
            raise MaskingError("mask_offset_type")
        if not 0 <= a < b <= n:
            raise MaskingError("mask_offset_bounds")
        if not isinstance(span["label"], str) or span["label"] not in LABELS:
            raise MaskingError("mask_label")
        pairs.append((a, b))
    if gold:
        pairs.sort()
        if any(b > c for (_, b), (c, _) in zip(pairs, pairs[1:])):
            raise MaskingError("mask_gold_overlap")


def interval_union(intervals, n):
    """Validated, disjoint union; merge adjacent intervals as well as overlaps."""
    _length(n)
    clean = []
    for pair in intervals:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise MaskingError("mask_interval_schema")
        a, b = pair
        if not _integer(a) or not _integer(b):
            raise MaskingError("mask_offset_type")
        if not 0 <= a < b <= n:
            raise MaskingError("mask_offset_bounds")
        clean.append((a, b))
    out = []
    for a, b in sorted(clean):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def intersection(left, right, n):
    """Validated union intersection, never double counting repeated intervals."""
    left, right = interval_union(left, n), interval_union(right, n)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        a, b = max(left[i][0], right[j][0]), min(left[i][1], right[j][1])
        if a < b:
            out.append((a, b))
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return out


def count_chars(intervals, n):
    return sum(b - a for a, b in interval_union(intervals, n))


def count_alnum(text, intervals):
    return sum(text[i].isalnum() for a, b in interval_union(intervals, len(text)) for i in range(a, b))


def span_class(gold, candidates, covered):
    a, b, label = gold["start"], gold["end"], gold["label"]
    exact = [p for p in candidates if p["start"] == a and p["end"] == b]
    if any(p["label"] == label for p in exact):
        category = "exact_correct_label"
    elif exact:
        category = "exact_different_label"
    elif covered == b - a:
        category = "fully_covered_nonexact"
    elif covered:
        category = "partially_covered"
    else:
        category = "untouched"
    if category.startswith("exact_") and covered != b - a:
        raise MaskingError("mask_semantics_mismatch")
    return category


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


class Aggregate:
    """Aggregates only. Row-level offsets/text/IDs are not retained."""
    def __init__(self):
        self.counts = Counter()
        self.classes = Counter({key: 0 for key in CLASSES})
        self.final_classes = Counter({key: 0 for key in CLASSES})
        self.overlap_labels = Counter()
        self.clean = Counter()

    def add(self, text, gold, raw, final, all_gold=None):
        n = len(text)
        validate_spans(gold, n, gold=True)
        validate_spans(raw, n)
        validate_spans(final, n)
        all_gold = gold if all_gold is None else all_gold
        validate_spans(all_gold, n, gold=True)
        mask_union = interval_union([(p["start"], p["end"]) for p in final], n)
        raw_union = interval_union([(p["start"], p["end"]) for p in raw], n)
        if raw_union != mask_union:
            raise MaskingError("mask_semantics_mismatch")
        gold_union = interval_union([(g["start"], g["end"]) for g in all_gold], n)
        masked = count_chars(mask_union, n)
        self.counts["rows"] += 1
        self.counts["text_chars"] += n
        self.counts["masked_chars"] += masked
        self.counts["excess_masked_chars"] += masked - count_chars(intersection(mask_union, gold_union, n), n)
        self.counts["raw_detection_candidates"] += len(raw)
        self.counts["final_mask_entities"] += len(final)
        if not gold:
            self.clean["rows"] += 1
            self.clean["masked_rows"] += bool(masked)
            self.clean["masked_chars"] += masked
            self.clean["text_chars"] += n
            return
        self.counts["positive_rows"] += 1
        complete = 0
        for g in gold:
            a, b = g["start"], g["end"]
            hits = intersection([(a, b)], mask_union, n)
            covered, alnum = count_chars(hits, n), count_alnum(text, [(a, b)])
            leaked_alnum = alnum - count_alnum(text, hits)
            category = span_class(g, raw, covered)
            self.classes[category] += 1
            self.final_classes[span_class(g, final, covered)] += 1
            self.counts["gold_spans"] += 1
            self.counts["gold_chars"] += b - a
            self.counts["covered_gold_chars"] += covered
            self.counts["uncovered_gold_chars"] += b - a - covered
            self.counts["gold_alnum_chars"] += alnum
            self.counts["covered_gold_alnum_chars"] += alnum - leaked_alnum
            self.counts["leaked_gold_alnum_chars"] += leaked_alnum
            self.counts["gold_spans_with_alnum_leakage"] += leaked_alnum > 0
            if covered == b - a:
                complete += 1
                self.counts["complete_gold_spans"] += 1
            else:
                self.counts["partial_gold_spans" if covered else "untouched_gold_spans"] += 1
                self.counts["nonalnum_only_incomplete_gold_spans"] += leaked_alnum == 0
            if covered:
                correct_overlap = any(p["label"] == g["label"] and p["start"] < b and a < p["end"] for p in raw)
                key = category + ("_correct_label_overlap" if correct_overlap else "_only_different_label_overlap")
                self.overlap_labels[key] += 1
        self.counts["fully_masked_positive_rows"] += complete == len(gold)

    def report(self):
        keys = (
            "rows", "positive_rows", "fully_masked_positive_rows", "gold_spans", "complete_gold_spans",
            "partial_gold_spans", "untouched_gold_spans", "gold_chars", "covered_gold_chars", "uncovered_gold_chars",
            "gold_alnum_chars", "covered_gold_alnum_chars", "leaked_gold_alnum_chars", "gold_spans_with_alnum_leakage",
            "nonalnum_only_incomplete_gold_spans", "text_chars", "masked_chars", "excess_masked_chars",
            "raw_detection_candidates", "final_mask_entities",
        )
        out: dict[str, Any] = {key: self.counts[key] for key in keys}
        out["raw_detection_classification"] = dict(self.classes)
        out["final_mask_classification"] = dict(self.final_classes)
        out["raw_label_overlap_diagnostic"] = dict(sorted(self.overlap_labels.items()))
        out["ratios"] = {
            "complete_gold_spans": _ratio(out["complete_gold_spans"], out["gold_spans"]),
            "covered_original_gold_chars": _ratio(out["covered_gold_chars"], out["gold_chars"]),
            "leaked_gold_alnum_chars": _ratio(out["leaked_gold_alnum_chars"], out["gold_alnum_chars"]),
            "fully_masked_positive_rows": _ratio(out["fully_masked_positive_rows"], out["positive_rows"]),
        }
        out["clean_controls"] = {key: self.clean[key] for key in ("rows", "masked_rows", "masked_chars", "text_chars")}
        out["clean_controls"]["completeness_ratio"] = None
        if sum(self.classes.values()) != out["gold_spans"] or sum(self.final_classes.values()) != out["gold_spans"]:
            raise MaskingError("mask_count_mismatch")
        if out["complete_gold_spans"] + out["partial_gold_spans"] + out["untouched_gold_spans"] != out["gold_spans"]:
            raise MaskingError("mask_count_mismatch")
        return out


class EngineAggregate:
    def __init__(self):
        self.overall = Aggregate()
        self.languages = {}
        self.labels = {}

    def add(self, text, gold, language, raw, final):
        self.overall.add(text, gold, raw, final)
        self.languages.setdefault(language, Aggregate()).add(text, gold, raw, final)
        for label in sorted({g["label"] for g in gold}):
            self.labels.setdefault(label, Aggregate()).add(text, [g for g in gold if g["label"] == label], raw, final, all_gold=gold)

    def report(self):
        return {
            "overall": self.overall.report(),
            "per_language": {key: value.report() for key, value in sorted(self.languages.items())},
            "per_gold_label": {key: value.report() for key, value in sorted(self.labels.items())},
        }
