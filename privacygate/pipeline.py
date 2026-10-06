"""Versioned, offline staged masking; candidate ledger stays in original coordinates.

Stdlib only at import time. Required detector modules are lazy, never silently skipped.
Blocked calls release neither original text nor partial masks. No raw-value logging.
"""
from functools import lru_cache
import importlib
import json
from pathlib import Path
from threading import RLock
from typing import NoReturn

from privacygate.model import inference
from privacygate.data.spans import make_candidate, validate, union

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "pipeline-v1.json"
# configs/pipeline-v1.json also lists retired profiles; its bytes stay unchanged
# because blind/ext-step1 manifests bind its sha256. Only "full" is admitted.
PROFILES = ("full",)
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
_MODULE_PATHS = {
    "structured": "rules.structured",
    "context": "rules.context",
    "address": "assemblers.address",
    "names": "assemblers.names",
    "refine": "rules.refine",
}
_BASE = ("mbert", "regex", "structured.detect", "structured.check")
_TAIL = ("refine", "coverage", "union", "render")
_EXPECTED = {
    "full": _BASE + ("context.decide", "address.assemble", "names.assemble", "names.propagate") + _TAIL,
}


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
                modules[name] = importlib.import_module("." + _MODULE_PATHS.get(name, name), __package__)
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
        from privacygate.model.hybrid import DEFAULT_MODEL_DIR
        model_dir = DEFAULT_MODEL_DIR
    return _cached_mbert(str(Path(model_dir).expanduser().resolve()))


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
    from privacygate.assemblers.address import scope_allowed
    return [cand for cand in added if scope_allowed(text, cand, ledger)]


def _refined(text, ledger):
    from privacygate.rules.refine import refine
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
    from privacygate.assemblers.address import contact_cues, value_boundaries

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


def _run(text, profile, model_dir, stages, modules, options=None):
    model = _get_mbert(model_dir)
    if options and (options.get("ensemble") or options.get("name_threshold") is not None):
        windows = model.raw_probabilities([text])[0]
        if options.get("ensemble"):
            other_dir = ensemble_peer(model_dir)
            peer = _get_mbert(other_dir)
            if model.id2label != peer.id2label or model.tok.get_vocab() != peer.tok.get_vocab():
                _fail("pipeline_ensemble_mismatch")
            windows = model.average_probabilities(windows, peer.raw_probabilities([text])[0])
        raw = model.decode_probabilities(windows, model.id2label, options.get("name_threshold"))
        batch = inference.mbert_candidates(text, model_dir=model_dir, _mbert=model, _raw=raw)
    else:
        batch = inference.mbert_candidates(text, model_dir=model_dir, _mbert=model)
    return _finish(text, batch, stages, modules, options) if options else _finish(text, batch, stages, modules)


def _finish(text, batch, stages, modules, options=None):
    """Replay only deterministic stages from an in-memory model candidate batch."""
    from privacygate.model.hybrid import regex
    ledger = _checked(text, batch["candidates"])
    diag = {"model_candidates": len(ledger), "regex_candidates": 0, "structured_candidates": 0,
            "validated_candidates": 0, "context_accept": 0, "context_reject": 0,
            "context_unresolved": 0, "protected_reject_prevented": 0,
            "address_candidates": 0, "name_candidates": 0, "propagated_candidates": 0,
            "refined_candidates": 0, "coverage_candidates": len(batch["coverage"]), "errors": 0}
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
        if options and options.get("name_propagation_ext"):
            propagated = modules["names"].propagate(text, [dict(c) for c in ledger],
                                                     name_propagation_ext=True)
        else:
            propagated = modules["names"].propagate(text, [dict(c) for c in ledger])
        added = _admit_additions(text, ledger, propagated, modules)
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


def normalize_options(options=None):
    """Value-free admission for three full-profile inference-only switches."""
    if options is None:
        return {}
    if not isinstance(options, dict) or set(options) - {"name_threshold", "ensemble", "name_propagation_ext"}:
        _fail("pipeline_options_invalid")
    threshold = options.get("name_threshold")
    if threshold is not None and (type(threshold) not in (int, float) or not 0 < threshold <= 1):
        _fail("pipeline_options_invalid")
    for key in ("ensemble", "name_propagation_ext"):
        if key in options and type(options[key]) is not bool:
            _fail("pipeline_options_invalid")
    return {key: value for key, value in options.items()
            if value is not None and value is not False}


def ensemble_peer(model_dir):
    """Ensemble is explicitly the sibling frozen region-v4/region-v5 pair."""
    if model_dir is None:
        _fail("pipeline_ensemble_model_invalid")
    path = Path(model_dir).expanduser().resolve()
    peers = {"region-v4-2ep": "region-v5-2ep", "region-v5-2ep": "region-v4-2ep"}
    if path.name not in peers:
        _fail("pipeline_ensemble_model_invalid")
    return path.parent / peers[path.name]


def run_pipeline(text, profile="full", model_dir=None, options=None):
    """Run a declared profile; status=blocked never includes original/partial text.

    Required-stage admission precedes model loading. Models are cached by resolved
    local path for this process, while candidates/receipts remain document-local.
    An ok receipt establishes processing only, not complete semantic PII recall.
    """
    if not isinstance(text, str):
        return _blocked("pipeline_input_invalid")
    try:
        stages = _stages(profile)
        effective = normalize_options(options)
        if effective and profile != "full":
            _fail("pipeline_options_full_only")
        modules = _modules(stages)
        with _MODEL_LOCK:
            if effective:
                return _run(text, profile, model_dir, stages, modules, effective)
            return _run(text, profile, model_dir, stages, modules)
    except PipelineError as error:
        return _blocked(str(error))
    except inference.InferenceError:
        return _blocked("pipeline_inference_failed")
    except Exception:
        return _blocked("pipeline_processing_failed")
