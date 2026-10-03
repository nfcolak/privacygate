"""Whole-value structured candidates, on original Python string offsets.

Phone dependency: phonenumberslite==9.0.40 (imports as phonenumbers,
Apache-2.0). Import is lazy; missing metadata is an explicit value-free error.
No python-stdnum, network, model, logging, or value-bearing output is used.
Validation is format/checksum evidence, NOT an existence/ownership assertion
and NEVER a veto. Explicit personal fields retain invalid/unknown values.
"""
import re

# Country length and BBAN grammar; national account checks are not required.
_IBAN_SPECS = {
    "DE": (22, r"[0-9]{18}"), "AT": (20, r"[0-9]{16}"),
    "CH": (21, r"[0-9]{5}[A-Z0-9]{12}"),
    "FR": (27, r"[0-9]{10}[A-Z0-9]{11}[0-9]{2}"),
    "IT": (27, r"[A-Z][0-9]{10}[A-Z0-9]{12}"),
    "ES": (24, r"[0-9]{20}"), "NL": (18, r"[A-Z]{4}[0-9]{10}"),
    "BE": (16, r"[0-9]{12}"), "LU": (20, r"[0-9]{3}[A-Z0-9]{13}"),
    "PT": (25, r"[0-9]{21}"), "GB": (22, r"[A-Z]{4}[0-9]{14}"),
    "IE": (22, r"[A-Z]{4}[0-9]{14}"), "PL": (28, r"[0-9]{24}"),
}
_REGIONS = ("DE", "AT", "CH", "FR", "IT", "ES", "GB", "US")
_SEP = " \t\r\n\u00a0\u202f.-/\u2010\u2011\u2013"
_COMPACT_RE = re.compile("[" + re.escape(_SEP) + "]+")
_GAP_RE = re.compile(r"[\s:=#]*")
_SUFFIX = (r"(?:[ \t-]*(?:number|nummer|numéro|numero|número|"
           r"no\.?|nr\.?|n[°º]\.?|n\.[º°]|id|code|ref\.?))?")
# Field keys are intentionally specific: never bare number, ID, ref, or pass.
_KEYS = {
    "IBAN": r"iban",
    "TELEPHONENUM": (r"phone(?:[ -]*number)?|telephone|téléphone|tel\.?|tél\.?|"
                     r"telefon(?:nummer)?|rufnummer|mobil(?:nummer)?|mobile|"
                     r"cell(?:ulare)?|telefono|teléfono|móvil|handy|fax"),
    "PASSPORTNUM": (r"reisepass(?:nummer)?|pass[ -]*nr\.?|passport|"
                    r"n[°º]\s+de\s+passeport|(?:numéro\s+de\s+)?passeport|"
                    r"(?:numero\s+(?:di\s+)?)?passaporto|"
                    r"(?:número\s+de\s+)?pasaporte"),
    "IDCARDNUM": (r"personalausweis(?:nummer)?|ausweis[ -]*nr\.?|"
                  r"(?:national\s+)?id\s+card|identity\s+card|"
                  r"carte\s+d['’]identité|cni|carta\s+d['’]identità|"
                  r"dni|nie|nif"),
    "DRIVERLICENSENUM": (r"führerschein(?:nummer)?|driv(?:ing|er['’]?s?)\s+"
                         r"licen[cs]e|permis\s+de\s+conduire|"
                         r"patente(?:\s+di\s+guida)?|permiso\s+de\s+conducir"),
    "TAXNUM": (r"steuer[ -]*id|idnr\.?|steuernummer|tax(?:payer)?\s+"
               r"(?:id|number|no\.?)|numéro\s+fiscal|codice\s+fiscale"),
    "SOCIALNUM": (r"svnr\.?|ahv(?:[ -]*(?:nummer|nr\.?))?|nir|"
                  r"numéro\s+de\s+sécurité\s+sociale|social\s+security"
                  r"(?:\s+(?:number|no\.?))?|nss|nuss|ssn|"
                  r"ni\s+(?:number|no\.?)|national\s+insurance(?:\s+number)?"),
    "ACCOUNTNUM": (r"kontonummer|konto(?:[ -]*nr\.?)?|"
                   r"(?:bank\s+)?account(?:\s+(?:number|no\.?))?|"
                   r"(?:numéro\s+de\s+)?compte(?:\s+bancaire)?|"
                   r"(?:numero\s+di\s+)?conto(?:\s+corrente)?|"
                   r"(?:número\s+de\s+)?cuenta(?:\s+bancaria)?"),
    "CREDITCARDNUMBER": (r"(?:credit|debit)\s+card(?:\s+number)?|"
                         r"card\s+(?:number|no\.?)|kreditkarte(?:nnummer)?|"
                         r"kartennummer|carte\s+bancaire|numéro\s+de\s+carte|"
                         r"carta\s+di\s+(?:credito|debito)|"
                         r"tarjeta(?:\s+(?:de\s+)?(?:crédito|débito|bancaria))?"),
    "PERSONALREF": (r"kundennummer|kunden[ -]*nr\.?|customer|"
                    r"n[°º]\s+client|(?:numéro\s+de\s+)?client|"
                    r"codice\s+cliente|n\.[º°]\s+de\s+cliente|"
                    r"número\s+de\s+cliente|aktenzeichen|case|patient(?:en)?|"
                    r"paziente|paciente|membership|member|mitgliedsnummer"),
}
_CUES = re.compile(r"(?<!\w)(?:" + "|".join(
    "(?P<" + label + ">(?:" + pattern + ")" + _SUFFIX + ")"
    for label, pattern in _KEYS.items()) + r")(?!\w)", re.IGNORECASE)
