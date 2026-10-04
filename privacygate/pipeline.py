"""Versioned, offline staged masking; candidate ledger stays in original coordinates.

Stdlib only at import time. Required detector modules are lazy, never silently skipped.
Blocked calls release neither original text nor partial masks. No raw-value logging.
"""
from functools import lru_cache
import hashlib
import importlib
import json
import math
from pathlib import Path
from threading import RLock
from typing import NoReturn

from . import inference
from .spans import make_candidate, validate, union

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "pipeline-v1.json"
PROFILES = ("legacy_union_refined", "structured", "structured_address_names", "full", "full_calibrated")
# A single shared model is serialized for safe process-local inference/cache use.
_MODEL_LOCK = RLock()
_REQUIRED = {
    "structured.detect": ("structured", "detect"),
    "structured.check": ("structured", "check"),
    "context.decide": ("context", "decide"),
    "address.assemble": ("address", "assemble"),
    "names.assemble": ("names", "assemble"),
    "names.propagate": ("names", "propagate"),
    "refine": ("refine", "refine"),
}
_BASE = ("mbert", "regex", "structured.detect", "structured.check")
_TAIL = ("refine", "coverage", "union", "render")
_EXPECTED = {
    "legacy_union_refined": ("mbert", "regex", "legacy_union", "coverage", "refine", "legacy_merge", "render"),
    "structured": _BASE + _TAIL,
    "structured_address_names": _BASE + ("address.assemble", "names.assemble", "names.propagate") + _TAIL,
    "full": _BASE + ("context.decide", "address.assemble", "names.assemble", "names.propagate") + _TAIL,
}
_EXPECTED["full_calibrated"] = ("mbert", "calibrate") + _EXPECTED["full"][1:]


class PipelineError(Exception):
    """Only fixed, value-free codes are raised internally."""


def _fail(code) -> NoReturn:
    raise PipelineError(code) from None


def _stages(profile):
    if not isinstance(profile, str) or profile not in PROFILES:
        _fail("pipeline_profile_invalid")
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        stages = tuple(config["profiles"][profile]["stages"])
        if config["version"] != 1 or stages != _EXPECTED[profile]:
            _fail("pipeline_config_invalid")
        return stages
    except PipelineError:
        raise
    except Exception:
        _fail("pipeline_config_invalid")


def _modules(stages):
    modules = {}
    for stage in stages:
        if stage not in _REQUIRED:
            continue
        name, method = _REQUIRED[stage]
        try:
            if name not in modules:
                modules[name] = importlib.import_module("." + name, __package__)
            if not callable(getattr(modules[name], method, None)):
                _fail("pipeline_stage_unavailable:" + name)
        except PipelineError:
            raise
        except Exception:
            _fail("pipeline_stage_unavailable:" + name)
    return modules


@lru_cache(maxsize=None)
def _cached_mbert(model_path):
    return inference._load_mbert(model_path)


def _get_mbert(model_dir):
    if model_dir is None:
        from .hybrid import DEFAULT_MODEL_DIR
        model_dir = DEFAULT_MODEL_DIR
    return _cached_mbert(str(Path(model_dir).expanduser().resolve()))


@lru_cache(maxsize=8)
def _weight_hash(path, identity):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _model_sha256(model_dir):
    if model_dir is None:
        from .hybrid import DEFAULT_MODEL_DIR
        model_dir = DEFAULT_MODEL_DIR
    path = (Path(model_dir).expanduser().resolve() / "model.safetensors")
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    return _weight_hash(str(path), identity)


def _calibration(profile, model_dir):
    """Admit thresholds before inference; errors never disclose paths or values."""
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        path = config["profiles"][profile]["threshold_file"]
        if not isinstance(path, str) or not path:
            _fail("pipeline_calibration_invalid")
        path = Path(path)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            _fail("pipeline_calibration_unavailable")
        data = json.loads(path.read_text(encoding="utf-8"))
        thresholds, default = data["thresholds"], data["default"]
        if not isinstance(thresholds, dict) or any(
                not isinstance(label, str) or not label for label in thresholds):
            _fail("pipeline_calibration_invalid")
        for value in [default, *thresholds.values()]:
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                _fail("pipeline_calibration_invalid")
        digest = data["model_sha256"]
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            _fail("pipeline_calibration_invalid")
        if digest != _model_sha256(model_dir):
            _fail("pipeline_calibration_model_mismatch")
        return data
    except PipelineError:
        raise
    except Exception:
        _fail("pipeline_calibration_invalid")


