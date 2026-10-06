#!/usr/bin/env python3
"""Offline, aggregate-only evaluation through the CLI's actual pipeline API."""
import argparse
from contextlib import contextmanager
import importlib
from importlib import metadata
import os
from pathlib import Path
import sys
import time
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation import masking_eval as ev

PROFILES = ("full",)


def load_v7_dataset(dataset, root=ROOT):
    """Frozen-generator replay of the (now development) v7 set; root is the repo."""
    try:
        from evaluation.checks import verify_frozen
        if Path(root).resolve() != verify_frozen.ROOT.resolve():
            raise ev.EvaluationError("eval_v7_root")
        rows, manifest = verify_frozen.load_v7_generator().verify(dataset)
        return rows, {"version": "v7", "path": manifest["dataset_path"],
                      "sha256": manifest["dataset_sha256"], "rows": manifest["counts"]["rows"],
                      "manifest_sha256": ev.sha256(root / ev.MANIFEST_PATHS["v7"])}
    except Exception:
        raise ev.EvaluationError("eval_v7_frozen_binding") from None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ev.EvaluationError("eval_arguments")


def parser():
    p = SafeParser(description=__doc__)
    p.add_argument("--dataset", required=True)
    p.add_argument("--version", choices=ev.VERSIONS, required=True)
    p.add_argument("--profile", choices=PROFILES, default="full")
    p.add_argument("--model-dir", required=True)
    p.add_argument("--out-dir", required=True)
    return p


