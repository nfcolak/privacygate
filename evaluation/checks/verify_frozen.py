#!/usr/bin/env python3
"""Verify frozen generators with runtime-only path adaptation; never rewrite sources.

Manifests keep the paths recorded when each set was frozen. Generators moved to
data/generators/ and ignored data moved to data/local/; this module maps the
current layout onto the recorded paths at runtime only. Retired sets (v1-v6,
window-cut, challenge, positives, negatives, train-v2..v5) live in git history.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = ROOT / "data/generators"
LOCAL = ROOT / "data/local"
V7_GENERATOR = GENERATORS / "make_masking_stress_v7.py"
V7_DATA = LOCAL / "augmentation/masking-stress-v7.jsonl"
V7_MANIFEST = ROOT / "data/manifests/masking-stress-v7.json"
POLICY = ROOT / "configs/privacy-policy-v1.json"


def load_v7_generator():
    """Frozen v7 generator bytes, executed with the current repository paths.

    Its manifest binds the generator's own sha256, so the file cannot be edited.
    Only module globals are redirected; the recorded dataset_path is restored
    after recomputation so the stored manifest bytes stay valid.
    """
    spec = importlib.util.spec_from_file_location("_frozen_v7", V7_GENERATOR)
    if spec is None or spec.loader is None:
        raise ValueError("v7_generator_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.DATA, module.MANIFEST, module.POLICY = ROOT, V7_DATA, V7_MANIFEST, POLICY
    recorded = json.loads(V7_MANIFEST.read_bytes())["dataset_path"]
    original = module.manifest_for

    def manifest_for(rows, formats):
        manifest = original(rows, formats)
        if Path(manifest["dataset_path"]).name != Path(recorded).name:
            raise ValueError("v7_dataset_name_changed")
        manifest["dataset_path"] = recorded
        return manifest

    module.manifest_for = manifest_for
    return module


def verify_v7():
    rows, manifest = load_v7_generator().verify(V7_DATA)
    print("v7 rows={} positive={} clean={}".format(
        len(rows), manifest["counts"]["positive_rows"], manifest["counts"]["clean_rows"]))


def verify_train_v6():
    """Full replay through the generator's own verify(); recorded input/output
    path strings (absolute owner paths at generation time) are restored for the
    comparison only when the file names match. Hashes, bytes and rows still bind."""
    if str(GENERATORS) not in sys.path:
        sys.path.insert(0, str(GENERATORS))
    from train_v6 import io, spec
    stored = json.loads(spec.MANIFEST.read_text(encoding="utf-8"))
    original = io.make_manifest

    def make_manifest(datasets, origins, metadata):
        manifest = original(datasets, origins, metadata)
        for section in ("inputs", "outputs"):
            for key, record in manifest[section].items():
                recorded = stored[section][key]["path"]
                if Path(recorded).name != Path(record["path"]).name:
                    raise ValueError("train_v6_input_name_changed")
                record["path"] = recorded
        return manifest

    io.make_manifest = make_manifest
    try:
        manifest = io.verify()
    finally:
        io.make_manifest = original
    print("train-v6 train={} dev={}".format(manifest["outputs"]["train"]["rows"], manifest["outputs"]["dev"]["rows"]))


def _train_v6_inputs():
    if str(GENERATORS) not in sys.path:
        sys.path.insert(0, str(GENERATORS))
    from train_v6 import spec
    files = [*spec.OUTPUTS.values(), spec.V5, spec.SCORER]
    files += [spec.DATA / (language + "_" + split + ".parquet")
              for language in spec.LANGUAGES for split in ("train", "test")]
    return files


SETS = {
    "v7": (verify_v7, lambda: [V7_DATA]),
    "train-v6": (verify_train_v6, _train_v6_inputs),
}


def verify_one(name):
    verify, inputs = SETS[name]
    if not all(path.is_file() for path in inputs()):
        print(f"{name} SKIPPED_NO_DATA")
        return 0
    try:
        verify()
    except Exception:
        print(f"{name} FAILED frozen_verify_error", file=sys.stderr)
        return 1
    print(f"{name} VERIFIED")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", choices=(*SETS, "all"))
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    selected = SETS if args.set == "all" else (args.set,)
    results = [verify_one(name) for name in selected]
    return int(any(results))


if __name__ == "__main__":
    raise SystemExit(main())
