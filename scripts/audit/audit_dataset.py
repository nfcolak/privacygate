#!/usr/bin/env python3
"""Local-only full-row audit. Output contains counts, categories and SHA256 IDs only."""
import argparse
import collections
import hashlib
import json
import math
import platform
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "ai4privacy/openpii-masking-mini-10k"
REVISION = "ad851605dfd3c1a3fefe51c8d8f1cc0e4a6853d0"
LANGUAGES = ("en", "de", "fr", "it", "es")
LABELS = frozenset("AGE BUILDINGNUM CITY CREDITCARDNUMBER DATE DRIVERLICENSENUM EMAIL GENDER GIVENNAME IDCARDNUM PASSPORTNUM SEX SOCIALNUM STREET SURNAME TAXNUM TELEPHONENUM TITLE ZIPCODE".split())
SEED = "privacygate-stage1-20260930"
EXPECTED_FIELDS = {"source_text", "masked_text", "privacy_mask", "split", "uid", "language", "region", "script", "mbert_tokens", "mbert_token_classes"}
FATAL = {"source_invalid", "empty_text", "annotation_list_invalid", "span_record_invalid", "span_bounds_invalid", "span_value_mismatch", "span_label_invalid", "span_overlap", "label_index_invalid", "token_list_invalid", "token_length_mismatch", "bio_class_invalid", "bio_transition_invalid", "bio_entity_count_mismatch", "inferred_bio_entity_boundary_mismatch", "inferred_token_span_label_mismatch", "inferred_token_crosses_span_boundary"}


def digest(value):
    if not isinstance(value, bytes):
        value = str(value).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def category(value, pattern):
    # Unknown categories must not leak unexpected free text.
    if isinstance(value, str) and re.fullmatch(pattern, value):
        return value
    return "invalid_sha256_" + digest(repr(value))


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def artifacts(raw, source, offline):
    if source["repo_id"] != REPO or source["revision"] != REVISION:
        raise ValueError("source_identity_mismatch")
    for item in source["artifacts"]:
        path = raw / item["path"]
        if not path.is_file():
            if offline:
                raise ValueError("offline_artifact_missing")
            path.parent.mkdir(parents=True, exist_ok=True)
            url = "https://huggingface.co/datasets/{}/resolve/{}/{}".format(REPO, REVISION, item["path"])
            # No local data is ever included in outbound requests.
            with urllib.request.urlopen(url, timeout=180) as response:
                payload = response.read()
            if len(payload) != item["bytes"] or digest(payload) != item["sha256"]:
                raise ValueError("download_hash_mismatch")
            path.write_bytes(payload)
        payload = path.read_bytes()
        if len(payload) != item["bytes"] or digest(payload) != item["sha256"]:
            raise ValueError("local_artifact_hash_mismatch")


