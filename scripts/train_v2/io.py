"""Exclusive JSONL generation and read-only full replay verification."""
import json

from .build import build_split
from .checks import require, validate_row
from .manifest import generator_hashes, inspect_datasets, make_manifest, sha256
from .spec import MANIFEST, OUTPUTS, POLICY_PATH, SIZES


def encode(item):
    return json.dumps(item, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n"


def generate():
    targets = [*OUTPUTS.values(), MANIFEST]
    require(not any(path.exists() or path.is_symlink() for path in targets), "output_exists")
    datasets = {split: build_split(split) for split in SIZES}
    observed = inspect_datasets(datasets)
    created = []
    try:
        for split, path in OUTPUTS.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(path)
                for row, _ in datasets[split]:
                    stream.write(encode(row))
        manifest = make_manifest(observed)
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with MANIFEST.open("x", encoding="utf-8", newline="\n") as stream:
            created.append(MANIFEST)
            stream.write(encode(manifest))
    except BaseException:
        # Roll back only files exclusively created by this invocation.
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return manifest


def verify():
    require(MANIFEST.is_file() and all(path.is_file() for path in OUTPUTS.values()), "missing_output")
    stored = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(isinstance(stored, dict), "manifest_schema")
    require(stored.get("generator_sha256s") == generator_hashes(), "generator_hash_mismatch")
    require(stored.get("policy_sha256") == sha256(POLICY_PATH), "policy_hash_mismatch")
    datasets = {}
    for split, path in OUTPUTS.items():
        require(stored.get("outputs", {}).get(split, {}).get("sha256") == sha256(path),
                "data_hash_mismatch")
        expected = build_split(split)
        actual = []
        with path.open(encoding="utf-8", newline="") as stream:
            for i, line in enumerate(stream):
                require(i < len(expected), "excess_rows")
                require(line.endswith("\n") and line.strip(), "jsonl_line")
                row = json.loads(line)
                validate_row(row, split)
                # Equality verifies all whole-value boundaries, repeated mentions,
                # policy linkage, template assignment and pool membership, not
                # merely plausible numeric offsets or checksums.
                require(row == expected[i][0], "whole_value_replay_mismatch")
                require(line == encode(row), "jsonl_canonical_encoding")
                actual.append((row, expected[i][1]))
        require(len(actual) == SIZES[split], "row_count")
        datasets[split] = actual
    observed = inspect_datasets(datasets)
    recomputed = make_manifest(observed)
    require(stored == recomputed, "manifest_aggregate_mismatch")
    return recomputed


def aggregate_message(action, manifest):
    sizes = " ".join(f"{split}={manifest['outputs'][split]['rows']}" for split in SIZES)
    return f"{action} {sizes} clean={manifest['clean_share']:.2%} languages=5"
