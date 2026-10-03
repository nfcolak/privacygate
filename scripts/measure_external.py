#!/usr/bin/env python3
"""Frozen aggregate-only GLiNER2 PII sweep on synthetic dev v1/v2/blind v3/v4.

Use the isolated requirements-external.txt environment and a local HF snapshot of
MODEL_REVISION. No downloads, training, test split access, tuning, or row logs.

  measure_external.py --version v1|v2|v3|v4 --model-dir SNAPSHOT --device cpu|mps [--out-dir DIR]
  measure_external.py --summary
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import measure_refine as mr  # noqa: E402
from privacygate import inference, positive_data  # noqa: E402
from privacygate.masking_metrics import (  # noqa: E402
    DEFINITIONS, EngineAggregate, MaskingError, SCORER_VERSION, interval_union,
    validate_spans,
)

mm = mr.mm
MODEL_ID = "fastino/gliner2-privacy-filter-PII-multi"
MODEL_REVISION = "1cb4166094dc58fa8d836429f060d6c95f62b495"
RUNTIME_REPOSITORY = "https://github.com/fastino-ai/GLiNER2"
RUNTIME_REVISION = "55656fbfa01d3d4a77485e1a1eeeaf682990ccdf"
THRESHOLD = 0.5
OVERLAP_WORD_TOKENS = 64  # Frozen before predictions; no boundary/threshold tuning.
LABELS = (
    "person", "full_name", "first_name", "middle_name", "last_name", "date_of_birth",
    "email", "phone_number", "address", "street_address", "city", "state_or_region", "postal_code", "country",
    "government_id", "national_id_number", "passport_number", "drivers_license_number", "license_number", "tax_id", "tax_number",
    "bank_account", "account_number", "routing_number", "iban", "payment_card", "card_number", "card_expiry", "card_cvv",
    "username", "ip_address", "account_id", "sensitive_account_id",
    "password", "secret", "api_key", "access_token", "recovery_code",
    "sensitive_date", "document_date", "expiration_date", "transaction_date",
)
ARM = "gliner2_pii"
RUNS = ROOT / "docs/runs/external-models-1003"
SCOPE = {**mr.SCOPE, "synthetic_only": True, "aggregate_only": True}
SOURCE_FILES = (
    "scripts/measure_external.py", "scripts/measure_refine.py", "scripts/measure_masking.py",
    "privacygate/masking_metrics.py", "privacygate/inference.py", "privacygate/positive_data.py",
    "requirements-external.txt",
)
MODEL_FILES = (
    "config.json", "encoder_config/config.json", "model.safetensors",
    "tokenizer.json", "tokenizer_config.json", "README.md",
)


def require(condition, code):
    if not condition:
        raise MaskingError(code)


def load_rows(version) -> tuple[Path, list, dict]:
    if version == "v4":
        from privacygate import masking_eval as ev
        path = ROOT / "data/augmentation/masking-stress-v4.jsonl"
        try:
            data, binding = ev.load_dataset(path, version, root=ROOT)
        except ev.EvaluationError as error:
            raise MaskingError(str(error)) from None
        frozen = json.loads((ROOT / "docs/masking-stress-v4/manifest.json").read_text(encoding="utf-8"))
        require(all(binding[k] == frozen["counts"][k] for k in ("positive_rows", "clean_rows", "gold_spans")), "external_v4_counts")
        # Loader compatibility only: historical scoring admits DATE, not the
        # canonical DATEOFBIRTH alias, and only legacy stress-family names.
        # Preserve every gold interval and input character; do not invent family
        # mappings. Class-agnostic coverage formulas and predictions are unchanged.
        binding.update({"gold_label_aliases": {"DATEOFBIRTH": "DATE"},
                        "family_reporting": "omitted: v4 families are outside the historical scorer allowlist",
                        "loader_source_sha256": mm.sha256(ROOT / "privacygate/masking_eval.py")})
        rows = [(r["text"], [{**g, "label": "DATE" if g["label"] == "DATEOFBIRTH" else g["label"]}
                             for g in r["gold"]], r["language"], None) for r in data]
        return path, rows, binding
    name = "masking-stress-dev.jsonl" if version == "v1" else "masking-stress-" + version + "-dev.jsonl"
    path = ROOT / "data/augmentation" / name
    if version in ("v1", "v2"):
        rows, binding = mr.load_rows(path, version)
        return path, rows, binding
    # v3 uses the frozen six-field stress schema, not the positive corpus schema.
    frozen = json.loads((ROOT / "docs/masking-stress-v3/manifest.json").read_text(encoding="utf-8"))
    raw = positive_data._read_bounded(path)
    expected = frozen["dataset"]
    require(hashlib.sha256(raw).hexdigest() == expected["sha256"], "external_v3_binding")
    lines = [line for line in raw.split(b"\n") if line.strip()]
    require(all(len(line) <= positive_data.MAX_LINE_BYTES for line in lines), "external_v3_line_bounds")
    try:
        data = [json.loads(line.decode("utf-8"), object_pairs_hook=mm._unique_object) for line in lines]
    except MaskingError:
        raise
    except (ValueError, RecursionError):
        raise MaskingError("external_v3_unparseable") from None
    mm.check_stress_rows(data)
    binding = {
        "sha256": expected["sha256"], "rows": len(data), "split": "dev", "bytes": len(raw),
        "positive_rows": sum(bool(r["gold"]) for r in data),
        "clean_rows": sum(not r["gold"] for r in data),
        "gold_spans": sum(len(r["gold"]) for r in data),
    }
    require(binding["rows"] == expected["rows"] and binding["bytes"] == expected["bytes"], "external_v3_shape")
    require(all(binding[k] == frozen["counts"][k] for k in ("positive_rows", "clean_rows", "gold_spans")), "external_v3_counts")
    return path, [(r["text"], r["gold"], r["language"], r["family"]) for r in data], binding


def runtime_versions():
    names = ("gliner2", "torch", "transformers", "tokenizers", "huggingface-hub", "safetensors", "numpy", "peft", "sentencepiece", "protobuf")
    distribution = importlib.metadata.distribution("gliner2")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    require(direct.get("vcs_info", {}).get("commit_id") == RUNTIME_REVISION, "external_runtime_binding")
    return {"python": platform.python_version(), "packages": {n: importlib.metadata.version(n) for n in names},
            "gliner2_direct_url": direct, "platform": platform.system(), "machine": platform.machine()}


def check_card(model_dir):
    card = (model_dir / "README.md").read_text(encoding="utf-8")
    table = card.split("## Supported PII Labels", 1)[1].split("## Benchmark Results", 1)[0]
    # Parse table rows only: retain exactly the full card label order, including aliases.
    actual = tuple(label for line in table.splitlines() if line.startswith("| **") for label in re.findall(r"`([^`]+)`", line))
    require(actual == LABELS, "external_card_labels_binding")
    require("threshold=0.5" in card and "license: apache-2.0" in card, "external_card_defaults_binding")


def chunks_for(text, model, schema, max_input_tokens):
    """Pack original-character chunks; include schema and runtime-added punctuation.

    The runtime tokenizes lowercase word values but keeps original character
    coordinates. Its exact transform_record input_ids length, not an approximate
    tokenizer(text) length or a word count, determines whether a chunk fits.
    Whitespace between token boundaries belongs to at least one chunk.
    """
    tokens = list(model.processor.word_splitter(text, lower=False))
    boundaries = sorted({0, len(text)} | {a for _, a, _ in tokens if a > 0})
    result = []
    current = 0
    while current < len(boundaries) - 1:
        start = boundaries[current]
        low, high, best = current + 1, len(boundaries) - 1, None
        while low <= high:
            middle = (low + high) // 2
            end = boundaries[middle]
            rec = model.processor.transform_record(text[start:end], schema, max_len=None)
            length = len(rec.input_ids)
            if length <= max_input_tokens:
                best = (middle, length)
                low = middle + 1
            else:
                high = middle - 1
        if best is None:
            raise MaskingError("external_chunk_cannot_fit")
        middle, length = best
        end = boundaries[middle]
        require(start < end and length <= max_input_tokens, "external_chunk_bounds")
        result.append((start, end, length))
        if end == len(text):
            break
        current = max(current + 1, middle - OVERLAP_WORD_TOKENS)
    coverage = interval_union([(a, b) for a, b, _ in result], len(text))
    require(coverage == [(0, len(text))], "external_input_not_fully_covered")
    assert coverage == [(0, len(text))]
    return result


def spans_from(result, chunk, base, mapping_counts=None):
    require(isinstance(result, dict) and isinstance(result.get("entities"), dict), "external_prediction_schema")
    # The pinned runtime appends a period to unfinished chunks. Map its known
    # synthetic terminal character back to the original domain, never repairing
    # arbitrary bad offsets or dropping any original-character prediction.
    normalized = chunk if chunk.endswith((".", "!", "?")) else chunk + "."
    out = []
    for label, entities in result["entities"].items():
        require(label in LABELS and isinstance(entities, list), "external_prediction_label")
        for entity in entities:
            require(isinstance(entity, dict), "external_prediction_span_schema")
            a, b = entity.get("start"), entity.get("end")
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(normalized), "external_prediction_offsets")
            require(entity.get("text") == normalized[a:b].strip(), "external_prediction_text_alignment")
            if a >= len(chunk):
                if mapping_counts is not None:
                    mapping_counts["synthetic_terminal_only_predictions"] += 1
                continue
            if b > len(chunk):
                require(normalized == chunk + "." and b == len(chunk) + 1, "external_padding_mapping")
                if mapping_counts is not None:
                    mapping_counts["predictions_projected_off_synthetic_terminal"] += 1
                b = len(chunk)
            # The unchanged scorer admits only PrivacyGate prediction labels.
            # Retain EVERY original-character external span and map its label to
            # STREET for scoring only; comparisons are class-agnostic coverage.
            out.append({"start": base + a, "end": base + b, "label": "STREET"})
    return out


def execute(args):
    require(os.environ.get("HF_HUB_OFFLINE") == "1" and os.environ.get("TRANSFORMERS_OFFLINE") == "1" and bool(os.environ.get("HF_HOME")), "external_offline_required")
    model_dir = Path(args.model_dir)
    require(model_dir.name == MODEL_REVISION, "external_snapshot_revision")
    path, rows, binding = load_rows(args.version)
    runtime = runtime_versions()
    check_card(model_dir)
    sources = {n: mm.sha256(ROOT / n) for n in SOURCE_FILES}
    model_hashes = {n: mm.sha256(model_dir / n) for n in MODEL_FILES}
    out = Path(args.out_dir) if args.out_dir else RUNS / args.version
    require(not out.exists(), "external_output_exists")
    out.mkdir(parents=True)
    # Reserving the run before loading/forward prevents an accidental repeat.
    mm.json_write(out / "manifest.json", {
        **SCOPE, "model_id": MODEL_ID, "revision": MODEL_REVISION,
        "dataset_version": args.version, "dataset": binding, "device": args.device,
        "threshold": THRESHOLD, "status": "reserved", "forward_sweeps_requested": 1,
    })
    total_start = time.perf_counter()
    load_start = time.perf_counter()
    with mm.quiet_libraries():
        import torch
        from gliner2 import GLiNER2
        from gliner2.training.trainer import ExtractorCollator
        require(args.device != "mps" or torch.backends.mps.is_available(), "external_mps_unavailable")
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.manual_seed(0)
        model = GLiNER2.from_pretrained(str(model_dir), local_files_only=True, map_location="cpu")
        model.to(args.device).eval()
        model.strict_extraction = True
        # Exact preprocessing must raise rather than silently replace a malformed
        # row with the runtime's fallback/dummy record.
        class StrictCollator(ExtractorCollator):
            def __call__(self, batch):
                return self.processor.collate_fn_inference(batch, max_len=None, error_policy="raise", architecture="span", build_targets=False)
        model._inference_collator = StrictCollator(model.processor, is_training=False)
        schema = model.create_schema().entities(list(LABELS))
        limits = [model.encoder.config.max_position_embeddings]
        tokenizer_limit = model.processor.tokenizer.model_max_length
        if isinstance(tokenizer_limit, int) and 0 < tokenizer_limit < 1000000:
            limits.append(tokenizer_limit)
        max_input_tokens = min(limits)
        require(type(max_input_tokens) is int and max_input_tokens > 0, "external_model_length")
    load_seconds = time.perf_counter() - load_start
    aggregate = EngineAggregate()
    chunk_count = multi_chunk_rows = covered_chars = input_chars = 0
    max_encoded_tokens = 0
    mapping_counts = {"synthetic_terminal_only_predictions": 0, "predictions_projected_off_synthetic_terminal": 0}
    scoring_start = time.perf_counter()
    with mm.quiet_libraries(), torch.inference_mode():
        for text, gold, language, family in rows:
            chunks = chunks_for(text, model, schema, max_input_tokens)
            chunk_count += len(chunks)
            multi_chunk_rows += len(chunks) > 1
            covered_chars += len(text)
            raw = []
            for a, b, length in chunks:
                input_chars += b - a
                max_encoded_tokens = max(max_encoded_tokens, length)
                result = model.extract_entities(text[a:b], list(LABELS), threshold=THRESHOLD,
                                                include_confidence=True, include_spans=True, max_len=None)
                raw.extend(spans_from(result, text[a:b], a, mapping_counts))
            validate_spans(raw, len(text))
            final = inference.merge_spans(raw, len(text))
            aggregate.add(text, gold, language, raw, final, family=family)
        if args.device == "mps":
            torch.mps.synchronize()
    sweep_seconds = time.perf_counter() - scoring_start
    require(aggregate.overall.counts["rows"] == len(rows), "external_row_count")
    require(mm.sha256(path) == binding["sha256"], "external_dataset_changed")
    require(all(mm.sha256(ROOT / n) == digest for n, digest in sources.items()), "external_source_changed")
    total_seconds = time.perf_counter() - total_start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = int(rss if platform.system() == "Darwin" else rss * 1024)
    timings = {
        "wall_seconds": sweep_seconds, "seconds_per_row": sweep_seconds / len(rows),
        "model_load_seconds": load_seconds, "total_wall_seconds_including_load": total_seconds,
        "peak_rss_bytes": peak_rss_bytes, "peak_rss_mib": peak_rss_bytes / (1024 ** 2),
        "timing_scope": "chunk planning, model forward/extraction, merging and aggregate scoring; excludes model load, binding hashes and artifact writes",
        "peak_rss_scope": "process-lifetime ru_maxrss, including imports and model load; host RSS, not device allocation",
    }
    chunking = {
        "algorithm": "greedy original-character word-boundary chunks; exact processor.transform_record encoded length includes full schema and runtime punctuation",
        "max_encoded_input_tokens": max_input_tokens, "encoder_max_position_embeddings": model.encoder.config.max_position_embeddings,
        "overlap_word_tokens": OVERLAP_WORD_TOKENS, "word_token_truncation": None,
        "batch_size": 1, "chunks": chunk_count, "rows_with_multiple_chunks": multi_chunk_rows,
        "max_observed_encoded_input_tokens": max_encoded_tokens,
        "all_original_characters_covered_asserted": True, "unique_original_characters_covered": covered_chars,
        "chunk_input_characters_with_overlap": input_chars, "offsets": "Python Unicode code points, half-open; original chunk base added, never text.find",
        "runtime_terminal_mapping": "validate against runtime-normalized chunk; project only the known added final period back to original characters; reject every other out-of-range offset",
        "runtime_terminal_mapping_counts": mapping_counts,
        "boundary_entity_completeness_guaranteed": False,
    }
    manifest = {
        **SCOPE, "scorer_version": SCORER_VERSION, "definitions": DEFINITIONS,
        "dataset_version": args.version, "dataset": binding, "model_id": MODEL_ID,
        "revision": MODEL_REVISION, "license": "Apache-2.0", "model_file_sha256": model_hashes,
        "runtime_repository": RUNTIME_REPOSITORY, "runtime_revision": RUNTIME_REVISION,
        "runtime": runtime, "device": args.device, "dtype": "float32", "cpu_threads": 4, "interop_threads": 1,
        "threshold": THRESHOLD, "threshold_selection": False, "labels": list(LABELS), "label_count": len(LABELS),
        "label_note": "All 42 supported labels from the pinned card table, in table order, including aliases.",
        "scoring_label_mapping": "every original-character GLiNER2 prediction -> STREET for scorer input only; no original-character spans discarded; exact-label/label-overlap diagnostics are not meaningful cross-model comparisons",
        "mask_semantics": "inference.merge_spans; unchanged masking_metrics.EngineAggregate, same add/report path as measure_refine.score",
        "source_sha256": sources, "chunking": chunking, "performance": timings,
        "forward_sweeps_requested": 1, "forward_sweeps_completed": 1, "status": "complete",
        "v3_row_level_failures_inspected": False, "offline": True,
    }
    report = {
        **SCOPE, "scorer_version": SCORER_VERSION, "dataset_version": args.version,
        "dataset_sha256": binding["sha256"], "model_id": MODEL_ID, "revision": MODEL_REVISION,
        "device": args.device, "threshold": THRESHOLD, "rows_evaluated": len(rows),
        "forward_sweeps": 1, "chunking": chunking, "performance": timings,
        "engines": {ARM: aggregate.report()},
    }
    mm.json_write(out / "metrics.json", report)
    mm.json_write(out / "manifest.json", manifest)
    print("external_complete version=" + args.version + " rows=" + str(len(rows)) + " chunks=" + str(chunk_count) + " sweeps=1")
    return 0


def table_row(name, report, timing):
    o = report["overall"]
    c = o["clean_controls"]
    return "| {} | {}/{} | {} | {} | {}/{} | {}/{} | {} | {}/{} | {} | {} |".format(
        name, o["complete_gold_spans"], o["gold_spans"], o["partial_gold_spans"], o["untouched_gold_spans"],
        o["leaked_gold_alnum_chars"], o["gold_alnum_chars"], o["fully_masked_positive_rows"], o["positive_rows"],
        o["excess_masked_chars"], c["masked_rows"], c["rows"], c["masked_chars"], timing)


def write_summary():
    lines = ["# Frozen GLiNER2-PII comparison (1003)", "",
             "One sweep on each synthetic development set, full pinned-card label list, threshold 0.5; no tuning, training or test evaluation.",
             "Model: " + MODEL_ID + ", revision " + MODEL_REVISION + ". Runtime: GLiNER2 commit " + RUNTIME_REVISION + ".", "",
             "Our-engine v1/v2 references are the committed hybrid_union_refined artifacts present on this writer's starting branch (350983f);",
             "they are not the parallel rules writer's later re-measurements. Own-engine v3 numbers come later from the integrator.", ""]
    external_reports = {}
    reference_bindings = {}
    for v in ("v1", "v2", "v3"):
        report = json.loads((RUNS / v / "metrics.json").read_text(encoding="utf-8"))
        manifest = json.loads((RUNS / v / "manifest.json").read_text(encoding="utf-8"))
        external_reports[v] = report
        require(report["test_evaluated"] is False and report["training"] is False and report["forward_sweeps"] == 1, "external_summary_scope")
        lines += ["## Stress " + v, "", "Dataset sha256: " + report["dataset_sha256"] + "; " + str(report["rows_evaluated"]) + " rows.", "",
                  "| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess masked chars | clean rows masked | clean masked chars | seconds/row |",
                  "|---|---|---|---|---|---|---|---|---|---|",
                  table_row(ARM, report["engines"][ARM], "{:.6f}".format(report["performance"]["seconds_per_row"]))]
        if v != "v3":
            p = ROOT / "docs/runs/masking-coverage" / ("refine-" + v) / "metrics.json"
            reference = json.loads(p.read_text(encoding="utf-8"))
            require(reference["dataset_sha256"] == report["dataset_sha256"], "external_reference_dataset")
            reference_bindings[v] = {"path": p.relative_to(ROOT).as_posix(), "sha256": mm.sha256(p)}
            lines.append(table_row("hybrid_union_refined (committed reference)", reference["engines"]["hybrid_union_refined"], "not recorded"))
        else:
            lines += ["", "hybrid_union_refined v3: pending the integrator's single blind measurement; no own-engine v3 run performed here."]
        perf = report["performance"]
        lines += ["", "Device: " + report["device"] + "; chunks: " + str(manifest["chunking"]["chunks"]) + "; measured sweep wall time: {:.3f} s; model load: {:.3f} s; peak host RSS: {:.2f} MiB.".format(perf["wall_seconds"], perf["model_load_seconds"], perf["peak_rss_mib"]), ""]
    count = len(LABELS)
    lines += ["## Fixed setup and limits", "",
              "All " + str(count) + " supported labels in the pinned card were requested in their table order, including name and identifier aliases.",
              "Package dependency constraints (Transformers <5) were kept rather than the checkpoint config's Transformers 5.8.0 metadata; exact installed versions are in requirements-external.txt and each manifest.",
              "Chunks are selected by the runtime's exact encoded-input length, including the full label schema and added terminal punctuation, bounded by the model/tokenizer limit.",
              "Overlap is fixed at 64 word-splitter tokens; all original characters are covered and asserted. No input truncation, text.find conversion, per-label filtering or boundary tuning.",
              "Only the runtime's known added terminal period is projected out of predictions when mapping back to original characters; every other invalid offset is rejected and mapping counts are aggregate-only in each manifest.",
              "The full original-character external prediction union is scored with unchanged masking_metrics after inference.merge_spans; predicted labels are mapped to STREET solely for scorer compatibility.",
              "Coverage is class-agnostic; the scorer's exact-label diagnostics are not cross-model detection accuracy. Own-engine timing was not recorded and is not inferred.",
              "Seconds/row includes chunk planning, model extraction, merging and scoring, excluding model load; process-lifetime peak RSS includes load and is host memory only.",
              "v3 was evaluated once, aggregates only, without inspecting row-level failures. Neither v1 nor v2 is blind to prior rule development.",
              "Synthetic dev diagnostics and annotation-relative coverage only; limited languages/formats, mechanically annotated invented values and chunk-boundary effects limit generalization.",
              "No real-data, production privacy or legal guarantee. Nothing was trained; no corpus test split was accessed.", "",
              "Reference artifact bindings (committed starting-branch files):", ""]
    for v, b in reference_bindings.items():
        lines.append("- " + v + ": " + b["path"] + "; sha256 " + b["sha256"])
    (RUNS / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("external_summary_written")
    return 0


def main():
    try:
        parser = mr.SafeParser(description=__doc__)
        parser.add_argument("--summary", action="store_true")
        parser.add_argument("--version", choices=("v1", "v2", "v3", "v4"))
        parser.add_argument("--out-dir")
        parser.add_argument("--model-dir")
        parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
        args = parser.parse_args()
        if args.summary:
            return write_summary()
        require(args.version and args.model_dir, "external_arguments")
        return execute(args)
    except MaskingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        # Exceptions may contain text/offsets; emit only the error class.
        print("external_operation_failed class=" + type(error).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
