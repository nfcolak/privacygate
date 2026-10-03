#!/usr/bin/env python3
"""Verify frozen generators with runtime-only paths; never rewrite their sources."""
import argparse
import importlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path(
    "/Users/necatifurkancolak/AI-Workplace/Obsidian Vaults/ProjectOS/"
    "10-Projects/privacygate/Work/repo-notes/docs/privacy-policy-v1.md"
)
SETS = {
    "v1": ("make_masking_stress", ("augmentation/masking-stress-dev.jsonl",)),
    "v2": ("make_masking_stress_v2", ("augmentation/masking-stress-v2-dev.jsonl",)),
    "v3": ("make_masking_stress_v3", ("augmentation/masking-stress-v3-dev.jsonl",)),
    "v4": ("make_masking_stress_v4", ("augmentation/masking-stress-v4.jsonl",)),
    "window-cut": ("make_window_cut_fixture", ("augmentation/window-cut-dev.jsonl",)),
    "challenge": ("make_challenge", ("challenge/dev.jsonl", "challenge/test.jsonl")),
    "positives": ("make_positives", ("augmentation/positive-train.jsonl", "augmentation/positive-dev.jsonl")),
    "negatives": ("make_negatives", ("augmentation/negatives-train.jsonl",)),
    "train-v2": ("make_train_v2", ("augmentation/train-v2.jsonl", "augmentation/dev-v2.jsonl")),
}


class ChallengeRoot(type(ROOT)):
    """Challenge has a local manifest path, not a module-level MANIFEST constant."""

    def __truediv__(self, other):
        if str(other) == "docs/challenge/manifest.json":
            return ROOT / "artifacts/challenge/manifest.json"
        return Path(self) / other


def redirect_paths(module):
    for name, value in tuple(vars(module).items()):
        if not name.isupper() or not isinstance(value, Path):
            continue
        if name == "POLICY_PATH" and module.__name__.startswith("train_v2."):
            setattr(module, name, POLICY_PATH)
            continue
        try:
            relative = value.relative_to(ROOT) if value.is_absolute() else value
        except ValueError:
            continue
        if relative.parts and relative.parts[0] == "docs":
            moved = Path("artifacts", *relative.parts[1:])
            setattr(module, name, ROOT / moved if value.is_absolute() else moved)


def verify_one(name):
    module_name, data_files = SETS[name]
    if not all((ROOT / "data" / path).is_file() for path in data_files):
        print(f"{name} SKIPPED_NO_DATA")
        return 0
    if name == "train-v2" and not POLICY_PATH.is_file():
        print("train-v2 FAILED frozen_policy_missing", file=sys.stderr)
        return 1
    argv = sys.argv
    try:
        module = importlib.import_module(module_name)
        redirect_paths(module)
        if name == "challenge":
            setattr(module, "ROOT", ChallengeRoot(ROOT))
        if name == "train-v2":
            for loaded_name, loaded in tuple(sys.modules.items()):
                if loaded_name.startswith("train_v2.") and loaded is not None:
                    redirect_paths(loaded)
        sys.argv = [str(ROOT / "scripts" / (module_name + ".py")), "--verify"]
        result = module.main()
        if result != 0:
            print(f"{name} FAILED", file=sys.stderr)
            return 1
        print(f"{name} VERIFIED")
        return 0
    except Exception:
        print(f"{name} FAILED frozen_verify_error", file=sys.stderr)
        return 1
    finally:
        sys.argv = argv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", choices=(*SETS, "all"))
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    selected = SETS if args.set == "all" else (args.set,)
    results = [verify_one(name) for name in selected]
    return int(any(results))


if __name__ == "__main__":
    raise SystemExit(main())
