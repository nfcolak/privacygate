"""Synthetic TRAIN-ONLY clean negatives (EN/DE/FR/IT/ES) and a fail-closed loader. Never prints text.

Semantics: generic, impersonal statements (general knowledge, weather, software, cooking, geography).
Deliberately excluded: person-linked references, names, identifiers/codes, contact details, addresses,
dates, digits, ambiguous sensitive context. No digits at all, so no code-like tokens can occur.
Limitations: statements are template-composed and low diversity; absence of personal content is by
construction of the word lists, not proven; independence from dev/test challenge templates is by
separate authoring only (those texts were not consulted), not a proven property.
"""
import hashlib
import json
import os
import random
import stat

LANGS = ("en", "de", "fr", "it", "es")
PER_LANG = 200
SEED = 20261002
GEN_VERSION = "neg-v2"
MAX_ROWS, MAX_CHARS = 20000, 2000
MAX_LINE_BYTES = 32768          # one JSONL row, raw bytes (escaped non-ASCII can be 6 bytes/char)
MAX_FILE_BYTES = 16 * 1024 * 1024  # hard read bound; checked before any parsing
KEYS = {"row_id", "language", "source_text", "privacy_mask", "template_id", "split"}

# per language: frames with {A} (singular impersonal subject incl. article) and {B} (predicate, main-clause order).
# German frames never use "dass" + main-clause order: they use a colon-introduced main clause (A is capitalised after ": ").
SPEC = {
    "en": (["In general, {A} {B}.", "It is widely understood that {A} {B}.", "Usually {A} {B}.", "As a rule, {A} {B}.",
            "Textbooks note that {A} {B}.", "Observers agree that {A} {B}.", "Often {A} {B}.", "Broadly speaking, {A} {B}."],
           ["the river", "a mountain lake", "the old bridge", "a freight train", "the autumn wind", "a bread dough"],
           ["changes slowly over the seasons", "depends on the local climate", "is easier to study from a distance",
            "requires patience and care", "looks different in the early morning", "is part of everyday life"]),
    "de": (["Im Allgemeinen gilt: {A} {B}.", "Man weiß allgemein: {A} {B}.", "Meistens gilt: {A} {B}.", "In der Regel gilt: {A} {B}.",
            "Lehrbücher halten fest: {A} {B}.", "Beobachter sind sich einig: {A} {B}.", "Oft gilt: {A} {B}.", "Grob gesagt: {A} {B}."],
           ["der Fluss", "ein Bergsee", "die alte Brücke", "ein Güterzug", "der Herbstwind", "ein Brotteig"],
           ["verändert sich langsam im Lauf der Jahreszeiten", "hängt vom örtlichen Klima ab", "lässt sich aus der Ferne leichter beobachten",
            "braucht Geduld und Sorgfalt", "sieht am frühen Morgen anders aus", "gehört zum Alltag"]),
    "fr": (["En général, {A} {B}.", "On sait bien que {A} {B}.", "Habituellement, {A} {B}.", "En règle générale, {A} {B}.",
            "Les manuels notent que {A} {B}.", "Les observateurs s'accordent à dire que {A} {B}.", "Souvent, {A} {B}.", "Globalement, {A} {B}."],
           ["la rivière", "un lac de montagne", "le vieux pont", "un train de marchandises", "le vent d'automne", "une pâte à pain"],
           ["change lentement au fil des saisons", "dépend du climat local", "s'étudie plus facilement de loin",
            "demande de la patience et du soin", "paraît différent tôt le matin", "fait partie de la vie quotidienne"]),
    "it": (["In generale, {A} {B}.", "È noto che {A} {B}.", "Di solito {A} {B}.", "Di regola {A} {B}.",
            "I manuali osservano che {A} {B}.", "Gli osservatori concordano che {A} {B}.", "Spesso {A} {B}.", "In linea di massima {A} {B}."],
           ["il fiume", "un lago di montagna", "il vecchio ponte", "un treno merci", "il vento d'autunno", "un impasto per il pane"],
           ["cambia lentamente nel corso delle stagioni", "dipende dal clima locale", "si studia meglio da lontano",
            "richiede pazienza e cura", "appare diverso al mattino presto", "fa parte della vita quotidiana"]),
    "es": (["En general, {A} {B}.", "Se sabe que {A} {B}.", "Normalmente {A} {B}.", "Por regla general, {A} {B}.",
            "Los manuales señalan que {A} {B}.", "Los observadores coinciden en que {A} {B}.", "A menudo {A} {B}.", "En términos generales, {A} {B}."],
           ["el río", "un lago de montaña", "el viejo puente", "un tren de mercancías", "el viento de otoño", "una masa de pan"],
           ["cambia despacio con las estaciones", "depende del clima local", "se estudia mejor desde lejos",
            "requiere paciencia y cuidado", "se ve distinto a primera hora", "forma parte de la vida cotidiana"]),
}


