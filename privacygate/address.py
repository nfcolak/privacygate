"""Additive, original-offset postal-region assembly; stdlib only and no logging.

Street and house evidence are independent anchors. A PO-box core additionally
needs a postal/locality anchor; cities, countries and postcodes alone never
establish a region. Model components can corroborate lexical anchors. Growth
crosses only postal components and punctuation, never arbitrary nearby prose.
All returned regions are at most 200 Unicode code points. Existing detections
are neither changed nor removed, including detections exceeding that budget.
"""
from dataclasses import dataclass
import re


MAX_REGION_CHARS = 200
_ADDRESS_LABELS = frozenset({
    "STREET", "BUILDINGNUM", "ZIPCODE", "CITY", "STATE", "COUNTY", "COUNTRY", "ADDRESS", "POBOX",
})
_NAME_LABELS = frozenset({"PERSONNAME", "GIVENNAME", "MIDDLENAME", "SURNAME", "TITLE"})
_H = r"[^\S\r\n]"
_WORD = r"[^\W\d_](?:[^\W\d_]|[\u0300-\u036f'’\-])*"
# Lowercase function words do not become English/German street-name prefixes.
_PARTICLE = r"(?:de|del|della|dei|degli|di|da|du|des|la|le|les|el|los|las|van|von|den|der|am|im|of|the)"
_STOP_WORD = (
    r"(?:Next|Then|Please|Thanks|Thank|Contact|Email|Phone|Telephone|Invoice|Order|Date|"
    r"Room|Meeting|Product|SKU|Dear|Bonjour|Hello|Return|Send|Deliver|Visit|We|The|This|"
    r"Tel|Tél|Mobil|Mobile|Handy|Cell|Mail|E-Mail|"
    r"Danach|Bitte|Danke|Telefon|Rechnung|Bestellung|Datum|Zimmer|Produkt|Sehr|"
    r"Ensuite|Merci|Veuillez|Téléphone|Courriel|Facture|Commande|Date|Chambre|Produit|"
    r"Poi|Grazie|Telefono|Fattura|Ordine|Data|Stanza|Prodotto|Gentile|"
    r"Luego|Gracias|Teléfono|Correo|Factura|Pedido|Fecha|Habitación|Producto|Estimado)"
)
_CAP = rf"(?!{_STOP_WORD}\b)(?-i:[A-ZÀ-ÖØ-Þ])(?:[^\W\d_]|[\u0300-\u036f'’\-])*"
_NAME = rf"{_CAP}(?:{_H}+(?:{_CAP}|{_PARTICLE})){{0,5}}"
_ROAD_WORD = rf"(?!{_STOP_WORD}\b){_WORD}"
_PREFIX_NAME = rf"{_ROAD_WORD}(?:{_H}+{_ROAD_WORD}){{0,5}}?"
_PREFIX_NAME_FRONT = rf"{_ROAD_WORD}(?:{_H}+{_ROAD_WORD}){{0,5}}"
_NUMBER = r"\d{1,4}(?:[^\S\r\n]*(?:bis|ter)|[a-z])?(?:[^\S\r\n]*[-–/][^\S\r\n]*\d{1,4}[a-z]?)?"
_SUFFIX = (
    r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|drive|dr\.?|court|ct\.?|"
    r"close|crescent|circuit|way|terrace|place|square|boulevard|blvd\.?|"
    r"straße|strasse|str\.?|weg|platz|gasse|allee|ring|steig|ufer)"
)
_PREFIX = (
    r"(?:rue|avenue|av\.?|boulevard|bd\.?|chemin|impasse|route|allée|allee|"
    r"via|viale|piazza|corso|strada|vicolo|largo|"
    r"calle|avenida|avda\.?|paseo|plaza|carretera|c(?:\.|/))"
)
_COMPOUND = rf"{_WORD}(?:straße|strasse|str\.?|weg|platz|gasse|allee|ring|steig|ufer)"
_STREET = rf"(?:{_COMPOUND}|{_NAME}{_H}+{_SUFFIX}|{_PREFIX}{_H}+{_PREFIX_NAME})"
_STREET_LAST = re.compile(rf"(?<!\w)(?P<street>{_STREET}){_H}+(?P<house>{_NUMBER})(?!\w)", re.I)
_STREET_FRONT = rf"(?:{_COMPOUND}|{_NAME}{_H}+{_SUFFIX}|{_PREFIX}{_H}+{_PREFIX_NAME_FRONT})"
_STREET_FIRST = re.compile(rf"(?<!\w)(?P<house>{_NUMBER}){_H}+(?P<street>{_STREET_FRONT})(?!\w)", re.I)
_BOX = re.compile(
    rf"(?<!\w)(?:P\.?{_H}*O\.?{_H}+Box|Postfach|BP|B\.?P\.?|"
    rf"Bo[iî]te{_H}+postale|case{_H}+postale|Casella{_H}+postale|C\.{_H}*P\.|"
    rf"Apartado(?:{_H}+(?:de{_H}+correos|postal))?|Apdo\.?){_H}+(?:n[º°o]\.?{_H}*)?"
    rf"\d{{1,6}}(?:[-/][a-z0-9]+)?(?!\w)", re.I,
)
_POSTAL = (
    r"(?:(?:CH|DE|D|AT|A|FR|F|IT|I|ES|E|NL|BE|B|US)-)?"
    r"(?:[A-Z]{1,2}\d[A-Z\d]?[^\S\r\n]+\d[A-Z]{2}|"
    r"\d{4}[^\S\r\n]*[A-Z]{2}|\d{5}-\d{4}|\d{2}[^\S\r\n]\d{3}|\d{5}|\d{4})"
)
_LOCALITY = rf"{_CAP}(?:{_H}+(?:{_PARTICLE}{_H}+)?{_CAP}){{0,3}}"
_POSTAL_FIRST = re.compile(rf"(?<!\w){_POSTAL}(?:{_H}*,{_H}*|{_H}+){_LOCALITY}(?!\w)", re.I)
_POSTAL_LAST = re.compile(rf"(?<!\w){_LOCALITY}(?:{_H}*,{_H}*(?-i:[A-Z]{{2}}))?{_H}+{_POSTAL}(?!\w)", re.I)
_COUNTRY = re.compile(
    r"(?<!\w)(?:United States(?: of America)?|United Kingdom|Great Britain|"
    r"Royaume-Uni|Regno Unito|Reino Unido|Großbritannien|Grossbritannien|"
    r"États-Unis|Etats-Unis|Stati Uniti|Estados Unidos|"
    r"Netherlands|Nederland|Niederlande|Pays-Bas|Paesi Bassi|Países Bajos|"
    r"Switzerland|Schweiz|Suisse|Svizzera|Suiza|"
    r"Deutschland|Germany|Allemagne|Germania|Alemania|"
    r"Österreich|Oesterreich|Austria|Autriche|"
    r"Belgium|Belgique|België|Belgien|Belgio|Bélgica|"
    r"France|Frankreich|Francia|Italia|Italy|Italien|Italie|"
    r"España|Spain|Spanien|Espagne|Spagna|UK|USA|U\.S\.A\.)(?!\w)", re.I,
)
_UNIT_WORD = (
    r"(?:floor|flat|apartment|apt\.?|unit|suite|room|building|"
    r"Stock|Stockwerk|Wohnung|Whg\.?|Etg\.?|OG|EG|DG|Hinterhaus|Haus|"
    r"étage|ét\.?|appartement|app\.?|bâtiment|bât\.?|escalier|"
    r"piano|interno|int\.?|scala|palazzina|"
    r"piso|planta|puerta|escalera|apartamento|apto\.?)"
)
_UNIT_VALUE = (
    r"(?:\d{1,3}(?:st|nd|rd|th|ème|eme|er|e|º|ª|°|\.)?"
    r"(?:[^\S\r\n]*[a-z](?!\w))?|[a-z](?!\w)|"
    r"ground|first|second|third|fourth|premier|deuxième|troisième|"
    r"primo|secondo|terzo|quarto|primero|segundo|tercero|bajo|izquierda|derecha)"
)
_UNIT = re.compile(
    rf"(?<!\w)(?:{_UNIT_WORD}{_H}+{_UNIT_VALUE}|"
    rf"{_UNIT_VALUE}{_H}+{_UNIT_WORD}|"
    rf"\d{{1,3}}[ºª°]{_H}+(?:[a-z]|izq\.?|der\.?|izquierda|derecha)|"
    rf"rez-de-chaussée|Erdgeschoss|ground{_H}+floor|bajo)(?!\w)", re.I,
)
_ROUTING = re.compile(rf"(?<!\w)CEDEX(?:{_H}+\d{{1,3}})?(?!\w)", re.I)
_REGION = re.compile(
    rf"(?<!\w)(?:canton|Kanton|county|province|provincia|Provinz|région|regione|región)"
    rf"{_H}+(?:(?:di|de|del|della){_H}+)?{_LOCALITY}(?!\w)|\((?-i:[A-Z]{{2}})\)", re.I,
)
_CARE_PREFIX = rf"(?:c/{_H}*o|care{_H}+of|z\.{_H}*Hd\.|zu{_H}+Händen|chez|à{_H}+l['’]attention{_H}+de|presso|a{_H}+cargo{_H}+de|a{_H}+la{_H}+atención{_H}+de)"
_RECIPIENT_WORD = rf"(?:(?:Dr|Prof|Herr|Frau|Mme|Mlle|Sig\.ra|Sig|Sr|Sra)\.?(?!\w)|(?-i:[A-Z])\.|{_CAP}|{_PARTICLE})"
_CARE = re.compile(
    rf"(?<!\w){_CARE_PREFIX}{_H}*(?:\r?\n{_H}*)?"
    rf"{_RECIPIENT_WORD}(?:{_H}+{_RECIPIENT_WORD}){{0,7}}(?!\w)", re.I,
)
_CARE_MARKER = re.compile(rf"(?<!\w){_CARE_PREFIX}(?!\w)", re.I)
_FIELD = re.compile(
    r"(?<!\w)(?:e-?mail|email address|courriel|correo(?: electrónico)?|phone|telephone|"
    r"tel(?:efon|éfono|ephone)?\.?|téléphone|telefono|mobile|IBAN|account|konto|compte|"
    r"invoice|order|SKU|product|Rechnung|Bestellung|facture|commande|fattura|ordine|factura|pedido|"
    r"birth date|date of birth|Geburtsdatum|date de naissance|data di nascita|fecha de nacimiento)"
    r"[^\S\r\n]*[:=]", re.I,
)
_CONTACT_CUE = re.compile(
    r"(?<![\w-])(?:e-?mail|mail|courriel|correo(?: electrónico)?|phone|telephone|"
    r"tel(?:efon|éfono|ephone)?|tél(?:éphone)?|telefono|mobil(?:e)?|handy|cell)(?!\w)\.?",
    re.I,
)
_EMAIL = re.compile(r"(?<!\w)[\w.+-]+@[\w.-]+\.[a-z]{2,}(?!\w)", re.I)
_BLANK = re.compile(r"\r?\n[^\S\r\n]*\r?\n")
_CONNECTOR = re.compile(r"[\s,;:/\-–—()[\]{}]*\Z")
_HOUSE = re.compile(rf"(?<!\w){_NUMBER}(?!\w)", re.I)
_ADDRESS_FIELD = re.compile(
    r"(?<!\w)(?:private[ \t]+delivery|delivery|Zustellung|Livraison|Consegna|Entrega|"
    r"address|Adresse|Dirección(?:[ \t]+privada)?|Indirizzo)(?!\w)"
    r"[ \t]*(?:[:=][ \t]*|[ \t]+|(?=\r?\n))", re.I,
)
_NEXT_FIELD = re.compile(
    r"(?<!\w)[^\W\d_][^\n\r,;:=]{0,35}[ \t]*[:=]", re.U,
)


