"""Reproducibility manifest: hashes and aggregates, never raw examples."""
from collections import Counter
import hashlib

from .build import catalog
from .checks import check_split_isolation, require, summarize
from .spec import (LANGUAGES, MANIFEST, NEGATIVE_KINDS, OUTPUTS, POLICY, POLICY_PATH,
                   ROOT, SEED, SIZES, TWIN_LABELS, pool_manifest)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def generator_hashes():
    sources = [ROOT / "scripts" / "make_train_v2.py"]
    sources.extend(sorted((ROOT / "scripts" / "train_v2").glob("*.py")))
    return {str(path.relative_to(ROOT)): sha256(path) for path in sorted(sources)}


def inspect_datasets(datasets):
    observed = {split: summarize(datasets[split], split) for split in SIZES}
    check_split_isolation(observed)
    for split in SIZES:
        require(observed[split][1] == set(catalog(split)), "template_catalog_coverage")
    require(len(TWIN_LABELS) * 2 >= len(NEGATIVE_KINDS), "negative_template_twin_coverage")
    return observed


def make_manifest(observed):
    outputs, totals = {}, {kind: Counter() for kind in ("label", "language", "family")}
    for split, path in OUTPUTS.items():
        summary = observed[split][0]
        outputs[split] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), **summary}
        for kind, counts in summary["counts"].items():
            totals[kind].update(counts)
    rows = sum(item["rows"] for item in outputs.values())
    clean = sum(item["clean_rows"] for item in outputs.values())
    return {
        "manifest_version": 2, "seed": SEED, "policy": POLICY,
        "policy_sha256": sha256(POLICY_PATH), "synthetic_only": True,
        "row_schema": ["case_id", "family", "gold", "language", "split", "text"],
        "outputs": outputs, "total_rows": rows, "clean_rows": clean, "clean_share": clean / rows,
        "counts": {"split": dict(SIZES), **{k: dict(sorted(v.items())) for k, v in totals.items()}},
        "template_ids": {split: catalog(split) for split in SIZES},
        "value_pool_slices": pool_manifest(),
        "lexical_component_slices": {"train": {"start": 0, "stop": 8},
                                     "dev": {"start": 8, "stop": 16}},
        "generator_sha256s": generator_hashes(),
        "matched_twins": {
            "negative_templates_per_split": len(NEGATIVE_KINDS) * len(LANGUAGES),
            "paired_negative_templates_per_split": len(TWIN_LABELS) * len(LANGUAGES),
            "paired_kinds": list(TWIN_LABELS),
            "labels": dict(TWIN_LABELS),
            "identical_value_payload": True,
        },
        "split_method": "Held-out constructions and family-grouped value slices; no row-level split.",
        "gold_method": "Explicit whole-value placeholder assembly, including repeated occurrences.",
        "verification": "Hashes, structural checks, checksums, split isolation and exact deterministic replay.",
        "excluded_families": ["form-style key/value records", "chat/messaging lines",
                              "email signature blocks", "mixed-language documents",
                              "OCR-like noise inside values"],
    }
