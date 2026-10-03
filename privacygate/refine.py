"""Rule-based span refinement applied after mBERT / hybrid detection (pure stdlib, deterministic).

refine(text, spans) -> spans, same dict shape {start,end,label,source}. Rules:
  a. phone extension   - extend a TELEPHONENUM (>= 6 digits) over a following extension keyword + digits (or "-12" style
                         suffix); a bare "x" extension needs whitespace/span end before it and no unit/"x"+digit after it
  b. address merge     - merge STREET/BUILDINGNUM/ZIPCODE/CITY runs into one ADDRESS span, then extend it over
                         ISO-like postcode prefixes, a street-type word before the first STREET piece (addition beyond the
                         original brief), adjacent unit phrases and a trailing country name. Pieces that overlap or share an
                         alphanumeric run with a non-address span, or are not word-bounded, are not address parts; a merged
                         group needs at least one STREET or CITY piece
  c. word completion   - extend any span that starts/ends inside an alphanumeric run to the whole run (not a digit-x-digit
                         dimension run such as "3x5"); also runs before phone extension so a fragmented base is completed first
  d. name gaps         - join name-labelled pieces over bounded whitespace/hyphens/apostrophes/name particles, never non-name pieces
  e. value gaps        - join short separator-only gaps within the same value family; identity-document labels share one family,
                         but phone/account/reference/email/username boundaries stay separate; include an attached username @ sigil
  f. age near misses   - discard only isolated numeric mBERT AGE pieces without multilingual age context; retain adjacent value pieces
Finally overlapping/touching spans are unioned (earliest label, ADDRESS preferred over parts).

Never logs or prints; errors are fixed, value-free messages. The vocabulary below is general real-world
vocabulary (extension keywords, unit words, country names) and contains no dataset values.
"""
import re

ADDRESS_PARTS = frozenset(("STREET", "BUILDINGNUM", "ZIPCODE", "CITY"))
MAX_GAP_CHARS = 40
MAX_GAP_WORDS = 4
MAX_RUN_EXTENSION = 40  # chars added per side by word completion (guards against runaway runs)

_ALNUM = r"[^\W_]"
_NOT_AFTER_ALNUM = r"(?<!" + _ALNUM + r")"
_NOT_BEFORE_ALNUM = r"(?!" + _ALNUM + r")"

# ---- a. phone extension -------------------------------------------------------------------------------
_EXT_KW = (r"(?:tel\.?[ ]?ext\.?|extensi[oó]n|extension|durchwahl|durchw\.?|apparat|interne|interno|anexo|extn|"
           r"ext/|ext\.?|poste|app\.?|int\.?|dw)")
_EXT = re.compile(
    r"[ \t,;:(\[/\-\u2013\u2014]{0,3}(?<![^\W\d_])(?:" + _EXT_KW + r"[ \t.:\-]{0,3}|(?P<x>x)[ \t]?)\d{1,6}" + _NOT_BEFORE_ALNUM,
    re.I)
_KW_TAIL = re.compile(r"(?<![^\W\d_])(?:" + _EXT_KW + r"|x)[ \t.:\-]{0,3}$", re.I)
_DIGITS = re.compile(r"[ \t.:\-]{0,3}\d{1,6}" + _NOT_BEFORE_ALNUM)
_X_BLOCK = re.compile(r"[ \t]*(?:(?:mm|cm|km|kg|m|in|ft|g|px)(?![^\W_])|%|\u00d7|x[ \t]?\d)", re.I)  # unit / dimension after a bare x
MIN_PHONE_DIGITS = 6
_DASH = re.compile(r"(?:[ \t]-[ \t]|-)\d{1,4}" + _NOT_BEFORE_ALNUM)