def _render(lang, ti, a, b):
    frame = SPEC[lang][0][ti]
    if ": {A}" in frame:  # a full main clause after a colon starts upper-case in German
        a = a[0].upper() + a[1:]
    return frame.format(A=a, B=b)


def generate():
    rows = []
    for lang in LANGS:
        frames, subj, pred = SPEC[lang]
        rng = random.Random("{}:{}:{}".format(SEED, GEN_VERSION, lang))
        combos = [(t, i, j) for t in range(len(frames)) for i in range(len(subj)) for j in range(len(pred))]
        rng.shuffle(combos)
        seen, n = set(), 0
        for t, i, j in combos:
            text = _render(lang, t, subj[i], pred[j])
            text = text[0].upper() + text[1:]
            if text in seen:
                continue
            seen.add(text)
            tid = "neg-{}-t{}".format(lang, t)
            rid = hashlib.sha256("{}:{}:{}:{}".format(GEN_VERSION, lang, t, text).encode()).hexdigest()
            rows.append({"row_id": rid, "language": lang, "source_text": text, "privacy_mask": [], "template_id": tid, "split": "train"})
            n += 1
            if n == PER_LANG:
                break
    check_rows(rows)
    return rows


def dumps(rows):
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def content_hash(rows):
    return hashlib.sha256(dumps(rows).encode()).hexdigest()


def counts(rows):
    c = {l: 0 for l in LANGS}
    for r in rows:
        c[r["language"]] += 1
    return c


def check_rows(rows, forbid_ids=()):
    """Fail-closed: raise ValueError with a code only (never the row content, keys or types)."""
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError("neg_row_count")
    ids, texts, tmpl = set(), set(), {}
    forbid = set(forbid_ids)
    for r in rows:
        if not isinstance(r, dict) or set(r) != KEYS:
            raise ValueError("neg_schema")
        for k in ("row_id", "language", "source_text", "template_id", "split"):
            if not isinstance(r[k], str):
                raise ValueError("neg_field_type")
        if not isinstance(r["privacy_mask"], list):
            raise ValueError("neg_field_type")
        if r["split"] != "train":
            raise ValueError("neg_split_not_train")
        if r["language"] not in LANGS:
            raise ValueError("neg_language")
        if r["privacy_mask"]:
            raise ValueError("neg_annotations_not_empty")
        t = r["source_text"]
        if not t.strip() or len(t) > MAX_CHARS:
            raise ValueError("neg_text_bounds")
        if not r["row_id"] or r["row_id"] in ids or r["row_id"] in forbid:
            raise ValueError("neg_row_id")
        if not r["template_id"]:
            raise ValueError("neg_template_id")
        if any(ch.isdigit() for ch in t):
            raise ValueError("neg_contains_digit")
        if (r["language"], t) in texts:
            raise ValueError("neg_duplicate_text")
        ids.add(r["row_id"]); texts.add((r["language"], t))
        tmpl.setdefault(r["template_id"], r["language"])
        if tmpl[r["template_id"]] != r["language"]:
            raise ValueError("neg_template_language")


def _read_bounded(path):
    """Read at most MAX_FILE_BYTES from a regular file; reject larger/non-regular files before parsing."""
    try:
        fd = os.open(os.fspath(path), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    except TypeError:
        raise ValueError("neg_path") from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("neg_not_regular_file")
        f = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with f:
        raw = f.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("neg_file_too_large")
    return raw


def load_negative_file(path, forbid_ids=()):
    """Return (rows, binding). binding = counts + sha256 of the file bytes; value-free.

    Raises ValueError(code) for any malformed content (OSError only for unreadable paths). The read is
    byte-bounded and the non-empty line count / line size are checked before any JSON parsing.
    """
    raw = _read_bounded(path)
    lines = [l for l in raw.split(b"\n") if l.strip()]
    if not lines or len(lines) > MAX_ROWS:
        raise ValueError("neg_row_count")
    if any(len(l) > MAX_LINE_BYTES for l in lines):
        raise ValueError("neg_line_too_long")
    rows = []
    for l in lines:
        try:
            rows.append(json.loads(l.decode("utf-8")))
        except (ValueError, RecursionError):  # JSONDecodeError and UnicodeDecodeError are ValueErrors
            raise ValueError("neg_unparseable") from None
    check_rows(rows, forbid_ids)
    return rows, {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "per_language": counts(rows),
                  "templates": len({r["template_id"] for r in rows})}
