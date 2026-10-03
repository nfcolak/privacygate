#!/usr/bin/env python3
"""Stage 2 local-only audit of openpii-masking-micro-100k + overlap with Mini 10K manifests.

Reuses the Stage 1 row checks, grouping and allocation (scripts/audit_dataset.py, unchanged).
Output contains counts, categories and SHA256 IDs only; never entity values, rows or templates.
"""
import argparse
import collections
import json
import platform
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_dataset as ad  # noqa: E402

ROOT = ad.ROOT
MINI_REPO, MINI_REVISION, MINI_SEED = ad.REPO, ad.REVISION, ad.SEED
MICRO_REPO = "ai4privacy/openpii-masking-micro-100k"
MICRO_REVISION = "f95b4e1539657c3d0047d9ad3f20f26675f22c7d"
MICRO_SEED = "privacygate-stage2-micro-20261001"
MICRO_FIELDS = ad.EXPECTED_FIELDS | {"source_dataset"}
OUT_DOCS, OUT_MAN = "artifacts/data-audit/micro/", "data/manifests/micro/"
MINI_SPLITS = ("train", "dev", "test")


def fetch_artifacts(raw, source, offline):
    ad.REPO, ad.REVISION = MICRO_REPO, MICRO_REVISION
    ad.artifacts(raw, source, offline)


def mini_rows():
    """Recompute Mini 10K selected rows locally (hashes/templates only) and map to manifest splits."""
    import pyarrow.parquet as pq
    source = json.loads((ROOT / "artifacts/data-audit/source.json").read_text())
    ad.REPO, ad.REVISION = MINI_REPO, MINI_REVISION
    raw = ROOT / "data/raw/openpii-masking-mini-10k"
    ad.artifacts(raw, source, True)
    split_of = {}
    manifest_hashes = {"exact": set(), "template": set()}
    for name in MINI_SPLITS + ("excluded",):
        for line in (ROOT / "data/manifests/{}.jsonl".format(name)).read_text().splitlines():
            entry = json.loads(line)
            if name != "excluded":
                split_of[entry["row_id"]] = name
            manifest_hashes["exact"].add(entry["exact_hash"])
            if entry["template_hash"]:
                manifest_hashes["template"].add(entry["template_hash"])
    rows = []
    for artifact in source["artifacts"]:
        if "split" not in artifact:
            continue
        for ordinal, row in enumerate(pq.read_table(raw / artifact["path"]).to_pylist()):
            r = ad.inspect_row(row, artifact, ordinal)
            if r["language"] in ad.LANGUAGES:
                r["mini_split"] = split_of.get(r["row_id"], "quarantined")
                rows.append(r)
    if {r["exact_hash"] for r in rows} != manifest_hashes["exact"] or \
            {r["template_hash"] for r in rows if r["template_hash"]} != manifest_hashes["template"] or len(rows) != 4272:
        raise ValueError("mini_manifest_recompute_mismatch")
    return rows


def read_micro(raw, source):
    rows, extra = [], collections.Counter()
    for artifact in source["artifacts"]:
        if "split" not in artifact:
            continue
        with open(raw / artifact["path"], "rb") as handle:
            for ordinal, line in enumerate(handle):
                row = json.loads(line)
                if set(row) != MICRO_FIELDS:
                    raise ValueError("unexpected_schema")
                extra[ad.category(row["source_dataset"], r"[A-Za-z0-9_.-]{1,40}")] += 1
                rows.append(ad.inspect_row(row, artifact, ordinal))
                if not isinstance(row["uid"], int):
                    rows[-1]["issues"]["uid_not_int"] += 1
    return rows, extra


