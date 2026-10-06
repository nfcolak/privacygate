"""Run-reuse guard for region training. Standard library only; fixed value-free errors.

Only COMPLETE provenance-compatible checkpoints may be reused. Historical outputs
are never migrated, rewritten or deleted.
"""
import argparse
import json
import math
import re

from privacygate.data.region_data import ERROR_CODES as REGION_ERROR_CODES
from privacygate.data.window_alignment import ALIGNMENT_POLICY, ALIGNMENT_SOURCE_VERSION

# Bound into the run identity: checkpoints trained under another windowing are never silently reused.
ENCODER_VERSION = "sliding-windows-full-coverage-v1"
MAX_META_BYTES = 1024 * 1024
RUN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
CHECKPOINT_FILES = ("config.json", "model.safetensors", "train_info.json")
# Only known literal codes may leave a validation boundary; unexpected parser/path errors are redacted.
REFUSAL_CODES = frozenset(
    ["run_" + c for c in ("settings_invalid name_invalid meta_unreadable meta_too_large meta_unparseable meta_schema "
      "without_provenance label_inventory_missing output_path_invalid checkpoint_incomplete "
      "identity_mismatch classifier_labels_mismatch metrics_mismatch").split()]) | REGION_ERROR_CODES


def build_region_identity(args, model_id, model_revision, max_len, stride, labels,
                          train_binding, dev_binding, model_dir):
    return {
        "version": "region-run-identity-v1", "mode": "region", "run": args.run,
        "model": model_id, "model_revision": model_revision,
        "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed,
        "max_len": max_len, "window_stride_tokens": stride, "encoder_version": ENCODER_VERSION,
        "alignment_policy": ALIGNMENT_POLICY, "alignment_source_version": ALIGNMENT_SOURCE_VERSION,
        "labels": list(labels), "region_train": train_binding, "region_dev": dev_binding,
        "selection": "region-dev-strict-span-f1-then-character-recall-v1",
        "output_dir": str(model_dir.resolve()),
    }


def check_region_existing(identity, model_dir):
    """Region artifacts live together; incompatible/partial/Micro directories refuse.

    No existing weight/metadata file is changed, even for a compatible rerun.
    """
    if model_dir.is_symlink() or (model_dir.exists() and not model_dir.is_dir()):
        raise ValueError("run_output_path_invalid")
    if not model_dir.exists():
        return "fresh"
    required = CHECKPOINT_FILES + ("metrics.json", "tokenizer.json", "tokenizer_config.json")
    if any(not (model_dir / name).is_file() or (model_dir / name).is_symlink() for name in required):
        raise ValueError("run_checkpoint_incomplete")
    info = _read_json(model_dir / "train_info.json")
    labels = _check_identity(info.get("run_identity"), identity, "run_identity_mismatch")
    config = _read_json(model_dir / "config.json")
    if (config.get("id2label") != {str(i): label for i, label in enumerate(labels)} or
            config.get("label2id") != {label: i for i, label in enumerate(labels)} or
            config.get("privacygate_training_mode") != "region"):
        raise ValueError("run_classifier_labels_mismatch")
    _check_identity(_read_json(model_dir / "metrics.json").get("run_identity"), identity,
                    "run_metrics_mismatch")
    return "reuse"


def refusal_code(exc):
    code = str(exc) if isinstance(exc, ValueError) else ""
    return code if code in REFUSAL_CODES else "input_unreadable_or_malformed"


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default errors can echo supplied paths/values.
        self.exit(2, "refused: cli_invalid_arguments\n")


def check_settings(args):
    if args.epochs < 1 or args.batch_size < 1 or not math.isfinite(args.lr) or args.lr <= 0:
        raise ValueError("run_settings_invalid")


def check_run_name(name):
    if not isinstance(name, str) or not RUN_NAME.fullmatch(name) or ".." in name:
        raise ValueError("run_name_invalid")


def _read_json(path):
    """Bounded read of a small JSON object; ValueError(code) otherwise."""
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_META_BYTES + 1)
    except OSError:
        raise ValueError("run_meta_unreadable") from None
    if len(raw) > MAX_META_BYTES:
        raise ValueError("run_meta_too_large")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        raise ValueError("run_meta_unparseable") from None
    if not isinstance(obj, dict):
        raise ValueError("run_meta_schema")
    return obj


def _check_identity(recorded, requested, code):
    if not isinstance(recorded, dict):
        raise ValueError("run_without_provenance")
    labels = recorded.get("labels")
    if (not isinstance(labels, list) or not labels or labels[0] != "O" or
            any(not isinstance(l, str) for l in labels) or len(set(labels)) != len(labels)):
        raise ValueError("run_label_inventory_missing")
    # The cheap preflight defers ONLY labels; all other fields must match, including version and bindings.
    expected = dict(requested)
    if expected["labels"] is None:
        expected["labels"] = labels
    if recorded != expected:
        raise ValueError(code)
    return labels