def inspect_row(row, artifact, ordinal):
    issues = collections.Counter()
    text = row["source_text"]
    if not isinstance(text, str):
        issues["source_invalid"] += 1
        text = ""
    if not text.strip():
        issues["empty_text"] += 1
    annotations = row["privacy_mask"]
    if not isinstance(annotations, list):
        issues["annotation_list_invalid"] += 1
        annotations = []
    labels = collections.Counter()
    spans = []
    for annotation in annotations:
        if not isinstance(annotation, dict):
            issues["span_record_invalid"] += 1
            continue
        label = annotation.get("label")
        if label not in LABELS:
            issues["span_label_invalid"] += 1
            label = "invalid_sha256_" + digest(repr(label))
        labels[label] += 1
        start, end = annotation.get("start"), annotation.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            issues["span_bounds_invalid"] += 1
            continue
        if text[start:end] != annotation.get("value"):
            issues["span_value_mismatch"] += 1
        index = annotation.get("label_index")
        if type(index) is not int or index < 1:
            issues["label_index_invalid"] += 1
        spans.append((start, end, label, index))
    spans.sort()
    max_end = -1
    for start, end, _, _ in spans:
        if start < max_end:
            issues["span_overlap"] += 1
        max_end = max(max_end, end)
    # Explicit contract: Python Unicode code-point, half-open offsets. Never repair.
    annotation_ok = not any(issues[k] for k in FATAL if not k.startswith(("token_", "bio_")))
    template = None
    if annotation_ok:
        pieces, masked, position = [], [], 0
        for start, end, label, index in spans:
            pieces += [text[position:start], " [" + label + "] "]
            masked += [text[position:start], "[{}_{}]".format(label, index)]
            position = end
        pieces.append(text[position:])
        masked.append(text[position:])
        template = normalized("".join(pieces))
        if "".join(masked) != row["masked_text"]:
            issues["masked_text_reconstruction_mismatch"] += 1
    tokens, classes = row["mbert_tokens"], row["mbert_token_classes"]
    if (not isinstance(tokens, list) or not isinstance(classes, list)
            or not all(isinstance(t, str) and t for t in tokens)
            or not all(isinstance(c, str) for c in classes)):
        issues["token_list_invalid"] += 1
        tokens, classes = [], []
    if len(tokens) != len(classes):
        issues["token_length_mismatch"] += 1
    if not tokens:
        issues["token_list_invalid"] += 1
    previous, begins = "O", collections.Counter()
    class_counts = collections.Counter()
    for cls in classes:
        if cls == "O":
            class_counts[cls] += 1
        elif re.fullmatch(r"[BI]-[A-Z]+", cls) and cls[2:] in LABELS:
            class_counts[cls] += 1
            if cls.startswith("B-"):
                begins[cls[2:]] += 1
            elif previous not in ("B-" + cls[2:], "I-" + cls[2:]):
                issues["bio_transition_invalid"] += 1
        else:
            issues["bio_class_invalid"] += 1
            class_counts["invalid_sha256_" + digest(cls)] += 1
        previous = cls
    if begins != labels:
        issues["bio_entity_count_mismatch"] += 1
    # No tokenizer/vocabulary/model download. Infer positions ONLY for exact
    # consecutive WordPiece pieces; skip whitespace, never search past text.
    cursor, positions, inference_failure = 0, [], None
    for token in tokens:
        if token == "[UNK]":
            inference_failure = "unknown_token"
            break
        piece = token[2:] if token.startswith("##") else token
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if not text.startswith(piece, cursor):
            inference_failure = "literal_reconstruction_failure"
            break
        positions.append((cursor, cursor + len(piece)))
        cursor += len(piece)
    if inference_failure is None and text[cursor:].strip():
        inference_failure = "uncovered_tail"
    inferred_comparable = inference_failure is None and len(positions) == len(classes) and annotation_ok
    if inferred_comparable:
        inferred_entities = []
        for (start, end), cls in zip(positions, classes):
            if cls.startswith("B-"):
                inferred_entities.append([start, end, cls[2:]])
            elif cls.startswith("I-") and inferred_entities and inferred_entities[-1][2] == cls[2:]:
                inferred_entities[-1][1] = end
        if sorted(tuple(entity) for entity in inferred_entities) != sorted((a, b, label) for a, b, label, _ in spans):
            issues["inferred_bio_entity_boundary_mismatch"] += 1
        counts = collections.Counter()
        for (start, end), cls in zip(positions, classes):
            overlaps = [label for a, b, label, _ in spans if start < b and end > a]
            actual = None if cls == "O" else cls[2:]
            if actual != (overlaps[0] if len(overlaps) == 1 else None) or len(overlaps) > 1:
                issues["inferred_token_span_label_mismatch"] += 1
            for a, b, label, _ in spans:
                if (start < a < end) or (start < b < end):
                    issues["inferred_token_crosses_span_boundary"] += 1
            counts[cls] += 1
    if row["split"] != artifact["split"]:
        issues["row_split_field_mismatch"] += 1
    excluded = sorted(k for k in FATAL if issues[k])
    return {
        "row_id": digest("{}:{}:{}:{}".format(REPO, REVISION, artifact["path"], ordinal)),
        "source_split": artifact["split"], "language": category(row["language"], r"[a-z]{2}"),
        "region": category(row["region"], r"[A-Z]{2}"), "script": category(row["script"], r"[A-Z][a-z]{3}"),
        "uid_hash": digest("uid:" + str(row["uid"])),
        "exact_hash": digest(text), "template_hash": digest(template) if template is not None else None,
        "template": template, "labels": labels, "class_counts": class_counts,
        "issues": issues, "excluded": excluded, "span_count": len(annotations), "token_count": len(tokens),
        "empty_annotations": not annotations, "target_free": not labels,
        "email_free": not labels["EMAIL"], "inference_status": inference_failure or "exact_literal_match",
        "inferred_comparable": inferred_comparable, "has_unknown_token": "[UNK]" in tokens,
        "empty_tokens": not tokens,
        "embedded_split": category(row["split"], r"train|validation|test"),
    }