def near_pairs(items, threshold=85):
    """Same complete prefix-filter Jaccard>=85/100 method as Stage 1, over unique templates.
    items: list of (template, tag). Returns matched pairs of template ids and the templates' order."""
    groups = collections.defaultdict(list)
    for template, tag in items:
        groups[template].append(tag)
    templates = sorted(groups, key=ad.digest)
    sets = [{t[i:i + 5] for i in range(max(0, len(t) - 4))} for t in templates]
    frequency = collections.Counter(s for shingles in sets for s in shingles)
    eligible = sorted((i for i, s in enumerate(sets) if len(s) >= 20), key=lambda i: (len(sets[i]), ad.digest(templates[i])))
    inverted = collections.defaultdict(list)
    pairs, comparisons = [], 0
    for index in eligible:
        shingles = sets[index]
        ordered = sorted(shingles, key=lambda s: (frequency[s], s))
        prefix = ordered[:len(shingles) - (threshold * len(shingles) + 99) // 100 + 1]
        candidates = set()
        for shingle in prefix:
            candidates.update(o for o in inverted[shingle] if 100 * len(sets[o]) >= threshold * len(shingles))
        for other in sorted(candidates):
            comparisons += 1
            overlap = len(shingles & sets[other])
            if 100 * overlap >= threshold * (len(shingles) + len(sets[other]) - overlap):
                pairs.append((templates[index], templates[other]))
        for shingle in prefix:
            inverted[shingle].append(index)
    return pairs, {"unique_templates": len(templates), "eligible_unique_templates": len(eligible),
                   "candidate_pairs_verified": comparisons, "matching_distinct_template_pairs": len(pairs)}


def build(raw, source):
    import pyarrow
    mini = mini_rows()
    ad.REPO, ad.REVISION, ad.SEED = MICRO_REPO, MICRO_REVISION, MICRO_SEED
    rows, source_dataset = read_micro(raw, source)
    n = len(rows)
    uf = ad.UnionFind(n)
    exact = ad.duplicate_stats(rows, "exact_hash", uf)
    template = ad.duplicate_stats(rows, "template_hash", uf)

    # Micro-internal near duplicates + Micro/Mini near overlap in one pass over the union of templates.
    by_template = collections.defaultdict(list)
    for i, r in enumerate(rows):
        if r["template"] is not None:
            by_template[r["template"]].append(i)
    mini_by_template = collections.defaultdict(list)
    for j, r in enumerate(mini):
        if r["template"] is not None:
            mini_by_template[r["template"]].append(j)
    items = [(t, "micro") for t in by_template] + [(t, "mini") for t in mini_by_template if t not in by_template]
    mini_only = {t for t in mini_by_template if t not in by_template}
    pairs, near_stats = near_pairs(items)
    near_micro_pairs = 0
    near_cross_templates = collections.defaultdict(set)  # micro template -> mini template set
    for a, b in pairs:
        a_micro, b_micro = a in by_template, b in by_template
        if a_micro and b_micro:
            near_micro_pairs += 1
            uf.union(by_template[a][0], by_template[b][0])
        for x, y, xm, ym in ((a, b, a_micro, b_micro), (b, a, b_micro, a_micro)):
            if xm and y in mini_by_template:
                near_cross_templates[x].add(y)
    # Micro/Mini overlap per row. Template identity is also reached by exact template matches (not only near).
    mini_exact, mini_template = collections.defaultdict(set), collections.defaultdict(set)
    for r in mini:
        mini_exact[r["exact_hash"]].add(r["mini_split"])
        if r["template_hash"]:
            mini_template[r["template_hash"]].add(r["mini_split"])
    mini_split_of_template = {t: {mini[j]["mini_split"] for j in js} for t, js in mini_by_template.items()}
    overlap = collections.Counter()
    micro_overlap_rows = 0
    for r in rows:
        kinds, splits = [], set()
        if r["exact_hash"] in mini_exact:
            kinds.append("exact"); splits |= mini_exact[r["exact_hash"]]
        if r["template_hash"] in mini_template:
            kinds.append("template"); splits |= mini_template[r["template_hash"]]
        if r["template"] in near_cross_templates:
            kinds.append("near")
            for t in near_cross_templates[r["template"]]:
                splits |= mini_split_of_template[t]
        r["mini_overlap_kinds"], r["mini_overlap_splits"] = kinds, sorted(splits)
        if kinds:
            micro_overlap_rows += 1
            best = kinds[0]
            overlap["best_kind:" + best] += 1
            if r["language"] in ad.LANGUAGES:
                overlap["target_language_rows_with_overlap"] += 1
            for k in kinds:
                overlap["any_kind:" + k] += 1
            for s in splits:
                overlap["touches_mini_{}:{}".format(s, "any")] += 1
                if r["language"] in ad.LANGUAGES:
                    overlap["target_touches_mini_" + s] += 1
    near = {"method": "complete prefix-filter Jaccard over unique normalized masked-template character 5-grams (same as Stage 1)",
            "threshold": "85/100", "minimum_unique_shingles": 20, **near_stats,
            "micro_internal_matching_template_pairs": near_micro_pairs,
            "micro_templates_with_near_mini_match": len(near_cross_templates),
            "limits": "Lexical metric only; short templates excluded; no semantic/translation/generation-source independence proof."}

    quarantine = collections.Counter(reason for r in rows if r["language"] in ad.LANGUAGES for reason in r["excluded"])
    quarantined_rows = sum(bool(r["excluded"]) for r in rows if r["language"] in ad.LANGUAGES)
    # Policy: Micro rows with ANY Mini selected overlap (exact/template/near, any Mini split) are withheld
    # from all Micro splits, so none can reach Micro train/dev/test. Never repaired or deduplicated silently.
    for r in rows:
        if r["language"] in ad.LANGUAGES and r["mini_overlap_kinds"]:
            r["excluded"] = sorted(set(r["excluded"]) | {"mini_overlap_" + k for k in r["mini_overlap_kinds"]})
    overlap_excluded = sum(1 for r in rows if r["language"] in ad.LANGUAGES and r["mini_overlap_kinds"] and not any(
        x in ad.FATAL for x in r["excluded"]))
    manifests, policy = ad.allocate(rows, uf)
    policy.update({"official_validation_retained_as_final": False, "seed": MICRO_SEED, "stage": 2,
                   "row_id": "SHA256(repo_id:revision:artifact_path:zero_based_line_index); uid values never emitted",
                   "mini_overlap_policy": "Rows overlapping any Mini 10K selected row (exact, template or near) are excluded from Micro train/dev/test; reasons mini_overlap_{exact,template,near}",
                   "mini_overlap_additional_excluded_rows": overlap_excluded,
                   "readiness": "provisional structural manifests only; provenance and semantic quality gates remain unresolved"})
    checks = ad.verify_disjoint(manifests)
    id_to_kind = {r["row_id"]: r["mini_overlap_kinds"] for r in rows}
    for name in MINI_SPLITS:
        checks["micro_{}_rows_overlapping_mini".format(name)] = sum(bool(id_to_kind[e["row_id"]]) for e in manifests[name])
        if checks["micro_{}_rows_overlapping_mini".format(name)]:
            raise ValueError("mini_overlap_leak")
    issues, issue_rows, inference = collections.Counter(), collections.Counter(), collections.Counter()
    for r in rows:
        issues.update(r["issues"])
        issue_rows.update(k for k, c in r["issues"].items() if c)
        inference[r["inference_status"]] += 1
    selected = [r for r in rows if r["language"] in ad.LANGUAGES]
    uid_groups = collections.defaultdict(list)
    for r in rows:
        uid_groups[r["uid_hash"]].append(r)
    audit = {"audit_version": 1, "stage": 2, "repo_id": MICRO_REPO, "revision": MICRO_REVISION,
             "source_metadata_sha256": ad.digest(ad.json_bytes(source)),
             "runtime": {"python": platform.python_version(), "pyarrow": pyarrow.__version__},
             "full_rows_examined": n, "source_dataset_field_counts": source_dataset,
             "embedded_split_field_counts": collections.Counter(r["embedded_split"] for r in rows),
             "overall_all_languages": ad.support(rows),
             "target_languages_selected": ad.support(selected),
             "physical_splits": {s: ad.support([r for r in rows if r["source_split"] == s]) for s in ("train", "validation")},
             "annotations": {"spans_examined": sum(r["span_count"] for r in rows), "tokens_examined": sum(r["token_count"] for r in rows),
                             "offset_contract": "Python Unicode code points, zero-based half-open; every annotated value compared locally against the source slice",
                             "issue_events": {k: v for k, v in issues.items() if v}, "rows_with_issue": issue_rows,
                             "structural_check_failure_counts": {k: issues[k] for k in sorted(ad.FATAL)},
                             "unknown_token_rows": sum(r["has_unknown_token"] for r in rows),
                             "token_position_inference": inference,
                             "target_language_quarantined_rows": quarantined_rows,
                             "target_language_quarantine_reason_events": quarantine,
                             "token_alignment_limit": "No published token offsets/tokenizer revision. Literal WordPiece alignment only where exactly reconstructable; mismatches quarantined (not repaired) when they disagree with spans."},
             "duplicate_uid_groups": sum(len(g) > 1 for g in uid_groups.values()),
             "duplicate_uid_groups_with_different_text": sum(len({r["exact_hash"] for r in g}) > 1 for g in uid_groups.values()),
             "duplicates_within_micro": {"exact_source": exact, "normalized_masked_template": template, "near_template": near},
             "mini_10k_overlap": {"mini_selected_rows_compared": len(mini), "micro_rows_all_languages_with_any_overlap": micro_overlap_rows,
                                  "counts": overlap},
             "split_policy": policy, "verification": checks,
             "verdict": "AUDITED_NOT_TRAINING_READY",
             "limitations": ["Structural validity does not prove semantic annotation completeness or correctness.",
                             "Publisher synthetic-only claim is not independently verified; labels/metadata cannot prove absence of real PII.",
                             "Card cites parent 1.5M dataset (not pinned here); Mini 10K cites the 1M dataset; lineage between them is unverified.",
                             "Lexical overlap/group-disjointness is not generation-family or semantic independence.",
                             "No models, training, evaluation, tuning, remote row submission or paid APIs."]}
    outputs = {OUT_DOCS + "audit.json": ad.json_bytes(audit)}
    for name, entries in manifests.items():
        outputs[OUT_MAN + name + ".jsonl"] = b"".join((json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n").encode() for e in entries)
    outputs[OUT_MAN + "split-policy.json"] = ad.json_bytes(policy)
    outputs[OUT_DOCS + "output-hashes.json"] = ad.json_bytes(ad.output_hashes(outputs, ROOT / OUT_DOCS / "output-hashes.json"))
    return outputs, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/openpii-masking-micro-100k")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--verify", action="store_true", help="Offline; recompute everything and byte-compare committed outputs; write nothing")
    args = parser.parse_args()
    try:
        source = json.loads((ROOT / OUT_DOCS / "source.json").read_text())
        fetch_artifacts(args.raw_dir, source, args.offline or args.verify)
        outputs, audit = build(args.raw_dir, source)
        for name, payload in outputs.items():
            target = ROOT / name
            if args.verify:
                if not target.is_file() or target.read_bytes() != payload:
                    raise ValueError("recomputed_output_mismatch:" + name)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
        v = audit["verification"]
        print(json.dumps({"status": "VERIFIED" if args.verify else "AUDITED", "rows": audit["full_rows_examined"],
                          "selected_rows": v["selected_rows"], "excluded_rows": v["excluded_rows"], "allocated_rows": v["allocated_rows"],
                          "quarantined_target_rows": audit["annotations"]["target_language_quarantined_rows"],
                          "mini_overlap": audit["mini_10k_overlap"]["counts"], "verification": v, "verdict": audit["verdict"]}, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__,
                          "safe_reason": str(error) if isinstance(error, ValueError) and re.fullmatch(r"[a-z_]+(?::[a-zA-Z0-9/_.-]+)?", str(error)) else "details_suppressed_to_prevent_raw_data_logging"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