_CLEAN_CUE = re.compile(
    r"(?<!\w)(?:invoice|order|product|sku|rechnung(?:snummer)?|"
    r"bestellung|artikel|facture|commande|produit|fattura|ordine|prodotto|"
    r"factura|pedido|producto|dimensions?|abmessungen|maße|room|zimmer|"
    r"salle|stanza|habitación|price|preis|prix|prezzo|precio|date|datum|"
    r"calendar\s+date|quantity|menge)" + _SUFFIX + r"(?!\w)", re.IGNORECASE)
_PIECE = re.compile(r"[A-Za-z0-9]+")
_STOP = frozenset(("OK", "EUR", "USD", "CHF", "GBP", "AND", "UND", "ET",
                   "THE", "FOR", "DER", "DIE", "DAS", "VON", "MIT", "DEL",
                   "DES", "LES", "NEXT", "THEN", "NO", "NR", "NIF", "DNI"))
_EXT = re.compile(r"[ \t,;/-]*(?:extension|ext\.?|x|durchwahl|dw\.?|"
                  r"poste|interno|int\.?|anexo|#)[ \t:=.-]*[0-9]{1,8}(?![0-9])",
                  re.IGNORECASE)
_PHONE_BASE = re.compile(r"(?<![A-Za-z0-9])(?:\+|\()?[0-9]"
                         r"[0-9() \t\u00a0\u202f.\-]{4,94}[0-9)](?![A-Za-z0-9])")
_ISEP = r"[ \t\u00a0\u202f.\-\u2010\u2011\u2013]{0,6}"
_IBAN_START = re.compile(r"(?<![A-Za-z0-9])([A-Za-z])" + _ISEP +
                         r"([A-Za-z])" + _ISEP + r"[0-9]" + _ISEP + r"[0-9]")


def _compact(value):
    return _COMPACT_RE.sub("", value).upper()


def _mod97(value):
    remainder = 0
    for char in value:
        digits = char if char.isdigit() else str(ord(char) - ord("A") + 10)
        for digit in digits:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder


def _iban_status(value):
    core = _compact(value)
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}", core):
        return "invalid"
    spec = _IBAN_SPECS.get(core[:2])
    if spec is None:
        return "unknown"
    length, bban = spec
    if len(core) != length or not re.fullmatch(bban, core[4:]):
        return "invalid"
    return "valid" if _mod97(core[4:] + core[:4]) == 1 else "invalid"


def _luhn(core):
    total = 0
    for index, char in enumerate(reversed(core)):
        digit = int(char)
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _dni_status(core):
    if re.fullmatch(r"[XYZ][0-9]{7}[A-Z]", core):
        core = str("XYZ".index(core[0])) + core[1:]
    if not re.fullmatch(r"[0-9]{8}[A-Z]", core):
        return None
    return "valid" if "TRWAGMYFPDXBNJZSQVHLCKE"[int(core[:8]) % 23] == core[-1] else "invalid"


def _fiscal_status(core):
    if not re.fullmatch(r"[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST]"
                        r"[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]", core):
        return None
    # Odd positions in the Italian fiscal code have a dedicated lookup;
    # even positions use digit values / alphabet indices. Omocodia letters
    # are checked as printed letters, not converted before the checksum.
    odd_digits = (1, 0, 5, 7, 9, 13, 15, 17, 19, 21)
    odd_letters = (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18,
                   20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23)
    total = 0
    for index, char in enumerate(core[:-1]):
        if index % 2 == 0:
            total += odd_digits[int(char)] if char.isdigit() else odd_letters[ord(char) - 65]
        else:
            total += int(char) if char.isdigit() else ord(char) - 65
    return "valid" if chr(65 + total % 26) == core[-1] else "invalid"


