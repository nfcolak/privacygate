"""Evidence-gated whole-name assembly and exact document-local propagation.

Pure stdlib; original Python-str offsets, additive outputs, no logging or name
resources. A seed, attached honorific, or bounded personal-name cue is required.
Capitalization alone is not a detector. Non-personal conflicts stop NEW additions
only: callers retain every input candidate. Grammar budgets are conservative
expansion limits, not permission to clip an existing detector span.
"""
from dataclasses import dataclass
import re
import unicodedata


NAME_PARTS = frozenset({"GIVENNAME", "SURNAME", "MIDDLENAME", "TITLE", "PERSONNAME"})
MAX_ATOMS = 16
MAX_CHARS = 160
_TITLES = (
    "Dipl.-Ing.", "Dott.ssa", "Sig.ra", "Sig.na", "Herr", "Frau", "Prof.",
    "Prof", "Dott.", "Dott", "Mlle.", "Mlle", "Mme.", "Mme", "Mrs.",
    "Mrs", "Mr.", "Mr", "Ms.", "Ms", "Dr.", "Dr", "Sig.", "Sig",
    "Sr.", "Sr", "Sra.", "Sra", "Dña.", "Dña", "Doña", "Don", "M.",
)
_TITLE = re.compile("(?:" + "|".join(re.escape(t) for t in sorted(_TITLES, key=len, reverse=True)) + ")", re.I)
_PARTICLES = frozenset("van der den von de la las los del della di da dos das du le ten ter zu des degli dei".split())
# These are structural/cue/common prose words, not given-name/surname lists.
_STOP = frozenset((
    "dear sehr geehrte geehrter geehrten liebe lieber lieben bonjour gentile "
    "estimado estimada estimados estimadas hello hi hallo salut ciao hola "
    "sir madam customer customers client clients cliente clientes kunden kunde "
    "and or und oder et ou e ed o y con mit with avec pour per para "
    "thanks thank regards sincerely best kind cordialement salutations "
    "cordiali saluti atentamente cordialmente grüße grüsse freundlichen "
    "name nom nome nombre signed gez firma email mail phone telephone tel "
    "department division team service services support manager director "
    "company corporation inc ltd llc gmbh ag sa srl sas brand product model "
    "marke produkt modell marque produit modèle marca prodotto modello producto modelo "
    "entreprise abteilung département dipartimento departamento "
    "street road avenue lane boulevard way strasse straße platz gasse weg "
    "rue route chemin via viale piazza corso calle avenida plaza paseo "
    "university institute museum park hotel store shop systems software "
    "heute morgen tomorrow yesterday today "
    "please merci bitte grazie gracias confidential meeting invoice order "
    "room floor suite building address adresse indirizzo dirección "
    "is are was were ist sind est suis sono è es soy called named heißt "
    "heiße heisse heißt heisst m'appelle chiamo llamo the this that a an "
    "der die das ein eine le les il lo gli el un una"
).split()) - _PARTICLES
_CUE = re.compile(
    r"(?<!\w)(?:my\s+name\s+is|je\s+m['’]appelle|mi\s+chiamo|me\s+llamo|"
    r"ich\s+hei(?:ß|ss)e|(?:name|nom|nome|nombre)\s*:|signed\s*:?|gez\.|firma\s*:?)"
    r"[ \t]*(?:\n[ \t]*)?", re.I)
_GREETING = re.compile(
    r"(?<!\w)(?:dear|sehr\s+geehrt(?:e|er|en)|liebe(?:r|n)?|bonjour|gentile|"
    r"estimad(?:o|a|os|as))[ \t]+", re.I)