# ---- b. address merge ---------------------------------------------------------------------------------
_ISO = re.compile(_NOT_AFTER_ALNUM + r"(?:CH|FL|DE|AT|FR|IT|ES|NL|PL|D|A|F|I|L|B|E)-$")
_COUNTRIES = (
    "Switzerland", "Schweiz", "Suisse", "Svizzera", "Svizra", "Suiza",
    "Germany", "Deutschland", "Allemagne", "Germania", "Alemania",
    "France", "Frankreich", "Francia",
    "Italy", "Italien", "Italie", "Italia",
    "Spain", "Spanien", "Espagne", "Spagna", "España",
    "Austria", "Österreich", "Autriche",
    "United Kingdom", "UK", "Vereinigtes Königreich", "Royaume-Uni", "Regno Unito", "Reino Unido",
    "Netherlands", "Niederlande", "Pays-Bas", "Paesi Bassi", "Países Bajos",
    "Belgium", "Belgien", "Belgique", "Belgio", "Bélgica",
    "Liechtenstein",
    "Luxembourg", "Luxemburg", "Lussemburgo", "Luxemburgo",
    "Portugal", "Portogallo",
    "Ireland", "Irland", "Irlande", "Irlanda",
    "Poland", "Polen", "Pologne", "Polonia",
    "United States", "USA",
    "Türkiye", "Turkey", "Türkei", "Turquie", "Turchia", "Turquía",
)
_COUNTRY_FORMS = sorted({f for c in _COUNTRIES for f in (c, c.upper())}, key=lambda f: (-len(f), f))
_COUNTRY = re.compile(
    r"(?:[ \t]*[,;][ \t]*|[ \t]+[\u2014\u2013-][ \t]+|[ \t]*\n[ \t]*|[ \t]*)" + _NOT_AFTER_ALNUM
    + r"(?:" + "|".join(re.escape(f) for f in _COUNTRY_FORMS) + r")" + _NOT_BEFORE_ALNUM)

_UNIT_KW = (r"(?:apartamento|appartement|apartment|apartado|casella[ ]postale|case[ ]postale|postfach|wohnung|"
            r"interno|etage|\u00e9tage|piano|scala|suite|floor|stock|flat|unit|apt|whg|int|app|puerta|piso|og|eg)")
_UNIT_TOKEN = r"(?:\d" + _ALNUM + r"{0,5}(?:[-/]\d" + _ALNUM + r"{0,3})?[\u00ba\u00b0\u00aa]?|(?-i:[A-Z]))" + _NOT_BEFORE_ALNUM
_FLOOR_KW = r"(?:floor|stock|og|eg|etage|\u00e9tage|piano|piso|planta)"
_NAME = r"[^\W\d_]" + _ALNUM + r"{0,14}"
_UNIT = re.compile(
    _NOT_AFTER_ALNUM + r"(?:"
    + _UNIT_KW + r"\.?[ \t]{0,2}" + _UNIT_TOKEN
    + r"|\d{1,2}(?:st|nd|rd|th|er|\u00e8re|\u00e8me|e|\u00ba|\u00b0|\u00aa|\.)?[ \t]{0,2}" + _FLOOR_KW + _NOT_BEFORE_ALNUM
    + r"|c/o[ \t]+" + _NAME + r"(?:[ \t]+" + _NAME + r")?" + _NOT_BEFORE_ALNUM
    + r")", re.I)
# Street-type word (+ optional article/preposition) directly before a STREET piece the model started late.
_STREET_TYPE = (r"(?:strasse|stra\u00dfe|street|avenue|boulevard|viale|via|piazza|piazzale|corso|strada|calle|avenida|paseo|plaza|"
                r"carrer|rue|route|chemin|avenue|all\u00e9e|impasse|place|quai|ruelle|cours|weg|platz|gasse|bd|av|c/)")
_ARTICLE = r"(?:de[ \t]+la|de[ \t]+las|de[ \t]+los|dell'|della|dello|degli|dei|del|des|du|de|di|d'|l')"
_STREET_PREFIX = re.compile(_NOT_AFTER_ALNUM + _STREET_TYPE + r"\.?[ \t]+(?:" + _ARTICLE + r"[ \t]*)?$", re.I)
_SEP = frozenset(" \t,;:/\n-\u2013\u2014().")
_SENT_END = re.compile(r"[.!?]\s+")
_BLANK_LINE = re.compile(r"\n[ \t]*\n")


def _err():
    raise ValueError("invalid spans for refinement") from None


def _check(text, spans):
    n = len(text)
    out = []
    for s in spans:
        if not isinstance(s, dict) or not {"start", "end", "label"} <= s.keys():
            _err()
        a, b = s["start"], s["end"]
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= n or not isinstance(s["label"], str):
            _err()
        out.append({"start": a, "end": b, "label": s["label"], "source": s.get("source", "")})
    return out


