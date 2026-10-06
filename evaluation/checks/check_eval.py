#!/usr/bin/env python3
"""Invented scorer contracts, blind custody refusals and the frozen v7 loader; no model."""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation import masking_eval as ev
from evaluation import evaluate_pipeline as runner
from evaluation.checks import verify_frozen


def _require(condition):
    if not condition:
        raise ev.EvaluationError("eval_check_assertion")


def _refuses(code, call):
    try:
        call()
    except ev.EvaluationError as error:
        _require(str(error) == code)
    else:
        raise ev.EvaluationError("eval_check_expected_refusal")


def invented_checks(scratch):
    text = "Ava 12-34 rest."
    rows = [
        {"case_id": "invented-a", "family": "invented_positive", "language": "en", "split": "dev", "text": text,
         "gold": [{"start": 0, "end": 3, "label": "PERSONNAME"},
                  {"start": 4, "end": 9, "label": "PERSONALREF"},
                  {"start": 10, "end": 14, "label": "NEW_LABEL"}]},
        {"case_id": "invented-b", "family": "invented_positive", "language": "en", "split": "dev", "text": "Mira",
         "gold": [{"start": 0, "end": 4, "label": "DATEOFBIRTH"}]},
        {"case_id": "invented-c", "family": "invented_clean", "language": "en", "split": "dev", "text": "Ordinary stock.", "gold": []},
        {"case_id": "invented-d", "family": "invented_clean", "language": "en", "split": "dev", "text": "No mask.", "gold": []},
    ]
    predictions = [
        [{"start": 0, "end": 3, "label": "ADDRESS"},
         {"start": 4, "end": 6, "label": "UNCOVERED"},
         {"start": 4, "end": 6, "label": "ANY_PRED_LABEL"},
         {"start": 14, "end": 15, "label": "PII"}],
        [{"start": 0, "end": 4, "label": "PERSONNAME"}],
        [{"start": 0, "end": 2, "label": "PII"}], [],
    ]
    aggregate = ev.EvaluationAggregate()
    for row, entities in zip(rows, predictions):
        aggregate.add(row, {"status": "ok", "masked_text": "invented contract output",
                            "entities": entities, "completion": {"uncovered_chars": 0}, "diagnostics": {}})
    report = aggregate.report()
    overall = report["overall"]
    _require(tuple(overall[k] for k in ("complete_gold_spans", "partial_gold_spans", "untouched_gold_spans", "leaked_gold_alnum_chars")) == (2, 1, 1, 6))
    _require(overall["fully_masked_positive_rows"] == 1 and overall["positive_rows"] == 2)
    _require(overall["excess_masked_chars"] == 3)
    clean = overall["clean_controls"]
    _require((clean["rows"], clean["masked_rows"], clean["masked_chars"]) == (2, 1, 2))
    _require(report["per_gold_label"]["PERSONNAME"]["complete_gold_spans"] == 1)
    _require(report["per_gold_label"]["NEW_LABEL"]["untouched_gold_spans"] == 1)
    _require(report["per_family"]["invented_positive"]["gold_spans"] == 4)
    _require(ev.wilson(0, 0)["low"] is None)
    _require(0 < ev.wilson(0, 40)["high"] < 0.1)
    blocked = ev.EvaluationAggregate()
    blocked.add(rows[1], {"status": "blocked", "masked_text": "", "entities": [],
                          "completion": {"uncovered_chars": 4}, "diagnostics": {}})
    _require(blocked.report()["overall"]["fully_masked_positive_rows"] == 0)
    _refuses("eval_span_offsets", lambda: ev.validate_spans([{"start": True, "end": 2, "label": "PII"}], 4))
    _refuses("eval_gold_order_overlap", lambda: ev.validate_spans(
        [{"start": 2, "end": 3, "label": "PII"}, {"start": 0, "end": 1, "label": "PII"}], 4, gold=True))

    digest = "d" * 64
    # This env override is enabled only through the check-only Python parameter.
    receipts = scratch / "receipts/RECEIPTS.jsonl"
    previous = os.environ.get(ev.CHECK_RECEIPTS_ENV)
    os.environ[ev.CHECK_RECEIPTS_ENV] = str(receipts)
    try:
        key = (scratch, "full", "a" * 64, digest)
        with ev.BlindCustody(*key, check=True) as custody:
            custody.reserve()
            custody.finish("c" * 64)
        entries = [json.loads(line) for line in receipts.read_text(encoding="utf-8").splitlines()]
        _require(len(entries) == 1 and entries[0]["metrics_sha256"] == "c" * 64)
        def repeat():
            with ev.BlindCustody(*key, check=True):
                raise ev.EvaluationError("eval_check_repeat_entered")
        _refuses("eval_blind_repeat_forbidden", repeat)
        # Interrupted inference also consumes its separate arm.
        failed = (scratch, "full", "b" * 64, digest)
        with ev.BlindCustody(*failed, check=True) as custody:
            custody.reserve()
        def failed_repeat():
            with ev.BlindCustody(*failed, check=True):
                raise ev.EvaluationError("eval_check_repeat_entered")
        _refuses("eval_blind_repeat_forbidden", failed_repeat)
        _refuses("eval_check_override_forbidden", lambda: ev.BlindCustody(*key))
    finally:
        if previous is None:
            del os.environ[ev.CHECK_RECEIPTS_ENV]
        else:
            os.environ[ev.CHECK_RECEIPTS_ENV] = previous
    _refuses("eval_blind_custody_binding", lambda: ev.BlindCustody(scratch, "full", "invented", digest))
    _refuses("eval_dataset_version", lambda: ev.BlindCustody(scratch, "full", "a" * 64, digest, version="v3"))
    _refuses("eval_arguments", lambda: runner.parser().parse_args(["--allow-repeat"]))
    for retired in (["--profile", "legacy_union_refined"], ["--version", "v4"]):
        _refuses("eval_arguments", lambda: runner.parser().parse_args(
            ["--version", "v7", "--dataset", "x", "--model-dir", "m", "--out-dir", "o", *retired]))
    args = runner.parser().parse_args(["--version", "v7", "--dataset", "x", "--model-dir", "m", "--out-dir", "o"])
    _require(args.profile == "full" and args.version == "v7")
    expected = scratch / "artifacts/runs/blind-v7/RECEIPTS.jsonl"
    _require(ev.BlindCustody(*key).path == expected and not expected.parent.exists())
    print("invented_eval_checks=ok blind_repeat_refused=ok")


