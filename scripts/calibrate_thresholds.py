#!/usr/bin/env python3
"""DEV-only, offline, whole-candidate calibration; aggregate output only."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacygate import masking_eval as ev, pipeline

GRID = (0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ev.EvaluationError("calibration_arguments")


def load_dev(path, version):
    # Exact DEV names and a manifest hash are required BEFORE reading any rows.
    number = {"dev2": 2, "dev3": 3}[version]
    path = Path(path)
    if path.name != f"dev-v{number}.jsonl" or path.resolve().name != path.name:
        raise ev.EvaluationError("calibration_dev_dataset_required")
    manifest = ev._json(ev.read_bounded(ROOT / f"artifacts/train-v{number}/manifest.json"))
    record = ev.manifest_dataset(manifest, "dev2", path.name)
    raw = ev.read_bounded(path)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != record["sha256"]:
        raise ev.EvaluationError("calibration_dataset_hash_mismatch")
    lines = [line for line in raw.split(b"\n") if line.strip()]
    if not 0 < len(lines) <= ev.MAX_ROWS or any(len(line) > ev.MAX_LINE_BYTES for line in lines):
        raise ev.EvaluationError("calibration_dataset_bounds")
    rows, ids = [ev._json(line) for line in lines], set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() != ev.ROW_KEYS:
            raise ev.EvaluationError("calibration_row_schema")
        if any(not isinstance(row[k], str) for k in ev.ROW_KEYS - {"gold"}):
            raise ev.EvaluationError("calibration_row_schema")
        if row["split"] != "dev" or row["language"] not in ev.LANGUAGES:
            raise ev.EvaluationError("calibration_dev_split_required")
        if (not row["text"].strip() or len(row["text"]) > ev.MAX_CHARS
                or not row["case_id"] or len(row["case_id"]) > 200
                or row["case_id"] in ids or not row["family"] or len(row["family"]) > 200):
            raise ev.EvaluationError("calibration_row_bounds")
        ev.validate_spans(row["gold"], len(row["text"]), gold=True)
        ids.add(row["case_id"])
    if record.get("rows", len(rows)) != len(rows):
        raise ev.EvaluationError("calibration_dataset_count_mismatch")
    return rows, digest


def footprint(row, result):
    # In-memory sets enforce no NEW exposed character or incomplete span, even
    # when an aggregate gain could otherwise hide a regression on another row.
    if result["status"] != "ok":
        raise ev.EvaluationError("calibration_pipeline_blocked")
    masked = {i for c in result["entities"] for i in range(c["start"], c["end"])}
    exposed, incomplete = set(), set()
    for index, gold in enumerate(row["gold"]):
        positions = range(gold["start"], gold["end"])
        missing = [i for i in positions if i not in masked]
        exposed.update(i for i in missing if row["text"][i].isalnum())
        if missing:
            incomplete.add(index)
    return exposed, incomplete


def compact(metric):
    return {"exposed_alnum": metric["leaked_gold_alnum_chars"],
            "complete_spans": metric["complete_gold_spans"], "gold_spans": metric["gold_spans"],
            "incomplete_spans": metric["partial_gold_spans"] + metric["untouched_gold_spans"],
            "clean_rows_masked": metric["clean_controls"]["masked_rows"],
            "clean_rows": metric["clean_controls"]["rows"], "blocked_rows": metric["blocked_rows"]}


def aggregates(rows, results):
    aggregate = ev.EvaluationAggregate()
    for row, result in zip(rows, results):
        aggregate.add(row, result)
    report = aggregate.report()
    return {"overall": compact(report["overall"]),
            "per_gold_label": {k: compact(v) for k, v in report["per_gold_label"].items()}}


def calibrate(rows, model_dir):
    batches, baseline = [], []
    finish = pipeline._finish

    def collect(text, batch, stages, modules, calibration=None):
        batches.append(batch)
        return finish(text, batch, stages, modules, calibration)

    # Exactly one real full-pipeline pass; no prediction caches on disk.
    with patch.object(pipeline, "_finish", collect):
        for row in rows:
            result = pipeline.run_pipeline(row["text"], profile="full", model_dir=model_dir)
            footprint(row, result)
            baseline.append(result)
    if len(batches) != len(rows):
        raise ev.EvaluationError("calibration_batch_count_mismatch")
    reference = [footprint(r, p) for r, p in zip(rows, baseline)]
    before = aggregates(rows, baseline)
    stages = pipeline._stages("full_calibrated")
    modules = pipeline._modules(stages)
    labels = sorted({c["label"] for b in batches for c in b["candidates"]})
    thresholds = {label: 0.0 for label in labels}
    current, kept = list(baseline), [b["candidates"] for b in batches]
    per_label = {}
    # Deterministic, cumulative coordinate search checks interactions against
    # the original zero-threshold parent, not isolated per-label approximations.
    for label in labels:
        label_before = aggregates(rows, current)["overall"]
        for threshold in reversed(GRID):
            trial = {"thresholds": dict(thresholds, **{label: threshold}), "default": 0.0}
            proposed, proposed_kept, safe = list(current), list(kept), True
            for index, (row, batch) in enumerate(zip(rows, batches)):
                candidates = pipeline._calibrate(row["text"], batch["candidates"], trial, modules["structured"])
                if candidates == kept[index]:
                    continue
                result = finish(row["text"], batch, stages, modules, trial)
                exposed, incomplete = footprint(row, result)
                if not exposed <= reference[index][0] or not incomplete <= reference[index][1]:
                    safe = False
                    break
                proposed[index], proposed_kept[index] = result, candidates
            if safe:
                thresholds[label], current, kept = threshold, proposed, proposed_kept
                break
        scores = [c["score"] for b in batches for c in b["candidates"]
                  if c["label"] == label and c["score"] is not None]
        bins = Counter(str(max(t for t in GRID if t <= score)) for score in scores)
        per_label[label] = {"threshold": thresholds[label], "scored_candidates": len(scores),
                            "score_histogram": dict(sorted(bins.items())), "selection_before": label_before,
                            "selection_after": aggregates(rows, current)["overall"]}
    after = aggregates(rows, current)
    empty = compact(ev.Aggregate().report())
    for label, statistics in per_label.items():
        statistics["before"] = before["per_gold_label"].get(label, empty)
        statistics["after"] = after["per_gold_label"].get(label, empty)
    for row, result, ref in zip(rows, current, reference):
        exposed, incomplete = footprint(row, result)
        if not exposed <= ref[0] or not incomplete <= ref[1]:
            raise ev.EvaluationError("calibration_safety_regression")
    return {"thresholds": thresholds, "default": 0.0, "grid": GRID,
            "selection": "sorted-label cumulative highest-safe grid; no new gold alnum or incomplete spans",
            "full_pipeline_passes": 1, "before": before, "after": after, "per_label": per_label}


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--version", choices=("dev2", "dev3"), required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if (os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1"
            or not os.environ.get("HF_HOME")):
        raise ev.EvaluationError("calibration_offline_required")
    out = Path(args.out).resolve()
    if out.parent != ROOT / "configs" or out.suffix != ".json":
        raise ev.EvaluationError("calibration_config_output_required")
    rows, digest = load_dev(args.dataset, args.version)
    with ev.quiet_libraries():
        model_digest = pipeline._model_sha256(args.model_dir)
        result = calibrate(rows, args.model_dir)
    result.update(model_sha256=model_digest, dataset_sha256=digest, dataset_version=args.version)
    # Compact per-key lines keep the generated configuration under 200 lines.
    out.write_text("{\n" + ",\n".join("  " + json.dumps(k) + ": " + json.dumps(v, sort_keys=True,
                   allow_nan=False) for k, v in sorted(result.items())) + "\n}\n", encoding="utf-8")
    print(json.dumps({"version": args.version, "before": result["before"]["overall"],
                      "after": result["after"]["overall"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.stderr.write("calibration_failed (input not shown)\n")
        sys.exit(1)
