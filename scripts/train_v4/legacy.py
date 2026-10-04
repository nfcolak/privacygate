"""Deterministic, family-stratified regeneration of the imported v3 recipe."""
from collections import defaultdict
from contextlib import contextmanager
import hashlib
import random
import re

import train_v3.build as recipe
import train_v3.values as recipe_values
from train_v2.checks import require

from .spec import AGE_UNITS, LANGUAGES, SEED, SIZES, grid_rows


@contextmanager
def reseeded_recipe():
    # Function globals are rebound only in this single-threaded generator process.
    # Imported source files, frozen constructors and lexical slices stay untouched.
    previous = recipe.SEED, recipe_values.SEED
    recipe.SEED = recipe_values.SEED = SEED
    try:
        yield
    finally:
        recipe.SEED, recipe_values.SEED = previous


def seeded_key(scope, item):
    return hashlib.sha256(f"{SEED}:{scope}:{item}".encode()).hexdigest()


def select_stratified(items, count, scope, key):
    require(0 <= count <= len(items), "recipe_budget")
    buckets = defaultdict(list)
    for item in items:
        buckets[key(item)].append(item)
    if not count:
        return []
    quotas = {k: count * len(v) // len(items) for k, v in buckets.items()}
    remainder = sorted(buckets, key=lambda k: (-(count * len(buckets[k]) % len(items)), k))
    for k in remainder[:count - sum(quotas.values())]:
        quotas[k] += 1
    selected = []
    for k in sorted(buckets):
        ordered = sorted(buckets[k], key=lambda x: seeded_key(scope, repr(x)))
        selected.extend(ordered[:quotas[k]])
    return selected


def relabel_age(row):
    gold = []
    expanded = 0
    for span in row["gold"]:
        span = dict(span)
        if span["label"] == "AGE":
            match = re.match(r"[ \t]+(?:" + AGE_UNITS[row["language"]] + r")\b",
                             row["text"][span["end"]:])
            if match:
                span["end"] += match.end()
                expanded += 1
        gold.append(span)
    return {**row, "gold": gold}, expanded


def build_recipe(split):
    with reseeded_recipe():
        candidates = recipe.build_split(split)
    result = []
    for language in LANGUAGES:
        local = [r for r in candidates if r[0]["language"] == language]
        paired = defaultdict(list)
        lone = []
        for record in local:
            pair_id = record[1]["pair_id"]
            if pair_id is None:
                lone.append(record)
            else:
                paired[pair_id].append(record)
        clean_local = sum(not r[0]["gold"] for r in local)
        total = SIZES[split] // len(LANGUAGES) - grid_rows(split, language)
        clean = (SIZES[split] * 45 // 100 // len(LANGUAGES)
                 - grid_rows(split, language, clean=True))
        positive = total - clean
        pair_count = min(clean * len(paired) // clean_local, positive)
        groups = list(paired.values())
        require(all(len(p) == 2 and sum(not r[0]["gold"] for r in p) == 1
                    for p in groups), "recipe_pair_schema")
        selected_pairs = select_stratified(
            groups, pair_count, f"{split}.{language}.pairs", key=lambda p: p[0][0]["family"])
        selected = [r for pair in selected_pairs for r in pair]
        for is_clean, budget in ((True, clean - pair_count), (False, positive - pair_count)):
            pool = [r for r in lone if bool(r[0]["gold"]) != is_clean]
            selected.extend(select_stratified(pool, budget, f"{split}.{language}.{is_clean}",
                                              key=lambda r: r[0]["family"]))
        for row, metadata in selected:
            row, expanded = relabel_age(row)
            tid = metadata["template_id"].replace(f"{split}.{language}.",
                                                  f"{split}.{language}.recipe.", 1)
            row = {**row, "case_id": row["case_id"].replace("-v3-", "-v4-", 1)
                   .split("--", 1)[0] + "--" + tid}
            result.append((row, {**metadata, "template_id": tid,
                                 "source": "regenerated-v3", "age_expanded": expanded}))
    random.Random(f"{SEED}:{split}:recipe-order").shuffle(result)
    return result