def _changed(s, **kw):
    return dict(s, source="refine", **kw)


# ---- name/value gaps and narrow clean-control filter ---------------------------------------------------
NAME_PARTS = frozenset(("GIVENNAME", "SURNAME", "MIDDLENAME", "TITLE", "PERSONNAME"))
_NAME_GAP = re.compile(r"(?:[\s\-'\u2019\u2010\u2011]|\b(?:van|von|der|de|la|di|da|del|du|le)\b)+", re.I)
_VALUE_FAMILY = {
    **{label: "identity" for label in ("PASSPORTNUM", "DRIVERLICENSENUM", "IDCARDNUM", "TAXNUM", "SOCIALNUM")},
    "ACCOUNTNUM": "account", "IBAN": "account", "CREDITCARDNUMBER": "card",
    "TELEPHONENUM": "phone", "PERSONALREF": "reference", "EMAIL": "email", "USERNAME": "username",
}
_VALUE_SEP = frozenset(" \t-/._")
_AGE_CONTEXT = re.compile(
    r"\b(?:age|aged|alter|alt|[aâ]ge|[eé]t[aà]|edad|years?|old|jahre?n?|ans?|anni|a[nñ]os?)\b", re.I)


def _short_value_gap(gap):
    # A full stop followed by whitespace is a sentence boundary, not an identifier separator.
    return (len(gap) <= 3 and all(c in _VALUE_SEP for c in gap)
            and not re.search(r"\.\s", gap))


def _age_near_misses(text, spans):
    out = []
    for s in spans:
        a, b = s["start"], s["end"]
        if s["label"] == "AGE" and s["source"] == "mbert" and 1 <= b - a <= 2 and text[a:b].isdigit():
            # AGE also mislabels fragments of account/identity numbers. Never remove those fragments.
            connected = any(o is not s and o["label"] in _VALUE_FAMILY and (
                (o["end"] <= a and _short_value_gap(text[o["end"]:a]))
                or (b <= o["start"] and _short_value_gap(text[b:o["start"]]))
                or (o["start"] < b and a < o["end"])) for o in spans)
            context = text[max(0, a - 40):min(len(text), b + 40)]
            if not connected and not _AGE_CONTEXT.search(context):
                continue
        out.append(s)
    return out


def _name_merge(text, spans):
    out = []
    for s in sorted(spans, key=lambda s: (s["start"], s["end"])):
        if out and out[-1]["label"] in NAME_PARTS and s["label"] in NAME_PARTS:
            prev = out[-1]
            gap = text[prev["end"]:s["start"]]
            if (prev["end"] <= s["start"] and len(gap) <= MAX_GAP_CHARS
                    and not _BLANK_LINE.search(gap) and (not gap or _NAME_GAP.fullmatch(gap))):
                out[-1] = _changed(prev, end=s["end"])
                continue
        out.append(s)
    return out


def _value_gaps(text, spans):
    out = []
    for s in sorted(spans, key=lambda s: (s["start"], s["end"])):
        family = _VALUE_FAMILY.get(s["label"])
        if out and family and family == _VALUE_FAMILY.get(out[-1]["label"]):
            prev = out[-1]
            if prev["end"] <= s["start"] and _short_value_gap(text[prev["end"]:s["start"]]):
                out[-1] = _changed(prev, end=s["end"])
                continue
        a, b = s["start"], s["end"]
        # mBERT sometimes calls an underscore username EMAIL and omits its attached @ marker.
        # This is a lexical sigil, not free punctuation: no internal @ and no preceding run/second @.
        if (s["label"] in ("USERNAME", "EMAIL") and a > 0 and text[a - 1] == "@"
                and "@" not in text[a:b] and text[a:b] and all(c.isalnum() or c in "._-" for c in text[a:b])
                and (a < 2 or not (text[a - 2].isalnum() or text[a - 2] in "._-@"))):
            s = _changed(s, start=a - 1)
        out.append(s)
    return out


# ---- rule a -------------------------------------------------------------------------------------------
def _x_ok(text, pos, a, b, end):
    """A bare 'x' at pos is an extension only after whitespace / the span end and not before a unit or another x+digit."""
    if pos != b and pos != a and text[pos - 1] not in " \t":
        return False
    return not _X_BLOCK.match(text, end)


