"""Independent seeded values for the diagnosis grid; no dataset reads."""
import hashlib

from train_v2.numbers import grouped, iban, mod97
from train_v3.values import invalid_iban

from .pools import DEV_STREETS, LOCALE, LOCATIONS, NAMES, SURNAMES
from .spec import SEED


def index(split, language, component, cell, value_index):
    key = f"{SEED}:{split}:{language}:{component}:{cell}:{value_index}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def name_parts(language, split, n):
    side = split == "dev"
    given = NAMES[language][side][n % 4]
    other = NAMES[language][side][(n + 1) % 4]
    surname = SURNAMES[side][n // 4 % 4]
    return given, other, surname


def whole_name(language, split, n, cell):
    given, other, surname = name_parts(language, split, n)
    locale = LOCALE[language]
    particle = locale["particle"]
    title = locale["titles"][n % 4]
    return (f"{title}{given}-{other} {surname}",
            f"{given[0]}. {other[0]}. {surname}",
            f"{given[0]}.\n{other[0]}. {surname}",
            f"{given}\n{surname}", f"{surname},\n{given}",
            f"{given}-{other} {particle} {surname}")[cell]


def postal(language, split, n, cell, sample=0):
    loc = LOCALE[language]
    street = (DEV_STREETS[language] if split == "dev" else LOCATIONS[language][0])[n % 4]
    city = (LOCATIONS[language][1] if split == "dev" else
            ("Velmorana", "Nuvrantia", "Lomverana", "Zarvellia"))[n // 4 % 4]
    postalcode = f"{(70000 if split == 'train' else 80000) + n % 9999:05d}"
    if language == "en":
        postalcode = f"{'VX' if split == 'train' else 'QZ'}{10 + n % 80} {n % 10}ZZ"
    house = 1 + n % 260
    unit = f"{loc['unit']} {1 + n % 7}, " + {
        "en": "unit", "de": "Wohnung", "fr": "appartement", "it": "interno", "es": "puerta"
    }[language] + f" {1 + n % 30}"
    region = {"en": "province of", "de": "Provinz", "fr": "province de",
              "it": ("provincia di", "provincia della")[n % 2],
              "es": ("provincia de", "provincia del")[n % 2]}[language] + f" Alto {city}"
    given, _, surname = name_parts(language, split, n)
    care = f"{loc['care']} {given} {surname}"
    tail = f"{postalcode} {city}, {region}, {loc['country']}"
    if cell == 2:
        return f"{loc['box']} {20 + n % 900}, {postalcode}, {city}, {loc['country']}"
    if cell == 3:
        if sample % 4 == 0:
            road = f"{street}\n{house}"
        elif sample % 4 == 1:
            road = f"{house}\n{street}"
        elif " " in street:
            road = street.replace(" ", "\n", 1) + f" {house}"
        else:
            road = street[:-3] + "\n" + street[-3:] + f" {house}"
        return f"{road}, {unit}, {tail}"
    if cell == 4:
        care = care.replace(" ", "\n", 1)
    if cell == 5:
        street = {"en": "Rd.", "de": "Str.", "fr": "Av.", "it": "V.le", "es": "Av."}[language]
        return f"{street} {surname} {house}, {tail}"
    road = f"{house} {street}" if cell == 1 else f"{street} {house}"
    return f"{care}, {road}, {unit}, {tail}"


def phone(language, split, n, unknown=False):
    loc = LOCALE[language]
    last = f"{(1000 if split == 'train' else 6000) + n % 3000:04d}"
    national = {"en": f"(0)20 7946 {last}", "de": f"(0)30 555 {last}",
                "fr": f"(0)1 5555 {last}", "it": f"06 5555 {last}",
                "es": f"91 555 {last}"}[language]
    if unknown:
        # A shape-compatible but unallocated national area prefix. Validity is
        # never used to infer whether the value belongs to a person.
        head, rest = national.split(" ", 1)
        head = "(0)" + "0" * len(head[3:]) if head.startswith("(0)") else "00"
        national = head + " " + rest
    return f"+{loc['dial']} {national}"


def multiline_phone(language, split, n, cell):
    layout, extension = divmod(cell, 2)
    token = phone(language, split, n)
    if layout == 0:
        token = token.replace(" ", "\n", 1)
    elif layout == 1:
        last = (1000 if split == "train" else 6000) + n % 3000
        token = f"+{LOCALE[language]['dial']}\n{70 + n % 20} {500 + n % 400} {last}"
    else:
        prefix, first, rest = token.split(" ", 2)
        token = f"{prefix} {first}\n{rest}"
    if extension:
        token += f" {LOCALE[language]['ext']} {100 + n % 800}"
    return token


def reference(split, n, cell):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    head = "".join(alphabet[n // (26 ** i) % 26] for i in range(3))
    sub = "".join(alphabet[n // (26 ** (i + 3)) % 26] for i in range(2))
    number = (2000000 if split == "train" else 7000000) + n % 2000000
    separator = (" / ", "/", " - ")[cell]
    return separator.join((head, sub, str(number)))


def operational(language, split, n, cell):
    shape, regime = divmod(cell, 2)
    if shape == 0:
        number = (710000000000 if split == "train" else 810000000000) + n % 9000000000
        token = iban(LOCALE[language]["cc"], number, 0)
        if regime:
            token = invalid_iban(token)
        return token, "IBAN", {"validation": "invalid" if regime else "valid", "shape": "iban"}
    if shape == 1:
        return phone(language, split, n, bool(regime)), "TELEPHONENUM", {
            "validation": "unknown_or_invalid" if regime else "valid", "shape": "phone"}
    year = (1952 if split == "train" else 2003) + 11 * regime + n % 8
    return f"{1 + n % 28:02d}.{1 + n // 28 % 12:02d}.{year}", "DATEOFBIRTH", {
        "validation": "plausible", "shape": "date", "regime": regime}


def serial(split, n, cell, driver=False):
    if driver:
        head = "".join(chr(65 + n // (26 ** i) % 26) for i in (0, 1))
        digits = str((200000000 if split == "train" else 800000000) + n % 100000000)
        return head + (" / " if cell == 0 else "/") + digits
    digits = str((710000000000 if split == "train" else 810000000000) + n % 9000000000)
    return grouped(digits, (3, 3, 3, 3), (" ", "-", ".", "")[cell])