_NONPERSONAL_PREFIX = re.compile(
    r"(?<!\w)(?:brand|product|model|marque|produit|modèle|marke|produkt|modell|"
    r"marca|prodotto|modello|producto|modelo|company|corporation|entreprise|"
    r"street|road|avenue|rue|route|via|viale|piazza|calle|avenida|plaza|"
    r"strasse|straße|platz|gasse|weg|museum|university|institute|hotel|park|"
    r"department|abteilung|département|dipartimento|departamento)"
    r"(?:[ \t]+(?:named|called|name|nom|nome|nombre|de|la|del|du|le|di|der|von))?"
    r"[ \t:='\"“«-]*$", re.I)
_NONPERSONAL_SUFFIX = re.compile(
    r"^[ \t'\"”»]*(?:street|road|avenue|lane|boulevard|strasse|straße|platz|weg|"
    r"gasse|company|corporation|inc\.?|ltd\.?|llc|gmbh|ag|srl|sas|university|"
    r"institute|museum|park|hotel|brand|product|model|systems|software)(?!\w)", re.I)
_NONPERSONAL_ROLE = re.compile(
    r"(?:sales|marketing|project|account|technical|general|human\s+resources)"
    r"\s+(?:manager|director|department|division|team)(?!\w)", re.I)
_CONTACT = re.compile(r"(?<!\w)@[^\s,;!?]+|[^\s,;!?@]+@[^\s,;!?@]+")
_JOINERS = frozenset("-'’\u2010\u2011")


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    kind: str
    key: str


def _letter(ch):
    return unicodedata.category(ch).startswith("L")


def _mark(ch):
    return unicodedata.category(ch).startswith("M")


def _word_char(ch):
    return ch.isalnum() or _mark(ch) or ch in "_-'’\u2010\u2011@"


def _check(text, cands):
    if not isinstance(text, str) or not isinstance(cands, (list, tuple)):
        raise ValueError("invalid name candidates") from None
    for cand in cands:
        if not isinstance(cand, dict):
            raise ValueError("invalid name candidates") from None
        a, b = cand.get("start"), cand.get("end")
        if (type(a) is not int or type(b) is not int or not 0 <= a < b <= len(text)
                or not isinstance(cand.get("label"), str)):
            raise ValueError("invalid name candidates") from None


def _tokens(text):
    """Unicode L/M words, internal compounds, title dots and dotted initials."""
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        start = i
        title = _TITLE.match(text, i)
        if (title and (i == 0 or not _word_char(text[i - 1]))
                and (title.end() == n or not _word_char(text[title.end()]))):
            i = title.end()
            out.append(_Token(start, i, "title", text[start:i].casefold()))
            continue
        if _letter(text[i]):
            i += 1
            while i < n:
                if _letter(text[i]) or _mark(text[i]):
                    i += 1
                elif text[i] in _JOINERS and i + 1 < n and _letter(text[i + 1]):
                    i += 2
                else:
                    break
            # An initial includes its dot. Compact J.R.R. and J.-P. stay one atom.
            if sum(_letter(c) for c in text[start:i]) == 1 and i < n and text[i] == ".":
                i += 1
                while i < n:
                    j = i + (text[i] in "-\u2010\u2011")
                    if j >= n or not _letter(text[j]):
                        break
                    j += 1
                    while j < n and _mark(text[j]):
                        j += 1
                    if j < n and text[j] == ".":
                        i = j + 1
                    else:
                        break
                out.append(_Token(start, i, "initial", text[start:i].casefold()))
            else:
                key = text[start:i].casefold()
                kind = "particle" if key in _PARTICLES else "word"
                out.append(_Token(start, i, kind, key))
        else:
            i += 1
            out.append(_Token(start, i, "comma" if text[start:i] == "," else "boundary", text[start:i]))
    return out


def _core(text, token):
    if token.kind == "initial":
        return any(c.isupper() for c in text[token.start:token.end] if _letter(c))
    if token.kind != "word" or token.key in _STOP:
        return False
    surface = text[token.start:token.end]
    if surface and surface[0].isupper():
        return True
    # Lowercase surname elisions remain one lexical atom, not ordinary prose.
    elision = re.match(r"(?:d|l|dell)['’]", surface)
    return bool(elision and elision.end() < len(surface) and surface[elision.end()].isupper())


