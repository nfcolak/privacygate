"""Value-free candidate contract and class-agnostic original-coordinate unions."""
import math
from typing import NoReturn

FIELDS = frozenset(("start", "end", "label", "source", "score", "validation",
                    "context", "protected", "stage"))
VALIDATIONS = frozenset(("valid", "invalid", "unknown", "n/a"))
CONTEXTS = frozenset(("personal", "nonpersonal", "unknown"))
STAGES = frozenset(("raw", "assembled", "propagated", "refined", "coverage"))
_NAME_PARTS = frozenset(("GIVENNAME", "MIDDLENAME", "SURNAME", "TITLE"))
_REGION_PARTS = {
    "PERSONNAME": _NAME_PARTS,
    "ADDRESS": _NAME_PARTS | frozenset(("PERSONNAME", "STREET", "BUILDINGNUM", "ZIPCODE",
                                        "CITY", "STATE", "COUNTRY", "POBOX")),
}


def _fail() -> NoReturn:
    raise ValueError("invalid_candidate_contract") from None


def _check(cand, n=None):
    if not isinstance(cand, dict) or set(cand) != FIELDS:
        _fail()
    a, b = cand["start"], cand["end"]
    if type(a) is not int or type(b) is not int or not 0 <= a < b:
        _fail()
    if n is not None and b > n:
        _fail()
    if not isinstance(cand["label"], str) or not cand["label"]:
        _fail()
    if not isinstance(cand["source"], str) or not cand["source"]:
        _fail()
    score = cand["score"]
    if score is not None and (type(score) is not float or not math.isfinite(score)):
        _fail()
    for key, choices in (("validation", VALIDATIONS), ("context", CONTEXTS), ("stage", STAGES)):
        if not isinstance(cand[key], str) or cand[key] not in choices:
            _fail()
    if type(cand["protected"]) is not bool:
        _fail()
    return dict(cand)


def make_candidate(start, end, label, source, score=None, validation="unknown",
                   context="unknown", protected=False, stage="raw"):
    """Construct a checked dict; validate(text, ...) additionally bounds it to the input.

    Labels and sources are extensible strings, not model-taxonomy allowlists. Enum
    fields are fixed. Scores are finite floats or None; no score threshold is applied.
    """
    return _check({"start": start, "end": end, "label": label, "source": source,
                   "score": score, "validation": validation, "context": context,
                   "protected": protected, "stage": stage})


def validate(text, cands):
    """Return independent contract-only copies, or raise a fixed value-free error.

    Offsets are half-open Python str indices, including for non-BMP characters.
    Booleans are not integers here. Extra fields (including text/values) are forbidden.
    """
    if not isinstance(text, str) or not isinstance(cands, (list, tuple)):
        _fail()
    return [_check(cand, len(text)) for cand in cands]


def union(cands):
    """Union overlapping/touching intervals without labels changing coverage.

    Earliest start wins the display label; ties prefer the longest interval, then
    label. A containing ADDRESS/PERSONNAME wins over its contained component.
    Adjacent regions have no intervening character and are therefore unioned too.
    validate(text, cands) must be called first to enforce the input-length bound.
    """
    if not isinstance(cands, (list, tuple)):
        _fail()
    items = sorted((_check(cand) for cand in cands),
                   key=lambda c: (c["start"], -c["end"], c["label"]))
    out, group, end = [], [], -1

    def flush():
        pick = group[0]
        for region in group:
            if (pick["label"] in _REGION_PARTS.get(region["label"], ())
                    and region["start"] <= pick["start"]
                    and pick["end"] <= region["end"]):
                pick = region
        out.append({"start": group[0]["start"], "end": max(c["end"] for c in group),
                    "label": pick["label"]})

    for cand in items:
        if group and cand["start"] > end:
            flush()
            group = []
        end = max(end, cand["end"]) if group else cand["end"]
        group.append(cand)
    if group:
        flush()
    return out
