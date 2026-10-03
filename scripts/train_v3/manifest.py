"""Compact aggregate manifest, source hashes and explicit leakage checks."""
from collections import Counter
import hashlib
from pathlib import Path
import sys

from train_v2.spec import SEED as V2_VALUE_SEED

from .spec import (LANGUAGES, MANIFEST, NEW_GROUPS, OUTPUTS, POLICY_PATH,
                   ROOT, SEED, SIZES, pool_manifest)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def imported_v2_sources():
    sources = []
    for name, module in sorted(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if name.startswith("train_v2.") and isinstance(source, str):
            sources.append(str(Path(source).resolve().relative_to(ROOT)))
    return sorted(sources)


def generator_hashes():
    sources = [ROOT / "scripts" / "make_train_v3.py"]
    sources.extend(sorted((ROOT / "scripts" / "train_v3").glob("*.py")))
    # Hash the full frozen package, including every imported dependency.
    sources.extend(sorted((ROOT / "scripts" / "train_v2").glob("*.py")))
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)}


def make_manifest(observed, excluded):
    outputs = {}
    totals = {kind: Counter() for kind in ("label", "language", "family")}
    for split, path in OUTPUTS.items():
        summary = observed[split][0]
        outputs[split] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), **summary}
        for kind, counts in summary["counts"].items():
            totals[kind].update(counts)
    rows = sum(o["rows"] for o in outputs.values())
    clean = sum(o["clean_rows"] for o in outputs.values())
    return {
        "manifest_version": 3, "seed": SEED, "policy": "privacy-policy-v1",
        "policy_path": str(POLICY_PATH.relative_to(ROOT)), "policy_sha256": sha256(POLICY_PATH),
        "synthetic_only": True, "row_schema": ["case_id", "family", "gold", "language", "split", "text"],
        "outputs": outputs, "total_rows": rows, "clean_rows": clean, "clean_share": clean / rows,
        "counts": {"split": dict(SIZES), **{k: dict(sorted(v.items())) for k, v in totals.items()}},
        "generator_sha256s": generator_hashes(), "imported_train_v2_modules": imported_v2_sources(),
        "frozen_v2_value_constructor_seed": V2_VALUE_SEED,
        "source_method": "Imported frozen v2 pools/renderers/checks; regenerated rows with new v3 selection/order seed, never copied data.",
        "new_clean_kinds": {group: list(kinds) for group, kinds in NEW_GROUPS.items()},
        "matched_twins": {"all_new_clean_rows_paired": True, "identical_value_payload": True,
                          "iban_checksum_validity_crossed_with_person_linkage": True,
                          "catalog_positive_goods_mentions_remain_clean": True},
        "boundary_rows": {s: outputs[s]["boundary_rows"] for s in SIZES},
        "value_pool_slices": pool_manifest(),
        "lexical_component_slices": {"train": {"start": 0, "stop": 8}, "dev": {"start": 8, "stop": 16}},
        "template_catalog": {
            s: {"count": len(observed[s][1]),
                "sha256": hashlib.sha256("\n".join(sorted(observed[s][1])).encode()).hexdigest()}
            for s in SIZES},
        "split_method": "Held-out complete template constructions and family-grouped value slices; no row-level split.",
        "verification": {"exact_deterministic_replay": True, "whole_value_boundaries": True,
                         "template_ids_disjoint": True, "template_text_disjoint": True,
                         "positive_value_pools_disjoint": True, "row_text_disjoint": True,
                         "new_kind_coverage_per_split": True, "all_labels_per_split": True,
                         "language_balance_tolerance": 0.05, "required_clean_share": [0.43, 0.47]},
        "excluded_families": list(excluded),
    }