def _candidate(a, b, stage, personal=False):
    return {"start": a, "end": b, "label": "PERSONNAME", "source": "names",
            "score": None, "validation": "n/a", "context": "personal" if personal else "unknown",
            "protected": False, "stage": stage}


def _nonpersonal(text, a, b):
    # A punctuation/newline boundary prevents cues from leaking from other clauses.
    prefix = re.split(r"[\n;.!?]", text[max(0, a - 90):a])[-1]
    return bool(_NONPERSONAL_PREFIX.search(prefix) or _NONPERSONAL_SUFFIX.match(text[b:b + 50])
                or _NONPERSONAL_ROLE.match(text[a:b + 50]))


def _blocked(text, tokens, cands):
    intervals = [(c["start"], c["end"]) for c in cands
                 if c["label"] not in NAME_PARTS and c["label"] != "UNCOVERED"]
    intervals += [(m.start(), m.end()) for m in _CONTACT.finditer(text)]
    return {i for i, t in enumerate(tokens)
            if any(a < t.end and t.start < b for a, b in intervals)
            or (t.start > 0 and (text[t.start - 1].isdigit() or text[t.start - 1] in "@_"))
            or (t.end < len(text) and (text[t.end].isdigit() or text[t.end] in "@_"))}


def _gap(text, left, right, soft=False):
    gap = text[left.end:right.start]
    if not gap:
        # No missing-space inference between plain words, but compact titles work.
        return left.kind == "title" or left.kind == "initial"
    if not all(ch.isspace() for ch in gap):
        return False
    newlines = gap.count("\n") + gap.count("\r") - gap.count("\r\n")
    return newlines == 0 or (soft and newlines == 1)


def _parse(text, tokens, start, blocked, *, soft=False, reverse=False):
    """One name region; pending particles are retained only before a core."""
    i, last, cores, titles, comma, atoms = start, None, 0, 0, False, 0
    left_cores = 0
    right_cores = 0
    while i < len(tokens) and atoms < MAX_ATOMS:
        t = tokens[i]
        if i in blocked or t.end - tokens[start].start > MAX_CHARS:
            break
        if i > start and not _gap(text, tokens[i - 1], t, soft=soft):
            # A single reversed-name comma has no whitespace requirement.
            if not (t.kind == "comma" or tokens[i - 1].kind == "comma"):
                break
            if "\n" in text[tokens[i - 1].end:t.start] or "\r" in text[tokens[i - 1].end:t.start]:
                break
        if t.kind == "title":
            if cores or titles >= 3 or comma:
                break
            titles += 1
        elif _core(text, t):
            cores += 1
            if comma:
                right_cores += 1
            last = i
        elif t.kind == "particle":
            # Neither a particle alone nor a dangling particle is a complete name.
            pass
        elif t.kind == "comma" and reverse and not comma and cores:
            comma = True
            left_cores = cores
        else:
            break
        atoms += 1
        i += 1
    if last is None:
        return None
    # Do not include a comma if the right side does not contain a name core.
    if comma and not right_cores:
        last = next(j for j in range(last, start - 1, -1) if _core(text, tokens[j]))
    return start, last, cores, titles, (left_cores if right_cores else 0)


def _cue_starts(text, tokens):
    cues = {}
    for pattern, soft in ((_CUE, True), (_GREETING, False)):
        for match in pattern.finditer(text):
            for i, t in enumerate(tokens):
                if t.start >= match.end():
                    if text[match.end():t.start].strip() == "":
                        cues[i] = soft
                    break
    return cues


