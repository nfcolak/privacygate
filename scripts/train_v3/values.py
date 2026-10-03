"""Seeded selection and new shapes using only frozen v2 synthetic value pools."""
import hashlib
import re

from train_v2.build import negative_payload
from train_v2.numbers import grouped, mod97
from train_v2.pools import POOLS
from train_v2.values import value

from .spec import (FAMILY, LANGUAGES, NUMERIC_LABELS, SEED, SHAPE_LABELS, SLICES)


def pick_index(split, language, family, sequence):
    lo, hi = SLICES[split]
    material = f"{SEED}:{split}:{language}:{family}:{sequence}".encode("ascii")
    number = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return lo + number % (hi - lo)


def invalid_iban(token):
    # Change only one check digit, keeping country, separators and total length.
    chars = list(token)
    positions = [i for i, c in enumerate(chars) if c.isalnum()]
    pos = positions[3]
    chars[pos] = str((int(chars[pos]) + 1) % 10)
    result = "".join(chars)
    if mod97(result) == 1:
        raise ValueError("invalid_iban_mutation_failed")
    return result


def ean(language, n):
    body = f"{710000000000 + LANGUAGES.index(language) * 1000000 + n:012d}"
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(body))
    return body + str((-total) % 10)


def shape(kind, language, split, sequence):
    label = SHAPE_LABELS[kind]
    n = pick_index(split, language, FAMILY[label], sequence)
    if kind == "ean":
        token = ean(language, n)
    elif kind in ("serial", "sample", "batch"):
        token = value("PERSONALREF", language, split, n)
    else:
        token = value(label, language, split, n)
    if kind == "iban_invalid":
        token = invalid_iban(token)
    return token, label, n


def numeric(kind, language, split, sequence):
    label = NUMERIC_LABELS[kind]
    n = pick_index(split, language, FAMILY[label], sequence)
    if kind == "statistics":
        return value("AGE", language, split, n), label, n
    tokens = {
        "percentages": f"{n // 8}.{(n % 8) * 10:02d}",
        "version": f"{1 + n // 128}.{n % 128}.{n % 29}",
        "measurements": f"{10 + n} × {20 + n % 137} × {5 + n % 41}",
        "timetable": f"{6 + n // 60:02d}:{n % 60:02d}",
        "scores": f"{n // 20}-{n % 20}",
        "tracking": f"{90000000000000 + LANGUAGES.index(language) * 1000000 + n}",
        "quantity": f"{1000 + n}",
    }
    return tokens[kind], label, n


def catalog_bindings(language, split, sequence, token):
    n = pick_index(split, language, "catalog-fields", sequence)
    pool = POOLS[language]
    v = 0 if split == "train" else 1
    products = {
        "en": (("lamp", "cable", "panel"), ("filter", "valve", "shelf")),
        "de": (("Lampe", "Kabel", "Platte"), ("Filter", "Ventil", "Regal")),
        "fr": (("lampe", "câble", "panneau"), ("filtre", "vanne", "étagère")),
        "it": (("lampada", "cavo", "pannello"), ("filtro", "valvola", "scaffale")),
        "es": (("lámpara", "cable", "panel"), ("filtro", "válvula", "estante")),
    }
    colours = {"en": ("blue", "green"), "de": ("blau", "grün"),
               "fr": ("bleu", "vert"), "it": ("blu", "verde"), "es": ("azul", "verde")}
    return {"x": (token, None), "product": (products[language][v][n % 3], None),
            "sku": (f"AR-{SEED % 10000}-{n:05d}", None),
            "ean": (ean(language, n), None),
            "price": (negative_payload("price", language, split, n), None),
            "size": (negative_payload("dimensions", language, split, n), None),
            "stock": (str(10 + n), None), "colour": (colours[language][v], None),
            "brand": (pool["brand"][v], None)}


def plain_address(language, split, sequence):
    n = pick_index(split, language, "postal", sequence)
    lo, hi = SLICES[split]
    # Forms 0 and 7 are one-line routing addresses without an embedded recipient.
    n = lo + ((n - lo) // 8) * 8 + (0 if sequence % 2 == 0 else 7)
    if n >= hi:
        raise ValueError("boundary_pool_slice")
    return value("ADDRESS", language, split, n)