class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def root(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left, right):
        a, b = self.root(left), self.root(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def duplicate_stats(rows, field, uf):
    groups = collections.defaultdict(list)
    for index, row in enumerate(rows):
        if row[field] is not None:
            groups[row[field]].append(index)
    duplicates = [indices for indices in groups.values() if len(indices) > 1]
    for indices in duplicates:
        for index in indices[1:]:
            uf.union(indices[0], index)
    cross = [g for g in duplicates if len({rows[i]["source_split"] for i in g}) > 1]
    pairs = sum(sum(rows[i]["source_split"] == "train" for i in g) * sum(rows[i]["source_split"] == "validation" for i in g) for g in cross)
    return {"duplicate_groups": len(duplicates), "rows_in_duplicate_groups": sum(map(len, duplicates)),
            "extra_duplicate_rows": sum(len(g) - 1 for g in duplicates),
            "cross_official_split_groups": len(cross), "cross_official_split_rows": sum(map(len, cross)),
            "cross_official_split_pairs": pairs, "largest_group_rows": max(map(len, groups.values()), default=0)}


def near_duplicates(rows, uf):
    # Complete prefix-filter candidates for Jaccard >= 85/100. No stochastic
    # candidate sampling; globally frequency-sorted unique character 5-grams.
    groups = collections.defaultdict(list)
    for index, row in enumerate(rows):
        if row["template"] is not None:
            groups[row["template"]].append(index)
    templates = sorted(groups, key=digest)
    sets = [{text[i:i + 5] for i in range(max(0, len(text) - 4))} for text in templates]
    frequency = collections.Counter(s for shingles in sets for s in shingles)
    eligible = [i for i, shingles in enumerate(sets) if len(shingles) >= 20]
    eligible.sort(key=lambda i: (len(sets[i]), digest(templates[i])))
    inverted = collections.defaultdict(list)
    comparisons, matched, cross_pairs, max_candidate = 0, 0, 0, 0
    for index in eligible:
        shingles = sets[index]
        ordered = sorted(shingles, key=lambda s: (frequency[s], s))
        prefix_length = len(shingles) - (85 * len(shingles) + 99) // 100 + 1
        prefix = ordered[:prefix_length]
        candidates = set()
        for shingle in prefix:
            candidates.update(other for other in inverted[shingle] if 100 * len(sets[other]) >= 85 * len(shingles))
        max_candidate = max(max_candidate, len(candidates))
        for other in sorted(candidates):
            comparisons += 1
            overlap = len(shingles & sets[other])
            union = len(shingles) + len(sets[other]) - overlap
            if 100 * overlap >= 85 * union:
                matched += 1
                left, right = groups[templates[index]], groups[templates[other]]
                uf.union(left[0], right[0])
                ltrain = sum(rows[i]["source_split"] == "train" for i in left)
                rtrain = sum(rows[i]["source_split"] == "train" for i in right)
                cross_pairs += ltrain * (len(right) - rtrain) + rtrain * (len(left) - ltrain)
        for shingle in prefix:
            inverted[shingle].append(index)
    return {"method": "complete prefix-filter Jaccard over unique normalized masked-template character 5-grams",
            "threshold": "85/100", "minimum_unique_shingles": 20, "unique_templates": len(templates),
            "eligible_unique_templates": len(eligible), "excluded_short_unique_templates": len(templates) - len(eligible),
            "candidate_pairs_verified": comparisons, "matching_distinct_template_pairs": matched,
            "matching_cross_official_split_row_pairs": cross_pairs, "largest_candidate_set": max_candidate,
            "grouped_for_allocation": True,
            "limits": "Lexical metric only; no semantic, translated, unannotated-entity or generation-source independence proof. Short templates excluded. Transitive groups can contain endpoints below threshold."}


def support(rows):
    language, labels, row_labels, regions, scripts = (collections.Counter() for _ in range(5))
    per_language = {}
    for row in rows:
        lang = row["language"]
        language[lang] += 1
        labels.update(row["labels"])
        row_labels.update(row["labels"].keys())
        regions[row["region"]] += 1
        scripts[row["script"]] += 1
        if lang not in per_language:
            per_language[lang] = {"rows": 0, "entity_counts": collections.Counter(), "rows_with_label": collections.Counter()}
        record = per_language[lang]
        record["rows"] += 1
        record["entity_counts"].update(row["labels"])
        record["rows_with_label"].update(row["labels"].keys())
    return {"rows": len(rows), "languages": language, "entity_counts": labels, "rows_with_label": row_labels,
            "per_language": per_language, "regions": regions, "scripts": scripts,
            "empty_annotations": sum(r["empty_annotations"] for r in rows),
            "warning_rows_by_code": collections.Counter(k for r in rows for k, count in r["issues"].items() if count),
            "target_free_all_observed_labels": sum(r["target_free"] for r in rows),
            "email_free": sum(r["email_free"] for r in rows), "iban_entities": labels["IBAN"]}


def allocate(rows, uf):
    groups = collections.defaultdict(list)
    for i, row in enumerate(rows):
        groups[uf.root(i)].append(i)
    group_ids = {root: digest("group:" + ":".join(sorted(rows[i]["row_id"] for i in indices))) for root, indices in groups.items()}
    selected = [r for r in rows if r["language"] in LANGUAGES]
    eligible = [i for i, r in enumerate(rows) if r["language"] in LANGUAGES and not r["excluded"]]
    eligible_groups = collections.defaultdict(list)
    for i in eligible:
        eligible_groups[uf.root(i)].append(i)
    # Conservatively replace official validation irrespective of observed leakage:
    # publisher shuffled rows, not groups; near/template checks cannot prove
    # source-family independence. No holdout is used for label/threshold tuning.
    assignment = {}
    for root in eligible_groups:
        value = int(digest(SEED + ":" + group_ids[root]), 16)
        bucket = (value * 100) // (1 << 256)
        assignment[root] = "train" if bucket < 80 else "dev" if bucket < 90 else "test"
    manifests = {name: [] for name in ("selected", "excluded", "train", "dev", "test")}
    for index, row in enumerate(rows):
        if row["language"] not in LANGUAGES:
            continue
        entry = {"row_id": row["row_id"], "source_split": row["source_split"], "language": row["language"],
                 "exact_hash": row["exact_hash"], "template_hash": row["template_hash"],
                 "group_id": group_ids[uf.root(index)],
                 "warnings": sorted(k for k, count in row["issues"].items() if count)}
        manifests["selected"].append(entry)
        if row["excluded"]:
            manifests["excluded"].append(dict(entry, reasons=row["excluded"]))
        else:
            manifests[assignment[uf.root(index)]].append(entry)
    for entries in manifests.values():
        entries.sort(key=lambda entry: entry["row_id"])
    supports = {}
    id_to_row = {row["row_id"]: row for row in rows}
    for name, entries in manifests.items():
        supports[name] = support([id_to_row[e["row_id"]] for e in entries])
    unavailable = []
    for name in ("train", "dev", "test"):
        for language in LANGUAGES:
            for label in sorted(LABELS):
                value = supports[name]["per_language"].get(language, {}).get("entity_counts", {}).get(label, 0)
                if not value:
                    unavailable.append({"split": name, "language": language, "label": label})
    excluded_reasons = collections.Counter(reason for r in selected for reason in r["excluded"])
    policy = {"official_validation_retained_as_final": False,
              "reason": "Conservative regrouping: official files were row-shuffled; lexical checks do not establish source-family independence. Physical split is authoritative; embedded split field is audited separately.",
              "seed": SEED, "algorithm": "SHA256(seed:group_id) interpreted as 256-bit integer; floor(100*value/2^256), buckets 0..79 train, 80..89 dev, 90..99 test; stable row-ID sort",
              "grouping": "Transitive union of exact source, NFKC/casefold/whitespace normalized entity-masked templates, and measured near-template pairs over ALL languages and physical splits before selection",
              "group_id": "SHA256 of group: plus sorted hashed source row IDs, colon-delimited",
              "row_id": "SHA256(repo_id:revision:artifact_path:zero_based_row_index); uid values never emitted",
              "target_languages": list(LANGUAGES), "allocation_uses_labels": False,
              "excluded_target_rows": len(manifests["excluded"]), "excluded_reason_counts": excluded_reasons,
              "non_target_rows": len(rows) - len(selected), "all_dataset_groups": len(groups),
              "eligible_target_groups": len(eligible_groups),
              "largest_all_dataset_group": max(map(len, groups.values()), default=0),
              "per_split_support": supports, "missing_language_label_cells": unavailable,
              "readiness": "provisional structural manifests only; provenance and semantic quality gates remain unresolved"}
    return manifests, policy


def verify_disjoint(manifests):
    counts = {}
    for field in ("row_id", "exact_hash", "template_hash", "group_id"):
        sets = {name: {e[field] for e in manifests[name] if e[field] is not None} for name in ("train", "dev", "test")}
        overlaps = sum(len(sets[a] & sets[b]) for a, b in (("train", "dev"), ("train", "test"), ("dev", "test")))
        counts[field + "_cross_split_overlap"] = overlaps
        if overlaps:
            raise ValueError("manifest_disjointness_failure")
    selected = {e["row_id"] for e in manifests["selected"]}
    excluded = {e["row_id"] for e in manifests["excluded"]}
    allocated = [e["row_id"] for name in ("train", "dev", "test") for e in manifests[name]]
    if len(allocated) != len(set(allocated)) or excluded & set(allocated) or selected != excluded | set(allocated):
        raise ValueError("manifest_partition_failure")
    counts.update({"selected_rows": len(selected), "excluded_rows": len(excluded), "allocated_rows": len(allocated), "selected_partition_complete": True})
    return counts


def build(raw, source):
    import pyarrow
    import pyarrow.parquet as pq
    rows, schemas = [], {}
    for artifact in source["artifacts"]:
        if "split" not in artifact:
            continue
        table = pq.read_table(raw / artifact["path"])
        if set(table.column_names) != EXPECTED_FIELDS:
            raise ValueError("unexpected_schema")
        schemas[artifact["split"]] = str(table.schema.remove_metadata())
        for ordinal, row in enumerate(table.to_pylist()):
            rows.append(inspect_row(row, artifact, ordinal))
    issues, issue_rows, class_counts, inference = (collections.Counter() for _ in range(4))
    for row in rows:
        issues.update(row["issues"])
        issue_rows.update(k for k, count in row["issues"].items() if count)
        class_counts.update(row["class_counts"])
        inference[row["inference_status"]] += 1
    uid_groups = collections.defaultdict(list)
    for row in rows:
        uid_groups[row["uid_hash"]].append(row)
    uf = UnionFind(len(rows))
    exact, template = duplicate_stats(rows, "exact_hash", uf), duplicate_stats(rows, "template_hash", uf)
    near = near_duplicates(rows, uf)
    manifests, policy = allocate(rows, uf)
    checks = verify_disjoint(manifests)
    audit = {"audit_version": 1, "repo_id": REPO, "revision": REVISION, "source_metadata_sha256": digest(json_bytes(source)),
             "runtime": {"python": platform.python_version(), "pyarrow": pyarrow.__version__},
             "full_rows_examined": len(rows), "schema_by_physical_split": schemas,
             "embedded_split_field_counts": collections.Counter(r["embedded_split"] for r in rows),
             "overall": support(rows), "physical_splits": {name: support([r for r in rows if r["source_split"] == name]) for name in ("train", "validation")},
             "annotations": {"spans_examined": sum(r["span_count"] for r in rows), "tokens_examined": sum(r["token_count"] for r in rows),
                             "offset_contract": "Python Unicode code points, zero-based half-open; every annotated value compared locally against original source slice",
                             "issue_events": {k: v for k, v in issues.items() if v}, "rows_with_issue": issue_rows,
                             "structural_check_failure_counts": {k: issues[k] for k in sorted(FATAL)},
                             "unknown_token_rows": sum(r["has_unknown_token"] for r in rows),
                             "empty_token_sequences": sum(r["empty_tokens"] for r in rows),
                             "structurally_excluded_all_languages": sum(bool(r["excluded"]) for r in rows),
                             "bio_class_counts": class_counts, "token_position_inference": inference,
                             "inferred_token_span_comparable_rows": sum(r["inferred_comparable"] for r in rows),
                             "token_alignment_limit": "No published token offsets or tokenizer revision. Length/BIO/count checks cover all rows; literal WordPiece-to-source alignment only on exactly reconstructable rows. UNK and literal mismatch rows are unverified, not repaired or declared invalid."},
             "duplicate_uid_groups": sum(len(group) > 1 for group in uid_groups.values()),
             "duplicate_uid_groups_with_different_text": sum(len({r["exact_hash"] for r in g}) > 1 for g in uid_groups.values()),
             "duplicates": {"exact_source": exact, "normalized_masked_template": template, "near_template": near},
             "split_policy": policy, "verification": checks,
             "verdict": "AUDITED_NOT_TRAINING_READY",
             "limitations": ["Structural validity does not prove semantic annotation completeness or correctness.",
                             "Publisher synthetic provenance wording conflict remains unresolved; not evidence of actual private data.",
                             "No clean negatives for all-label masking are established; EMAIL-free rows are not all-label clean negatives.",
                             "No observed IBAN label; no IBAN model coverage claim.",
                             "Lexical group-disjointness is not proven generation-family or semantic independence.",
                             "No models, training, evaluation, label/threshold tuning, remote row submission or paid APIs."]}
    outputs = {"artifacts/data-audit/audit.json": json_bytes(audit)}
    for name, entries in manifests.items():
        outputs["data/manifests/" + name + ".jsonl"] = b"".join((json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n").encode() for entry in entries)
    outputs["data/manifests/split-policy.json"] = json_bytes(policy)
    outputs["artifacts/data-audit/output-hashes.json"] = json_bytes(output_hashes(outputs, ROOT / "artifacts/data-audit/output-hashes.json"))
    return outputs, audit


def output_hashes(outputs, index_path):
    """Preserve frozen logical hash keys while resolving relocated output files."""
    if not index_path.is_file():
        return {name: digest(payload) for name, payload in sorted(outputs.items())}
    frozen = json.loads(index_path.read_text())
    resolved = {name: "artifacts/" + name.split("/", 1)[1]
                if name.split("/", 1)[0] == "docs" else name for name in frozen}
    if len(resolved) != len(outputs) or set(resolved.values()) != set(outputs):
        raise ValueError("output_hash_paths_mismatch")
    return {name: digest(outputs[path]) for name, path in sorted(resolved.items())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/openpii-masking-mini-10k", help="Local ignored pinned artifacts")
    parser.add_argument("--offline", action="store_true", help="Never access network; require frozen local artifact hashes")
    parser.add_argument("--verify", action="store_true", help="Force offline, recompute full audit, byte-compare committed outputs; write nothing")
    args = parser.parse_args()
    try:
        source = json.loads((ROOT / "artifacts/data-audit/source.json").read_text())
        artifacts(args.raw_dir, source, args.offline or args.verify)
        outputs, audit = build(args.raw_dir, source)
        for name, payload in outputs.items():
            target = ROOT / name
            if args.verify:
                if not target.is_file() or target.read_bytes() != payload:
                    raise ValueError("recomputed_output_mismatch:" + name)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
        print(json.dumps({"status": "VERIFIED" if args.verify else "AUDITED", "rows": audit["full_rows_examined"],
                          "selected_rows": audit["verification"]["selected_rows"],
                          "allocated_rows": audit["verification"]["allocated_rows"],
                          "excluded_rows": audit["verification"]["excluded_rows"],
                          "issue_counts": audit["annotations"]["issue_events"], "verification": audit["verification"],
                          "verdict": audit["verdict"]}, sort_keys=True))
        return 0
    except Exception as error:
        # No exception message/traceback: libraries can include row values.
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__,
                          "safe_reason": str(error) if isinstance(error, ValueError) and re.fullmatch(r"[a-z_]+(?::[a-zA-Z0-9/_.-]+)?", str(error)) else "details_suppressed_to_prevent_raw_data_logging"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