def _ocr_matches(text):
    """Replace one field-local line break with equal-width spaces, in RAM only.

    Only matches crossing that break are additions. Existing postal anchors,
    foreign-value barriers and the final envelope budget still decide admission.
    """
    patterns = ((_STREET_LAST, ("street", "house"), "street"),
                (_STREET_FIRST, ("street", "house"), "street"),
                (_BOX, ("box",), "box"), (_CARE, (), ""))
    for field in _ADDRESS_FIELD.finditer(text):
        low, high = field.end(), min(len(text), field.end() + MAX_REGION_CHARS)
        for barrier in (_BLANK, _NEXT_FIELD):
            found = barrier.search(text, low, high)
            if found:
                high = min(high, found.start())
        for br in re.finditer(r"\r?\n", text[low:high]):
            a, b = low + br.start(), low + br.end()
            view = text[low:a] + " " * (b - a) + text[b:high]
            for pattern, anchors, core in patterns:
                for match in pattern.finditer(view):
                    start, end = low + match.start(), low + match.end()
                    if start < a and b < end:
                        yield start, end, anchors, core, a


@dataclass(frozen=True)
class _Piece:
    start: int
    end: int
    anchors: frozenset
    core: str = ""
    soft_break: int = -1


def _candidate(start, end):
    return {
        "start": start, "end": end, "label": "ADDRESS", "source": "address",
        "score": None, "validation": "unknown", "context": "unknown",
        "protected": False, "stage": "assembled",
    }


