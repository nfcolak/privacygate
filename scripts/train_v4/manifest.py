"""Hashes and aggregate provenance only; never serialize synthetic values."""
from collections import Counter
import hashlib
from pathlib import Path
import sys

from train_v2.spec import SEED as V2_SEED, pool_manifest
from train_v3.spec import SEED as V3_SEED

from .spec import AGE_POLICY, GRID_AXES, OUTPUTS, POLICY_PATH, ROOT, SEED, SIZES


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def generator_hashes():
    sources = [ROOT / "scripts" / "make_train_v4.py"]
    for package in ("train_v4", "train_v3", "train_v2"):
        sources.extend(sorted((ROOT / "scripts" / package).glob("*.py")))
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)}


def imported_sources():
    result = []
    for name, module in sorted(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if (name.split(".")[0] in ("train_v2", "train_v3") and isinstance(source, str)
                and source.endswith(".py")):
            result.append(str(Path(source).resolve().relative_to(ROOT)))
    return sorted(result)


def make_manifest(observed):
    outputs = {}
    totals = {kind: Counter() for kind in ("label", "language", "family")}
    for split, path in OUTPUTS.items():
        outputs[split] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                          **observed[split][0]}
        for kind, counts in outputs[split]["counts"].items():
            totals[kind].update(counts)
    rows = sum(o["rows"] for o in outputs.values())
    clean = sum(o["clean_rows"] for o in outputs.values())
    return {
        "manifest_version": 4, "seed": SEED, "synthetic_only": True,
        "policy": "privacy-policy-v1", "policy_path": str(POLICY_PATH.relative_to(ROOT)),
        "policy_sha256": sha256(POLICY_PATH), "age_unit_policy_note": AGE_POLICY,
        "outputs": outputs, "total_rows": rows, "clean_rows": clean, "clean_share": clean / rows,
        "counts": {"split": dict(SIZES), **{k: dict(sorted(v.items())) for k, v in totals.items()}},
        "generator_sha256s": generator_hashes(), "imported_generator_sources": imported_sources(),
        "source_method": "Import frozen v3 recipe and v2 constructors; regenerate with a new selection/order seed, stratify families and retain paired rows. No existing dataset is copied or read.",
        "frozen_v2_value_constructor_seed": V2_SEED, "previous_v3_selection_seed": V3_SEED,
        "recipe_sampling": "Per-language clean/positive budgets subtract the full new grid; proportional family sampling keeps matched pairs and every v3 family in both splits.",
        "grid_source": "Value-free diagnosis-v5 diagnosis.md Ranked fix list (development evidence only).",
        "grid_scaling": {s: {"independent_values_per_cell": axes[0], "held_out_paraphrases_per_cell": axes[1]}
                         for s, axes in GRID_AXES.items()},
        "grid_independent_context_twins": True,
        "grid_phone_validation_note": "Valid national-plan versus unknown/unallocated-prefix phones, independently generated in both personal and operational contexts. Pinned-seed phone regimes were checked offline with phonenumbers 9.0.40: 200/200 valid-regime rows valid, 200/200 unknown-regime rows invalid. Generator remains stdlib-only; validator failure never declassifies personal gold.",
        "recipe_value_pool_slices": pool_manifest(),
        "grid_value_pools": "Fresh train/dev lexical pools and disjoint numeric ranges; all grid payloads including clean controls checked for cross-split equality.",
        "template_catalog": {s: {"count": len(observed[s][1]),
                                 "sha256": hashlib.sha256("\n".join(sorted(observed[s][1])).encode()).hexdigest()}
                             for s in SIZES},
        "split_method": "Whole held-out paraphrases and value pools, not row-level random splitting.",
        "blind_set_safety": {"data_or_generators_read": False,
                             "reserved_exact_templates_reused": False,
                             "independent_monolingual_grid_templates": True},
        "verification": {"exact_deterministic_replay": True, "canonical_jsonl": True,
                         "whole_age_value_boundaries": True, "age_cues_excluded": True,
                         "template_ids_disjoint": True, "template_text_disjoint": True,
                         "positive_value_pools_disjoint": True, "grid_value_pools_disjoint": True,
                         "row_text_disjoint": True, "all_grid_cells_per_split": True,
                         "all_recipe_families_per_language_per_split": True,
                         "all_labels_per_split": True, "language_balance_tolerance": 0.05,
                         "required_clean_share": [0.43, 0.47]},
    }
