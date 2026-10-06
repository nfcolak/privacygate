"""Build the single zip that colab/train_region_v6.ipynb trains from (run on the Mac).

python -m privacygate.training.colab_bundle --out /path/colab-bundle-v6.zip
    [--data-dir data/local/augmentation] [--manifest data/manifests/train-v6.json]

Contents: the privacygate package, requirements-train.txt, pyproject.toml, the
train-v6 manifest, train-v6.jsonl, dev-v6-ext.jsonl and SHA256SUMS. Data hashes
must match the manifest before anything is written. Nothing from data/raw/
(OpenPII), models/ or any checkpoint folder is ever included. Prints counts and
hashes only, never dataset rows.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/train-v6.json"
DATA_DIR = ROOT / "data/local/augmentation"
DATA_FILES = {"train": "train-v6.jsonl", "dev": "dev-v6-ext.jsonl"}
# Archive layout mirrors the repository, so the notebook runs the same commands.
ARCHIVE_DATA = "data/local/augmentation/"
ARCHIVE_MANIFEST = "data/manifests/train-v6.json"
CODE_FILES = ("requirements-train.txt", "pyproject.toml")
FORBIDDEN_DIRS = (ROOT / "data/raw", ROOT / "models")
CHECKPOINT_MARKERS = ("model.safetensors", "pytorch_model.bin", "train_info.json")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


class BundleError(ValueError):
    """Fixed, value-free refusal codes."""


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def admit(path):
    """Refuse OpenPII raw data, model folders and checkpoint-looking folders."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise BundleError("bundle_source_not_regular_file")
    resolved = path.resolve()
    for forbidden in FORBIDDEN_DIRS:
        if resolved == forbidden.resolve() or forbidden.resolve() in resolved.parents:
            raise BundleError("bundle_forbidden_source")
    for parent in resolved.parents:
        if any((parent / marker).is_file() for marker in CHECKPOINT_MARKERS):
            raise BundleError("bundle_forbidden_source")
    return path.read_bytes()


def code_sources():
    files = sorted(p for p in (ROOT / "privacygate").rglob("*.py") if "__pycache__" not in p.parts)
    return [(str(p.relative_to(ROOT)), p) for p in files] + [(name, ROOT / name) for name in CODE_FILES]


def manifest_hashes(raw):
    manifest = json.loads(raw)
    outputs = manifest.get("outputs") if isinstance(manifest, dict) else None
    if not isinstance(outputs, dict):
        raise BundleError("bundle_manifest_schema")
    hashes = {}
    for split, name in DATA_FILES.items():
        record = outputs.get(split)
        if not isinstance(record, dict) or Path(str(record.get("path", ""))).name != name:
            raise BundleError("bundle_manifest_schema")
        hashes[split] = record.get("sha256")
    return hashes


def build(out, data_dir=DATA_DIR, manifest=MANIFEST):
    out = Path(out)
    if out.exists() or out.is_symlink():
        raise BundleError("bundle_output_exists")
    manifest_raw = admit(manifest)
    expected = manifest_hashes(manifest_raw)
    entries = [(name, admit(path)) for name, path in code_sources()]
    entries.append((ARCHIVE_MANIFEST, manifest_raw))
    for split, name in DATA_FILES.items():
        raw = admit(Path(data_dir) / name)
        if sha256_bytes(raw) != expected[split]:
            raise BundleError("bundle_data_hash_mismatch")
        entries.append((ARCHIVE_DATA + name, raw))
    names = [name for name, _ in entries]
    if len(set(names)) != len(names) or any(n.startswith(("data/raw/", "models/")) for n in names):
        raise BundleError("bundle_layout_invalid")
    sums = "".join("{}  {}\n".format(sha256_bytes(raw), name) for name, raw in entries)
    out.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in entries + [("SHA256SUMS", sums.encode())]:
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, raw)
    with out.open("xb") as handle:
        handle.write(buffer.getvalue())
    return {"files": len(entries), "bundle_sha256": sha256_bytes(buffer.getvalue()),
            "data_sha256": expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True, help="zip to create; refuses to overwrite")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="folder with train-v6.jsonl and dev-v6-ext.jsonl")
    parser.add_argument("--manifest", type=Path, default=MANIFEST, help="train-v6 manifest binding both files")
    args = parser.parse_args()
    try:
        result = build(args.out, args.data_dir, args.manifest)
    except BundleError as error:
        print("refused: {}".format(error), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("refused: bundle_input_unreadable", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
