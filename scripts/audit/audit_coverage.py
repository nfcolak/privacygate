"""Offline, value-free coverage inventory; never opens corpus or split files.

Reads only existing aggregate metadata, detector source and checkpoint config.
No model import, inference, evaluation, training or network access.
"""
import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/scope"
PATHS = {
    "mini": "artifacts/data-audit/audit.json",
    "micro": "artifacts/data-audit/micro/audit.json",
    "metrics": "artifacts/runs/compare-dev/metrics.json",
    "run": "artifacts/runs/full-1/config.json",
    "alignment": "artifacts/data-audit/micro/alignment.json",
    "rules": "privacygate/detect.py",
    "challenge_generator": "scripts/make_challenge.py",
}
# A non-exhaustive requirement map, not a definition of all personal information.
CATEGORIES = [
    ("names", ["GIVENNAME", "SURNAME"], [], "partial", "Component spans only; full-name, alias and nickname coverage unmeasured."),
    ("phones", ["TELEPHONENUM"], [], "label_supported", "Extensions, obfuscation, regional formats and person linkage unmeasured."),
    ("identity_numbers", ["IDCARDNUM", "PASSPORTNUM", "DRIVERLICENSENUM", "SOCIALNUM", "TAXNUM"], [], "partial", "Named label families do not establish all national or institutional ID formats."),
    ("person_address", ["STREET", "BUILDINGNUM", "CITY", "ZIPCODE"], [], "partial", "No whole-address/person-link recall; apartment, country, region, PO box and coordinates not separately supported."),
    ("email", ["EMAIL"], ["EMAIL"], "label_and_rule_supported", "Rule is format-based; aliases, obfuscation and contextual person linkage unmeasured."),
    ("payment_cards", ["CREDITCARDNUMBER"], [], "partial", "No separate CVV, PIN, expiry or payment-token label."),
    ("bank_iban", [], ["IBAN"], "rule_only", "Checksum/form rule only; no learned IBAN label or person-link classification."),
    ("age", ["AGE"], [], "label_supported", "Person-linked attributes remain personal even without direct identifiers."),
    ("personal_dates", ["DATE"], [], "partial", "DATE does not establish birthdate/event semantics or TIME coverage."),
    ("sex_gender", ["SEX", "GENDER"], [], "label_supported", "Broader sensitive traits and contextual linkage unmeasured."),
    ("personal_titles", ["TITLE"], [], "partial", "Not evidence for occupation, employer or education-history coverage."),
    ("person_linked_order_tracking_serial_reference", [], [], "absent_dedicated_support", "Format or invalid IBAN checksum never establishes a safe negative; incidental ID labels are not validated coverage."),
    ("usernames_handles_customer_membership_accounts", [], [], "absent_dedicated_support", "Person-linked handles, URLs, membership and non-IBAN account IDs remain targets."),
    ("ip_mac_device_cookie_online_identifiers", [], [], "absent_dedicated_support", "No dedicated online/device identifier labels or rules."),
    ("precise_location_and_movements", [], [], "absent_dedicated_support", "Address components do not establish coordinates, journeys or habitual-location coverage."),
    ("health_disability_genetic_biometric", [], [], "absent_dedicated_support", "No dedicated labels/rules; incidental detections cannot establish coverage."),
    ("religion_politics_ethnicity_sexuality", [], [], "absent_dedicated_support", "No dedicated labels/rules for these person-linked sensitive attributes."),
    ("employment_education_financial_history", [], [], "absent_dedicated_support", "Employer, school, salary, debt and history coverage unknown."),
    ("relationships_behavior_personal_narratives", [], [], "absent_dedicated_support", "Indirect identification and combined quasi-identifiers are not measured."),
    ("credentials_and_person_linked_secrets", [], [], "absent_dedicated_support", "No dedicated password, access-token or security-answer coverage."),
]


