"""Schema, full-value annotation, coverage cells and paired scope checks."""
from collections import Counter, defaultdict
import re

from train_v2.checks import require
from train_v4.checks import validate_row as validate_v4

from .lexicon import CARDINALS, LOCALE, NUMBERS
from .spec import GRID, LABELS, LANGUAGES, axes

FIELDS = {"case_id", "family", "gold", "language", "split", "text"}


def validate_row(row, split):
    require(isinstance(row, dict) and set(row) == FIELDS, "row_schema")
    require(all(isinstance(row[k], str) and row[k] for k in FIELDS - {"gold"}), "row_fields")
    require(row["split"] == split and row["language"] in LANGUAGES, "row_split_language")
    require(len(row["case_id"]) <= 200 and len(row["family"]) <= 200, "identifier_bounds")
    require(len(row["text"]) <= 2500 and isinstance(row["gold"], list), "row_bounds")
    previous = 0
    for span in row["gold"]:
        require(isinstance(span, dict) and set(span) == {"start", "end", "label"}, "span_schema")
        a, b, label = span["start"], span["end"], span["label"]
        require(type(a) is int and type(b) is int and label in LABELS, "span_types")
        require(previous <= a < b <= len(row["text"]), "span_bounds")
        previous = b
        require(row["text"][a:b] == row["text"][a:b].strip(), "span_boundary_space")
    if not row["family"].startswith("grid-v5."):
        validate_v4(row, split)


def check_grid_row(row, metadata):
    token = metadata["payload"]
    positive = bool(row["gold"])
    component = metadata["component"]
    require(row["text"].count(token) == 1, "grid_payload_occurrence")
    require(len(row["gold"]) == int(positive), "grid_whole_gold_count")
    if positive:
        span = row["gold"][0]
        require(span["label"] == metadata["label"], "grid_label")
        require(row["text"][span["start"]:span["end"]] == token, "whole_value_boundary")
        require(span["start"] == row["text"].index(token), "cue_excluded")
    layout = metadata["layout"]
    if component == "semantic_ages":
        side = row["split"] == "dev"
        unit = LOCALE[row["language"]]["unit"]
        number = token.removesuffix(" " + unit)
        require(number in CARDINALS[row["language"]][side] or
                number in {str(n) for n in NUMBERS[side]}, "semantic_age_cardinal")
        require(token.endswith(" " + unit) == (layout == 1), "age_attached_unit")
    elif component == "signature_greeting_names":
        require((", " in token) == (layout == 3), "name_inverted_layout")
        require((". " in token) == (layout == 1), "name_initial_layout")
    elif component == "postal_object_envelopes":
        separator = (" | ", " / ", "\n")[layout]
        require(token.count(separator) >= 2, "postal_whole_components")
        require(token.endswith(LOCALE[row["language"]]["country"]), "postal_country_tail")
    elif component == "birth_calendar_fields":
        if layout < 2:
            separator = "/" if layout == 0 else " · "
            require(bool(re.fullmatch(r"\d{2}" + re.escape(separator) + r"\d{2}" +
                                      re.escape(separator) + r"\d{4}", token)), "birth_date_layout")
        else:
            require(any(month in token for month in LOCALE[row["language"]]["months"]), "named_birth_month")
    elif component == "balanced_phone_envelopes":
        if positive or not metadata["malformed_serial"]:
            require(token.startswith("(+" + LOCALE[row["language"]]["dial"] + ")"), "balanced_prefix")
            require(token.count("(") == token.count(")"), "phone_balanced_parentheses")
        else:
            require(token.startswith("[+") and token.count("[") != token.count("]"), "malformed_serial")
        require(token.count("\n") == (layout == 1), "phone_field_local_break")
    elif component == "document_alias_sections":
        separator = (" ", " / ", "\n")[layout % 3]
        require(token.count(separator) >= 2, "document_whole_groups")


def summarize_grid(records, split):
    cells = Counter()
    pairs, values = defaultdict(list), defaultdict(set)
    components, evidence = defaultdict(Counter), Counter()
    for row, metadata in records:
        if metadata["source"] != "diagnosis-v6-grid":
            continue
        check_grid_row(row, metadata)
        component = metadata["component"]
        positive = bool(row["gold"])
        key = (component, row["language"], metadata["layout"], metadata["scope"], metadata["sample"], positive)
        cells[key] += 1
        values[key[:4]].add(metadata["personal_payload"])
        pairs[metadata["pair_id"]].append((row, metadata))
        components[component]["positive_rows" if positive else "clean_rows"] += 1
        evidence[f"{component}.layout.{metadata['layout']}"] += 1
        evidence[f"{component}.scope.{metadata['scope']}"] += 1
        if metadata["malformed_serial"]:
            evidence["malformed_serial_rows"] += 1
    expected = {(component, language, layout, scope, sample, positive)
                for component in GRID for language in LANGUAGES
                for layout in range(axes(component, split)[0])
                for scope in range(axes(component, split)[1])
                for sample in range(axes(component, split)[2])
                for positive in (True, False)}
    require(set(cells) == expected and all(n == 1 for n in cells.values()), "full_v5_grid_axes")
    require(all(len(tokens) == axes(key[0], split)[2] for key, tokens in values.items()),
            "grid_distinct_values")
    for pair in pairs.values():
        require(len(pair) == 2 and sum(bool(row["gold"]) for row, _ in pair) == 1, "grid_twins")
        tokens = [metadata["payload"] for _, metadata in pair]
        require("".join(c for c in tokens[0] if c.isalnum()) ==
                "".join(c for c in tokens[1] if c.isalnum()), "grid_twin_semantic_payload")
    positive = sum(c["positive_rows"] for c in components.values())
    clean = sum(c["clean_rows"] for c in components.values())
    require(positive == clean, "grid_side_balance")
    require(evidence["malformed_serial_rows"] > 0, "malformed_serial_coverage")
    return {"rows": positive + clean, "positive_rows": positive, "clean_rows": clean,
            "matched_pairs": len(pairs), "cells": len(expected),
            "components": {component: {"rank": GRID[component][0], **dict(counts),
                                       "axes_per_language_side": list(axes(component, split))}
                           for component, counts in sorted(components.items())},
            "evidence_counts": dict(sorted(evidence.items()))}
