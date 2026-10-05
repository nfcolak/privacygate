"""Engine dispatch for the CLI: regex (stdlib only), mbert, hybrid. Never logs text, values or confidences.

mBERT/hybrid are imported lazily (torch/transformers) and run strictly offline with local assets.
"""
import os
from pathlib import Path
from typing import NoReturn

ENGINES = ("regex", "mbert", "hybrid")
POLICIES = ("union", "rules_first", "rules_first_thr", "union_refined")
DEFAULT_THR = 0.5  # rules_first_thr default (the dev-chosen value in the README)
LAST_UNCOVERED_CHARS = 0  # value-free diagnostic for the most recent run; not thread-local


class InferenceError(Exception):
    """Generic, value-free error; message is safe to print."""


def _fail(msg) -> NoReturn:
    raise InferenceError(msg) from None


def uncovered_regions(text, covered_offsets):
    """Maximal non-whitespace runs outside all half-open token offsets.

    Accepts offsets from every predicted window, in any order; None denotes a special
    token and empty offsets cover nothing. Invalid offsets fail with a value-free error.
    This is a pure character-coverage check, not a detector-quality certificate.
    """
    n = len(text)
    covered = bytearray(n)
    for offset in covered_offsets:
        if offset is None:
            continue
        if not isinstance(offset, (tuple, list)) or len(offset) != 2:
            _fail("invalid token offsets for coverage")
        a, b = offset
        if type(a) is not int or type(b) is not int or not 0 <= a <= b <= n:
            _fail("invalid token offsets for coverage")
        covered[a:b] = b"\x01" * (b - a)
    out, start = [], None
    for i, ch in enumerate(text):
        if not covered[i] and not ch.isspace():
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, n))
    return out


def merge_spans(spans, n):
    """Validate offsets against text length n and union overlapping spans (first label wins).
    Returns [{start,end,label}] sorted, non-overlapping."""
    clean = []
    for s in spans:
        a, b = s["start"], s["end"]
        if not (isinstance(a, int) and isinstance(b, int)) or not (0 <= a < b <= n):
            _fail("invalid span offsets from detector")
        clean.append((a, b, s["label"]))
    clean.sort(key=lambda c: (c[0], -c[1], c[2]))
    out = []
    for a, b, l in clean:
        if out and a < out[-1]["end"]:
            out[-1]["end"] = max(out[-1]["end"], b)
        else:
            out.append({"start": a, "end": b, "label": l})
    return out


def apply_mask(text, spans):
    parts, pos = [], 0
    for sp in spans:
        parts.append(text[pos:sp["start"]])
        parts.append("[" + sp["label"] + "]")
        pos = sp["end"]
    parts.append(text[pos:])
    return {"masked_text": "".join(parts), "entities": spans}


def _load_mbert(model_dir):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    p = Path(model_dir)
    if not p.is_dir() or not (p / "config.json").is_file():
        _fail("model directory not found or incomplete (local path required)")
    try:
        from privacygate.model import hybrid
        return hybrid.Mbert(p)
    except Exception:
        _fail("could not load mBERT model/tokenizer offline (check --model-dir and local HF cache; "
              "torch/transformers must be installed)")


def run_with_completion(text, engine="regex", model_dir=None, policy="union", confidence=None,
                        refine=False, _mbert=None):
    """Legacy inference plus a per-call completion receipt (no global diagnostic reads).

    _mbert is an internal adapter for the pipeline's cached model. All detection,
    policy, refinement and rendering operations retain the legacy ordering.
    """
    global LAST_UNCOVERED_CHARS
    LAST_UNCOVERED_CHARS = 0
    uncovered_count = 0
    if engine == "regex":
        from privacygate.detect import mask
        return dict(mask(text), completion={"uncovered_chars": 0})
    if engine not in ENGINES or policy not in POLICIES:
        _fail("invalid engine or policy")
    from privacygate.model import hybrid  # stdlib only at import time
    if model_dir is None:
        model_dir = hybrid.DEFAULT_MODEL_DIR
    mb = _mbert if _mbert is not None else _load_mbert(model_dir)
    try:
        # Use the offsets returned by actual prediction, not a separate re-encoding.
        raw = mb.raw([text])[0]
        regions = uncovered_regions(text, (o for offs, _, _ in raw for o in offs))
        uncovered_count = sum(b - a for a, b in regions)
        LAST_UNCOVERED_CHARS = uncovered_count
        coverage = [{"start": a, "end": b, "label": "UNCOVERED", "source": "coverage"}
                    for a, b in regions]
        thr = confidence or 0.0
        if engine == "hybrid" and policy == "rules_first_thr" and confidence is None:
            thr = DEFAULT_THR
        detected = mb.spans(raw, thr)
        if engine == "mbert":
            spans = detected + coverage
            if refine:
                from privacygate.rules.refine import refine as _refine
                spans = _refine(text, spans)
        else:
            rx = hybrid.regex(text)
            if policy in ("union", "union_refined"):
                spans = hybrid.union(rx, detected)
            else:
                spans = hybrid.rules_first(rx, detected)
            # Coverage must bypass rule precedence/confidence and survive final refinement/merge.
            spans.extend(coverage)
            if policy == "union_refined":
                from privacygate.rules.refine import refine as _refine
                spans = _refine(text, spans)
    except InferenceError:
        raise
    except Exception:
        _fail("inference failed (input not shown)")
    result = apply_mask(text, merge_spans(spans, len(text)))
    result["completion"] = {"uncovered_chars": uncovered_count}
    return result


def run(text, engine="regex", model_dir=None, policy="union", confidence=None, refine=False):
    """Legacy two-field result, with byte-identical masking and entity ordering.

    LAST_UNCOVERED_CHARS remains a backward-compatible, non-thread-local diagnostic.
    New callers should use the per-call receipt from run_with_completion instead.
    """
    result = run_with_completion(text, engine, model_dir, policy, confidence, refine)
    return {"masked_text": result["masked_text"], "entities": result["entities"]}


def mbert_candidates(text, model_dir=None, _mbert=None, _raw=None):
    """Scored contract candidates and protected coverage from actual model windows.

    The raw token/window arrays are ephemeral; only value-free candidate dicts and
    aggregate completion leave this adapter. No confidence filtering is applied.
    """
    global LAST_UNCOVERED_CHARS
    LAST_UNCOVERED_CHARS = 0
    if not isinstance(text, str):
        _fail("invalid inference input")
    from privacygate.model import hybrid
    from privacygate.data.spans import make_candidate, validate
    mb = _mbert if _mbert is not None else _load_mbert(
        hybrid.DEFAULT_MODEL_DIR if model_dir is None else model_dir)
    try:
        raw = mb.raw([text])[0] if _raw is None else _raw
        regions = uncovered_regions(text, (o for offs, _, _ in raw for o in offs))
        count = sum(b - a for a, b in regions)
        cands = [make_candidate(s["start"], s["end"], s["label"], "mbert", score=s["score"])
                 for s in mb.spans_with_scores(raw)]
        coverage = [make_candidate(a, b, "UNCOVERED", "coverage", validation="n/a",
                                   protected=True, stage="coverage") for a, b in regions]
        LAST_UNCOVERED_CHARS = count
        return {"candidates": validate(text, cands), "coverage": validate(text, coverage),
                "completion": {"uncovered_chars": count}}
    except InferenceError:
        raise
    except Exception:
        _fail("inference failed (input not shown)")
