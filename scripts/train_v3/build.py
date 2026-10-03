"""Regenerate v2 families, then add matched hard negatives and boundary triples."""
import random

from train_v2.build import negative_payload
from train_v2.render import letter, render
from train_v2.templates_neg import negative_template
from train_v2.templates_pos import positive_template
from train_v2.templates_twin import twin_template
from train_v2.values import value

from .spec import (BOUNDARY_ROWS, FAMILY, LABELS, LANGUAGES, LEGACY_CLEAN,
                   NEGATIVE_KINDS, NEW_CLEAN_PER_GROUP, NEW_GROUPS, SEED,
                   SIZES, TWIN_LABELS, template_id)
from .templates_catalog import catalog_template
from .templates_near import boundary_template, near_template
from .templates_numeric import numeric_template, patient_template
from .values import catalog_bindings, numeric, pick_index, plain_address, shape


def linked_template(language, split, label):
    if label == "PERSONALREF":
        return patient_template(language, split)
    return positive_template(language, split, label, 0)


def build_split(split):
    records = []
    for language in LANGUAGES:
        sequence = 0

        def add(family, kind, template, bindings, pair=None, variant=0):
            nonlocal sequence
            sequence += 1
            tid = template_id(split, language, kind, variant)
            text, gold = render(template, bindings)
            row = {"case_id": f"{split}-v3-{language}-{sequence:05d}--{tid}",
                   "family": family, "gold": gold, "language": language,
                   "split": split, "text": text}
            metadata = {"template_id": tid, "template": template, "pair_id": pair}
            records.append((row, metadata))

        # Frozen v2 renderers/pools are reused; row selection and order use SEED v3.
        for i in range(LEGACY_CLEAN[split]):
            kind = NEGATIVE_KINDS[i % len(NEGATIVE_KINDS)]
            group = FAMILY[TWIN_LABELS[kind]] if kind in TWIN_LABELS else "hard-negative"
            n = pick_index(split, language, group, i)
            token = negative_payload(kind, language, split, n)
            pair = f"{split}.{language}.legacy.{i}" if kind in TWIN_LABELS else None
            add("hard-negative." + kind, "legacy.neg." + kind,
                negative_template(language, split, kind), {"x": (token, None)}, pair)
            if pair:
                template = (positive_template(language, split, "DATEOFBIRTH", 0)
                            if split == "dev" and kind == "date"
                            else twin_template(language, split, kind))
                # V2's English dev date twin duplicates a train positive phrase;
                # reuse its genuinely held-out dev positive renderer instead.
                add("person-linked." + kind, "legacy.twin." + kind,
                    template, {"x": (token, TWIN_LABELS[kind])}, pair)

        for group, kinds in NEW_GROUPS.items():
            for i in range(NEW_CLEAN_PER_GROUP[split]):
                kind = kinds[i % len(kinds)]
                # Alternates catalog line/table independently of shape kind.
                variant = (i // len(kinds)) % 2 if group == "catalog" else 0
                token, label, _ = (numeric if group == "numeric" else shape)(
                    kind, language, split, i + 10000)
                pair = f"{split}.{language}.{group}.{i}"
                suffix = group + "." + kind
                if group == "catalog":
                    template = catalog_template(language, split, variant)
                    bindings = catalog_bindings(language, split, i, token)
                    format_name = ".line" if variant == 0 else ".table"
                    # The positive keeps ALL goods values clean and adds one
                    # person-linked occurrence of the very same lookalike.
                    linked = linked_template(language, split, label).replace("{x}", "{personal}")
                    add("target.clean." + suffix + format_name, "target.neg." + suffix,
                        template, bindings, pair, variant)
                    add("target.person-linked." + suffix + format_name, "target.twin." + suffix,
                        template + "\n" + linked,
                        {**bindings, "personal": (token, label)}, pair, variant)
                else:
                    template = (numeric_template if group == "numeric" else near_template)(
                        language, split, kind)
                    add("target.clean." + suffix, "target.neg." + suffix,
                        template, {"x": (token, None)}, pair)
                    add("target.person-linked." + suffix, "target.twin." + suffix,
                        linked_template(language, split, label), {"x": (token, label)}, pair)

        for i in range(BOUNDARY_ROWS[split]):
            bindings = {
                "name": (value("PERSONNAME", language, split,
                               pick_index(split, language, "identity", i + 20000)), "PERSONNAME"),
                "address": (plain_address(language, split, i + 20000), "ADDRESS"),
                "phone": (value("TELEPHONENUM", language, split,
                                pick_index(split, language, "contact", i + 20000)), "TELEPHONENUM"),
            }
            add("boundary.name-address-phone", "boundary.triple",
                boundary_template(language, split), bindings)

        remaining = SIZES[split] // len(LANGUAGES) - sequence
        if remaining < len(LABELS) * 2 + 2:
            raise ValueError("legacy_positive_budget")
        direct = 0
        for i in range(remaining):
            if i % 12 == 11:
                # Rendered by v2, with v3's seed-sensitive index callback.
                text, gold = letter(language, split, i + 30000, pick_index)
                tid = template_id(split, language, "legacy.letter")
                sequence += 1
                row = {"case_id": f"{split}-v3-{language}-{sequence:05d}--{tid}",
                       "family": "letter.repeated-values", "gold": gold,
                       "language": language, "split": split, "text": text}
                records.append((row, {"template_id": tid, "template": None, "pair_id": None}))
                continue
            label = LABELS[direct % len(LABELS)]
            variant = (direct // len(LABELS)) % 2
            direct += 1
            token = value(label, language, split,
                          pick_index(split, language, FAMILY[label], i + 30000))
            add(FAMILY[label], "legacy.pos." + label,
                positive_template(language, split, label, variant), {"x": (token, label)},
                variant=variant)
    random.Random(f"{SEED}:{split}:ordering").shuffle(records)
    return records
