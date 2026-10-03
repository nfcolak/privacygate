"""Narrow, additive-evidence context gate; unresolved candidates remain masked.

Only a whole candidate contained in an explicit non-personal construction may
be rejected. Scores and failed validators are never evidence of clean text.
No input text, values, offsets or candidate dictionaries are logged or returned.
"""
import re
from typing import Union

_RADIUS = 40
_NAME_LABELS = frozenset({"PERSONNAME", "GIVENNAME", "SURNAME"})
_NEVER_REJECT = _NAME_LABELS | frozenset({
    "EMAIL", "USERNAME", "IBAN", "PASSPORTNUM", "IDCARDNUM",
    "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "CREDITCARDNUMBER",
})
_DATE_LABELS = frozenset({
    "DATE", "TIME", "DATETIME", "DATEOFBIRTH", "BIRTHDATE", "DOB", "AGE",
})
_ORG_LABELS = frozenset({
    "ORG", "ORGANIZATION", "ORGANISATION", "ORGANIZATIONNAME",
    "ORGANISATIONNAME", "COMPANY", "COMPANYNAME", "BRAND", "BRANDNAME",
})


def _rx(pattern):
    return re.compile(pattern, re.IGNORECASE)


# Word boundaries are Unicode-aware. Possessives intentionally err toward keep.
_PERSONAL = _rx(
    r"(?<!\w)(?:my|me|mine|our|his|her|their|your|I|you|he|she|"
    r"mein(?:e[rmns]?|em|en|er|es)?|mir|mich|ich|dein(?:e[rmns]?|em|en|er|es)?|"
    r"sein(?:e[rmns]?|em|en|er|es)?|ihr(?:e[rmns]?|em|en|er|es)?|unser\w*|"
    r"mon|ma|mes|moi|je|ton|ta|tes|son|sa|ses|notre|votre|leur|il|elle|"
    r"mio|mia|miei|mie|io|tuo|tua|suoi|sua|nostro|nostra|lui|lei|"
    r"mi|mis|mío|mía|míos|mías|yo|su|sus|nuestro|nuestra|él|ella|"
    r"customers?|kund(?:e|en|in|innen)|clients?|clientes?|patients?|patienten?|"
    r"patientin(?:nen)?|patiente?s?|pazient[ei]|pacientes?|"
    r"born|birth(?:day|date)?|geboren|geburt(?:sdatum|stag)?|né|née|naissance|"
    r"nato|nata|nascita|nacido|nacida|nacimiento|"
    r"person|personne|persona|recipient|empfänger|destinataire|destinatario|"
    r"resident|residente|inhaber|titulaire|holder|owner|proprietario|propietario"
    r")(?!\w)|(?<=\w)['’]s(?!\w)"
)
# An explicit age attribute is personal evidence, not a blanket veto on 'years'.
_AGE_CUE = _rx(
    r"(?<!\w)(?:aged|age|alter|âge|età|edad)[ \t]*(?:[:=]|(?:is|ist|est|è|es)\b)?"
    r"[ \t]*\d{1,3}(?!\d)|"
    r"(?<!\w)\d{1,3}[ \t]+(?:years?[ -]old|jahre?[ \t]+alt|ans|anni|años)(?!\w)"
)

_NUMBER = r"\d+(?:[.,]\d+)?"
_UNIT = r"(?:mm|cm|km|m|ml|cl|dl|l|mg|kg|g|µg|μg|oz|lb)"
_DIMENSION = _rx(
    rf"(?<![\w/.-]){_NUMBER}[ \t]*[x×][ \t]*{_NUMBER}"
    rf"(?:[ \t]*[x×][ \t]*{_NUMBER})?(?:[ \t]*{_UNIT})?(?!\w)"
)
_QUANTITY = _rx(rf"(?<![\w/.-]){_NUMBER}[ \t]*{_UNIT}(?!\w)")