def existing_receipt_checks(scratch):
    """Replay custody refusals using unchanged real receipts, never blind data."""
    total = 0
    for version in ev.BLIND_VERSIONS:
        relative = Path(f"artifacts/runs/blind-{version}/RECEIPTS.jsonl")
        original = ROOT / relative
        entries = [json.loads(line) for line in original.read_text(encoding="utf-8").splitlines() if line.strip()]
        _require(bool(entries))
        before = {}
        for name in ("RECEIPTS.jsonl", "RECEIPTS.jsonl.STARTED"):
            source = original.with_name(name)
            before[name] = ev.sha256(source)
            target = scratch / relative.parent / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        for entry in entries:
            key = (entry["profile"], entry["model_sha256"], entry["dataset_sha256"])
            _require(ev.BlindCustody(ROOT, *key, version=version).path == original)
            def repeat():
                with ev.BlindCustody(scratch, *key, version=version):
                    raise ev.EvaluationError("eval_check_repeat_entered")
            _refuses("eval_blind_repeat_forbidden", repeat)
            total += 1
        _require(all(ev.sha256(original.with_name(name)) == digest for name, digest in before.items()))
    print(f"existing_receipt_repeats_refused={total}/{total} custody_unchanged=ok")


def v7_loader_check():
    """Frozen v7 replay through the runner when the ignored dev file is present."""
    if not verify_frozen.V7_DATA.is_file():
        print("v7_loader=SKIPPED_NO_DATA")
        return
    rows, binding = runner.load_v7_dataset(verify_frozen.V7_DATA)
    manifest = json.loads(verify_frozen.V7_MANIFEST.read_text(encoding="utf-8"))
    _require(len(rows) == binding["rows"] == 600 and binding["sha256"] == manifest["dataset_sha256"])
    _require(binding["manifest_sha256"] == ev.sha256(ROOT / ev.MANIFEST_PATHS["v7"]))
    print("v7_loader=ok")


def main():
    try:
        with tempfile.TemporaryDirectory(prefix="privacygate-eval-check-") as directory:
            invented_checks(Path(directory))
            existing_receipt_checks(Path(directory))
        v7_loader_check()
        print("EVAL CHECK OK")
        return 0
    except (Exception, KeyboardInterrupt):
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, ev.EvaluationError) else "eval_check_failed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
