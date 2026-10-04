"""Dataset-level aggregates and whole held-out grammar/value isolation."""
from collections import Counter, defaultdict
import hashlib
import json

from train_v2.checks import require
from train_v4.checks import recipe_families
from train_v4.grid_checks import summarize_grid as summarize_v4_grid

from .build import reseeded_v4
from .grid_checks import summarize_grid, validate_row
from .spec import LABELS, LANGUAGES, POLICY_PATH, SIZES


def summarize(records, split):
    counts = {kind: Counter() for kind in ("label", "language", "family")}
    ids, tids, templates, text_hashes = set(), set(), set(), set()
    signatures, values = {}, {label: set() for label in LABELS}
    families, pairs = defaultdict(set), defaultdict(list)
    payloads, clean, ages = set(), 0, Counter()
    inherited, regenerated_v3 = 0, 0
    for row, metadata in records:
        validate_row(row, split)
        require(row["case_id"] not in ids, "duplicate_case_id")
        ids.add(row["case_id"])
        tid = metadata["template_id"]
        require(row["case_id"].endswith("--" + tid), "case_template_id")
        require(tid.startswith(split + "." + row["language"] + "."), "template_split")
        tids.add(tid)
        if metadata["template"] is not None:
            templates.add(metadata["template"])
        digest = hashlib.sha256(row["text"].encode()).digest()
        signature = (row["language"], tuple((s["start"], s["end"], s["label"]) for s in row["gold"]))
        require(digest not in signatures or signatures[digest] == signature, "conflicting_duplicate_text")
        signatures[digest] = signature
        text_hashes.add(digest)
        counts["language"][row["language"]] += 1
        counts["family"][row["family"]] += 1
        clean += not row["gold"]
        if metadata["source"] == "regenerated-v3":
            regenerated_v3 += 1
            families[row["language"]].add(row["family"])
        inherited += metadata.get("provenance") == "regenerated-v4"
        if metadata["source"] == "diagnosis-v6-grid":
            payloads.add(metadata["payload"])
        for span in row["gold"]:
            label = span["label"]
            token = row["text"][span["start"]:span["end"]]
            counts["label"][label] += 1
            values[label].add(token)
            if label == "AGE":
                ages["lexical_cardinal" if any(c.isalpha() for c in token.split()[0]) else "numeric_cardinal"] += 1
                from .lexicon import LOCALE
                ages["unit_bearing" if token.endswith(" " + LOCALE[row["language"]]["unit"]) else "bare_cardinal"] += 1
        if metadata.get("pair_id"):
            pairs[metadata["pair_id"]].append((row, metadata))
    require(len(records) == SIZES[split], "row_count")
    require(clean * 100 == len(records) * 45, "clean_share")
    require(set(counts["label"]) == set(LABELS), "label_coverage")
    require(set(counts["language"]) == set(LANGUAGES), "language_coverage")
    require(all(n == SIZES[split] // 5 for n in counts["language"].values()), "language_balance")
    require(all(families[lang] == recipe_families() for lang in LANGUAGES), "all_recipe_families")
    require(ages["lexical_cardinal"] > 0 and ages["unit_bearing"] > 0, "semantic_age_coverage")
    for pair in pairs.values():
        require(len(pair) == 2 and sum(bool(row["gold"]) for row, _ in pair) == 1, "matched_pair_classes")
        if pair[0][1]["source"] == "diagnosis-v6-grid":
            continue  # Whole semantic twins checked by the new grid validator.
        positive = next(row for row, _ in pair if row["gold"])
        negative = next(row for row, _ in pair if not row["gold"])
        require(len(positive["gold"]) == 1, "recipe_pair_gold_count")
        span = positive["gold"][0]
        token = positive["text"][span["start"]:span["end"]]
        if span["label"] == "AGE":
            token = token.split()[0]
        require(token in negative["text"], "recipe_twin_payload")
    with reseeded_v4():
        old_grid = summarize_v4_grid(records, split)
    new_grid = summarize_grid(records, split)
    summary = {"rows": len(records), "clean_rows": clean, "clean_share": clean / len(records),
               "counts": {kind: dict(sorted(count.items())) for kind, count in counts.items()},
               "unique_texts": len(text_hashes), "matched_pairs": len(pairs),
               "regenerated_v4_rows": inherited, "regenerated_v3_rows": regenerated_v3,
               "recipe_families_per_language": len(recipe_families()),
               "age_boundaries": dict(sorted(ages.items())), "regenerated_v4_grid": old_grid,
               "grid": new_grid}
    return summary, tids, templates, text_hashes, values, payloads


def inspect_datasets(datasets):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    require(policy.get("synthetic_only") and set(policy["labels"]) == set(LABELS), "policy_contract")
    observed = {split: summarize(datasets[split], split) for split in SIZES}
    for position, code in ((1, "template_id_leakage"), (2, "template_text_leakage"),
                           (3, "row_text_leakage"), (5, "grid_payload_leakage")):
        require(not observed["train"][position] & observed["dev"][position], code)
    for label in LABELS:
        require(not observed["train"][4][label] & observed["dev"][4][label], "positive_value_pool_leakage")
    return observed