_CONNECTOR = (
    r"[ \t]*(?:(?:no\.?|number|nr\.?|n[°º]|num(?:ber|éro|ero)?\.?|nummer)"
    r"[ \t]*)?(?:[:=#][ \t]*)?"
)
_CODE_CUE = (
    r"order|bestellnummer|bestell[ -]nr\.?|commande|ordine|pedido|"
    r"invoice|rechnung|facture|fattura|factura|sku|art\.[ \t]*-?[ \t]*nr\.?|"
    r"article|artikelnummer|réf\.[ \t]*produit|référence[ \t]+produit|"
    r"codice[ \t]+articolo|referencia(?:[ \t]+(?:de[ \t]+)?producto)?"
)
_CODE = _rx(
    rf"(?<!\w)(?:{_CODE_CUE})(?!\w){_CONNECTOR}"
    r"(?P<value>[\w]+(?:[-./][\w]+)*)(?!\w)"
)
_ROOM_CUE = (
    r"room|raum|zimmer|salle|sala|aula|gate|gleis|quai|binario|andén|"
    r"platform|bahnsteig|plateforme|binario|andén|seat|sitz|platz|siège|posto|asiento"
)
_ROOM = _rx(
    rf"(?<!\w)(?:{_ROOM_CUE})(?!\w){_CONNECTOR}"
    r"(?P<value>[A-Z]{0,3}\d{1,5}[A-Z]?(?:[-/]\d{1,5}[A-Z]?)?)(?!\w)"
)
_SCHEDULE = _rx(
    r"(?<!\w)(?:meeting|termin|réunion|riunione|reunión|schedule|timetable|"
    r"opening[ \t]+hours|öffnungszeiten|horaires?(?:[ \t]+d['’]ouverture)?|"
    r"orari(?:[ \t]+di[ \t]+apertura)?|horario(?:[ \t]+de[ \t]+apertura)?|"
    r"deadline|due[ \t]+date|frist|échéance|scadenza|plazo|fecha[ \t]+límite)(?!\w)"
)
_DAY = r"(?:0?[1-9]|[12]\d|3[01])"
_MONTH = r"(?:0?[1-9]|1[0-2])"
_YEAR = r"(?:19|20)\d{2}"
_MONTH_NAME = (
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"januar|februar|märz|mai|juni|juli|oktober|dezember|"
    r"janvier|février|mars|avril|juin|juillet|août|septembre|octobre|novembre|décembre|"
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|dicembre|"
    r"enero|febrero|marzo|abril|mayo|junio|julio|septiembre|octubre|noviembre|diciembre"
)
_DATE = _rx(
    rf"(?<![\w/.-])(?:{_YEAR}-{_MONTH}-{_DAY}|"
    rf"{_DAY}(?P<sep>[/.-]){_MONTH}(?P=sep){_YEAR}|"
    rf"{_DAY}[ \t]+(?:{_MONTH_NAME})[ \t]+{_YEAR}|"
    rf"(?:{_MONTH_NAME})[ \t]+{_DAY},?[ \t]+{_YEAR})(?!\w)"
)
_TIME = _rx(
    r"(?<![\w:])(?:(?:[01]?\d|2[0-3]):[0-5]\d(?:[:][0-5]\d)?"
    r"(?:[ \t]*[ap]\.?m\.?)?|(?:0?[1-9]|1[0-2])[ \t]+[ap]\.?m\.?)(?!\w)"
)
# Explicit fields/quoted descriptions, not an allowlist of company/name tokens.
_ORG = _rx(
    r"(?<!\w)(?:brand|marke|marque|marca|company|unternehmen|société|azienda|empresa)"
    r"(?!\w)[ \t]*(?:[:=]|named\b|namens\b|nommée\b|chiamata\b|llamada\b)"
    r"[ \t]*(?P<value>[\w-]+(?:[ \t]+[\w-]+){0,3})(?!\w)"
)


def _bounds(text, cand):
    if not isinstance(cand, dict):
        return None
    start, end = cand.get("start"), cand.get("end")
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(text)
            or not isinstance(cand.get("label"), str)):
        return None
    return start, end


def _contains(match, start, end, group: Union[int, str] = 0):
    lo, hi = match.span(group)
    return lo <= start < end <= hi


def _construction(text, start, end, label):
    # Discover on the original string, preserving Unicode offsets and boundaries.
    lo, hi = max(0, start - _RADIUS), min(len(text), end + _RADIUS)
    for pattern, reason in ((_DIMENSION, "dimension"), (_QUANTITY, "quantity")):
        if any(_contains(m, start, end) for m in pattern.finditer(text, lo, hi)):
            return reason
    for pattern, reason in ((_CODE, "operational_code"), (_ROOM, "room_number")):
        for match in pattern.finditer(text, lo, hi):
            if (_contains(match, start, end, "value")
                    and any(ch.isdigit() for ch in match.group("value"))):
                return reason
    # A schedule heading in another line/field is not evidence for this value.
    clause_lo, clause_hi = lo, hi
    for boundary in ("\n", "\r", ";", "!", "?"):
        before = text.rfind(boundary, lo, start)
        after = text.find(boundary, end, hi)
        clause_lo = max(clause_lo, before + 1)
        if after >= 0:
            clause_hi = min(clause_hi, after)
    if label in _DATE_LABELS and _SCHEDULE.search(text, clause_lo, clause_hi):
        if any(_contains(m, start, end)
               for pattern in (_DATE, _TIME) for m in pattern.finditer(text, clause_lo, clause_hi)):
            return "calendar_schedule"
    if label in _ORG_LABELS:
        if any(_contains(m, start, end, "value") for m in _ORG.finditer(text, lo, hi)):
            return "organisation_field"
    return None


def _personal(text, start, end, cand, cands):
    if cand.get("context") == "personal":
        return True
    lo, hi = max(0, start - _RADIUS), min(len(text), end + _RADIUS)
    if _PERSONAL.search(text, lo, hi) or _AGE_CUE.search(text, lo, hi):
        return True
    for other in cands:
        bounds = _bounds(text, other)
        if bounds is None:
            continue
        a, b = bounds
        if other.get("label", "").upper() in _NAME_LABELS and a <= hi and b >= lo:
            return True
        # Independent sensitive evidence wins even when a clean construction overlaps.
        if a < end and b > start and (
            other.get("protected") is True
            or (other.get("source") == "structured" and other.get("validation") == "valid")
        ):
            return True
    return False


def decide(text, cand, cands):
    """Return (accept|reject|unresolved, fixed reason code), without mutations.

    Reject is intentionally restricted to unprotected candidates. A personal cue
    conflicting with a clean-looking construction produces unresolved (mask),
    not reject. Callers must preserve unresolved and coverage candidates.
    """
    if not isinstance(text, str) or not isinstance(cands, (list, tuple)):
        return "unresolved", "invalid_input"
    bounds = _bounds(text, cand)
    if bounds is None:
        return "unresolved", "invalid_candidate"
    start, end = bounds
    label = cand["label"].upper()
    if cand.get("protected") is not False:
        return "accept", "protected_or_unknown"
    if label in _NEVER_REJECT:
        return "accept", "sensitive_label"
    if cand.get("source") == "structured" and cand.get("validation") == "valid":
        return "accept", "structured_valid"
    if cand.get("source") == "coverage" or cand.get("stage") == "coverage":
        return "accept", "coverage"
    reason = _construction(text, start, end, label)
    if reason is None:
        return "accept", "default"
    if _personal(text, start, end, cand, cands):
        return "unresolved", "conflicting_context"
    return "reject", reason
