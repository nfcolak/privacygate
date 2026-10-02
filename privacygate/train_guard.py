"""Run-reuse guard for train_mbert. Standard library only; raises ValueError(code), never echoes file contents.

A run may be reused (skip training) only if a COMPLETE checkpoint exists whose recorded `run_identity` equals the
identity requested now. Anything incomplete, inconsistent, lacking provenance (all runs made before this guard) or
already holding history files for the run name is refused; nothing is migrated, overwritten or deleted.
"""
import json
import re

IDENTITY_VERSION = "run-identity-v1"
MAX_META_BYTES = 1024 * 1024
RUN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
CHECKPOINT_FILES = ("config.json", "model.safetensors", "train_info.json")


def build_identity(args, model_id, model_revision, max_len, stride, manifests_sha256, neg_binding, model_dir):
    """Requested settings + augmentation binding + data manifests hash + the actual output path (resolved)."""
    return {
        "version": IDENTITY_VERSION, "run": args.run, "model": model_id, "model_revision": model_revision,
        "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed,
        "max_len": max_len, "window_stride_tokens": stride,
        "max_train_rows": args.max_train_rows, "max_dev_rows": args.max_dev_rows,
        "manifests_sha256": manifests_sha256,
        "negative_train": neg_binding,  # None = no augmentation (default); else sha256 + row/language/template counts
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


def check_existing(identity, model_dir, docs_run_dir, results_run_dir):
    """Return "fresh" (nothing exists; safe to train) or "reuse" (complete, identity-matching checkpoint).

    Raises ValueError(code) before any write for every other state. Pure reads; no side effects.
    """
    ck = {n: (model_dir / n).is_file() for n in CHECKPOINT_FILES}
    has_ckpt_dir = _nonempty(model_dir)
    docs_cfg = docs_run_dir / "config.json"
    history = _nonempty(docs_run_dir) or _nonempty(results_run_dir)
    if not has_ckpt_dir:
        if history:
            raise ValueError("run_history_without_checkpoint")  # would overwrite recorded config/metrics
        return "fresh"
    if not all(ck.values()) or any(model_dir.joinpath(n).is_symlink() for n in CHECKPOINT_FILES):
        raise ValueError("run_checkpoint_incomplete")
    info = _read_json(model_dir / "train_info.json")
    if info.get("run_identity") is None:
        raise ValueError("run_without_provenance")  # historical run: compatibility cannot be asserted
    if info["run_identity"] != identity:
        raise ValueError("run_identity_mismatch")
    if docs_cfg.is_file():
        cfg = _read_json(docs_cfg)
        if cfg.get("run_identity") != identity:
            raise ValueError("run_config_mismatch")
    elif history:
        raise ValueError("run_metadata_inconsistent")
    return "reuse"
