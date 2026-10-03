"""Reuse v2 schema checks; enforce v3 linkage, counts, twins and split isolation."""
from collections import Counter, defaultdict
import json
import re

from train_v2.checks import check_split_isolation, require, validate_row as validate_v2
from train_v2.numbers import mod97
from train_v2.pools import POOLS

from .spec import (BOUNDARY_ROWS, INVALID_IBAN_FAMILY, LABELS, LANGUAGES,
                   NEGATIVE_KINDS, NEW_GROUPS, POLICY_PATH, SIZES, TWIN_LABELS,
                   template_id)


def validate_row(row, split):
    if isinstance(row, dict) and row.get("family") == INVALID_IBAN_FAMILY:
        spans = row.get("gold")
        if not isinstance(spans, list) or len(spans) != 1:
            raise ValueError("invalid_iban_span_count")
        require(isinstance(spans[0], dict) and spans[0].get("label") == "IBAN",
                "invalid_iban_label")
        # Frozen v2 requires valid MOD97. Change only the validation copy's label
        # to run its full schema/boundary checks; the actual gold stays IBAN.
        shadow = {**row, "gold": [{**spans[0], "label": "ACCOUNTNUM"}]}
        validate_v2(shadow, split)
        token = row["text"][spans[0]["start"]:spans[0]["end"]]
        compact = re.sub(r"[ -]", "", token)
        country = POOLS[row["language"]]["cc"]
        length = {"GB": 22, "DE": 22, "FR": 27, "IT": 27, "ES": 24}[country]
        require(compact.startswith(country) and len(compact) == length,
                "iban_locale")
        require(compact.isalnum() and mod97(token) != 1, "expected_invalid_iban")
    else:
        validate_v2(row, split)


def expected_templates(split):
    result = set()
    for language in LANGUAGES:
        for kind in NEGATIVE_KINDS:
            result.add(template_id(split, language, "legacy.neg." + kind))
        for kind in TWIN_LABELS:
            result.add(template_id(split, language, "legacy.twin." + kind))
        for label in LABELS:
            for variant in (0, 1):
                result.add(template_id(split, language, "legacy.pos." + label, variant))
        result.add(template_id(split, language, "legacy.letter"))
        result.add(template_id(split, language, "boundary.triple"))
        for group, kinds in NEW_GROUPS.items():
            for kind in kinds:
                for variant in ((0, 1) if group == "catalog" else (0,)):
                    for side in ("neg", "twin"):
                        result.add(template_id(split, language,
                                               f"target.{side}.{group}.{kind}", variant))
    return result


def summarize(records, split, excluded):
    languages, families, labels, label_rows = Counter(), Counter(), Counter(), Counter()
    templates, ids, texts, signatures = set(), set(), set(), set()
    pairs = defaultdict(list)
    values = {label: set() for label in LABELS}
    clean, boundaries, max_length = 0, 0, 0
    for row, metadata in records:
        validate_row(row, split)
        require(row["family"] not in excluded, "reserved_family")
        require(row["case_id"] not in ids, "duplicate_case_id")
        ids.add(row["case_id"])
        texts.add(row["text"])
        tid = metadata["template_id"]
        require(row["case_id"].endswith("--" + tid), "case_template_id")
        require(tid.startswith(split + "." + row["language"] + "."), "template_split")
        templates.add(tid)
        if metadata["template"] is not None:
            signatures.add(metadata["template"])
        languages[row["language"]] += 1
        families[row["family"]] += 1
        clean += not row["gold"]
        max_length = max(max_length, len(row["text"]))
        for span in row["gold"]:
            labels[span["label"]] += 1
            values[span["label"]].add(row["text"][span["start"]:span["end"]])
        label_rows.update({span["label"] for span in row["gold"]})
        if row["family"] == "boundary.name-address-phone":
            require([s["label"] for s in row["gold"]] ==
                    ["PERSONNAME", "ADDRESS", "TELEPHONENUM"], "boundary_labels")
            require("\n" not in row["text"], "boundary_single_line")
            boundaries += 1
        if metadata["pair_id"] is not None:
            pairs[metadata["pair_id"]].append(row)
    require(len(records) == SIZES[split], "row_count")
    require(clean * 100 == len(records) * 45, "clean_share")
    ideal = len(records) // len(LANGUAGES)
    require(set(languages) == set(LANGUAGES), "language_coverage")
    require(all(abs(n - ideal) <= ideal * 0.05 for n in languages.values()), "language_balance")
    require(set(labels) == set(LABELS), "label_coverage")
    require(boundaries == BOUNDARY_ROWS[split] * len(LANGUAGES), "boundary_count")
    require(templates == expected_templates(split), "template_catalog_coverage")
    checksum_counts = Counter()
    for rows in pairs.values():
        require(len(rows) == 2, "twin_pair_count")
        negatives = [r for r in rows if not r["gold"]]
        positives = [r for r in rows if r["gold"]]
        require(len(negatives) == len(positives) == 1, "twin_pair_classes")
        positive, negative = positives[0], negatives[0]
        require(len(positive["gold"]) == 1, "twin_whole_payload")
        span = positive["gold"][0]
        token = positive["text"][span["start"]:span["end"]]
        require(token in negative["text"], "twin_identical_payload")
        if positive["family"].startswith("target.person-linked.near-miss.iban_"):
            validity = "valid" if mod97(token) == 1 else "invalid"
            expected = positive["family"].rsplit("_", 1)[1]
            require(validity == expected, "iban_validity_class")
            checksum_counts["clean_" + validity] += 1
            checksum_counts["personal_" + validity] += 1
    require(all(checksum_counts[k] > 0 for k in
                ("clean_valid", "clean_invalid", "personal_valid", "personal_invalid")),
            "checksum_context_coverage")
    summary = {"rows": len(records), "clean_rows": clean, "clean_share": clean / len(records),
               "counts": {"label": dict(sorted(labels.items())),
                          "language": dict(sorted(languages.items())),
                          "family": dict(sorted(families.items()))},
               "label_rows": dict(sorted(label_rows.items())), "matched_pairs": len(pairs),
               "boundary_rows": boundaries, "iban_checksum_contexts": dict(sorted(checksum_counts.items())),
               "unique_texts": len(texts), "max_text_chars": max_length}
    return summary, templates, values, signatures, texts


def inspect_datasets(datasets):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    require(set(policy["labels"]) == set(LABELS) and policy["synthetic_only"], "policy_contract")
    excluded = policy["reserved_v4_families"]
    require(len(excluded) == 5, "reserved_family_contract")
    observed = {s: summarize(datasets[s], s, excluded) for s in SIZES}
    check_split_isolation(observed)
    require(not observed["train"][3] & observed["dev"][3], "template_text_leakage")
    require(not observed["train"][4] & observed["dev"][4], "row_text_leakage")
    return observed, excluded