def _runtime():
    versions: dict[str, Optional[str]] = {"python": sys.version.split()[0]}
    for name in ("transformers", "torch", "tokenizers", "phonenumberslite"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def fingerprints(args, root):
    model = Path(args.model_dir)
    if not model.is_dir() or not (model / "model.safetensors").is_file() or not (model / "config.json").is_file():
        raise ev.EvaluationError("eval_model_unavailable")
    model_files = {p.name: ev.sha256(p) for p in sorted(model.iterdir())
                   if p.is_file() and p.suffix in (".json", ".txt", ".safetensors", ".bin")}
    source = {str(p.relative_to(root)): ev.sha256(p) for p in sorted((root / "privacygate").rglob("*.py"))}
    # The runner and its scorer are also part of the frozen source binding.
    for relative in ("evaluation/evaluate_pipeline.py", "evaluation/masking_eval.py"):
        source[relative] = ev.sha256(root / relative)
    config = root / "configs/pipeline-v1.json"
    if not config.is_file():
        raise ev.EvaluationError("eval_pipeline_config_unavailable")
    config_hash = ev.sha256(config)
    config_origin = "configs/pipeline-v1.json"
    tokenizer_files = {}
    try:
        from privacygate import mbert_data
        snapshot = Path(os.environ["HF_HOME"]) / "hub/models--google-bert--bert-base-multilingual-cased/snapshots" / mbert_data.MODEL_REVISION
        for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt"):
            if (snapshot / name).is_file():
                tokenizer_files[name] = ev.sha256(snapshot / name)
    except (ImportError, KeyError, AttributeError):
        raise ev.EvaluationError("eval_tokenizer_binding_unavailable") from None
    policy = root / "configs/privacy-policy-v1.json"
    return {"model_sha256": model_files["model.safetensors"],
            "checkpoint_file_sha256": model_files, "source_sha256": source,
            "config_sha256": config_hash, "config_origin": config_origin,
            "tokenizer_file_sha256": tokenizer_files,
            "policy_sha256": ev.sha256(policy) if policy.is_file() else None}


@contextmanager
def predictions(args):
    """Lazy import of the public pipeline API; real weights, never cached predictions."""
    with ev.quiet_libraries():
        try:
            module = importlib.import_module("privacygate.pipeline")
        except Exception:
            raise ev.EvaluationError("eval_prediction_module_unavailable") from None
    run = getattr(module, "run_pipeline", None)
    if not callable(run):
        raise ev.EvaluationError("eval_prediction_entrypoint_unavailable")
    yield lambda text: run(text, profile=args.profile, model_dir=args.model_dir)


def summary(report):
    metric = report["overall"]
    clean = metric["clean_controls"]
    lines = ["# Pipeline masking evaluation", "",
             "Synthetic annotation-relative masking only; no training or test split evaluated.",
             "Not a privacy or legal guarantee. Wilson intervals describe row indicators under an IID assumption;",
             "shared synthetic grammars and small strata limit population inference.", "",
             "Profile: " + report["profile"], "Dataset version: " + report["dataset_version"],
             "Dataset sha256: " + report["dataset_sha256"], "",
             "Complete spans: {}/{}".format(metric["complete_gold_spans"], metric["gold_spans"]),
             "Partial spans: {}".format(metric["partial_gold_spans"]),
             "Untouched spans: {}".format(metric["untouched_gold_spans"]),
             "Exposed alphanumeric characters: {}/{}".format(metric["leaked_gold_alnum_chars"], metric["gold_alnum_chars"]),
             "Uncovered gold characters: {}".format(metric["uncovered_gold_chars"]),
             "Fully masked positive rows (blocked counted as failures): {}/{}".format(metric["fully_masked_positive_rows"], metric["positive_rows"]),
             "Excess masked characters: {}".format(metric["excess_masked_chars"]),
             "Clean rows masked: {}/{}".format(clean["masked_rows"], clean["rows"]),
             "Clean characters masked: {}/{}".format(clean["masked_chars"], clean["text_chars"]),
             "OK / blocked rows: {} / {}".format(metric["ok_rows"], metric["blocked_rows"]),
             "Execution uncovered characters: {}".format(metric["uncovered_chars"]), "",
             "## Row-rate Wilson 95% intervals", ""]
    for key, interval in metric["row_rate_wilson_95"].items():
        if interval["rate"] is None:
            lines.append(key + ": N/A (zero denominator)")
        else:
            lines.append("{}: {}/{}; {:.2%} [{:.2%}, {:.2%}]".format(
                key, interval["successes"], interval["total"], interval["rate"], interval["low"], interval["high"]))
    for title, key in (("Per gold label", "per_gold_label"), ("Per family", "per_family")):
        lines.extend(["", "## " + title, "", "| group | complete spans | partial | untouched | exposed alnum | positive rows complete | clean rows masked |", "|---|---|---|---|---|---|---|"])
        for name, cell in report[key].items():
            c = cell["clean_controls"]
            lines.append("| {} | {}/{} | {} | {} | {} | {}/{} | {}/{} |".format(
                name, cell["complete_gold_spans"], cell["gold_spans"], cell["partial_gold_spans"], cell["untouched_gold_spans"],
                cell["leaked_gold_alnum_chars"], cell["fully_masked_positive_rows"], cell["positive_rows"], c["masked_rows"], c["rows"]))
    lines.extend(["", "Per-label row success concerns that label only; row-scoped excess repeats across labels and is not additive.",
                  "Human semantic review is not performed by this evaluator; that gate remains incomplete.", ""])
    return "\n".join(lines)


def execute(args, root=ROOT, check_receipts=False):
    root = Path(root)
    if args.profile not in PROFILES or args.version not in ev.VERSIONS:
        raise ev.EvaluationError("eval_arguments")
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1" or not os.environ.get("HF_HOME"):
        raise ev.EvaluationError("eval_offline_required")
    if ev.CHECK_RECEIPTS_ENV in os.environ and not check_receipts:
        raise ev.EvaluationError("eval_check_override_forbidden")
    started_at, start = ev.utc_now(), time.perf_counter()
    rows, binding = load_v7_dataset(args.dataset, root)
    frozen = fingerprints(args, root)
    out = Path(args.out_dir)
    if out.exists():
        raise ev.EvaluationError("eval_output_exists")
    custody = ev.BlindCustody(root, args.profile, frozen["model_sha256"], binding["sha256"],
                              check=check_receipts, version=args.version)
    with custody as blind:
        # Module availability is checked before custody is consumed; an inference
        # or scoring failure after reservation consumes this blind arm.
        with predictions(args) as predict:
            out.mkdir(parents=True, exist_ok=False)
            blind.reserve()
            aggregate = ev.EvaluationAggregate()
            with ev.quiet_libraries():
                try:
                    for row in rows:
                        aggregate.add(row, predict(row["text"]))
                except ev.EvaluationError:
                    raise
                except Exception:
                    raise ev.EvaluationError("eval_prediction_failed") from None
        if fingerprints(args, root) != frozen or ev.sha256(args.dataset) != binding["sha256"] or ev.sha256(root / ev.MANIFEST_PATHS[args.version]) != binding["manifest_sha256"]:
            raise ev.EvaluationError("eval_binding_changed")
        wall_time = time.perf_counter() - start
        scope = {"training": False, "test_evaluated": False, "synthetic_only": True, "aggregate_only": True}
        report = {**scope, "scorer_version": ev.SCORER_VERSION, "dataset_version": args.version,
                  "dataset_sha256": binding["sha256"], "model_sha256": frozen["model_sha256"],
                  "profile": args.profile, "predictions_from": "pipeline",
                  "rows_evaluated": len(rows), **aggregate.report()}
        manifest = {**scope, **frozen, "scorer_version": ev.SCORER_VERSION,
                    "interval_functions_version": ev.mm.SCORER_VERSION,
                    "dataset_version": args.version, "dataset": binding,
                    "dataset_sha256": binding["sha256"], "profile": args.profile,
                    "predictions_from": "pipeline", "runtime_versions": _runtime(),
                    "started_at": started_at, "finished_at": ev.utc_now(), "wall_time_seconds": wall_time,
                    "model_load_reused": False,
                    "predictions_cached": False, "human_review_performed": False,
                    "blind": True, "development": False, "threshold_selection": False}
        ev.json_write(out / "metrics.json", report)
        ev.json_write(out / "manifest.json", manifest)
        blind.finish(ev.sha256(out / "metrics.json"))
    return report


def main():
    try:
        args = parser().parse_args()
        report = execute(args)
        overall = report["overall"]
        print("evaluation_complete version={} profile={} complete={}/{}".format(
            args.version, args.profile, overall["complete_gold_spans"], overall["gold_spans"]))
        return 0
    except (Exception, KeyboardInterrupt):
        # Never expose parser tokens, paths, row ids, offsets or library exceptions.
        error = sys.exc_info()[1]
        code = str(error) if isinstance(error, ev.EvaluationError) else "eval_failed"
        print(code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
