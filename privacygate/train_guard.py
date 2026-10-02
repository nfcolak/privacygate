"""Run-reuse guard for train_mbert. Standard library only; fixed value-free errors.

Only COMPLETE provenance-compatible checkpoints may be reused. Label inventory is deferred
until ALL Micro train rows are loaded, then checked again before model work or output writes.
Historical outputs are never migrated, rewritten or deleted.
"""
import argparse
import json
import math
import re

from .augmentation_data import POSITIVE_SCHEMA_VERSION, POSITIVE_SOURCE_VERSION
from .window_alignment import ALIGNMENT_POLICY, ALIGNMENT_SOURCE_VERSION

IDENTITY_VERSION = "run-identity-v3"
# Bound into the run identity: checkpoints trained under another windowing are never silently reused.
ENCODER_VERSION = "sliding-windows-full-coverage-v1"
MAX_META_BYTES = 1024 * 1024
RUN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
CHECKPOINT_FILES = ("config.json", "model.safetensors", "train_info.json")
# Only known literal codes may leave a validation boundary; unexpected parser/path errors are redacted.
REFUSAL_CODES = frozenset(
    ["pos_" + c for c in ("bad_allowed_split row_count bad_forbid_ids schema field_type split_mismatch language "
      "text_bounds row_id template_id duplicate_text annotation_count mask_schema mask_type label span_bounds "
      "span_overlap template_language path not_regular_file file_too_large line_too_long unparseable "
      "train_dev_text_overlap train_dev_template_overlap dev_label_not_in_train").split()] +
    ["neg_" + c for c in ("row_count schema field_type split_not_train language annotations_not_empty text_bounds "
      "row_id template_id contains_digit duplicate_text template_language path not_regular_file file_too_large "
      "line_too_long unparseable").split()] +
    ["run_" + c for c in ("settings_invalid name_invalid meta_unreadable meta_too_large meta_unparseable meta_schema "
      "without_provenance label_inventory_missing output_path_invalid history_without_checkpoint checkpoint_incomplete "
      "identity_mismatch classifier_labels_mismatch metadata_inconsistent config_mismatch metrics_mismatch").split()] +
    ["micro_manifest_malformed", "dev_label_not_in_train", "rows_missing_from_raw"])


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
    if any(n is not None and n < 1 for n in (args.max_train_rows, args.max_dev_rows)):
        raise ValueError("run_settings_invalid")


def build_identity(args, model_id, model_revision, max_len, stride, manifests_sha256, neg_binding, model_dir,
                   positive_train=None, positive_dev=None, labels=None):
    """Settings, separate input bindings, schema/source version, ordered labels and resolved output path."""
    return {
        "version": IDENTITY_VERSION, "run": args.run, "model": model_id, "model_revision": model_revision,
        "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed,
        "max_len": max_len, "window_stride_tokens": stride, "encoder_version": ENCODER_VERSION,
        "max_train_rows": args.max_train_rows, "max_dev_rows": args.max_dev_rows,
        "manifests_sha256": manifests_sha256,
        "negative_train": neg_binding,
        "positive_train": positive_train, "positive_dev": positive_dev,
        "positive_schema_version": POSITIVE_SCHEMA_VERSION,
        "positive_source_version": POSITIVE_SOURCE_VERSION,
        "alignment_policy": ALIGNMENT_POLICY,
        "alignment_source_version": ALIGNMENT_SOURCE_VERSION,
        "labels": list(labels) if labels is not None else None,
        "output_dir": str(model_dir.resolve()),
    }


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


def _nonempty(path):
    return path.is_dir() and any(path.iterdir())


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


def check_existing(identity, model_dir, docs_run_dir, results_run_dir):
    """Return fresh/reuse; compare known labels strictly, otherwise defer their final comparison.

    Pure reads, no model imports. Every existing metadata file must have matching provenance.
    """
    for path in (model_dir, docs_run_dir, results_run_dir):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError("run_output_path_invalid")
    ck = {n: (model_dir / n).is_file() for n in CHECKPOINT_FILES}
    has_ckpt_dir = _nonempty(model_dir)
    docs_cfg = docs_run_dir / "config.json"
    history = _nonempty(docs_run_dir) or _nonempty(results_run_dir)
    if not has_ckpt_dir:
        if history:
            raise ValueError("run_history_without_checkpoint")
        return "fresh"
    if not all(ck.values()) or any(model_dir.joinpath(n).is_symlink() for n in CHECKPOINT_FILES):
        raise ValueError("run_checkpoint_incomplete")
    info = _read_json(model_dir / "train_info.json")
    labels = _check_identity(info.get("run_identity"), identity, "run_identity_mismatch")
    classifier = _read_json(model_dir / "config.json")
    if (classifier.get("id2label") != {str(i): l for i, l in enumerate(labels)} or
            classifier.get("label2id") != {l: i for i, l in enumerate(labels)}):
        raise ValueError("run_classifier_labels_mismatch")
    if docs_cfg.is_file():
        if docs_cfg.is_symlink():
            raise ValueError("run_metadata_inconsistent")
        cfg = _read_json(docs_cfg)
        _check_identity(cfg.get("run_identity"), identity, "run_config_mismatch")
        if cfg.get("labels") != labels:
            raise ValueError("run_classifier_labels_mismatch")
    elif history:
        raise ValueError("run_metadata_inconsistent")
    for base in (docs_run_dir, results_run_dir):
        metrics = base / "metrics.json"
        if metrics.exists() or metrics.is_symlink():
            if not metrics.is_file() or metrics.is_symlink():
                raise ValueError("run_metadata_inconsistent")
            _check_identity(_read_json(metrics).get("run_identity"), identity, "run_metrics_mismatch")
    return "reuse"