def _ext_end(text, s):
    a, b = s["start"], s["end"]
    if sum(ch.isdigit() for ch in text[a:b]) < MIN_PHONE_DIGITS:
        return b
    m = _EXT.match(text, b)
    if m and (m.group("x") is None or _x_ok(text, m.start("x"), a, b, m.end())):
        return m.end()
    kw = _KW_TAIL.search(text, a, b)
    if kw:  # span already holds the keyword but stops before its digits
        m = _DIGITS.match(text, b)
        if m and (kw.group(0).rstrip(" \t.:-").lower() != "x" or _x_ok(text, kw.start(), a, b, m.end())):
            return m.end()
    if text[b - 1].isdigit():
        m = _DASH.match(text, b)
        if m:
            return m.end()
    return b


def _phone_extension(text, spans):
    out = []
    for s in spans:
        if s["label"] == "TELEPHONENUM":
            e = _ext_end(text, s)
            if e > s["end"]:
                s = _changed(s, end=e)
        out.append(s)
    return out


# ---- rule b -------------------------------------------------------------------------------------------
def _sentence_end(text, a, b):
    seg = text[a:b + 1]  # include the char after the gap: it decides "uppercase follows"
    if _BLANK_LINE.search(text[a:b]):
        return True
    for m in _SENT_END.finditer(seg):
        if m.end() < len(seg) and seg[m.end()].isupper():
            return True
    return False


def _zip_prefix(text, spans):
    out = []
    for s in spans:
        if s["label"] == "ZIPCODE" and s["start"] > 0:
            m = _ISO.search(text, max(0, s["start"] - 3), s["start"])
            if m:
                s = _changed(s, start=m.start())
        out.append(s)
    return out


def _street_prefix(text, group):
    """Pull the left edge over a street-type word that precedes the first STREET piece (e.g. 'via', 'rue de')."""
    first = min(group, key=lambda p: p["start"])
    if first["label"] != "STREET":
        return first["start"]
    m = _STREET_PREFIX.search(text, max(0, first["start"] - 16), first["start"])
    return m.start() if m else first["start"]


def _unit_left(text, a):
    for k in range(4):
        if a - k < 0 or any(ch not in _SEP for ch in text[a - k:a]):
            break
        if k == 0 and a > 0 and text[a - 1].isalnum() and text[a].isalnum():
            continue
        end = a - k
        for p in range(max(0, end - MAX_GAP_CHARS), end):
            m = _UNIT.match(text, p, end)
            if m and m.end() == end:
                return p
    return a


def _unit_right(text, b):
    for k in range(4):
        if b + k > len(text) or any(ch not in _SEP for ch in text[b:b + k]):
            break
        m = _UNIT.match(text, b + k)
        if m:
            return m.end()
    return b


def _extend_address(text, a, b):
    for _ in range(4):
        before = (a, b)
        b = _unit_right(text, b)
        a = _unit_left(text, a)
        m = _COUNTRY.match(text, b)
        if m:
            b = m.end()
        if (a, b) == before:
            break
    return a, b


_RUN_CH = frozenset("._-@/")


def _run_bounds(text, a, b):
    """Alphanumeric run (letters/digits joined by . _ - @ /) around [a, b), trimmed to alphanumeric edges."""
    lo, hi = a, b
    while lo > 0 and (text[lo - 1].isalnum() or text[lo - 1] in _RUN_CH):
        lo -= 1
    while hi < len(text) and (text[hi].isalnum() or text[hi] in _RUN_CH):
        hi += 1
    while lo < a and not text[lo].isalnum():
        lo += 1
    while hi > b and not text[hi - 1].isalnum():
        hi -= 1
    return lo, hi


def _usable_part(text, s, others, parts):
    """Word-bounded (alnum neighbours must belong to an adjacent address piece, e.g. '12' + 'a' of '12a') and not in a non-address run."""
    a, b = s["start"], s["end"]

    def covered(j):
        return any(p is not s and p["start"] <= j < p["end"] for p in parts)

    if a > 0 and text[a - 1].isalnum() and text[a].isalnum() and not covered(a - 1):
        return False
    if b < len(text) and text[b - 1].isalnum() and text[b].isalnum() and not covered(b):
        return False
    lo, hi = _run_bounds(text, a, b)
    return not any(o["start"] < hi and lo < o["end"] for o in others)


