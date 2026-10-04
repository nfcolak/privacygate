"""Deterministic fresh payloads, independent of every stress-set generator."""
import hashlib

from .lexicon import CARDINALS, CITIES, LOCALE, NAMES, NUMBERS, STEMS, SURNAMES
from .spec import DOCUMENT_LABELS, SEED


def index(split, language, component, layout, scope, sample):
    key = f"{SEED}:{split}:{language}:{component}:{layout}:{scope}:{sample}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def age(language, split, layout, scope, sample):
    side = split == "dev"
    words = CARDINALS[language][side]
    # Each lexical cell traverses every cardinal exactly once in seeded order.
    rotation = index(split, language, "age-rotation", layout, scope, 0) % len(words)
    i = (rotation + sample) % len(words)
    if layout == 1:
        number = str(NUMBERS[side][i]) if sample % 2 else words[i]
        return f"{number} {LOCALE[language]['unit']}"
    return words[i]


def name(language, split, layout, scope, sample):
    side = split == "dev"
    given_pool = NAMES[language][side]
    i = (index(split, language, "name-rotation", layout, scope, 0) + sample) % len(given_pool)
    given, other = given_pool[i], given_pool[(i + 1) % len(given_pool)]
    surname = SURNAMES[side][i]
    return (f"{given} {surname}", f"{given[0]}. {surname}",
            f"{given}-{other} {LOCALE[language]['particle']} {surname}",
            f"{surname}, {given}")[layout]


def phone_digits(split, n):
    return str((4600000000 if split == "train" else 8700000000) + n % 900000000)


def table_number(language, split, layout, pattern, sample):
    n = index(split, language, "table-number", layout, pattern, sample)
    digits = phone_digits(split, n)
    return (digits[:3] + "-" + digits[3:6] + "-" + digits[6:],
            "+" + LOCALE[language]["dial"] + " " + digits[:2] + " " + digits[2:6] + " " + digits[6:],
            digits[:4] + "/" + digits[4:8] + "/" + digits[8:])[pattern]


def postal(language, split, separator, order, sample):
    side = split == "dev"
    n = index(split, language, "postal", separator, order, sample)
    grammar = (separator + 2 * order + sample) % 4
    loc = LOCALE[language]
    stem = STEMS[side][grammar]
    road_type = loc["roads"][grammar]
    street = (stem + road_type if language == "de" else
              f"{stem} {road_type}" if language == "en" else f"{road_type} {stem}")
    house = 7 + n % 280
    street = f"{house} {street}" if language in ("en", "fr") else f"{street} {house}"
    postcode = str((41000 if side else 31000) + n % 5000)
    if language == "en":
        postcode = f"{'QY' if side else 'ZX'}{10 + n % 70} {n % 10}ZZ"
    locality = f"{postcode} {CITIES[side][grammar]}"
    parts = [locality, street] if order else [street, locality]
    if grammar in (1, 3):
        parts.insert(1, f"{loc['apartment']} {1 + n % 24}")
    if grammar in (2, 3):
        parts.insert(0, f"{loc['care']} {NAMES[language][side][0]} {SURNAMES[side][0]}")
    parts.append(loc["country"])
    return (" | ", " / ", "\n")[separator].join(parts)


def date(language, split, layout, scope, sample):
    n = index(split, language, "date", layout, scope, sample)
    day, month = 1 + n % 28, 1 + n // 28 % 12
    # Disjoint also from the regenerated recipe's birthday-year pools.
    year = (1924 if split == "train" else 1937) + n // 336 % 5
    if layout == 0:
        a, b = (month, day) if language == "en" else (day, month)
        return f"{a:02d}/{b:02d}/{year}"
    if layout == 1:
        return f"{day:02d} · {month:02d} · {year}"
    named = LOCALE[language]["months"][n // 28 % 4]
    if language == "en":
        return f"{named} {day}, {year}"
    if language == "es":
        return f"{day} de {named} de {year}"
    return f"{day}{'.' if language == 'de' else ''} {named} {year}"


def balanced_phone(language, split, layout, scope, sample):
    n = index(split, language, "balanced-phone", layout, scope, sample)
    d = phone_digits(split, n)
    prefix = f"(+{LOCALE[language]['dial']})"
    if layout == 0:
        return f"{prefix} {d[:3]}.{d[3:6]}.{d[6:]}"
    if layout == 1:
        return f"{prefix} {d[:2]} {d[2:6]}\n{d[6:]}"
    trunk = "0" if language == "it" else "(0)"
    return f"{prefix} {trunk} {d[:3]} {d[3:6]} {d[6:]}"


def document(language, split, layout, scope, sample):
    label_index, separator = divmod(layout, 3)
    n = index(split, language, "document", layout, scope, sample)
    number = str((2400000000 if split == "train" else 9200000000) + n % 700000000)
    if label_index == 0:
        groups = (number[:3], number[3:6], number[6:] + "R")
    elif label_index == 1:
        groups = ("V" + number[:2], number[2:5], number[5:] + "K")
    elif label_index == 2:
        groups = ("MVR" if split == "train" else "AZQ", number[:3], number[3:6], number[6:])
    else:
        groups = (number[:3], number[3:5], number[5:6], number[6:])
    return (" ", " / ", "\n")[separator].join(groups), DOCUMENT_LABELS[label_index]


def payload(component, language, split, layout, scope, sample):
    builders = {"semantic_ages": age, "signature_greeting_names": name,
                "contact_stock_records": table_number, "postal_object_envelopes": postal,
                "birth_calendar_fields": date, "balanced_phone_envelopes": balanced_phone}
    if component == "document_alias_sections":
        return document(language, split, layout, scope, sample)
    from .spec import GRID
    return builders[component](language, split, layout, scope, sample), GRID[component][1]
