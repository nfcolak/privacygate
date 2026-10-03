#!/usr/bin/env python3
"""One aggregate-only legacy equivalence check on exposed v1, plus invented probes.

Never reads v3, emits dataset text/values/row identifiers/offsets, or downloads assets.
Missing specialist modules are expected in the pipeline writer's unmerged branch.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
SOURCE_V1 = REPO / ".worktrees/privacygate-prep-1002/data/augmentation/masking-stress-dev.jsonl"
DEFAULT_MODEL = REPO / ".worktrees/privacygate-prep-1002/models/pos-neg-alignment-pilot-1002"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ.setdefault("HF_HOME", str(REPO / ".cache/hf"))
sys.path.insert(0, str(ROOT))

from privacygate import inference, pipeline
from privacygate.spans import make_candidate, validate, union


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    invented_contracts()
    missing = pipeline.run_pipeline("The invented panel is 3x5 cm.", profile="structured", model_dir=args.model_dir)
    _require(missing["status"] == "blocked" and missing.get("error") == "pipeline_stage_unavailable:structured")
    _require(missing["masked_text"] == "" and missing["entities"] == [])
    print("stage_unavailable=PASS")

    dataset = ROOT / "data/augmentation/masking-stress-dev.jsonl"
    if not dataset.exists():
        dataset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_V1, dataset)
    # Only exposed synthetic development rows are read, never case IDs or gold in logs.
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    _require(len(rows) == 110)
    with pipeline._MODEL_LOCK:
        model = pipeline._get_mbert(args.model_dir)
    identical = 0
    # Reuse the real loaded checkpoint for both paths, not synthesized predictions.
    with patch.object(inference, "_load_mbert", return_value=model):
        for row in rows:
            legacy = inference.run(row["text"], engine="hybrid", policy="union_refined", model_dir=args.model_dir)
            result = pipeline.run_pipeline(row["text"], profile="legacy_union_refined", model_dir=args.model_dir)
            _require(result["status"] == "ok")
            if (result["entities"] == legacy["entities"] and result["masked_text"] == legacy["masked_text"]):
                identical += 1
            _require(all(type(v) is int for v in result["diagnostics"].values()))
    print("legacy_identical={}/{}".format(identical, len(rows)))
    _require(identical == len(rows))

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

    proc = subprocess.run([sys.executable, "-m", "privacygate", "--pipeline-profile", "legacy_union_refined",
                           "--model-dir", str(args.model_dir)], input=invented, text=True,
                          capture_output=True, cwd=ROOT, env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"})
    _require(proc.returncode == 0)
    cli = json.loads(proc.stdout)
    api = pipeline.run_pipeline(invented, profile="legacy_union_refined", model_dir=args.model_dir)
    _require(cli == api)
    _require(cli["status"] == "ok" and isinstance(cli["completion"]["uncovered_chars"], int))
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