def _checked(text, cands):
    if not isinstance(text, str) or not isinstance(cands, (list, tuple)):
        raise ValueError("address_input_invalid") from None
    for cand in cands:
        if not isinstance(cand, dict):
            raise ValueError("address_candidate_invalid") from None
        start, end = cand.get("start"), cand.get("end")
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(text) or not isinstance(cand.get("label"), str)):
            raise ValueError("address_candidate_invalid") from None


def _overlap(start, end, barriers):
    return any(start < b and a < end for a, b in barriers)


def _connects(text, start, end, barriers):
    return (end >= start and not _overlap(start, end, barriers)
            and not _BLANK.search(text, start, end)
            and _CONNECTOR.fullmatch(text[start:end]) is not None)


def _established(anchors):
    # A street name plus its independently observed house number also permits
    # truncated addresses. A postal-locality pair never establishes one alone.
    return ("street" in anchors and ("house" in anchors or {"postal", "locality"} <= anchors)
            or {"box", "postal", "locality"} <= anchors)


def value_boundaries(text, cands):
    """Other-family evidence, exempting only explicitly introduced recipients.

    A broad model ADDRESS can hide an honorific/cued name from the name stage.
    For boundary/label arbitration only, recover that evidence without ADDRESS
    blockers. This never changes the supplied candidates or their mask coverage.
    """
    from .names import assemble as assemble_names

    care = [m.span() for m in _CARE.finditer(text)]
    care += [(a, b) for a, b, anchors, core, br in _ocr_matches(text) if not anchors]
    foreign = [c for c in cands if c["label"] not in _ADDRESS_LABELS
               and c["label"] != "UNCOVERED"]
    name_seeds = [c for c in cands if c["label"] != "ADDRESS"]
    # Removing a broad ADDRESS must not let inverted-name grammar reinterpret
    # an adjacent lexical street as a surname (especially German compounds).
    for pattern in (_STREET_LAST, _STREET_FIRST, _BOX, _POSTAL_FIRST, _POSTAL_LAST):
        name_seeds.extend(dict(_candidate(*m.span()), label="STREET") for m in pattern.finditer(text))
    foreign += assemble_names(text, name_seeds)
    return [c for c in foreign if not (
        c["label"] in _NAME_LABELS
        and any(a <= c["start"] and c["end"] <= b for a, b in care)
    )]


