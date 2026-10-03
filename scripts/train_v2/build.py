"""Finite catalogs and family-wise held-out values; no random row splitting."""
import hashlib
import random

from .pools import POOLS
from .render import letter, render
from .spec import (FAMILY, LABELS, LANGUAGES, NEGATIVE_KINDS, SEED, SIZES,
                   SLICES, TWIN_LABELS, template_id)
from .templates_neg import negative_template
from .templates_pos import positive_template
from .templates_twin import twin_template
from .values import value


def pick_index(split, language, family, sequence):
    lo, hi = SLICES[split]
    material = f"{SEED}:{split}:{language}:{family}:{sequence}".encode("ascii")
    integer = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return lo + integer % (hi - lo)


def negative_payload(kind, language, split, n):
    if kind in TWIN_LABELS:
        label = TWIN_LABELS[kind]
        if kind == "place" and n % 8 in (2, 6):
            n += 1  # Public venues cannot contain a c/o natural-person recipient.
        if kind in ("room", "gate", "platform"):
            return str(1 + n)
        token = value(label, language, split, n)
        if kind == "time":
            token += f" {8 + n % 12:02d}:{n % 60:02d}"
        return token
    pool = POOLS[language]
    if kind == "version":
        return f"{1 + n % 20}.{n % 12}.{n % 30}"
    if kind == "price":
        amount = f"{10 + n % 500}.{n % 100:02d}"
        if language != "en":
            amount = amount.replace(".", ",")
        return amount + (" GBP" if language == "en" else " EUR")
    if kind == "dimensions":
        return f"{10 + n % 200} × {20 + n % 150} × {5 + n % 40} cm"
    if kind in ("brand", "organisation"):
        # These invented organisational names are not person names.
        return pool[kind][0 if split == "train" else 1]
    if kind == "quantity":
        return str(100 + n * 3)
    raise ValueError("unknown_negative_kind")


def catalog(split):
    result = []
    for language in LANGUAGES:
        result.extend(template_id(split, language, "neg." + k) for k in NEGATIVE_KINDS)
        result.extend(template_id(split, language, "twin." + k) for k in TWIN_LABELS)
        result.extend(template_id(split, language, "pos." + label, v)
                      for label in LABELS for v in (0, 1))
        result.append(template_id(split, language, "letter"))
    return sorted(result)


def build_split(split):
    records = []
    per_language = SIZES[split] // len(LANGUAGES)
    clean_count = per_language * 2 // 5
    for language in LANGUAGES:
        sequence = 0
        positives = 0

        def add(family, tid, text, gold, pair=None):
            nonlocal sequence
            sequence += 1
            row = {"case_id": f"{split}-v2-{language}-{sequence:05d}--{tid}",
                   "family": family, "gold": gold, "language": language,
                   "split": split, "text": text}
            metadata = {"template_id": tid, "pair_id": pair}
            records.append((row, metadata))

        for i in range(clean_count):
            kind = NEGATIVE_KINDS[i % len(NEGATIVE_KINDS)]
            group = FAMILY[TWIN_LABELS[kind]] if kind in TWIN_LABELS else "hard-negative"
            n = pick_index(split, language, group, i)
            token = negative_payload(kind, language, split, n)
            text, gold = render(negative_template(language, split, kind), {"x": (token, None)})
            pair = f"{split}.{language}.{i}" if kind in TWIN_LABELS else None
            add("hard-negative." + kind, template_id(split, language, "neg." + kind),
                text, gold, pair)
            if kind in TWIN_LABELS:
                text, gold = render(twin_template(language, split, kind),
                                    {"x": (token, TWIN_LABELS[kind])})
                add("person-linked." + kind, template_id(split, language, "twin." + kind),
                    text, gold, pair)
                positives += 1
        direct = 0
        for i in range(per_language - clean_count - positives):
            if i % 12 == 11:
                text, gold = letter(language, split, i, pick_index)
                add("letter.repeated-values", template_id(split, language, "letter"), text, gold)
                continue
            label = LABELS[direct % len(LABELS)]
            variant = (direct // len(LABELS)) % 2
            direct += 1
            n = pick_index(split, language, FAMILY[label], i + clean_count)
            token = value(label, language, split, n)
            text, gold = render(positive_template(language, split, label, variant),
                                {"x": (token, label)})
            add(FAMILY[label], template_id(split, language, "pos." + label, variant), text, gold)
    random.Random(f"{SEED}:{split}:ordering").shuffle(records)
    return records
