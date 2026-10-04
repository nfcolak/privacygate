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
    r"mon|ma|mes|moi|je|ton|ta|tes|ses|notre|votre|leur|"
    r"mio|mia|miei|mie|io|tuo|tua|suoi|sua|nostro|nostra|lui|lei|"
    r"mi|mis|mío|mía|míos|mías|yo|su|sus|nuestro|nuestra|él|ella|"
    r"customers?|kund(?:e|en|in|innen)|clients?|clientes?|patients?|patienten?|"
    r"patientin(?:nen)?|patiente?s?|pazient[ei]|pacientes?|"
    r"born|birth(?:day|date)?|geboren|geburt(?:sdatum|stag)?|naissance|"
    r"nato|nata|nascita|nacido|nacida|nacimiento|"
    r"person|personal|private|privat(?:e[rmns]?|em|en|er|es)?|privé|privée|privato|privata|privado|privada|"
    r"personne|persona|recipient|empfänger|destinataire|destinatario|"
    r"resident|residente|inhaber|titulaire|holder|owner|proprietario|propietario"
    r")(?!\w)|(?<=\w)['’]s(?!\w)"
)
# Homographs require French syntax; Italian articles/conjunctions and Spanish
# 'son' (are) cannot manufacture ownership evidence merely by proximity.
_HOMOGRAPH_PERSONAL = _rx(
    r"(?<!\w)(?:il|elle)[ \t]+(?:est|a|possède|habite|réside|communique|"
    r"donne|utilise|fournit)(?!\w)|"
    r"(?<!\w)(?:son|sa)[ \t]+(?:téléphone|adresse|compte|passeport|"
    r"permis|numéro|date[ \t]+de[ \t]+naissance)(?!\w)|"
    r"(?<!\w)née?[ \t]+(?:le[ \t]+(?=[0-9])|"
    r"(?=[0-9]{1,2}[/.-][0-9])|(?:à|en)[ \t]+(?=[A-ZÀ-ÖØ-Þ]))"
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
    r"[ \t]*(?:(?:no\.?|number|nr\.?|n[°º]|num(?:ber|éro|ero)?\.?|nummer|code)"
    r"[ \t]*)?(?:[:=#][ \t]*)?"
)
_CODE_CUE = (
    r"order|bestellnummer|bestell[ -]nr\.?|commande|ordine|pedido|"
    r"invoice|rechnung|facture|fattura|factura|sku|art\.[ \t]*-?[ \t]*nr\.?|"
    r"article|artikelnummer|réf\.[ \t]*produit|référence[ \t]+produit|"
    r"codice[ \t]+articolo|referencia(?:[ \t]+(?:de[ \t]+)?producto)?"
)
_OP_CUE = (
    r"product[ \t]+serial(?:[ \t]+(?:code|number))?|produktseriencode|"
    r"série[ \t]+produit|seriale[ \t]+prodotto|(?:número[ \t]+)?de[ \t]+serie|"
    r"order[ \t]+code|bestellcode|non[ \t]+attribué|non[ \t]+assegnato|sin[ \t]+asignar"
)
_H = r"[ \t\u00a0\u202f]"
_TYPED_IBAN = rf"[A-Z]{{2}}[0-9]{{2}}(?:{_H}+[A-Z0-9]{{1,4}}){{3,8}}"
_TYPED_PHONE = (r"\+?[0-9][0-9() \t\u00a0\u202f.\-\r\n]{5,94}[0-9)]"
                r"(?:[ \t,;/-]*(?:extension|ext\.?|x|durchwahl|dw\.?|"
                r"poste|interno|int\.?|anexo|#)[ \t:=.-]*[0-9]{1,8})?")
