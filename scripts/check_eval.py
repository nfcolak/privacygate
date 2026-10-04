#!/usr/bin/env python3
"""One compact invented-contract check plus one real, non-blind v1 legacy run."""
from argparse import Namespace
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from privacygate import masking_eval as ev
import evaluate_pipeline as runner


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

    # Invented six-field dataset, runtime-only manifests and dev2 selection.
    fixture = scratch / "invented-v4.jsonl"
    fixture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    record = {"path": fixture.name, "sha256": ev.sha256(fixture), "rows": 4}
    manifest = scratch / ev.MANIFEST_PATHS["v4"]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    ev.json_write(manifest, {"dataset": record})
    loaded, binding = ev.load_dataset(fixture, "v4", root=scratch)
    _require(len(loaded) == 4 and binding["gold_spans"] == 4)
    devmanifest = scratch / ev.MANIFEST_PATHS["dev2"]
    devmanifest.parent.mkdir(parents=True, exist_ok=True)
    ev.json_write(devmanifest, {"datasets": {"train": {"path": "train-v2.jsonl", "sha256": "a" * 64}, "dev": record}})
    _require(ev.load_dataset(fixture, "dev2", root=scratch)[1]["rows"] == 4)
    dev4 = scratch / "dev-v4.jsonl"
    dev4.write_bytes(fixture.read_bytes())
    dev4manifest = scratch / ev.MANIFEST_PATHS["dev4"]
    dev4manifest.parent.mkdir(parents=True, exist_ok=True)
    ev.json_write(dev4manifest, {"manifest_version": 4, "outputs": {
        "train": {"path": "train-v4.jsonl", "sha256": "a" * 64},
        "dev": {**record, "path": dev4.name}},
        "template_catalog": {"dev": {"count": 4, "sha256": "b" * 64}}})
    _require(ev.load_dataset(dev4, "dev4", root=scratch)[1]["rows"] == 4)
    _refuses("eval_dev_dataset_required", lambda: ev.load_dataset(scratch / "train-v4.jsonl", "dev4", root=scratch))
    _require(runner.parser().parse_args(["--version", "dev4", "--dataset", str(dev4),
                                       "--model-dir", "invented-model", "--out-dir", "invented-output"]).version == "dev4")
    ev.json_write(manifest, {"dataset": {**record, "sha256": "b" * 64}})
    _refuses("eval_dataset_hash_mismatch", lambda: ev.load_dataset(fixture, "v4", root=scratch))

    # This env override is enabled only through the check-only Python parameter.
    receipts = scratch / "receipts/RECEIPTS.jsonl"
    previous = os.environ.get(ev.CHECK_RECEIPTS_ENV)
    os.environ[ev.CHECK_RECEIPTS_ENV] = str(receipts)
    try:
        key = (scratch, "full", "a" * 64, binding["sha256"])
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
        failed = (scratch, "structured", "a" * 64, binding["sha256"])
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
    _refuses("eval_arguments", lambda: runner.parser().parse_args(["--allow-repeat"]))
    print("invented_eval_checks=ok blind_repeat_refused=ok")


def invented_blind_checks(scratch, version):
    """v5/v6-shaped invented rows and temporary custody; no real blind data."""
    languages = ("EN", "DE", "FR", "IT", "ES") if version == "v5" else ("en", "de", "fr", "it", "es")
    rows = [{"case_id": f"invented-{version}-{i}", "family": "invented_clean",
             "language": language, "split": "blind", "text": "Ordinary stock.", "gold": []}
            for i, language in enumerate(languages)]
    fixture = scratch / f"invented-{version}.jsonl"
    fixture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    digest = ev.sha256(fixture)
    manifest = scratch / ev.MANIFEST_PATHS[version]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    record = {"path": fixture.name, "sha256": digest, "bytes": fixture.stat().st_size, "rows": 5}
    ev.json_write(manifest, {"dataset": record} if version == "v5" else
                  {**record, "dataset": "masking-stress-v6", "split": "blind"})
    loaded, binding = ev.load_dataset(fixture, version, root=scratch)
    _require(binding["split"] == "blind" and ev.sha256(fixture) == digest)
    _require(loaded == [{**row, "language": row["language"].lower()} for row in rows])
    aggregate = ev.EvaluationAggregate()
    for row in loaded:
        aggregate.add(row, {"status": "ok", "masked_text": row["text"], "entities": [],
                            "completion": {"uncovered_chars": 0}})
    _require(set(aggregate.report()["per_language"]) == ev.LANGUAGES)
    args = runner.parser().parse_args(["--version", version, "--dataset", str(fixture),
                                      "--model-dir", "invented-model", "--out-dir", "invented-output"])
    _require(args.version == version)
    key = (scratch, "full", "a" * 64, digest)
    expected = scratch / f"artifacts/runs/blind-{version}/RECEIPTS.jsonl"
    _require(ev.BlindCustody(*key, version=version).path == expected and not expected.parent.exists())
    receipts = scratch / f"receipts-{version}/RECEIPTS.jsonl"
    previous = os.environ.get(ev.CHECK_RECEIPTS_ENV)
    os.environ[ev.CHECK_RECEIPTS_ENV] = str(receipts)
    try:
        with ev.BlindCustody(*key, version=version, check=True) as custody:
            custody.reserve()
            custody.finish("c" * 64)
        entries = [json.loads(line) for line in receipts.read_text(encoding="utf-8").splitlines()]
        _require(len(entries) == 1 and entries[0]["dataset_sha256"] == digest)
        def repeat():
            with ev.BlindCustody(*key, version=version, check=True):
                raise ev.EvaluationError("eval_check_repeat_entered")
        _refuses("eval_blind_repeat_forbidden", repeat)
        _refuses("eval_check_override_forbidden", lambda: ev.BlindCustody(*key, version=version))
    finally:
        if previous is None:
            del os.environ[ev.CHECK_RECEIPTS_ENV]
        else:
            os.environ[ev.CHECK_RECEIPTS_ENV] = previous
    _require(ev.sha256(fixture) == digest and not expected.parent.exists())
    print(f"{version}_check=ok blind_repeat_refused=ok source_bytes_unchanged=ok")


