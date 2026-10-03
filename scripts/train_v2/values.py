"""Whole-value constructors from disjoint, family-grouped pool slices."""
import unicodedata

from .numbers import card, grouped, iban
from .pools import POOLS, word
from .spec import LANGUAGES, SEED, SLICES


def person(pool, split, n):
    given = word(pool, "given", split, n)
    surname = word(pool, "surname", split, n // 8)
    other = word(pool, "surname", split, n // 64 + 3)
    title = pool["title"][n % 4]
    particle = pool["particle"][(n // 4) % 4]
    forms = (
        f"{given} {surname}", f"{title} {given} {surname}",
        f"{given[0]}. {surname}", f"{given} {particle} {surname}",
        f"{given} {surname}-{other}", f"{surname}, {given}",
        f"{title} {given[0]}. {particle} {surname}",
        f"{given}-{word(pool, 'given', split, n + 3)} {surname}",
    )
    return forms[(n // 8 + n) % len(forms)]


def address(pool, language, split, n):
    street = word(pool, "street", split, n)
    city = word(pool, "city", split, n // 8)
    house = 1 + n % 280
    postcode = f"{10000 + n * 73:05d}"
    if language == "en":
        postcode = f"VR{1 + n % 90} {n % 10}XX"
    road = f"{house} {street}" if language in ("en", "fr") else f"{street} {house}"
    locality = f"{postcode} {city}"
    country, region = pool["country"], pool["region"]
    unit = f"{pool['floor']} {1 + n % 9}, {pool['unit']} {1 + n % 34}"
    box = f"{pool['box']} {300 + n}, {locality}, {country}"
    recipient = person(pool, split, n + 5)
    forms = (
        f"{road}, {locality}", f"{road}, {unit}, {locality}, {country}",
        f"c/o {recipient}, {road}, {unit}, {locality}, {region}, {country}",
        box, f"{country}, {locality}, {unit}, {road}",
        f"{road}\n{unit}\n{locality}\n{country}",
        f"c/o {recipient}\n{road}\n{unit}\n{pool['box']} {300 + n}\n{locality}\n{country}",
        f"{locality}, {road}, {country}",
    )
    return forms[n % 8]


def ascii_word(value):
    return "".join(c.lower() for c in unicodedata.normalize("NFKD", value)
                   if c.isascii() and c.isalpha())


def birth(pool, language, split, n):
    year = (1950 + n % 50) if split == "train" else (2000 + n % 20)
    month, day = 1 + (n // 3) % 12, 1 + (n // 7) % 28
    month_name = pool["months"][month - 1]
    numeric = f"{month:02d}/{day:02d}/{year}" if language == "en" else f"{day:02d}/{month:02d}/{year}"
    named = f"{month_name} {day}, {year}" if language == "en" else f"{day} {month_name} {year}"
    if language in ("it", "es"):
        named = f"{day} {'de ' if language == 'es' else ''}{month_name} {'de ' if language == 'es' else ''}{year}"
    return (numeric, named, f"{year}-{month:02d}-{day:02d}",
            f"{day:02d}.{month:02d}.{year}")[n % 4]


def phone(pool, language, n):
    digits = f"{700000000 + n * 7919:09d}"
    groups = grouped(digits, (3, 3, 3), "-" if n % 3 == 1 else " ")
    prefix = f"+{pool['dial']}"
    forms = (
        f"{prefix} {groups}", f"{prefix} (0) {groups}",
        f"{prefix} ({digits[:3]}) {digits[3:6]} {digits[6:]}",
        f"{prefix} {groups} {pool['extension']} {10 + n % 900}",
        f"{prefix} (0) {groups} {pool['extension']} {10 + n % 900}",
        f"{prefix} {grouped(digits, (2, 2, 2, 3), '.')} {pool['extension']} {10 + n % 900}",
    )
    # Italy retains its domestic zero; the '(0)' variants are for other locales.
    if language == "it":
        forms = tuple(v.replace("(0) ", "0 ") for v in forms)
    return forms[n % 6]


def value(label, language, split, n):
    lo, hi = SLICES[split]
    if not lo <= n < hi:
        raise ValueError("value_outside_pool_slice")
    pool = POOLS[language]
    number = 10000000 + n * 7919 + LANGUAGES.index(language) * 10000000 + SEED % 100000
    given = ascii_word(word(pool, "given", split, n))
    surname = ascii_word(word(pool, "surname", split, n // 8))
    if label == "PERSONNAME":
        return person(pool, split, n)
    if label == "ADDRESS":
        return address(pool, language, split, n)
    if label == "EMAIL":
        return f"{given}.{surname}.{n}@{language}.example.invalid"
    if label == "USERNAME":
        return f"@{given}_{surname}{n}"
    if label == "TELEPHONENUM":
        return phone(pool, language, n)
    if label == "IBAN":
        return iban(pool["cc"], number, n)
    if label == "ACCOUNTNUM":
        return grouped(f"{number:012d}", ((3, 3, 3, 3), (4, 4, 4), (2, 5, 5))[n % 3], "-" if n % 2 else " ")
    if label == "CREDITCARDNUMBER":
        return card(number, n)
    if label == "DATEOFBIRTH":
        return birth(pool, language, split, n)
    if label == "AGE":
        return str(18 + n % 42 if split == "train" else 60 + n % 40)
    prefixes = {"PASSPORTNUM": "PX", "IDCARDNUM": "ID", "DRIVERLICENSENUM": "DL",
                "TAXNUM": "TX", "SOCIALNUM": "SS", "PERSONALREF": "CR"}
    if label in prefixes:
        raw = prefixes[label] + f"{number:010d}"
        return grouped(raw, ((2, 3, 3, 4), (4, 4, 4), (2, 5, 5))[n % 3], "-" if n % 2 else " ")
    raise ValueError("unknown_value_label")
