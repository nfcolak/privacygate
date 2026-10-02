"""Engine dispatch for the CLI: regex (stdlib only), mbert, hybrid. Never logs text, values or confidences.

mBERT/hybrid are imported lazily (torch/transformers) and run strictly offline with local assets.
"""
import os
from pathlib import Path

ENGINES = ("regex", "mbert", "hybrid")
POLICIES = ("union", "rules_first", "rules_first_thr")
DEFAULT_THR = 0.5  # rules_first_thr default (the dev-chosen value in the README)


class InferenceError(Exception):
    """Generic, value-free error; message is safe to print."""


def _fail(msg):
    raise InferenceError(msg) from None


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
        from . import hybrid
        return hybrid.Mbert(p)
    except Exception:
        _fail("could not load mBERT model/tokenizer offline (check --model-dir and local HF cache; "
              "torch/transformers must be installed)")


def run(text, engine="regex", model_dir=None, policy="union", confidence=None):
    """Return {masked_text, entities:[{start,end,label}]} for text."""
    if engine == "regex":
        from .detect import mask
        return mask(text)
    if engine not in ENGINES or policy not in POLICIES:
        _fail("invalid engine or policy")
    from . import hybrid  # stdlib only at import time
    if model_dir is None:
        model_dir = hybrid.DEFAULT_MODEL_DIR
    mb = _load_mbert(model_dir)
    try:
        if engine == "mbert":
            spans = mb.detect(text, confidence or 0.0)
        else:
            rx = hybrid.regex(text)
            if policy == "union":
                spans = hybrid.union(rx, mb.detect(text, confidence or 0.0))
            elif policy == "rules_first":
                spans = hybrid.rules_first(rx, mb.detect(text, confidence or 0.0))
            else:
                thr = DEFAULT_THR if confidence is None else confidence
                spans = hybrid.rules_first(rx, mb.detect(text, thr))
    except InferenceError:
        raise
    except Exception:
        _fail("inference failed (input not shown)")
    return apply_mask(text, merge_spans(spans, len(text)))
