"""Schema, whole AGE boundaries, recipe coverage and split isolation checks."""
from collections import Counter, defaultdict
import json
import re

from train_v2.checks import require, validate_row as validate_v2
from train_v3.checks import validate_row as validate_v3
from train_v3.spec import FAMILY, NEGATIVE_KINDS, NEW_GROUPS, TWIN_LABELS

from .grid_checks import summarize_grid
from .spec import AGE_UNITS, GRID, LABELS, LANGUAGES, POLICY_PATH, SIZES


def validate_row(row, split):
    require(isinstance(row, dict), "row_schema")
    spans = row.get("gold")
    invalid_grid = (row.get("family") == "grid.person_linked_operational_shape_twins"
                    and isinstance(spans, list) and len(spans) == 1 and isinstance(spans[0], dict)
                    and spans[0].get("label") == "IBAN"
                    and str(row.get("case_id", "")).split("--")[-1].split(".")[-2:-1] == ["1"])
    if invalid_grid:
        shadow = {**row, "gold": [{**span, "label": "ACCOUNTNUM"} for span in row["gold"]]}
        validate_v2(shadow, split)
    else:
        validate_v3(row, split)
    unit = AGE_UNITS[row["language"]]
    for span in row["gold"]:
        if span["label"] != "AGE":
            continue
        token = row["text"][span["start"]:span["end"]]
        require(bool(re.fullmatch(r"\d+(?:[ \t]+(?:" + unit + r"))?", token)),
                "age_number_and_unit_only")
        require(not re.match(r"[ \t]+(?:" + unit + r")\b", row["text"][span["end"]:]),
                "age_attached_unit_uncovered")
        require(span["start"] == 0 or not row["text"][span["start"] - 1].isdigit(),
                "age_numeric_start")
        require(span["end"] == len(row["text"]) or not row["text"][span["end"]].isalnum(),
                "age_whole_word_end")


def recipe_families():
    families = set(FAMILY.values()) | {"boundary.name-address-phone", "letter.repeated-values"}
    families.update("hard-negative." + kind for kind in NEGATIVE_KINDS)
    families.update("person-linked." + kind for kind in TWIN_LABELS)
    for group, kinds in NEW_GROUPS.items():
        for kind in kinds:
            for side in ("clean", "person-linked"):
                for suffix in ((".line", ".table") if group == "catalog" else ("",)):
                    families.add(f"target.{side}.{group}.{kind}{suffix}")
    return families


def summarize(records, split):
    counts = {kind: Counter() for kind in ("label", "language", "family")}
    ids, templates, signatures, texts = set(), set(), set(), set()
    values = {label: set() for label in LABELS}
    local_families, pairs = defaultdict(set), defaultdict(list)
    clean = 0
    age_counts = Counter()
    for row, metadata in records:
        validate_row(row, split)
        require(row["case_id"] not in ids, "duplicate_case_id")
        ids.add(row["case_id"])
        tid = metadata["template_id"]
        require(row["case_id"].endswith("--" + tid), "case_template_id")
        require(tid.startswith(split + "." + row["language"] + "."), "template_split")
        templates.add(tid)
        if metadata["template"] is not None:
            signatures.add(metadata["template"])
        texts.add(row["text"])
        counts["language"][row["language"]] += 1
        counts["family"][row["family"]] += 1
        clean += not row["gold"]
        if metadata["source"] == "regenerated-v3":
            local_families[row["language"]].add(row["family"])
        age_counts["reused_spans_expanded"] += metadata.get("age_expanded", 0)
        for span in row["gold"]:
            label = span["label"]
            counts["label"][label] += 1
            token = row["text"][span["start"]:span["end"]]
            values[label].add(token)
            if label == "AGE":
                age_counts["unit_bearing" if " " in token else "bare_numeric"] += 1
        if metadata["pair_id"]:
            pairs[metadata["pair_id"]].append(row)
    require(len(records) == SIZES[split], "row_count")
    require(clean * 100 == len(records) * 45, "clean_share")
    require(set(counts["label"]) == set(LABELS), "label_coverage")
    require(set(counts["language"]) == set(LANGUAGES), "language_coverage")
    require(all(n == SIZES[split] // 5 for n in counts["language"].values()), "language_balance")
    require(all(local_families[lang] == recipe_families() for lang in LANGUAGES),
            "all_recipe_families_per_language")
    for rows in pairs.values():
        require(len(rows) == 2 and sum(not r["gold"] for r in rows) == 1, "recipe_twins")
        positive = next(r for r in rows if r["gold"])
        negative = next(r for r in rows if not r["gold"])
        require(len(positive["gold"]) == 1, "recipe_twin_gold_count")
        span = positive["gold"][0]
        token = positive["text"][span["start"]:span["end"]]
        if span["label"] == "AGE":
            token = token.split()[0]
        require(token in negative["text"], "recipe_twin_shared_payload")
    summary = {"rows": len(records), "clean_rows": clean, "clean_share": clean / len(records),
               "counts": {k: dict(sorted(c.items())) for k, c in counts.items()},
               "recipe_rows": sum(metadata["source"] == "regenerated-v3" for _, metadata in records),
               "recipe_families_per_language": len(recipe_families()),
               "recipe_matched_pairs": len(pairs), "unique_texts": len(texts),
               "age_boundaries": dict(sorted(age_counts.items())),
               "grid": summarize_grid(records, split)}
    return summary, templates, signatures, texts, values


def inspect_datasets(datasets):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    require(policy.get("synthetic_only") and set(policy["labels"]) == set(LABELS), "policy_contract")
    require(len(policy["reserved_v4_families"]) == 5, "reserved_family_contract")
    observed = {split: summarize(datasets[split], split) for split in SIZES}
    for position, code in ((1, "template_id_leakage"), (2, "template_text_leakage"),
                           (3, "row_text_leakage")):
        require(not observed["train"][position] & observed["dev"][position], code)
    for label in LABELS:
        require(not observed["train"][4][label] & observed["dev"][4][label], "positive_value_pool_leakage")
    # Independent v4 grid value pools include clean controls, not only gold values.
    from .build import grid_value
    payloads = {}
    for split in SIZES:
        payloads[split] = {grid_value(m["component"], r["language"], split, m["cell"], m["sample"])[0]
                           for r, m in datasets[split] if m["source"] == "diagnosis-grid"}
    require(not payloads["train"] & payloads["dev"], "grid_value_pool_leakage")
    return observed
