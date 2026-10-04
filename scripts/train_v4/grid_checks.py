"""Value-free checks of every grid cell and original whole-value envelope."""
from collections import Counter, defaultdict
import re

from train_v2.checks import require
from train_v2.numbers import mod97

from .spec import GRID, GRID_AXES


def check_grid_value(row, metadata):
    component = metadata["component"]
    _, _, label, _ = GRID[component]
    cell = metadata["cell"]
    if label == "typed":
        label = ("IBAN", "TELEPHONENUM", "DATEOFBIRTH")[cell // 2]
    require(len(row["gold"]) == (label is not None), "grid_gold_count")
    if label is None:
        from .build import grid_value
        token = grid_value(component, row["language"], row["split"], cell, metadata["sample"])[0]
        require(row["text"].count(token) == 1, "clean_grid_whole_payload")
        typed_twins = {
            "operational_reference_twins": ("personal_reference_formats", "PERSONALREF"),
            "clean_operational_shape_twins": ("person_linked_operational_shape_twins",
                                              ("IBAN", "TELEPHONENUM", "DATEOFBIRTH")[cell // 2]),
            "multiline_operational_phone_twins": ("multiline_personal_phones", "TELEPHONENUM"),
            "social_number_operational_twins": ("social_number_group_layouts", "SOCIALNUM"),
            "french_driver_operational_twins": ("french_driver_serial_layouts", "DRIVERLICENSENUM"),
        }
        if component in typed_twins:
            positive_component, positive_label = typed_twins[component]
            start = row["text"].index(token)
            shadow = {**row, "gold": [{"start": start, "end": start + len(token),
                                      "label": positive_label}]}
            check_grid_value(shadow, {**metadata, "component": positive_component})
        return
    span = row["gold"][0]
    require(span["label"] == label, "grid_gold_label")
    token = row["text"][span["start"]:span["end"]]
    if component == "postal_envelopes":
        require(token.count("\n") == (cell in (3, 4)), "postal_ocr_line_count")
        if cell == 2:
            require(bool(re.search(r", [A-Z0-9]+(?: \d[A-Z]{2})?, [A-Z]", token)),
                    "postal_box_comma_locality")
    elif component == "whole_person_names":
        require(token.count("\n") == (cell in (2, 3, 4)), "name_ocr_line_count")
        if cell == 0:
            require(bool(re.match(r"[A-Z][a-z.]*\.[A-Z]", token)), "compact_title")
        if cell == 4:
            require(",\n" in token, "reversed_newline_name")
    elif component == "personal_reference_formats":
        sep = (" / ", "/", " - ")[cell]
        require(bool(re.fullmatch(r"[A-Z]{3}" + re.escape(sep) + r"[A-Z]{2}"
                                 + re.escape(sep) + r"\d{7}", token)), "reference_layout")
    elif component == "person_linked_operational_shape_twins":
        shape, regime = divmod(cell, 2)
        if shape == 0:
            require((mod97(token) == 1) == (regime == 0), "grid_iban_regime")
        if shape == 2:
            require(bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", token)), "grid_date_shape")
    elif component == "multiline_personal_phones":
        require(token.count("\n") == 1 and token.startswith("+"), "multiline_phone_envelope")
        require(bool(re.search(r"[A-Za-zéóü]+\.? \d+$", token)) == bool(cell % 2),
                "multiline_extension")
    elif component == "social_number_group_layouts":
        pattern = (r"\d{3} \d{3} \d{3} \d{3}", r"\d{3}-\d{3}-\d{3}-\d{3}",
                   r"\d{3}\.\d{3}\.\d{3}\.\d{3}", r"\d{12}")[cell]
        require(bool(re.fullmatch(pattern, token)), "social_layout")
    elif component == "french_driver_serial_layouts":
        require(bool(re.fullmatch(r"[A-Z]{2}" + (r" / " if cell == 0 else "/")
                                 + r"\d{9}", token)), "driver_layout")


def summarize_grid(records, split):
    values, paraphrases = GRID_AXES[split]
    axes = Counter()
    evidence = Counter()
    cell_values, cell_templates = defaultdict(set), defaultdict(set)
    from .build import grid_value
    for row, metadata in records:
        if metadata["source"] != "diagnosis-grid":
            continue
        check_grid_value(row, metadata)
        component = metadata["component"]
        axes[(component, row["language"], metadata["cell"],
              metadata["sample"], metadata["paraphrase"])] += 1
        cell_key = component, row["language"], metadata["cell"]
        cell_values[cell_key].add(grid_value(component, row["language"], split,
                                            metadata["cell"], metadata["sample"])[0])
        cell_templates[cell_key].add(metadata["template"])
        for key, value in metadata["evidence"].items():
            evidence[f"{component}.{key}.{value}"] += 1
    expected = {(component, language, cell, sample, paraphrase)
                for component, (_, cells, _, languages) in GRID.items()
                for language in languages for cell in range(cells)
                for sample in range(values) for paraphrase in range(paraphrases)}
    require(set(axes) == expected and all(n == 1 for n in axes.values()), "full_grid_axes")
    require(all(len(v) == values for v in cell_values.values()), "grid_distinct_values_per_cell")
    require(all(len(v) == paraphrases for v in cell_templates.values()), "grid_distinct_paraphrases_per_cell")
    components = {}
    for component, (rank, cells, label, languages) in GRID.items():
        per_language = cells * values * paraphrases
        components[component] = {"rank": rank, "label": label or "empty",
                                 "cells_per_language": cells, "samples_per_cell": values * paraphrases,
                                 "rows": per_language * len(languages),
                                 "language_counts": {lang: per_language for lang in languages}}
    positive = sum(info["rows"] for info in components.values() if info["label"] != "empty")
    clean = sum(info["rows"] for info in components.values() if info["label"] == "empty")
    return {"components": components, "positive_rows": positive, "clean_rows": clean,
            "rows": positive + clean, "cells": len(expected) // (values * paraphrases),
            "evidence_counts": dict(sorted(evidence.items()))}
