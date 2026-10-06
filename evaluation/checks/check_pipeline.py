#!/usr/bin/env python3
"""Invented pipeline contract probes plus one region-model CLI/API parity check.

Never emits dataset text/values/row identifiers/offsets, or downloads assets.
The model part needs a local region checkpoint (default models/region-v4-2ep).
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "models/region-v4-2ep"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ.setdefault("HF_HOME", str(ROOT / ".cache/hf"))
sys.path.insert(0, str(ROOT))

from privacygate.model import inference
from privacygate import pipeline
from privacygate.data.spans import make_candidate, validate, union


def _require(condition):
    if not condition:
        raise ValueError("pipeline_check_failed") from None


def invented_contracts():
    text = "A😀 BC-DE F"
    a = make_candidate(1, 2, "CUSTOM", "contract")
    b = make_candidate(1, 5, "PERSONNAME", "names", stage="assembled")
    c = make_candidate(4, 7, "SURNAME", "mbert", score=0.75)
    _require(validate(text, [a])[0] == a)
    merged = union(validate(text, [a, b, c]))
    _require(merged == [{"start": 1, "end": 7, "label": "PERSONNAME"}])
    part = make_candidate(3, 6, "GIVENNAME", "mbert")
    region = make_candidate(3, 6, "PERSONNAME", "names", stage="assembled")
    _require(union([part, region])[0]["label"] == "PERSONNAME")
    for bad in (dict(a, start=True), dict(a, end=len(text) + 1), dict(a, stage="invalid"),
                dict(a, validation="invalid_enum"), dict(a, context="invalid_enum"),
                dict(a, protected=1), dict(a, score=float("nan")), dict(a, text="not_allowed")):
        try:
            validate(text, [bad])
        except ValueError as error:
            _require(str(error) == "invalid_candidate_contract")
        else:
            _require(False)
    _require(inference.uncovered_regions(text, [(0, 1), (3, len(text))]) == [(1, 2)])
    # The old refiner drops isolated AGE fragments. New-profile unresolved
    # candidates remain masked; only the preceding context stage can reject.
    age_text = "The invented panel is 23 cm."
    start = age_text.index("23")
    age = make_candidate(start, start + len("23"), "AGE", "mbert", score=0.75)
    _require(union(pipeline._refined(age_text, [age])) == [
        {"start": age["start"], "end": age["end"], "label": "AGE"}])
    print("candidate_contract=PASS")


def profile_contracts():
    _require(pipeline.PROFILES == ("full",))
    _require(pipeline._stages("full") == ("mbert", "regex", "structured.detect", "structured.check",
                                         "context.decide", "address.assemble", "names.assemble",
                                         "names.propagate", "refine", "coverage", "union", "render"))
    for retired in ("legacy_union_refined", "structured", "structured_address_names", "full_calibrated"):
        result = pipeline.run_pipeline("The invented panel is 3x5 cm.", profile=retired)
        _require(result["status"] == "blocked" and result["error"] == "pipeline_profile_invalid")
    for options in ({"name_threshold": 0}, {"ensemble": 1}, {"unknown": True}):
        result = pipeline.run_pipeline("The invented panel is 3x5 cm.", options=options)
        _require(result["status"] == "blocked" and result["error"] == "pipeline_options_invalid")
    print("profile_contract=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    invented_contracts()
    profile_contracts()
    # Specialist modules exist after integration; probe a genuinely missing module.
    with patch.dict(pipeline._REQUIRED, {"structured.detect": ("missing_pipeline_stage", "detect")}):
        missing = pipeline.run_pipeline("The invented panel is 3x5 cm.", profile="full", model_dir=args.model_dir)
    _require(missing["status"] == "blocked" and missing.get("error") == "pipeline_stage_unavailable:missing_pipeline_stage")
    _require(missing["masked_text"] == "" and missing["entities"] == [])
    print("stage_unavailable=PASS")

    with pipeline._MODEL_LOCK:
        model = pipeline._get_mbert(args.model_dir)
    invented = "Dear Dr. Elara Voss, contact elara.voss@example.org."
    raw = model.raw([invented])[0]
    scored = model.spans_with_scores(raw)
    _require(len(scored) > 0)
    _require([{k: c[k] for k in ("start", "end", "label", "source")} for c in scored] == model.spans(raw))
    _require(all(type(c["score"]) is float and 0.0 <= c["score"] <= 1.0 for c in scored))
    batch = inference.mbert_candidates(invented, _mbert=model)
    _require(batch["completion"]["uncovered_chars"] == sum(
        b - a for a, b in inference.uncovered_regions(invented, (o for offsets, _, _ in raw for o in offsets))))
    print("scored_adapter=PASS")

    proc = subprocess.run([sys.executable, "-m", "privacygate", "--pipeline-profile", "full",
                           "--model-dir", str(args.model_dir)], input=invented, text=True,
                          capture_output=True, cwd=ROOT, env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"})
    _require(proc.returncode == 0)
    cli = json.loads(proc.stdout)
    api = pipeline.run_pipeline(invented, profile="full", model_dir=args.model_dir)
    _require(cli == api)
    _require(cli["status"] == "ok" and isinstance(cli["completion"]["uncovered_chars"], int))
    _require(all(type(v) is int for v in api["diagnostics"].values()))
    print("pipeline_cli=PASS")
    print("PIPELINE OK")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        # A traceback could print dataset data or malformed input. Fail value-free.
        sys.stderr.write("pipeline_check_failed (input not shown)\n")
        code = 1
    sys.exit(code)