def existing_receipt_checks(scratch):
    """Replay custody refusals using unchanged real receipts, never blind data."""
    relative = Path("artifacts/runs/blind-v4/RECEIPTS.jsonl")
    original = ROOT / relative
    entries = [json.loads(line) for line in original.read_text(encoding="utf-8").splitlines() if line.strip()]
    _require(bool(entries))
    before = {}
    for name in ("RECEIPTS.jsonl", "RECEIPTS.jsonl.STARTED", "freeze.json"):
        source = original.with_name(name)
        before[name] = ev.sha256(source)
        target = scratch / relative.parent / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    refused = 0
    for entry in entries:
        key = (entry["profile"], entry["model_sha256"], entry["dataset_sha256"])
        _require(ev.BlindCustody(ROOT, *key).path == original)
        def repeat():
            with ev.BlindCustody(scratch, *key):
                raise ev.EvaluationError("eval_check_repeat_entered")
        _refuses("eval_blind_repeat_forbidden", repeat)
        refused += 1
    _require(refused == len(entries))
    _require(all(ev.sha256(original.with_name(name)) == digest for name, digest in before.items()))
    _require(all(ev.sha256(scratch / relative.parent / name) == digest for name, digest in before.items()))
    print(f"existing_receipt_repeats_refused={refused}/{len(entries)} custody_unchanged=ok")


def legacy_check():
    prep = ROOT.parent / "privacygate-prep-1002"
    dataset = Path(os.environ.get("PRIVACYGATE_EVAL_V1_DATASET", str(prep / "data/augmentation/masking-stress-dev.jsonl")))
    model = Path(os.environ.get("PRIVACYGATE_EVAL_MODEL_DIR", str(prep / "models/pos-neg-alignment-pilot-1002")))
    out_parent = Path(os.environ.get("TMPDIR", str(ROOT.parent / "_runs/pg-notes-out")))
    out_parent.mkdir(parents=True, exist_ok=True)
    # Fresh output directory; never overwrite a historical receipt/artifact.
    unique = Path(tempfile.mkdtemp(prefix="v1-legacy-", dir=out_parent))
    args = Namespace(dataset=str(dataset), version="v1", profile="legacy_union_refined",
                     model_dir=str(model), out_dir=str(unique / "evaluation"), predictions_from="inference")
    report = runner.execute(args)
    historical = json.loads((ROOT / "artifacts/runs/masking-coverage/refine-v1-1003/metrics.json").read_text(encoding="utf-8"))
    parent = historical["engines"]["hybrid_union_refined"]["overall"]
    actual = report["overall"]
    _require((actual["complete_gold_spans"], actual["gold_spans"]) == (parent["complete_gold_spans"], parent["gold_spans"]) == (369, 370))
    # Read exact written targets back and check that all required receipts exist.
    written = json.loads((unique / "evaluation/metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((unique / "evaluation/manifest.json").read_text(encoding="utf-8"))
    _require(written == report and manifest["training"] is False and manifest["test_evaluated"] is False)
    _require(not list((unique / "evaluation").glob("*.md")) and ev._digest(manifest["config_sha256"]))
    _require(manifest["policy_sha256"] == ev.sha256(ROOT / "configs/privacy-policy-v1.json"))
    print("v1_legacy_complete=369/370")


def main():
    try:
        scratch_parent = Path(os.environ.get("TMPDIR", str(Path.home() / ".hermes/cache/scratch")))
        scratch_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="privacygate-eval-check-", dir=scratch_parent) as directory:
            invented_checks(Path(directory))
            invented_blind_checks(Path(directory), "v5")
            invented_blind_checks(Path(directory), "v6")
            existing_receipt_checks(Path(directory))
        legacy_check()
        print("EVAL CHECK OK")
        return 0
    except (Exception, KeyboardInterrupt):
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, ev.EvaluationError) else "eval_check_failed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