def assemble(text, cands):
    """Return NEW whole PERSONNAME regions without changing input candidates.

    Seeds are name-component candidates from any source; an honorific or an
    explicit multilingual name cue can also anchor a bounded capitalized name.
    Salutations are scope evidence, never part of the returned value. The
    assembler abstains at conflicts, sentence/list boundaries and contacts.
    """
    _check(text, cands)
    tokens = _tokens(text)
    blocked = _blocked(text, tokens, cands)
    cues = _cue_starts(text, tokens)
    seeds = {}
    for cand in cands:
        if cand["label"] in NAME_PARTS and cand.get("context") != "nonpersonal":
            for i, token in enumerate(tokens):
                if cand["start"] < token.end and token.start < cand["end"]:
                    seeds.setdefault(i, set()).add(cand["label"])
    triggers = set(seeds) | set(cues) | {i for i, t in enumerate(tokens) if t.kind == "title"}
    out = {}
    for trigger in sorted(triggers):
        if trigger in blocked:
            continue
        start = trigger
        # Expand only inside the same grammatical run. Newlines require an
        # explicit name field and are checked when parsing from that cue.
        while start > 0 and trigger not in cues:
            prev, cur = tokens[start - 1], tokens[start]
            if start - 1 in blocked or not _gap(text, prev, cur):
                break
            if not (prev.kind in {"title", "particle"} or _core(text, prev)):
                break
            if cur.kind == "title" and prev.kind != "title":
                break
            if tokens[trigger].end - prev.start > MAX_CHARS:
                break
            start -= 1
        soft = cues.get(start, False)
        preliminary = _parse(text, tokens, start, blocked, soft=soft)
        if preliminary is None:
            continue
        _, end, count, titles, _ = preliminary
        # A comma is reversed order only in a name scope, after an evidenced
        # single surname, or after explicitly surname-labelled left components.
        left_seeds = set().union(*(seeds.get(j, set()) for j in range(start, end + 1)))
        field_reverse = cues.get(start, False) and not (count > 1 and "GIVENNAME" in left_seeds)
        reversed_ok = (field_reverse or (bool(left_seeds) and count == 1)
                       or (bool(left_seeds) and left_seeds <= {"SURNAME", "TITLE"}))
        parsed = _parse(text, tokens, start, blocked, soft=soft, reverse=reversed_ok)
        if parsed is None:
            continue
        _, end, count, titles, reversed_cores = parsed
        if not start <= trigger <= end:
            continue
        has_seed = any(j in seeds and seeds[j] - {"TITLE"} for j in range(start, end + 1))
        personal = start in cues or titles > 0
        if not (has_seed or personal):
            continue
        if not has_seed and not titles and count > 4:
            continue
        # Never swallow a recipient list through a reversed-name comma.
        if reversed_cores and not start in cues and reversed_cores > 1 and left_seeds != {"SURNAME"}:
            continue
        a, b = tokens[start].start, tokens[end].end
        if _nonpersonal(text, a, b):
            continue
        # Preserve already overlong/wide detector spans; this module cannot clip
        # them into a smaller purported assembled replacement.
        intersecting = [c for c in cands if c["label"] in NAME_PARTS
                        and c["start"] < b and a < c["end"]]
        if any(c["start"] < a or c["end"] > b for c in intersecting):
            continue
        out[a, b] = _candidate(a, b, "assembled", personal)
    return [out[key] for key in sorted(out)]


def _title_start(text, tokens, start):
    i = start
    count = 0
    while i > 0 and count < 3:
        prev = tokens[i - 1]
        if prev.kind != "title" or not _gap(text, prev, tokens[i]):
            break
        i -= 1
        count += 1
    return i