def contact_cues(text):
    """Original-coordinate contact cue boundaries, with no colon requirement."""
    return [m.span() for m in _CONTACT_CUE.finditer(text)]


def assemble(text, cands):
    """Return NEW whole ADDRESS candidates; never mutate, delete or shrink seeds.

    Invalid offsets raise fixed, value-free errors. Labels not in the address
    family contribute only explicit value-family boundaries (names may overlap
    care-of lines). No text or component values escape this interface.
    """
    _checked(text, cands)
    if not text:
        return []
    barriers = [(c["start"], c["end"]) for c in value_boundaries(text, cands)]
    barriers += contact_cues(text)
    barriers += [m.span() for m in _FIELD.finditer(text)]
    barriers += [m.span() for m in _NEXT_FIELD.finditer(text)]
    barriers += [m.span() for m in _EMAIL.finditer(text)]
    pieces = []

    def add(start, end, anchors=(), core="", soft_break=-1):
        if (start < end and end - start <= MAX_REGION_CHARS
                and not _overlap(start, end, barriers) and not _BLANK.search(text, start, end)):
            pieces.append(_Piece(start, end, frozenset(anchors), core, soft_break))

    for start, end, anchors, core, br in _ocr_matches(text):
        add(start, end, anchors, core, br)
    for pattern in (_STREET_LAST, _STREET_FIRST):
        for match in pattern.finditer(text):
            add(*match.span(), ("street", "house"), "street")
    for match in _BOX.finditer(text):
        add(*match.span(), ("box",), "box")
    for pattern in (_POSTAL_FIRST, _POSTAL_LAST):
        for match in pattern.finditer(text):
            add(*match.span(), ("postal", "locality"))
    for pattern in (_COUNTRY, _UNIT, _ROUTING, _REGION, _CARE):
        for match in pattern.finditer(text):
            add(*match.span())
    # A care-of marker on its own line can connect its recipient line, which is
    # already classified by _CARE; do not treat arbitrary addressee prose as a line.
    for match in _CARE_MARKER.finditer(text):
        add(*match.span())

    seed_anchor = {
        "STREET": ("street",), "BUILDINGNUM": ("house",), "ZIPCODE": ("postal",),
        "CITY": ("locality",), "STATE": (), "COUNTY": (), "COUNTRY": (), "ADDRESS": (), "POBOX": ("box",),
    }
    for cand in cands:
        label = cand["label"]
        if label not in _ADDRESS_LABELS:
            continue
        start, end = cand["start"], cand["end"]
        add(start, end, seed_anchor[label])
        if label == "STREET":
            # Opaque model street names still admit neighboring house numbers;
            # numbers elsewhere in the document never become free-floating anchors.
            low, high = max(0, start - 15), min(len(text), end + 15)
            for match in _HOUSE.finditer(text, low, high):
                hs, he = match.span()
                if ((he <= start and _connects(text, he, start, barriers))
                        or (hs >= end and _connects(text, end, hs, barriers))):
                    add(hs, he, ("house",))

    # Independent components separated by classified postal material form a
    # region. Blank lines, other values, prose and sentence punctuation break it.
    pieces.sort(key=lambda p: (p.start, -p.end))
    groups = []
    group = []
    left = right = 0
    for piece in pieces:
        joins = bool(group) and (
            piece.start < right or _connects(text, right, piece.start, barriers)
        )
        second_street = (piece.core == "street" and piece.start >= right
                         and any(p.core == "street" for p in group))
        second_box = (piece.core == "box" and piece.start >= right
                      and any(p.core == "box" for p in group))
        breaks = {p.soft_break for p in group + [piece] if p.soft_break >= 0}
        if joins and (max(right, piece.end) - left > MAX_REGION_CHARS or second_street
                      or second_box or len(breaks) > 1):
            joins = False
        if not joins:
            if group:
                groups.append((left, right, group))
            group, left, right = [], piece.start, piece.end
        group.append(piece)
        right = max(right, piece.end)
    if group:
        groups.append((left, right, group))

    out = []
    seen = set()
    for start, end, group in groups:
        anchors = frozenset(a for piece in group for a in piece.anchors)
        if not _established(anchors):
            continue
        # Sentence-final periods are never part of a value; periods internal to
        # abbreviations remain untouched. Closing province parentheses ARE value.
        while end > start and (text[end - 1].isspace() or text[end - 1] in ",;.!?"):
            end -= 1
        while start < end and text[start].isspace():
            start += 1
        if start < end and (start, end) not in seen:
            seen.add((start, end))
            out.append(_candidate(start, end))
    return out
