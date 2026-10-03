#!/usr/bin/env python3
"""One offline synthetic-dev masking diagnostic; aggregate-only output, no tuning.

Positive format explicitly admits dev through the existing six-key loader.
Stress format has EXACT case_id/language/family/text/gold/split keys and split=dev.
No input text, row IDs, predicted fragments or per-example offsets are emitted.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacygate import hybrid, inference, mbert_data, positive_data
from privacygate.masking_metrics import (
    Aggregate, CLASSES, DEFINITIONS, EngineAggregate, GOLD_DIAGNOSTIC_LABELS,
    LABELS, MaskingError, STRESS_FAMILIES,
    SCORER_VERSION, count_chars, intersection, interval_union, validate_spans,
)

EXPECTED_MODEL = "0058a5c93c2ef14c5f65daf8ae8afc061851acf8d5cf5d52ba0342f578d9cac9"
EXPECTED_POSITIVE = "7cc5c56f555021d135118e9e6b772e5fe8271cf887ddba3aa38530f3ac777a42"
ENGINES = ("regex", "mbert", "hybrid_union")
STRESS_KEYS = frozenset({"case_id", "language", "family", "text", "gold", "split"})
STRESS_MAX_CHARS = 12000  # Frozen stress generator cap; positive_data limits unchanged.
EXPECTED_STRESS = "b901873cbdd3715aaae2c78477193fecb3fd47410344fdb240ce75abdbfb6cbf"
SOURCES = (
    "privacygate/masking_metrics.py", "scripts/measure_masking.py",
    "privacygate/hybrid.py", "privacygate/inference.py", "privacygate/detect.py",
    "privacygate/mbert_data.py", "privacygate/positive_data.py",
    "scripts/make_masking_stress.py", "artifacts/masking-stress/manifest.json",
)
TOKENIZER_FILES = ("config.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt")
SCOPE = {"test_evaluated": False, "training": False, "scoring_scope": "development_diagnostic"}


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise MaskingError("mask_arguments")


def sha256(path):
    result = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def source_path(name):
    """Resolve frozen logical artifact paths without changing bound bytes or keys."""
    path = Path(name)
    if path.parts and path.parts[0] == "docs":
        path = Path("artifacts", *path.parts[1:])
    return ROOT / path


def json_write(path, value):
    # Outputs contain only fixed codes, aggregate numbers, approved labels and hashes.
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def check_stress_rows(rows):
    if not isinstance(rows, list) or not 0 < len(rows) <= positive_data.MAX_ROWS:
        raise MaskingError("stress_row_count")
    ids = set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() != STRESS_KEYS:
            raise MaskingError("stress_schema")
        if any(not isinstance(row[key], str) for key in ("case_id", "language", "family", "text", "split")):
            raise MaskingError("stress_field_type")
        if row["split"] != "dev":
            raise MaskingError("stress_split")
        if row["language"] not in positive_data.LANGS:
            raise MaskingError("stress_language")
        if not row["case_id"] or len(row["case_id"]) > positive_data.MAX_ID_CHARS or row["case_id"] in ids:
            raise MaskingError("stress_case_id")
        if row["family"] not in STRESS_FAMILIES:
            raise MaskingError("stress_family")
        if not row["text"].strip() or len(row["text"]) > STRESS_MAX_CHARS:
            raise MaskingError("stress_text_bounds")
        gold = row["gold"]
        if not isinstance(gold, list) or len(gold) > positive_data.MAX_ANNOTATIONS:
            raise MaskingError("stress_gold_count")
        if any(not isinstance(span, dict) or span.keys() != positive_data.MASK_KEYS for span in gold):
            raise MaskingError("stress_gold_schema")
        validate_spans(gold, len(row["text"]), gold=True)
        if (row["family"] == "clean") != (not gold):
            raise MaskingError("stress_clean_family")
        ids.add(row["case_id"])


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MaskingError("mask_duplicate_json_key")
        result[key] = value
    return result


def load_dataset(path, format_name):
    if format_name == "positive":
        rows, binding = positive_data.load_positive_file(path, allowed_split="dev")
        if binding["sha256"] != EXPECTED_POSITIVE or len(rows) != 280:
            raise MaskingError("mask_positive_binding")
        return [(row["source_text"], row["privacy_mask"], row["language"], None) for row in rows], binding
    raw = positive_data._read_bounded(path)
    lines = [line for line in raw.split(b"\n") if line.strip()]
    if not lines or len(lines) > positive_data.MAX_ROWS:
        raise MaskingError("stress_row_count")
    if any(len(line) > positive_data.MAX_LINE_BYTES for line in lines):
        raise MaskingError("stress_line_bounds")
    try:
        rows = [json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object) for line in lines]
    except MaskingError:
        raise
    except (ValueError, RecursionError):
        raise MaskingError("stress_unparseable") from None
    check_stress_rows(rows)
    binding = {
        "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "split": "dev",
        "per_language": {lang: sum(row["language"] == lang for row in rows) for lang in positive_data.LANGS},
        "per_label": {label: sum(g["label"] == label for row in rows for g in row["gold"]) for label in sorted({g["label"] for row in rows for g in row["gold"]})},
        "clean_rows": sum(not row["gold"] for row in rows),
        "positive_rows": sum(bool(row["gold"]) for row in rows),
        "gold_spans": sum(len(row["gold"]) for row in rows), "bytes": len(raw),
        "per_family": {family: sum(row["family"] == family for row in rows) for family in sorted(STRESS_FAMILIES)},
    }
    if (binding["sha256"], binding["rows"], binding["positive_rows"], binding["clean_rows"], binding["gold_spans"], binding["bytes"]) != (EXPECTED_STRESS, 110, 100, 10, 370, 137089):
        raise MaskingError("mask_stress_binding")
    return [(row["text"], row["gold"], row["language"], row["family"]) for row in rows], binding


@contextmanager
def quiet_libraries():
    # Suppress Python/native library diagnostics: unexpected exceptions cannot echo inputs.
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(fd) for fd in (1, 2)]
    try:
        with open(os.devnull, "w") as sink:
            for fd in (1, 2):
                os.dup2(sink.fileno(), fd)
            yield
            sys.stdout.flush()
            sys.stderr.flush()
    finally:
        for fd, original in zip((1, 2), saved):
            os.dup2(original, fd)
            os.close(original)


def sanity_checks():
    """One compact numeric/loader/actual-mask proof; no raw values printed."""
    from unittest.mock import patch
    checks = 0

    def ok(condition):
        nonlocal checks
        if not condition:
            raise MaskingError("mask_sanity_failed")
        checks += 1

    def rejects(call, code):
        nonlocal checks
        try:
            call()
        except ValueError as error:
            if str(error) != code:
                raise MaskingError("mask_sanity_failed") from None
            checks += 1
            return
        raise MaskingError("mask_sanity_failed")

    ok(interval_union([], 8) == [])
    ok(interval_union([(1, 3), (3, 5), (2, 4), (1, 3)], 8) == [(1, 5)])
    ok(intersection([(0, 4), (3, 7)], [(2, 5), (4, 6)], 8) == [(2, 6)])
    ok(count_chars([(1, 3), (1, 3), (2, 4)], 8) == 3)
    for intervals, code in (([(False, 2)], "mask_offset_type"), ([(1, True)], "mask_offset_type"), ([(-1, 2)], "mask_offset_bounds"), ([(1, 9)], "mask_offset_bounds"), ([(3, 3)], "mask_offset_bounds")):
        rejects(lambda: interval_union(intervals, 8), code)
    text = "".join(chr(value) for value in range(97, 105))
    gold = [{"start": 1, "end": 5, "label": "GIVENNAME"}]
    pred = [{"start": 1, "end": 3, "label": "SURNAME"}, {"start": 3, "end": 5, "label": "SURNAME"}]
    aggregate = Aggregate()
    aggregate.add(text, gold, pred + pred, inference.merge_spans(pred, len(text)))
    result = aggregate.report()
    ok(result["complete_gold_spans"] == 1 and result["masked_chars"] == 4)
    ok(result["raw_detection_classification"]["fully_covered_nonexact"] == 1)
    wrong = [{"start": 1, "end": 5, "label": "SURNAME"}]
    aggregate = Aggregate()
    aggregate.add(text, gold, wrong, inference.merge_spans(wrong, len(text)))
    ok(aggregate.report()["raw_detection_classification"]["exact_different_label"] == 1)
    aggregate = Aggregate()
    aggregate.add(text, gold, pred[:1], inference.merge_spans(pred[:1], len(text)))
    ok(aggregate.report()["partial_gold_spans"] == 1 and aggregate.report()["leaked_gold_alnum_chars"] == 2)
    aggregate = Aggregate()
    aggregate.add(text, gold, [], [])
    ok(aggregate.report()["untouched_gold_spans"] == 1)
    aggregate = Aggregate()
    aggregate.add(text, [], wrong, inference.merge_spans(wrong, len(text)))
    result = aggregate.report()
    ok(result["clean_controls"]["masked_rows"] == 1 and result["ratios"]["complete_gold_spans"] is None)
    rejects(lambda: validate_spans(gold + gold, len(text), gold=True), "mask_gold_overlap")
    synthetic = {"case_id": "sanity", "language": "en", "family": "clean", "text": text, "gold": [], "split": "dev"}
    check_stress_rows([synthetic])
    checks += 1
    rejects(lambda: check_stress_rows([dict(synthetic, split="train")]), "stress_split")
    rejects(lambda: check_stress_rows([dict(synthetic, split="test")]), "stress_split")
    rejects(lambda: check_stress_rows([dict(synthetic, extra=0)]), "stress_schema")
    rejects(lambda: check_stress_rows([dict(synthetic, gold=[{"start": False, "end": 3, "label": "GIVENNAME"}])]), "mask_offset_type")
    rejects(lambda: check_stress_rows([dict(synthetic, gold=gold + gold)]), "mask_gold_overlap")
    positive = {"row_id": "sanity", "language": "en", "source_text": text, "privacy_mask": gold, "template_id": "sanity", "split": "dev"}
    positive_data.check_rows([positive], allowed_split="dev")
    checks += 1
    rejects(lambda: positive_data.check_rows([positive]), "pos_split_mismatch")
    rejects(lambda: positive_data.check_rows([dict(positive, split="test")], allowed_split="dev"), "pos_split_mismatch")
    # Narrow stress compatibility: diagnostic labels remain GOLD-only.
    for label in sorted(GOLD_DIAGNOSTIC_LABELS):
        diagnostic = [dict(gold[0], label=label)]
        validate_spans(diagnostic, len(text), gold=True)
        checks += 1
        rejects(lambda: validate_spans(diagnostic, len(text)), "mask_label")
        rejects(lambda: positive_data.check_rows([dict(positive, privacy_mask=diagnostic)], allowed_split="dev"), "pos_label")
    rejects(lambda: validate_spans([dict(gold[0], label="UNKNOWN")], len(text), gold=True), "mask_label")
    check_stress_rows([dict(synthetic, text=text[0] * STRESS_MAX_CHARS)])
    checks += 1
    rejects(lambda: check_stress_rows([dict(synthetic, text=text[0] * (STRESS_MAX_CHARS + 1))]), "stress_text_bounds")
    positive_data.check_rows([dict(positive, source_text=text[0] * positive_data.MAX_CHARS)], allowed_split="dev")
    checks += 1
    rejects(lambda: positive_data.check_rows([dict(positive, source_text=text[0] * (positive_data.MAX_CHARS + 1))], allowed_split="dev"), "pos_text_bounds")
    rejects(lambda: check_stress_rows([dict(synthetic, family="UNKNOWN")]), "stress_family")
    rejects(lambda: check_stress_rows([dict(synthetic, family="phone")]), "stress_clean_family")
    by_family = EngineAggregate()
    by_family.add(text, gold, "en", wrong, wrong, family="names")
    by_family.add(text, [], "en", [], [], family="clean")
    family_report = by_family.report()
    ok(family_report["per_family"]["names"]["complete_gold_spans"] == 1)
    ok(family_report["per_family"]["clean"]["clean_controls"]["rows"] == 1)
    ok(sum(group["rows"] for group in family_report["per_family"].values()) == family_report["overall"]["rows"])
    rejects(lambda: by_family.add(text, gold, "en", wrong, wrong, family="UNKNOWN"), "stress_family")
    compatible = EngineAggregate()
    compatible.add(text, gold, "en", wrong, wrong)
    ok(compatible.report()["per_family"] == {} and compatible.report()["overall"]["complete_gold_spans"] == 1)
    with patch.object(positive_data, "load_positive_file", return_value=([positive] * 280, {"sha256": EXPECTED_POSITIVE})) as loader:
        loaded, _ = load_dataset("unused", "positive")
        ok(len(loaded) == 280 and loaded[0] == (text, gold, "en", None))
        loader.assert_called_once_with("unused", allowed_split="dev")
        checks += 1
    # Actual run/apply_mask semantics, including overlapping labels and adjacency.
    raw = pred + [{"start": 2, "end": 4, "label": "CITY"}]
    final = inference.merge_spans(raw, len(text))
    ok(interval_union([(p["start"], p["end"]) for p in final], len(text)) == [(1, 5)])
    actual = inference.apply_mask(text, final)
    expected = text[:1] + "[GIVENNAME]".replace("GIVENNAME", final[0]["label"]) + text[5:]
    ok(actual["masked_text"] == expected and actual["entities"] == final)

    class FixedMbert:
        def detect(self, value, threshold):
            return raw

    with patch.object(inference, "_load_mbert", return_value=FixedMbert()), patch.object(hybrid, "regex", return_value=[]):
        ok(inference.run(text, engine="mbert", confidence=0)["entities"] == final)
        hybrid_final = inference.merge_spans(hybrid.union([], raw), len(text))
        ok(inference.run(text, engine="hybrid", policy="union", confidence=0)["entities"] == hybrid_final)
    # Actual regex CLI path uses its detector's non-overlapping returned intervals.
    from privacygate.detect import detect as regex_detect
    regex_raw = hybrid.regex(text)
    ok(inference.run(text, engine="regex") == inference.apply_mask(text, regex_detect(text)))
    ok(regex_raw == [] and interval_union([], len(text)) == [])
    return {"passed": checks, "failed": 0, "scope": "compact_interval_loader_and_actual_mask_semantics"}


def freeze_manifest(args, dataset, checks):
    model_dir = Path(args.model_dir)
    model_files = {name: sha256(model_dir / name) for name in ("config.json", "model.safetensors", "train_info.json")}
    if model_files["model.safetensors"] != EXPECTED_MODEL:
        raise MaskingError("mask_model_binding")
    # Bind the exact cached tokenizer assets before a single model forward sweep.
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1" or not os.environ.get("HF_HOME"):
        raise MaskingError("mask_offline_required")
    snapshot = Path(os.environ["HF_HOME"]) / "hub" / "models--google-bert--bert-base-multilingual-cased" / "snapshots" / mbert_data.MODEL_REVISION
    tokenizer_files = {name: sha256(snapshot / name) for name in TOKENIZER_FILES}
    return {
        **SCOPE, "scorer_version": SCORER_VERSION, "definitions": DEFINITIONS,
        "dataset_format": args.format, "dataset": dataset, "model_sha256": EXPECTED_MODEL,
        "schema_limits": {"stress_max_chars": STRESS_MAX_CHARS, "positive_max_chars": positive_data.MAX_CHARS,
                          "max_file_bytes": positive_data.MAX_FILE_BYTES, "max_line_bytes": positive_data.MAX_LINE_BYTES,
                          "max_rows": positive_data.MAX_ROWS, "max_gold_spans_per_row": positive_data.MAX_ANNOTATIONS},
        "gold_only_diagnostic_labels": sorted(GOLD_DIAGNOSTIC_LABELS), "stress_family_allowlist": sorted(STRESS_FAMILIES),
        "checkpoint_file_sha256": model_files,
        "tokenizer": {"model_id": mbert_data.MODEL_ID, "revision": mbert_data.MODEL_REVISION, "file_sha256": tokenizer_files},
        "source_sha256": {name: sha256(ROOT / name) for name in SOURCES},
        "engines": {
            "regex": {"confidence": None, "scope": "EMAIL and checksum-valid IBAN only; not a general personal-information detector"},
            "mbert": {"confidence": 0.0, "mask_semantics": "inference.merge_spans then apply_mask"},
            "hybrid_union": {"confidence": 0.0, "policy": "union", "mask_semantics": "hybrid.union then inference.merge_spans then apply_mask"},
        },
        "sanity_checks": checks, "scoring_time_limit_s": 360,
        "model_forward_sweeps_requested": 1, "threshold_selection": False,
        "synthetic_only": True, "aggregate_only": True, "input_modification": False,
        "scope_exclusions": ["Micro corpus", "test manifests", "train evaluation", "old checkpoints", "real/company data", "production/privacy guarantees"],
        "runtime": {"python_version": sys.version.split()[0], "bytecode_disabled": bool(sys.dont_write_bytecode)},
    }


def verify_bindings(args, manifest):
    if sha256(args.dataset) != manifest["dataset"]["sha256"]:
        raise MaskingError("mask_input_changed")
    for name, digest in manifest["checkpoint_file_sha256"].items():
        if sha256(Path(args.model_dir) / name) != digest:
            raise MaskingError("mask_input_changed")
    for name, digest in manifest["source_sha256"].items():
        if sha256(source_path(name)) != digest:
            raise MaskingError("mask_source_changed")
    snapshot = Path(os.environ["HF_HOME"]) / "hub" / "models--google-bert--bert-base-multilingual-cased" / "snapshots" / mbert_data.MODEL_REVISION
    for name, digest in manifest["tokenizer"]["file_sha256"].items():
        if sha256(snapshot / name) != digest:
            raise MaskingError("mask_input_changed")


def summary_text(report):
    lines = [
        "Synthetic development masking diagnostic", "",
        "Training: false. Test evaluated: false. Scope: development_diagnostic.",
        "Counts are annotated synthetic coverage, not coverage of all personal information or a production privacy guarantee.",
        "Unannotated information is outside these measurements. No complete address/person-linkage assertion.",
        "Non-alphanumeric-only misses are not claimed to expose an identifier; Unicode alphanumeric leakage is separate.",
        "Raw exact detections and final merged mask entities have distinct diagnostics; historical strict F1 is unchanged.",
        "Regex supports EMAIL/checksum-valid IBAN only. No predictions were filtered by gold, no tuning or threshold selection.",
        "Per-label row success covers that label only. Per-label excess is whole-row excess and cannot be summed across labels.",
        "Clean completeness ratios are N/A, never a trivial 100% success.", "",
    ]
    for name in ENGINES:
        engine = report["engines"][name]
        overall = engine["overall"]
        lines.extend([
            name,
            "  Complete spans: {complete_gold_spans}/{gold_spans}; original gold chars covered: {covered_gold_chars}/{gold_chars}; alnum leakage: {leaked_gold_alnum_chars}/{gold_alnum_chars}.".format(**overall),
            "  Positive rows completely masked: {fully_masked_positive_rows}/{positive_rows}; partial/untouched spans: {partial_gold_spans}/{untouched_gold_spans}; excess masked chars: {excess_masked_chars}.".format(**overall),
            "  Clean controls: " + json.dumps(overall["clean_controls"], sort_keys=True),
            "  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched",
        ])
        for label, metrics in engine["per_gold_label"].items():
            classes = metrics["raw_detection_classification"]
            lines.append("  " + label + ": " + "{complete_gold_spans}/{gold_spans}; {covered_gold_chars}/{gold_chars}; {leaked_gold_alnum_chars}/{gold_alnum_chars}; ".format(**metrics) + "/".join(str(classes[key]) for key in CLASSES))
        lines.append("  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess")
        for language, metrics in engine["per_language"].items():
            lines.append("  " + language + ": " + "{complete_gold_spans}/{gold_spans}; {covered_gold_chars}/{gold_chars}; {leaked_gold_alnum_chars}/{gold_alnum_chars}; {fully_masked_positive_rows}/{positive_rows}; {partial_gold_spans}/{untouched_gold_spans}; {excess_masked_chars}".format(**metrics))
        lines.append("  Family: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess; clean masked/total")
        for family, metrics in engine["per_family"].items():
            clean = metrics["clean_controls"]
            lines.append("  " + family + ": " + "{complete_gold_spans}/{gold_spans}; {covered_gold_chars}/{gold_chars}; {leaked_gold_alnum_chars}/{gold_alnum_chars}; {fully_masked_positive_rows}/{positive_rows}; {partial_gold_spans}/{untouched_gold_spans}; {excess_masked_chars}".format(**metrics) + "; " + str(clean["masked_rows"]) + "/" + str(clean["rows"]))
        lines.append("")
    lines.extend(["Full aggregate counts, classifications and clean controls: metrics.json.", "Pre-scoring frozen definitions and input/checkpoint/source/tokenizer hashes: manifest.json.", "Execution receipt: receipt.json."])
    return "\n".join(lines) + "\n"


def execute(args):
    checks = sanity_checks()
    rows, dataset = load_dataset(args.dataset, args.format)
    manifest = freeze_manifest(args, dataset, checks)
    out = Path(args.out_dir)
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise MaskingError("mask_output_exists") from None
    json_write(out / "manifest.json", manifest)
    aggregates = {name: EngineAggregate() for name in ENGINES}
    receipt = {**SCOPE, "status": "started", "stage": "frozen", "rows_requested": len(rows), "rows_scored": 0, "model_forward_sweeps_started": 0, "model_forward_sweeps_completed": 0, "manifest_sha256": sha256(out / "manifest.json")}
    json_write(out / "receipt.json", receipt)
    start = time.monotonic()
    old_alarm = signal.getsignal(signal.SIGALRM)

    def deadline(signum, frame):
        raise MaskingError("mask_scoring_timeout")

    try:
        signal.signal(signal.SIGALRM, deadline)
        signal.setitimer(signal.ITIMER_REAL, 360)
        receipt["stage"] = "model_load"
        json_write(out / "receipt.json", receipt)
        texts = [row[0] for row in rows]
        with quiet_libraries():
            tokenizer = mbert_data.load_tokenizer()
            model = hybrid.Mbert(Path(args.model_dir), tok=tokenizer)
            receipt["device"] = str(model.device)
            receipt["stage"] = "model_forward"
            receipt["model_forward_sweeps_started"] = 1
            json_write(out / "receipt.json", receipt)
            # Cheap regex arm runs concurrently; the SAME raw sweep feeds both learned arms.
            with ThreadPoolExecutor(max_workers=1) as pool:
                regex_future = pool.submit(lambda: [hybrid.regex(text) for text in texts])
                raw_predictions = model.raw(texts)
                receipt["model_forward_sweeps_completed"] = 1
                regex_predictions = regex_future.result()
        if len(raw_predictions) != len(rows) or len(regex_predictions) != len(rows):
            raise MaskingError("mask_prediction_count")
        receipt["stage"] = "aggregate_scoring"
        json_write(out / "receipt.json", receipt)
        for (text, gold, language, family), raw, regex in zip(rows, raw_predictions, regex_predictions):
            mb = model.spans(raw, thr=0.0)
            # No prediction is selected, removed or changed using gold.
            validate_spans(regex, len(text))
            validate_spans(mb, len(text))
            candidates = {"regex": regex, "mbert": mb, "hybrid_union": regex + mb}
            final = {
                "regex": regex,  # detect.mask returns these non-overlapping entities unchanged.
                "mbert": inference.merge_spans(mb, len(text)),
                "hybrid_union": inference.merge_spans(hybrid.union(regex, mb), len(text)),
            }
            for name in ENGINES:
                aggregates[name].add(text, gold, language, candidates[name], final[name], family=family)
            receipt["rows_scored"] += 1
        signal.setitimer(signal.ITIMER_REAL, 0)
        receipt["scoring_elapsed_s"] = round(time.monotonic() - start, 6)
        verify_bindings(args, manifest)
        report = {**SCOPE, "scorer_version": SCORER_VERSION, "manifest_sha256": receipt["manifest_sha256"], "dataset_sha256": dataset["sha256"], "model_sha256": EXPECTED_MODEL, "rows_evaluated": len(rows), "engines": {name: aggregate.report() for name, aggregate in aggregates.items()}}
        if any(arm["overall"]["rows"] != len(rows) for arm in report["engines"].values()):
            raise MaskingError("mask_count_mismatch")
        json_write(out / "metrics.json", report)
        receipt.update(status="complete", stage="complete", bindings_unchanged=True, metrics_sha256=sha256(out / "metrics.json"))
        json_write(out / "receipt.json", receipt)
        print("mask_complete rows=" + str(len(rows)) + " engines=3 sweeps=1 sanity_passed=" + str(checks["passed"]))
        for name in ENGINES:
            overall = report["engines"][name]["overall"]
            print(name + " " + "complete_spans={complete_gold_spans}/{gold_spans} covered_chars={covered_gold_chars}/{gold_chars} alnum_leakage={leaked_gold_alnum_chars}/{gold_alnum_chars} complete_rows={fully_masked_positive_rows}/{positive_rows} excess_chars={excess_masked_chars}".format(**overall))
        return 0
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        code = str(error) if isinstance(error, MaskingError) else "mask_execution_failed"
        receipt.update(status="partial", error_code=code, elapsed_s=round(time.monotonic() - start, 6))
        json_write(out / "partial-metrics.json", {**SCOPE, "manifest_sha256": receipt["manifest_sha256"], "engines": {name: aggregate.report() for name, aggregate in aggregates.items()}})
        json_write(out / "receipt.json", receipt)
        print(code, file=sys.stderr)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_alarm)


def main():
    try:
        parser = SafeParser(description=__doc__)
        parser.add_argument("--dataset", required=True)
        parser.add_argument("--format", choices=("positive", "stress"), required=True)
        parser.add_argument("--model-dir", required=True)
        parser.add_argument("--out-dir", required=True)
        return execute(parser.parse_args())
    except MaskingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except ValueError as error:
        code = str(error)
        safe_codes = {"pos_" + key for key in ("bad_allowed_split", "row_count", "bad_forbid_ids", "schema", "field_type", "split_mismatch", "language", "text_bounds", "row_id", "template_id", "duplicate_text", "annotation_count", "mask_schema", "mask_type", "label", "span_bounds", "span_overlap", "template_language", "path", "not_regular_file", "file_too_large", "line_too_long", "unparseable")}
        print(code if code in safe_codes else "mask_validation_failed", file=sys.stderr)
        return 1
    except Exception:
        print("mask_setup_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