def _calibrate(text, ledger, calibration, structured):
    """Drop only whole raw MODEL proposals; validation/protection always wins."""
    kept = []
    for cand in ledger:
        threshold = calibration["thresholds"].get(cand["label"], calibration["default"])
        droppable = (cand["source"] == "mbert" and cand["stage"] == "raw"
                     and not cand["protected"] and cand["validation"] != "valid"
                     and cand["score"] is not None and cand["score"] < threshold)
        if droppable:
            # The stage precedes structured.check, so check would-be drops now.
            # Keep original metadata; the declared check stage remains unchanged.
            checked = _checked(text, [structured.check(text, dict(cand))])[0]
            if any(checked[k] != cand[k] for k in
                   ("start", "end", "label", "source", "stage", "protected")):
                _fail("pipeline_candidate_invalid")
            droppable = checked["validation"] != "valid" and not checked["protected"]
        if not droppable:
            kept.append(cand)
    return kept


def _blocked(error):
    return {"status": "blocked", "masked_text": "", "entities": [],
            "completion": {"uncovered_chars": 0}, "diagnostics": {"errors": 1},
            "error": error}


def _checked(text, cands):
    try:
        return validate(text, cands)
    except Exception:
        _fail("pipeline_candidate_invalid")


def _add(text, ledger, added, source, stage):
    added = _checked(text, added)
    if any(c["source"] != source or c["stage"] != stage for c in added):
        _fail("pipeline_candidate_invalid")
    ledger.extend(added)
    return len(added)


def _admit_additions(text, ledger, added, modules):
    """Arbitrate only novel assembler coverage, never the accepted mask ledger.

    A context rejection alone cannot revoke an old personal envelope: suppression
    requires an explicit nonpersonal scope bound to this field/sentence. Covered
    parts of rejected additions are still masked by the unchanged raw/protected
    ledger, which _refined restores before final union.
    """
    added = _checked(text, added)
    from .address import scope_allowed
    return [cand for cand in added if scope_allowed(text, cand, ledger)]


def _refined(text, ledger):
    from .refine import refine
    # The legacy refiner strips metadata. Keep ledger/protected seeds separately
    # and restore evidence for unchanged intervals when adapting its output.
    refined = []
    for cand in refine(text, ledger):
        match = next((c for c in ledger if (c["start"], c["end"], c["label"], c["source"])
                      == (cand["start"], cand["end"], cand["label"], cand["source"])), None)
        if match is not None:
            refined.append(dict(match, stage="refined"))
        else:
            refined.append(make_candidate(cand["start"], cand["end"], cand["label"],
                                          cand["source"], stage="refined"))
    # Refinement is additive in new profiles: accepted/unresolved proposals must
    # still be masked even if a legacy heuristic discards AGE or metadata. Keep
    # the original ledger so whole-region labels and protected anchors survive.
    refined.extend(dict(c) for c in ledger)
    return _checked(text, refined)


def _address_union(text, cands):
    """Prefer separate value labels inside ADDRESS envelopes, without unmasking.

    The ordinary union remains the coverage authority. Only label arbitration
    inside a conflicting address group changes: non-address values win their
    own intervals, and every residual character keeps its original mask. A
    contact cue already covered by an over-wide ADDRESS belongs to the adjacent
    contact label, not to the postal region; it is never newly masked here.
    """
    from .address import contact_cues, value_boundaries

    baseline = union(cands)
    addresses = [c for c in cands if c["label"] == "ADDRESS"]
    if not addresses:
        return baseline
    foreign = value_boundaries(text, cands)
    overrides = union([c for c in foreign if any(
        a["start"] < c["end"] and c["start"] < a["end"] for a in addresses
    )])
    cues = contact_cues(text)
    out = []
    for region in baseline:
        lo, hi = region["start"], region["end"]
        choices = [dict(c, start=max(lo, c["start"]), end=min(hi, c["end"]))
                   for c in overrides if c["start"] < hi and lo < c["end"]]
        if not choices:
            out.append(region)
            continue
        for choice in choices:
            if choice["label"] not in {"TELEPHONENUM", "EMAIL"}:
                continue
            for start, end in reversed(cues):
                if (lo <= start < end <= choice["start"]
                        and not text[end:choice["start"]].strip(" \t.:=,-;()")
                        and any(a["start"] <= start and end <= a["end"] for a in addresses)):
                    choice["start"] = start
                    break
        points = sorted({lo, hi} | {p for c in choices for p in (c["start"], c["end"])})
        parts = []
        for start, end in zip(points, points[1:]):
            label = next((c["label"] for c in choices
                          if c["start"] <= start and end <= c["end"]), "ADDRESS")
            if parts and parts[-1]["label"] == label:
                parts[-1]["end"] = end
            else:
                parts.append({"start": start, "end": end, "label": label})
        out.extend(parts)
    return out


