"""Import and regenerate the complete v4 recipe; never read previous JSONL."""
from contextlib import contextmanager
import random

import train_v4.build as v4_build
import train_v4.legacy as v4_legacy
import train_v4.values as v4_values
from train_v4.spec import grid_rows as v4_grid_rows

from .grid import build_grid
from .spec import SEED, SIZES, grid_rows


def total_grid_rows(split, language, clean=False):
    return v4_grid_rows(split, language, clean) + grid_rows(split, language, clean)


@contextmanager
def reseeded_v4():
    # Rebinding function globals is process-local and restored even on failure.
    # No imported source file or frozen v2 constructor/pool is modified.
    overrides = ((v4_build, "SEED", SEED), (v4_values, "SEED", SEED),
                 (v4_legacy, "SEED", SEED), (v4_legacy, "SIZES", SIZES),
                 (v4_legacy, "grid_rows", total_grid_rows),
                 # More fresh positive candidates, not oversampling old rows.
                 (v4_legacy.recipe, "SIZES", {"train": 28000, "dev": 3000}))
    previous = [(module, key, getattr(module, key)) for module, key, _ in overrides]
    try:
        for module, key, value in overrides:
            setattr(module, key, value)
        yield
    finally:
        for module, key, value in previous:
            setattr(module, key, value)


def build_split(split):
    with reseeded_v4():
        inherited = v4_legacy.build_recipe(split) + v4_build.build_grid(split)
    records = []
    for row, metadata in inherited:
        tid = metadata["template_id"].replace(f"{split}.{row['language']}.",
                                              f"{split}.{row['language']}.v5reuse.", 1)
        base_id = row["case_id"].split("--", 1)[0].replace("-v4-", "-v5-", 1)
        records.append(({**row, "case_id": base_id + "--" + tid},
                        {**metadata, "template_id": tid, "provenance": "regenerated-v4"}))
    records.extend(build_grid(split))
    random.Random(f"{SEED}:{split}:v5-order").shuffle(records)
    return records