def propagate(text, cands):
    """Add exact full-core repeats and uniquely resolved titled surnames.

    Only accepted, non-propagated PERSONNAME seeds with two core atoms or an
    attached title are eligible. No bare single-word propagation, fuzzy matching,
    diacritic stripping, cross-document state, or recursive amplification. The
    local token index retains exact surfaces/spacing and original offsets.
    """
    _check(text, cands)
    tokens = _tokens(text)
    blocked = _blocked(text, tokens, cands)
    accepted = [c for c in cands if c["label"] == "PERSONNAME"
                and c.get("stage") != "propagated" and c.get("context") != "nonpersonal"
                and c.get("validation") != "invalid"]
    full, surnames = {}, {}
    occupied = [(c["start"], c["end"]) for c in cands if c["label"] == "PERSONNAME"]
    for cand in accepted:
        idx = [i for i, t in enumerate(tokens) if cand["start"] <= t.start and t.end <= cand["end"]]
        if not idx or idx != list(range(idx[0], idx[-1] + 1)):
            continue
        first, last = idx[0], idx[-1]
        if tokens[first].start != cand["start"] or tokens[last].end != cand["end"]:
            continue
        if _nonpersonal(text, cand["start"], cand["end"]):
            continue
        parsed = _parse(text, tokens, first, blocked, reverse=True)
        if parsed is None or parsed[1] < last:
            continue
        # Approval is based on the given accepted region, not later words.
        title = any(tokens[i].kind == "title" for i in idx)
        core_count = sum(_core(text, tokens[i]) for i in idx)
        if core_count < 2 and not title:
            continue
        if not any(tokens[i].kind == "word" and _core(text, tokens[i]) for i in idx):
            continue
        while first <= last and tokens[first].kind == "title":
            first += 1
        if first > last:
            continue
        alias = text[tokens[first].start:tokens[last].end]
        signature = tuple(text[tokens[i].start:tokens[i].end] for i in range(first, last + 1))
        if core_count >= 2:
            full.setdefault(signature[0], {})[signature] = alias
        # Explicit component evidence retains Spanish double surnames; absent
        # that evidence infer the last core plus its directly preceding particles.
        commas = [i for i in range(first, last + 1) if tokens[i].kind == "comma"]
        if commas:
            sa, sb = first, commas[0] - 1
        else:
            parts = [c for c in cands if c["label"] == "SURNAME"
                     and cand["start"] <= c["start"] < c["end"] <= cand["end"]]
            if parts:
                sa = next((i for i in range(first, last + 1) if tokens[i].end > min(c["start"] for c in parts)), last)
                sb = max(i for i in range(first, last + 1) if tokens[i].start < max(c["end"] for c in parts))
            else:
                sa = sb = last
            while sa > first and tokens[sa - 1].kind == "particle":
                sa -= 1
        if sa > sb or not any(_core(text, tokens[i]) for i in range(sa, sb + 1)):
            continue
        surname = text[tokens[sa].start:tokens[sb].end]
        sig = tuple(text[tokens[i].start:tokens[i].end] for i in range(sa, sb + 1))
        surnames.setdefault(sig[0], {}).setdefault(sig, {"surface": surname, "owners": set()})["owners"].add(alias)
    out = {}

    def add(start, end):
        a, b = tokens[start].start, tokens[end].end
        if (any(i in blocked for i in range(start, end + 1))
                or any(x < b and a < y for x, y in occupied)
                or _nonpersonal(text, a, b)
                or (a > 0 and _word_char(text[a - 1]))
                or (b < len(text) and _word_char(text[b]))):
            return
        out[a, b] = _candidate(a, b, "propagated", True)

    for i, token in enumerate(tokens):
        surface = text[token.start:token.end]
        for sig, alias in full.get(surface, {}).items():
            end = i + len(sig) - 1
            if end >= len(tokens):
                continue
            # Exact original surface equality includes internal separators.
            if text[token.start:tokens[end].end] == alias:
                add(_title_start(text, tokens, i), end)
        titled = _title_start(text, tokens, i)
        if titled == i:
            continue
        for sig, entry in surnames.get(surface, {}).items():
            end = i + len(sig) - 1
            if end >= len(tokens) or len(entry["owners"]) != 1:
                continue
            if text[token.start:tokens[end].end] == entry["surface"]:
                add(titled, end)
    return [out[key] for key in sorted(out)]
