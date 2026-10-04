"""Value-free hashes, coverage grids and imported-builder provenance."""
from collections import Counter
import hashlib
from pathlib import Path
import sys

from train_v2.spec import SEED as V2_SEED, pool_manifest
from train_v4.spec import SEED as V4_SEED

from .spec import AGE_POLICY, AXIS_MEANINGS, OUTPUTS, POLICY_PATH, ROOT, SEED, SIZES


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def generator_hashes():
    sources = [ROOT / "scripts" / "make_train_v5.py"]
    for package in ("train_v5", "train_v4", "train_v3", "train_v2"):
        sources.extend(sorted((ROOT / "scripts" / package).glob("*.py")))
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)}


def imported_sources():
    paths = set()
    for name, module in sorted(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if (name.split(".")[0] in ("train_v2", "train_v3", "train_v4") and
                isinstance(source, str) and source.endswith(".py")):
            paths.add(str(Path(source).resolve().relative_to(ROOT)))
    return sorted(paths)


def make_manifest(observed):
    outputs, totals = {}, {kind: Counter() for kind in ("label", "language", "family")}
    for split, path in OUTPUTS.items():
        outputs[split] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), **observed[split][0]}
        for kind, counts in outputs[split]["counts"].items():
            totals[kind].update(counts)
    clean = sum(o["clean_rows"] for o in outputs.values())
    rows = sum(SIZES.values())
    return {
        "manifest_version": 5, "seed": SEED, "synthetic_only": True,
        "policy": "privacy-policy-v1", "policy_path": str(POLICY_PATH.relative_to(ROOT)),
        "policy_sha256": sha256(POLICY_PATH), "age_unit_policy_note": AGE_POLICY,
        "outputs": outputs, "total_rows": rows, "clean_rows": clean, "clean_share": clean / rows,
        "counts": {"split": dict(SIZES), **{kind: dict(sorted(c.items())) for kind, c in totals.items()}},
        "generator_sha256s": generator_hashes(), "imported_generator_sources": imported_sources(),
        "source_method": "Import v4/v3/v2 builders and regenerate every v4 family with a new seed. "
                         "Process-local selection/value/ordering seeds are restored after use. No previous dataset is read or copied.",
        "previous_v4_seed": V4_SEED, "frozen_v2_value_constructor_seed": V2_SEED,
        "recipe_value_pool_slices": pool_manifest(),
        "recipe_sampling": "Per-language 45% clean budgets subtract both complete grids; "
                           "proportional family sampling retains v3 matched pairs and every v4 recipe family.",
        "grid_source": "Value-free diagnosis-v6 Ranked fixes (ii), development evidence only.",
        "grid_requested_train_counts": {"positive_rows": 1680, "clean_rows": 1680},
        "grid_axes": AXIS_MEANINGS,
        "grid_scaling": "Train covers the exact 1680-positive/1680-clean diagnosis grid. "
                        "Dev retains all layout/scope families with 2 age/name and 1 other variant per cell (450 twins).",
        "grid_value_pools": "Independent invented names, streets, towns and disjoint cardinal/date/serial ranges. "
                            "All new payloads including clean/malformed controls checked for cross-split equality.",
        "template_catalog": {split: {"count": len(observed[split][1]),
                                    "sha256": hashlib.sha256("\n".join(sorted(observed[split][1])).encode()).hexdigest(),
                                    "grammar_count": len(observed[split][2]),
                                    "grammar_sha256": hashlib.sha256("\n".join(sorted(observed[split][2])).encode()).hexdigest()}
                             for split in SIZES},
        "split_method": "Held-out grammar: dev uses question/answer ages, postposed signer/ownership evidence, "
                        "transposed/nested records and delivery instructions. Regenerated v4 also retains its held-out dev templates.",
        "data_read_scope": {"previous_jsonl_read": False, "stress_generators_imported": False,
                            "blind_data_read": False, "new_grid_independent_vocabulary": True},
        "verification": {"exact_deterministic_replay": True, "canonical_jsonl": True,
                         "all_grid_cells_per_split": True, "whole_semantic_age_boundaries": True,
                         "age_cues_excluded": True, "balanced_phone_boundary_annotation": True,
                         "template_ids_disjoint": True, "template_grammars_disjoint": True,
                         "positive_value_pools_disjoint": True, "new_grid_payloads_disjoint": True,
                         "row_text_disjoint": True, "all_recipe_families_per_language_per_split": True,
                         "all_labels_per_split": True, "language_balance_tolerance": 0.05,
                         "required_clean_share": [0.43, 0.47]},
    }