class AuditError(Exception):
    """Errors carry only a fixed message, never source content."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def load_sources(model_config):
    sources, documents, text = {}, {}, {}
    paths = dict(PATHS, checkpoint=str(model_config.resolve()))
    for source, name in paths.items():
        path = Path(name) if source == "checkpoint" else ROOT / name
        raw = path.read_bytes()
        sources[source] = {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
        if path.suffix == ".json":
            documents[source] = json.loads(raw)
        else:
            text[source] = raw.decode("utf-8")
    return sources, documents, text


def number(docs, source, key):
    """JSON Pointer into an allowlisted aggregate file, with scalar validation."""
    value = docs[source]
    for part in key.lstrip("/").split("/"):
        value = value[part]
    require(type(value) in (int, float), "Expected aggregate numeric field.")
    require(value >= 0, "Invalid aggregate numeric field.")
    return {"value": value, "source": source, "key": key}


def checkpoint_labels(config):
    id2label, label2id = config["id2label"], config["label2id"]
    require(isinstance(id2label, dict) and isinstance(label2id, dict), "Missing checkpoint label maps.")
    ids = sorted(int(i) for i in id2label)
    require(ids == list(range(len(ids))), "Non-contiguous checkpoint label IDs.")
    bio = [id2label[str(i)] for i in ids]
    require(len(set(bio)) == len(bio), "Duplicate checkpoint labels.")
    require(label2id == {label: i for i, label in enumerate(bio)}, "Checkpoint label maps disagree.")
    require(bio.count("O") == 1, "Missing outside label.")
    require(all(label == "O" or re.fullmatch(r"[BI]-[A-Z][A-Z0-9_]*", label) for label in bio), "Unsupported checkpoint label grammar.")
    labels = sorted({label[2:] for label in bio if label != "O"})
    require(set(bio) == {"O"} | {prefix + label for label in labels for prefix in ("B-", "I-")}, "Unpaired checkpoint BIO labels.")
    return bio, labels


def rule_labels(source):
    """Inspect output tuples statically; do not import the detector."""
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "detect")
    labels = sorted({node.elts[-1].value for node in ast.walk(function)
                     if isinstance(node, ast.Tuple) and len(node.elts) == 3
                     and isinstance(node.elts[-1], ast.Constant)
                     and isinstance(node.elts[-1].value, str)})
    require(labels == ["EMAIL", "IBAN"], "Detector rules changed; descriptions need reconciliation.")
    return labels


def build(model_config):
    sources, docs, text = load_sources(model_config)
    bio, labels = checkpoint_labels(docs["checkpoint"])
    rules = rule_labels(text["rules"])
    require(bio == docs["run"]["labels"], "Checkpoint taxonomy differs from historical full-1; cannot attach its metrics.")
    mini = docs["mini"]["overall"]["entity_counts"]
    micro = docs["micro"]["overall_all_languages"]["entity_counts"]
    require(set(mini) == set(labels), "Mini audit and checkpoint taxonomy disagree.")
    require(set(labels) <= set(micro), "Micro audit lacks checkpoint labels.")
    extra = sorted(set(micro) - set(labels))
    require(all(re.fullmatch(r"invalid_sha256_[a-f0-9]{64}", label) for label in extra), "Unexpected Micro label metadata; manual reconciliation required.")
    require(sum(micro[label] for label in extra) == docs["micro"]["annotations"]["structural_check_failure_counts"]["span_label_invalid"], "Micro out-of-taxonomy counts disagree.")
    require(sum(mini.values()) == docs["mini"]["annotations"]["spans_examined"], "Mini aggregate span counts disagree.")
    require(sum(micro.values()) == docs["micro"]["annotations"]["spans_examined"], "Micro aggregate span counts disagree.")
    rows = []
    for label in labels:
        row = {
            "label": label,
            "checkpoint_ids": {prefix: docs["checkpoint"]["label2id"][prefix + "-" + label] for prefix in ("B", "I")},
            "mini_spans": number(docs, "mini", "/overall/entity_counts/" + label),
            "micro_spans": number(docs, "micro", "/overall_all_languages/entity_counts/" + label),
            "historical_micro_dev": {},
        }
        for arm in ("mbert", "rules_first_thr"):
            base = "/arms/" + arm + "/micro_dev/per_label/" + label
            stats = {key: number(docs, "metrics", base + "/" + key) for key in ("recall", "support")}
            require(stats["support"]["value"] > 0 and stats["recall"]["value"] <= 1, "Invalid historical label support/recall.")
            row["historical_micro_dev"][arm] = stats
        rows.append(row)
    categories = []
    for name, wanted_labels, wanted_rules, status, caveat in CATEGORIES:
        require(set(wanted_labels) <= set(labels) and set(wanted_rules) <= set(rules), "Requirement map refers to unsupported labels/rules.")
        categories.append({
            "category": name, "checkpoint_labels": wanted_labels, "rules": wanted_rules,
            "support_status": status,
            "measurement_status": "historical_label_recall_only; category/person-link recall unknown" if wanted_labels else
                                  "historical_synthetic_IBAN_recall_only; person-link recall unknown" if wanted_rules else "unknown",
            "caveat": caveat,
        })
    benchmark = {}
    for arm in sorted(docs["metrics"]["arms"]):
        base = "/arms/" + arm + "/challenge_dev/"
        benchmark[arm] = {key: number(docs, "metrics", base + key) for key in
                          ("iban_recall_strict", "iban_recall_label_agnostic", "decoy_fp_rate", "clean_fp_rate")}
    historical = {key: number(docs, "metrics", "/" + key) for key in
                  ("micro_rows_evaluated", "micro_rows_excluded_broken_boundary", "challenge_rows", "chosen_threshold")}
    # Surface, rather than silently fix, discrepancies between historical stages.
    alignment = {key: number(docs, "alignment", "/splits/dev/" + key) for key in
                 ("rows", "rows_excluded", "spans_boundary_inside_wordpiece")}
    counts = {"checkpoint_bio_labels": len(bio), "checkpoint_entity_labels": len(labels),
              "rule_labels": len(rules), "micro_extra_hashed_label_bins": len(extra),
              "micro_extra_label_spans": sum(micro[label] for label in extra)}
    return {
        "schema_version": 1,
        "target": "Mask ALL personal information, including but not limited to names, phones, identity numbers and a person's address.",
        "scope": "Offline synthetic research preparation; label inventory and previously committed aggregates only; no privacy guarantee.",
        "sources": sources,
        "inventory": {"counts": counts, "bio_labels": bio, "entity_labels": labels, "rule_labels": rules,
                      "checkpoint_source_keys": ["/id2label", "/label2id"],
                      "historical_taxonomy_match": True, "checkpoint_weights_verified": False,
                      "mini_taxonomy_match": True, "micro_supported_labels_present": True,
                      "micro_extra_label_count_source": {"source": "micro", "key": "/overall_all_languages/entity_counts"},
                      "micro_extra_label_spans_check": number(docs, "micro", "/annotations/structural_check_failure_counts/span_label_invalid"),
                      "rule_source": "rules:detect output tuples; EMAIL_RE; IBAN_RE and iban_valid"},
        "labels": rows, "categories": categories,
        "historical_dev_context": historical,
        "historical_challenge_dev": benchmark,
        "alignment_dev_metadata": alignment,
        "caveats": [
            "Label supported is not successful detection, semantic completeness or a privacy guarantee; no finite taxonomy proves all personal information covered.",
            "Recall values are unchanged historical strict start/end/label dev aggregates, not new evaluation, category-level recall or current CLI recall.",
            "Historical taxonomy equality does not verify checkpoint weights or bind historical scores to a new inference implementation.",
            "Threshold was tuned on dev; single seed/model and synthetic templates; no test inspection or scoring performed.",
            "Decoy FP is a benchmark-convention result, not a proven masking error under the all-personal-information policy.",
            "Regex negatives were selected by absence of regex detections; zero FP is by construction, not robustness evidence.",
            "Alignment metadata excludes 38 dev rows, comparison metadata excludes 39; their row sets cannot be reconciled from aggregates alone.",
            "Micro extra labels are hashed out-of-taxonomy audit bins, not checkpoint support; semantic label names cannot be recovered from hashes alone.",
            "Full person-address, person linkage, unannotated information and combinations of indirect identifiers remain unmeasured.",
        ],
    }


def markdown(report):
    counts = report["inventory"]["counts"]
    lines = ["# Personal-information coverage (aggregate-only)", "",
             report["target"], "", "This is a target, not achieved coverage. Synthetic research only; no privacy guarantee.", "",
             "## Reconciled inventory", "",
             "Checkpoint: {} BIO labels (including O), {} entity labels; {} rule labels. Full-1 historical label order and both checkpoint maps reconcile.".format(
                 counts["checkpoint_bio_labels"], counts["checkpoint_entity_labels"], counts["rule_labels"]),
             "Mini taxonomy matches. Micro also contains {} hashed out-of-taxonomy bins / {} spans; these do not add checkpoint coverage.".format(
                 counts["micro_extra_hashed_label_bins"], counts["micro_extra_label_spans"]), "",
             "## Supported labels and historical recall", "",
             "Counts are full-population audit span counts, not evaluation. R is historical strict span recall on Micro dev, not person/category recall or current CLI recall.", "",
             "| Label | Mini spans | Micro spans | mBERT R | rules_first_thr R |",
             "|---|---:|---:|---:|---:|"]
    for row in report["labels"]:
        lines.append("| {} | {} | {} | {:.6f} | {:.6f} |".format(
            row["label"], row["mini_spans"]["value"], row["micro_spans"]["value"],
            row["historical_micro_dev"]["mbert"]["recall"]["value"],
            row["historical_micro_dev"]["rules_first_thr"]["recall"]["value"]))
    lines += ["", "Exact unrounded values, support and source/key are in `coverage.json`: every numeric evidence object has `source` + JSON Pointer `key`; `sources` resolves paths and SHA256.",
              "Counts: `mini#/overall/entity_counts/<LABEL>` and `micro#/overall_all_languages/entity_counts/<LABEL>`.",
              "R: `metrics#/arms/<ARM>/micro_dev/per_label/<LABEL>/recall` (support at sibling `/support`).", "",
              "## Requirement map (non-exhaustive)", "",
              "| Category | Actual labels / rules | Status |",
              "|---|---|---|"]
    for category in report["categories"]:
        support = ", ".join(category["checkpoint_labels"] + ["rule:" + rule for rule in category["rules"]]) or "none dedicated"
        lines.append("| {} | {} | {} |".format(category["category"], support, category["support_status"]))
    lines += ["", "Detailed gaps and measurement status are in `coverage.json#/categories`; component recall never proves whole-address or person-link recall.", "",
              "## Limits and gates", ""]
    lines.extend("- " + caveat for caveat in report["caveats"])
    lines += ["", "Policy and open gates: ProjectOS project `10-Projects/privacygate`.", "",
              "Reproduce without corpus access or model loading:", "",
              "    env -u PYTHONPATH HF_HUB_OFFLINE=1 python3 scripts/audit/audit_coverage.py --model-config /absolute/path/to/models/full-1/config.json", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-config", required=True, type=Path, help="Read-only local full-1 checkpoint label config")
    args = parser.parse_args()
    try:
        report = build(args.model_config)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "coverage.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    except (AuditError, OSError, ValueError, KeyError, TypeError, StopIteration, SyntaxError):
        print("COVERAGE FAILED: local aggregate/config reconciliation failed; no source values emitted.", file=sys.stderr)
        return 1
    counts = report["inventory"]["counts"]
    print("COVERAGE OK " + json.dumps(counts, sort_keys=True))
    print("SOURCE LABELS RECONCILED: checkpoint id2label/label2id, historical full-1, Mini and Micro supported taxonomy")
    print("OUTPUT " + str(OUT / "coverage.json"))
    print("CAVEAT: historical aggregates only; no corpus, model load, training, test inspection or scoring; no privacy guarantee")
    return 0


if __name__ == "__main__":
    sys.exit(main())