_SERIAL = r"[A-Z0-9]+(?:[ \t]*[-./][ \t]*[A-Z0-9]+)*"
_CODE = _rx(
    rf"(?<!\w)(?:{_CODE_CUE}|{_OP_CUE})(?!\w){_CONNECTOR}"
    rf"(?P<value>{_TYPED_IBAN}|{_TYPED_PHONE}|{_SERIAL})(?!\w)"
)
# Only these explicit operational fields may precede unconditional acceptance.
# Generic short Order/SKU values retain the previous sensitive-label policy.
_OP_CODE = _rx(
    rf"(?<!\w)(?:{_OP_CUE})(?!\w){_CONNECTOR}"
    rf"(?P<value>{_TYPED_IBAN}|{_TYPED_PHONE}|{_SERIAL})(?!\w)"
)
_OP_TYPED = _rx(
    rf"(?<!\w)(?:{_CODE_CUE})(?!\w){_CONNECTOR}"
    rf"(?P<value>{_TYPED_IBAN}|{_TYPED_PHONE})(?!\w)"
)
_OP_DATE_CUE = _rx(
    r"(?<!\w)(?:manufacturing[ \t]+date|maintenance[ \t]+(?:date|calendar)|"
    r"herstelldatum|wartungskalender|(?:date[ \t]+de[ \t]+)?fabrication|"
    r"(?:fecha[ \t]+de[ \t]+)?fabricación|d['’]entretien|"
    r"(?:data[ \t]+di[ \t]+)?manutenzione|(?:fecha[ \t]+de[ \t]+)?mantenimiento)"
    r"(?!\w)[ \t]*(?:[:=][ \t]*)?"
)
_PERSONAL_FIELD = _rx(
    r"(?<!\w)(?:iban|bank[ \t]+account|konto|compte[ \t]+bancaire|"
    r"phone|telephone|téléphone|telefon(?:nummer)?|telefono|teléfono|"
    r"date[ \t]+of[ \t]+birth|geburtsdatum|naissance|nascita|nacimiento|"
    r"case|fall|dossier|caso|passport|reisepass|social[ \t]+security)"
    r"(?!\w)[ \t]*[:=]"
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


# Typed roles are semantic field families, shared with the structured detector.
# A table role is inherited by its cell, never by a nearby contact column.
_PHONE_ROLE = _rx(r"(?<!\w)(?:phone|telephone|téléphone|tel\.?|tél\.?|"
                 r"telefon(?:nummer)?|telefono|teléfono|mobile|mobil|fax)(?!\w)")
_OPERATIONAL_ROLE = _rx(
    r"(?<!\w)(?:serial(?:[ \t]+(?:number|code))?|seriale|serien(?:nummer|code)?|"
    r"série|serie|sku|part(?:[ \t]+(?:number|no\.?))?|teil(?:enummer)?|"
    r"pièce|pezzo|pieza|lot|lotto|lote|charge|batch|order|bestellung|bestell\w*|"
    r"commande|ordine|pedido|invoice|rechnung\w*|facture|fattura|factura|"
    r"inventory|inventar\w*|inventaire|inventario|stock|bestand|lager\w*|"
    r"scorta|existencias|quantity|qty|menge|quantité|quantità|cantidad|"
    r"price|preis|prix|prezzo|precio|cost|kosten|coût|costo|coste|"
    r"product|produkt|produit|prodotto|producto|article|artikel|articolo|artículo|"
    r"dimensions?|abmessungen|maße|room|zimmer|salle|stanza|habitación)(?!\w)"
)
_TABLE_SEP = re.compile(r"[ \t]*\|[ \t]*|\t+|[ ]+/[ ]+|[ ]{2,}")
_TYPED_OPERATION = _rx(
    r"(?P<key>(?:" + _OP_CUE + r"|" + _OPERATIONAL_ROLE.pattern + r"))"
    r"[ \t]*(?:(?:number|no\.?|nr\.?|nummer|numéro|numero|número|code)"
    r"[ \t]*)?[:=][ \t]*(?P<value>[^;|\n\r]{1,140})"
)


def _cells(text, lo, hi):
    cursor, cells = lo, []
    for sep in _TABLE_SEP.finditer(text, lo, hi):
        cells.append((cursor, sep.start()))
        cursor = sep.end()
    cells.append((cursor, hi))
    return cells


def phone_scope(text, start, end):
    """Return (operational, contact) from typed field/cell ownership, not shape."""
    lo = text.rfind('\n', 0, start) + 1
    hi = text.find('\n', end)
    hi = len(text) if hi < 0 else hi
    cells = _cells(text, lo, hi)
    touched = [i for i, (a, b) in enumerate(cells) if a < end and start < b]
    if len(cells) > 1:
        previous = lo - 1
        # Only contiguous rows with the same column grammar inherit a header.
        for _ in range(24):
            if previous <= 0:
                break
            header_lo = text.rfind('\n', 0, previous) + 1
            headers = _cells(text, header_lo, previous)
            if not text[header_lo:previous].strip() or len(headers) != len(cells):
                break
            roles = [(bool(_OPERATIONAL_ROLE.search(text, a, b)),
                      bool(_PHONE_ROLE.search(text, a, b))) for a, b in headers]
            if any(op or contact for op, contact in roles):
                contact = len(touched) == 1 and roles[touched[0]][1]
                operational = any(roles[i][0] and not roles[i][1] for i in touched)
                return operational or len(touched) > 1, contact
            previous = header_lo - 1
    for field in _TYPED_OPERATION.finditer(text, max(0, start - 180), hi):
        if _contains(field, start, end, 'value'):
            return True, False
    return False, False


def personal_evidence(text, start, end):
    """Clause-local independent ownership for numeric detectors/refinement."""
    lo, hi = max(0, start - 120), min(len(text), end + 80)
    for boundary in (';', '\n', '\r', '|', '!', '?'):
        lo = max(lo, text.rfind(boundary, lo, start) + 1)
        after = text.find(boundary, end, hi)
        if after >= 0:
            hi = min(hi, after)
    return bool(_PERSONAL.search(text, lo, hi) or _HOMOGRAPH_PERSONAL.search(text, lo, hi)
                or _PERSONAL_FIELD.search(text, lo, hi))


def _operational(text, start, end, label):
    """Independent typed field evidence, not a checksum/score-based exemption."""
    lo, hi = max(0, start - 120), min(len(text), end + 120)
    if label == 'TELEPHONENUM':
        operational, contact = phone_scope(text, start, end)
        if operational and not contact:
            return 'operational_phone_scope', start, end
    for pattern in (_OP_CODE, _OP_TYPED):
        for match in pattern.finditer(text, lo, hi):
            value = match.group("value")
            if (_contains(match, start, end, "value")
                    and any(ch.isdigit() for ch in value)
                    and len(re.findall(r"\r\n|\r|\n", value)) <= 1):
                return "operational_code", match.start(), match.end("value")
    if label in _DATE_LABELS or label == "TELEPHONENUM":
        for cue in _OP_DATE_CUE.finditer(text, lo, hi):
            value = _DATE.match(text, cue.end())
            if value is not None and _contains(value, start, end):
                return "operational_date", cue.start(), value.end()
    return None


def _personal(text, start, end, cand, cands, ownership_only=False):
    if cand.get("context") == "personal":
        return True
    lo, hi = max(0, start - _RADIUS), min(len(text), end + _RADIUS)
    if (_PERSONAL.search(text, lo, hi) or _HOMOGRAPH_PERSONAL.search(text, lo, hi)
            or _AGE_CUE.search(text, lo, hi)):
        return True
    if ownership_only and _PERSONAL_FIELD.search(text, lo, hi):
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
            or (ownership_only and other.get("context") == "personal")
            or (not ownership_only and other.get("source") == "structured"
                and other.get("validation") == "valid")
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
    if cand.get("source") == "coverage" or cand.get("stage") == "coverage":
        return "accept", "coverage"
    operational = _operational(text, start, end, label)
    if operational is not None and label not in _NAME_LABELS | {"EMAIL", "USERNAME"}:
        reason, value_start, value_end = operational
        if _personal(text, value_start, value_end, cand, cands, ownership_only=True):
            return "unresolved", "conflicting_context"
        return "reject", reason
    if label in _NEVER_REJECT:
        return "accept", "sensitive_label"
    if cand.get("source") == "structured" and cand.get("validation") == "valid":
        return "accept", "structured_valid"
    reason = _construction(text, start, end, label)
    if reason is None:
        return "accept", "default"
    if _personal(text, start, end, cand, cands):
        return "unresolved", "conflicting_context"
    return "reject", reason