def _identifier_status(value, label):
    core = _compact(value)
    if not re.fullmatch(r"[A-Z0-9]{3,34}", core) or sum(c.isdigit() for c in core) < 2:
        return "invalid"
    if label == "IBAN":
        return _iban_status(value)
    if label == "CREDITCARDNUMBER":
        if not re.fullmatch(r"[0-9]{13,19}", core):
            return "invalid"
        return "valid" if _luhn(core) else "invalid"
    if label in ("IDCARDNUM", "TAXNUM"):
        status = _dni_status(core)
        if status is not None:
            return status
    if label == "TAXNUM":
        status = _fiscal_status(core)
        return status if status is not None else "unknown"
    if label == "SOCIALNUM":
        if re.fullmatch(r"[0-9]{3}-[0-9]{2}-[0-9]{4}", value.strip()):
            return "valid" if (core[:3] not in ("000", "666") and
                               int(core[:3]) < 900 and core[3:5] != "00" and
                               core[5:] != "0000") else "invalid"
        if len(core) == 13 and core.isdigit() and core.startswith("756"):
            total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(core[:-1]))
            return "valid" if (total + int(core[-1])) % 10 == 0 else "invalid"
        if len(core) == 15 and core.isdigit() and core[0] in "12":
            return "valid" if 97 - int(core[:13]) % 97 == int(core[-2:]) else "invalid"
        return "unknown"
    if label == "ACCOUNTNUM":
        if re.match(r"[A-Z]{2}[0-9]{2}", core):
            return _iban_status(value)
        # Domestic schemes are unknown without country metadata/checksums.
        return "unknown"
    if label in ("PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM"):
        # Bounded generic SERIAL FORMAT only; no unaudited national checksum.
        return "valid" if 5 <= len(core) <= 32 else "invalid"
    if label == "PERSONALREF":
        return "valid" if len(core) <= 32 else "invalid"
    return "n/a"


def _phone_library():
    try:
        import phonenumbers
    except ImportError:
        raise RuntimeError("structured_phone_dependency_missing") from None
    return phonenumbers


def _phone_status(value, phones):
    ext = _EXT.search(value)
    base = value[:ext.start()] if ext else value
    # Optional international trunk display marker: NOT Italy's leading zero.
    base = re.sub(r"^(\+|00)(49|43|41|33|34|44|1)([ \t.\-]*)\(0\)",
                  r"\1\2\3", base.strip())
    possible = False
    for region in _REGIONS:
        try:
            number = phones.parse(base, region)
        except phones.NumberParseException:
            continue
        if phones.is_valid_number(number):
            return "valid"
        possible = possible or phones.is_possible_number(number)
    return "invalid" if possible or any(c.isdigit() for c in base) else "unknown"


def _bound_key(text, start, label=None, clean=False):
    left = max(0, start - 120)
    for match in (_CLEAN_CUE if clean else _CUES).finditer(text, left, start):
        if label is not None and match.lastgroup != label:
            continue
        if _GAP_RE.fullmatch(text[match.end():start]):
            return True
    return False


def _candidate(text, start, end, label, status):
    personal = _bound_key(text, start, label)
    return {"start": start, "end": end, "label": label, "source": "structured",
            "score": None, "validation": status,
            "context": "personal" if personal else "unknown",
            "protected": personal and status == "valid", "stage": "raw"}


def _value_end(text, start):
    """Bounded digit-bearing serial tokens; separators are inside, not padding."""
    cursor, end, core_count, digits = start, start, 0, 0
    while cursor < len(text) and cursor - start <= 100:
        token = _PIECE.match(text, cursor)
        if token is None:
            break
        piece = token.group()
        has_digit = any(c.isdigit() for c in piece)
        if not has_digit:
            if (not piece.isupper() or piece in _STOP or
                    len(piece) > (6 if end == start else 3)):
                break
        # Do not consume the next field, even when its key resembles a prefix.
        if _CUES.match(text, cursor) or text[token.end():token.end() + 1] in (":", "="):
            break
        if core_count + len(piece) > 34:
            break
        end = token.end()
        core_count += len(piece)
        digits += sum(c.isdigit() for c in piece)
        cursor = end
        while cursor < len(text) and text[cursor] in _SEP and cursor - end < 12:
            cursor += 1
        if "\n\n" in text[end:cursor]:
            break
    return end if digits >= 2 and core_count >= 3 else start


def _iban_candidates(text):
    result = []
    for match in _IBAN_START.finditer(text):
        country = (match.group(1) + match.group(2)).upper()
        spec = _IBAN_SPECS.get(country)
        if spec is None:
            continue  # Unknown countries are still recognized in explicit fields.
        start, cursor, count = match.start(), match.start(), 0
        while cursor < len(text) and cursor - start < 100:
            char = text[cursor]
            if char.isascii() and char.isalnum():
                count += 1
                cursor += 1
                if count == spec[0]:
                    if cursor == len(text) or not (text[cursor].isascii() and text[cursor].isalnum()):
                        core = _compact(text[start:cursor])
                        # A country-like product prefix must not harvest prose
                        # into its BBAN. Malformed explicit IBAN fields are
                        # retained independently by the keyword scanner.
                        if re.fullmatch(spec[1], core[4:]):
                            status = _iban_status(text[start:cursor])
                            result.append(_candidate(text, start, cursor, "IBAN", status))
                    break
            elif char in _SEP and char not in "/\r\n":
                cursor += 1
            else:
                break
    return result