def _address_merge(text, spans):
    spans = sorted(spans, key=lambda s: (s["start"], s["end"]))
    others = [s for s in spans if s["label"] not in ADDRESS_PARTS]
    parts = [s for s in spans if s["label"] in ADDRESS_PARTS]
    unused = [s for s in parts if not _usable_part(text, s, others, parts)]
    groups, cur = [], []
    for s in spans:
        if s["label"] not in ADDRESS_PARTS or any(s is u for u in unused):
            continue
        if cur:
            prev_end = max(p["end"] for p in cur)
            gap = text[prev_end:s["start"]] if s["start"] > prev_end else ""
            ok = (len(gap) <= MAX_GAP_CHARS and len(gap.split()) <= MAX_GAP_WORDS
                  and not (gap and _sentence_end(text, prev_end, s["start"]))
                  and not any(o["start"] < s["start"] and o["end"] > prev_end for o in others))
            if not ok:
                groups.append(cur)
                cur = []
        cur.append(s)
    if cur:
        groups.append(cur)
    out = list(others) + unused
    for g in groups:
        if len(g) < 2 or not any(p["label"] in ("STREET", "CITY") for p in g):
            out.extend(g)
            continue
        a, b = _extend_address(text, _street_prefix(text, g), max(p["end"] for p in g))
        out.append({"start": a, "end": b, "label": "ADDRESS", "source": "refine"})
    return out


# ---- rule c -------------------------------------------------------------------------------------------
def _word_pos(text, j):
    if not 0 <= j < len(text):
        return False
    ch = text[j]
    if ch.isalnum():
        return True
    return ch in "-./_@'\u2019\u2010\u2011" and 0 < j < len(text) - 1 and text[j - 1].isalnum() and text[j + 1].isalnum()


_DIMENSION = re.compile(r"\d+(?:[x\u00d7]\d+)+", re.I)


def _is_dimension(text, a, b):
    lo, hi = _run_bounds(text, a, b)
    return _DIMENSION.fullmatch(text, lo, hi) is not None


def _word_completion(text, spans):
    out = []
    for s in spans:
        a, b = s["start"], s["end"]
        if _is_dimension(text, a, b):
            out.append(s)
            continue
        if _word_pos(text, a - 1) and _word_pos(text, a):
            lim = max(0, a - MAX_RUN_EXTENSION)
            while a > lim and _word_pos(text, a - 1):
                a -= 1
        if _word_pos(text, b - 1) and _word_pos(text, b):
            lim = min(len(text), b + MAX_RUN_EXTENSION)
            while b < lim and _word_pos(text, b):
                b += 1
        out.append(_changed(s, start=a, end=b) if (a, b) != (s["start"], s["end"]) else s)
    return out


# ---- final union --------------------------------------------------------------------------------------
def _collapse(group):
    if len(group) == 1:
        return dict(group[0])
    label = "ADDRESS" if any(g["label"] == "ADDRESS" for g in group) else group[0]["label"]
    sources = {g["source"] for g in group}
    source = "refine" if "refine" in sources else ("both" if len(sources) > 1 else next(iter(sources)))
    return {"start": min(g["start"] for g in group), "end": max(g["end"] for g in group), "label": label, "source": source}


def _union(spans):
    out, group, end = [], [], -1
    for s in sorted(spans, key=lambda s: (s["start"], -s["end"])):
        if group and s["start"] > end:  # touching spans (start == end) merge too
            out.append(_collapse(group))
            group = []
        end = s["end"] if not group else max(end, s["end"])
        group.append(s)
    if group:
        out.append(_collapse(group))
    return out


def refine(text, spans):
    if not isinstance(text, str) or not isinstance(spans, (list, tuple)):
        _err()
    spans = _check(text, spans)
    if not spans:
        return []
    spans = _age_near_misses(text, spans)
    spans = _value_gaps(text, _union(_word_completion(text, spans)))
    spans = _phone_extension(text, spans)
    spans = _address_merge(text, _zip_prefix(text, spans))
    spans = _name_merge(text, _word_completion(text, spans))
    return _union(spans)