def _run(text, profile, model_dir, stages, modules, calibration=None):
    model = _get_mbert(model_dir)
    if profile == "legacy_union_refined":
        result = inference.run_with_completion(text, engine="hybrid", model_dir=model_dir,
                                               policy="union_refined", _mbert=model)
        return {"status": "ok", "masked_text": result["masked_text"], "entities": result["entities"],
                "completion": result["completion"],
                "diagnostics": {"final_entities": len(result["entities"]), "errors": 0}}

    batch = inference.mbert_candidates(text, model_dir=model_dir, _mbert=model)
    return _finish(text, batch, stages, modules, calibration)


def _finish(text, batch, stages, modules, calibration=None):
    """Replay only deterministic stages from an in-memory model candidate batch."""
    from .hybrid import regex
    ledger = _checked(text, batch["candidates"])
    diag = {"model_candidates": len(ledger), "regex_candidates": 0, "structured_candidates": 0,
            "validated_candidates": 0, "context_accept": 0, "context_reject": 0,
            "context_unresolved": 0, "protected_reject_prevented": 0,
            "address_candidates": 0, "name_candidates": 0, "propagated_candidates": 0,
            "refined_candidates": 0, "coverage_candidates": len(batch["coverage"]), "errors": 0}
    if "calibrate" in stages:
        if calibration is None:
            _fail("pipeline_calibration_unavailable")
        ledger = _calibrate(text, ledger, calibration, modules["structured"])
        diag["calibration_dropped"] = diag["model_candidates"] - len(ledger)
    rx = [make_candidate(c["start"], c["end"], c["label"], "regex", validation="n/a")
          for c in regex(text)]
    diag["regex_candidates"] = _add(text, ledger, rx, "regex", "raw")
    structured = modules["structured"]
    diag["structured_candidates"] = _add(text, ledger, structured.detect(text), "structured", "raw")

    checked = []
    for cand in ledger:
        if cand["source"] == "mbert":
            updated = _checked(text, [structured.check(text, dict(cand))])[0]
            if any(updated[k] != cand[k] for k in ("start", "end", "label", "source", "stage", "protected")):
                _fail("pipeline_candidate_invalid")
            checked.append(updated)
            diag["validated_candidates"] += 1
        else:
            checked.append(cand)
    ledger = checked

    if "context.decide" in stages:
        accepted = []
        for cand in ledger:
            decision = modules["context"].decide(text, dict(cand), [dict(c) for c in ledger])
            if (not isinstance(decision, tuple) or len(decision) != 2
                    or decision[0] not in ("accept", "reject", "unresolved")
                    or not isinstance(decision[1], str) or not decision[1]):
                _fail("pipeline_context_invalid")
            action = decision[0]
            if action == "reject" and cand["protected"]:
                action = "unresolved"
                diag["protected_reject_prevented"] += 1
            diag["context_" + action] += 1
            if action != "reject":
                accepted.append(cand)
        ledger = accepted

    if "address.assemble" in stages:
        added = _admit_additions(text, ledger, modules["address"].assemble(text, [dict(c) for c in ledger]), modules)
        diag["address_candidates"] = _add(text, ledger, added, "address", "assembled")
    if "names.assemble" in stages:
        added = _admit_additions(text, ledger, modules["names"].assemble(text, [dict(c) for c in ledger]), modules)
        diag["name_candidates"] = _add(text, ledger, added, "names", "assembled")
    if "names.propagate" in stages:
        added = _admit_additions(text, ledger, modules["names"].propagate(text, [dict(c) for c in ledger]), modules)
        diag["propagated_candidates"] = _add(text, ledger, added, "names", "propagated")

    final = _refined(text, ledger)
    diag["refined_candidates"] = len(final)
    # Coverage never enters context arbitration or semantic refinement.
    final.extend(batch["coverage"])
    checked_final = _checked(text, final)
    entities = (_address_union(text, checked_final) if "address.assemble" in stages
                else union(checked_final))
    diag["protected_candidates"] = sum(c["protected"] for c in final)
    diag["final_entities"] = len(entities)
    rendered = inference.apply_mask(text, entities)
    return {"status": "ok", "masked_text": rendered["masked_text"], "entities": entities,
            "completion": dict(batch["completion"]), "diagnostics": diag}


def run_pipeline(text, profile="full", model_dir=None):
    """Run a declared profile; status=blocked never includes original/partial text.

    Required-stage admission precedes model loading. Models are cached by resolved
    local path for this process, while candidates/receipts remain document-local.
    An ok receipt establishes processing only, not complete semantic PII recall.
    """
    if not isinstance(text, str):
        return _blocked("pipeline_input_invalid")
    try:
        stages = _stages(profile)
        modules = _modules(stages)
        with _MODEL_LOCK:
            calibration = _calibration(profile, model_dir) if "calibrate" in stages else None
            return _run(text, profile, model_dir, stages, modules, calibration)
    except PipelineError as error:
        return _blocked(str(error))
    except inference.InferenceError:
        return _blocked("pipeline_inference_failed")
    except Exception:
        return _blocked("pipeline_processing_failed")