def _phone_end(text, end):
    extension = _EXT.match(text, end)
    return extension.end() if extension else end


def _phone_candidates(text, fields, phones):
    result, seen = [], set()

    def add(start, end, anchored=False):
        end = _phone_end(text, end)
        key = (start, end)
        if key in seen:
            return
        seen.add(key)
        value = text[start:end]
        base = value.split("\n", 1)[0]
        digit_count = sum(c.isdigit() for c in (_EXT.split(base, 1)[0]))
        if not 7 <= digit_count <= 17:
            return
        if _bound_key(text, start, clean=True) and not anchored:
            return
        status = _phone_status(value, phones)
        grouped = len(re.findall(r"[0-9]+", base)) >= 2
        international = base.startswith("+") or base.startswith("00")
        if not anchored and not international and (status != "valid" or not grouped):
            return
        result.append(_candidate(text, start, end, "TELEPHONENUM", status))

    for start in fields:
        match = _PHONE_BASE.match(text, start)
        if match:
            add(match.start(), match.end(), anchored=True)
    # Boundary pass completes trunk markers, parentheses, dots and extensions;
    # only explicit international shapes are promoted without a field here.
    for match in _PHONE_BASE.finditer(text):
        if match.group().startswith(("+", "00")):
            add(match.start(), match.end())
    for leniency in (phones.Leniency.VALID, phones.Leniency.POSSIBLE):
        for region in _REGIONS:
            matcher = phones.PhoneNumberMatcher(text, region, leniency=leniency, max_tries=1000)
            for match in matcher:
                anchored = _bound_key(text, match.start, "TELEPHONENUM")
                if leniency == phones.Leniency.POSSIBLE and not anchored:
                    continue
                add(match.start, match.end, anchored=anchored)
            if getattr(matcher, "_max_tries", 1) <= 0:
                raise RuntimeError("structured_phone_budget_exhausted")
    return result


def detect(text):
    """Return additive whole-value Candidate dictionaries; never text/values."""
    if not isinstance(text, str):
        raise ValueError("structured_invalid_input") from None
    phones = _phone_library()
    try:
        result, fields = _iban_candidates(text), []
        for match in _CUES.finditer(text):
            start = _GAP_RE.match(text, match.end()).end()
            label = match.lastgroup
            if label == "TELEPHONENUM":
                fields.append(start)
                continue
            end = _value_end(text, start)
            if end > start:
                status = _identifier_status(text[start:end], label)
                result.append(_candidate(text, start, end, label, status))
        result.extend(_phone_candidates(text, fields, phones))
        # Same-label contained matches are library fragments, not extra values.
        # Cross-label overlaps are intentionally retained for pipeline union.
        unique = {(c["start"], c["end"], c["label"]): c for c in result}
        kept = []
        ends = {}
        for cand in sorted(unique.values(), key=lambda c: (c["start"], -c["end"], c["label"])):
            if cand["end"] > ends.get(cand["label"], -1):
                kept.append(cand)
                ends[cand["label"]] = cand["end"]
        return sorted(kept, key=lambda c: (c["start"], c["end"], c["label"]))
    except Exception as error:
        if isinstance(error, RuntimeError) and str(error) == "structured_phone_budget_exhausted":
            raise RuntimeError("structured_phone_budget_exhausted") from None
        raise RuntimeError("structured_detection_failed") from None


def check(text, cand):
    """Copy a model candidate, filling validation without deleting/modifying it."""
    if not isinstance(text, str) or not isinstance(cand, dict):
        raise ValueError("structured_invalid_candidate") from None
    start, end, label = cand.get("start"), cand.get("end"), cand.get("label")
    if (type(start) is not int or type(end) is not int or not isinstance(label, str)
            or not 0 <= start < end <= len(text)):
        raise ValueError("structured_invalid_candidate") from None
    result = dict(cand)
    try:
        if label == "TELEPHONENUM":
            result["validation"] = _phone_status(text[start:end], _phone_library())
        elif label in _KEYS:
            result["validation"] = _identifier_status(text[start:end], label)
        else:
            result["validation"] = "n/a"
    except Exception as error:
        if isinstance(error, RuntimeError) and str(error) == "structured_phone_dependency_missing":
            raise RuntimeError("structured_phone_dependency_missing") from None
        raise RuntimeError("structured_validation_failed") from None
    return result
