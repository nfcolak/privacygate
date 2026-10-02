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
import random

LANGS = ("en", "de", "fr", "it", "es")
PER_LANG = 200
SEED = 20261002
GEN_VERSION = "neg-v1"
MAX_ROWS, MAX_CHARS = 20000, 2000
KEYS = {"row_id", "language", "source_text", "privacy_mask", "template_id", "split"}

# per language: frames with {A} (singular impersonal subject incl. article) and {B} (predicate)
SPEC = {
    "en": (["In general, {A} {B}.", "It is widely understood that {A} {B}.", "Usually {A} {B}.", "As a rule, {A} {B}.",
            "Textbooks note that {A} {B}.", "Observers agree that {A} {B}.", "Often {A} {B}.", "Broadly speaking, {A} {B}."],
           ["the river", "a mountain lake", "the old bridge", "a freight train", "the autumn wind", "a bread dough"],
           ["changes slowly over the seasons", "depends on the local climate", "is easier to study from a distance",
            "requires patience and care", "looks different in the early morning", "is part of everyday life"]),
    "de": (["Im Allgemeinen gilt: {A} {B}.", "Man weiß allgemein, dass {A} {B}.", "Meistens gilt: {A} {B}.", "In der Regel gilt: {A} {B}.",
            "Lehrbücher halten fest, dass {A} {B}.", "Beobachter sind sich einig, dass {A} {B}.", "Oft gilt: {A} {B}.", "Grob gesagt: {A} {B}."],
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
    return SPEC[lang][0][ti].format(A=a, B=b)


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
    """Fail-closed: raise ValueError with a code only (never the row content)."""
    if not rows or len(rows) > MAX_ROWS:
        raise ValueError("neg_row_count")
    ids, texts, tmpl = set(), set(), {}
    forbid = set(forbid_ids)
    for r in rows:
        if not isinstance(r, dict) or set(r) != KEYS:
            raise ValueError("neg_schema")
        if r["split"] != "train":
            raise ValueError("neg_split_not_train")
        if r["language"] not in LANGS:
            raise ValueError("neg_language")
        if r["privacy_mask"] != []:
            raise ValueError("neg_annotations_not_empty")
        t = r["source_text"]
        if not isinstance(t, str) or not t.strip() or len(t) > MAX_CHARS:
            raise ValueError("neg_text_bounds")
        if not isinstance(r["row_id"], str) or not r["row_id"] or r["row_id"] in ids or r["row_id"] in forbid:
            raise ValueError("neg_row_id")
        if not isinstance(r["template_id"], str) or not r["template_id"]:
            raise ValueError("neg_template_id")
        if any(ch.isdigit() for ch in t):
            raise ValueError("neg_contains_digit")
        if (r["language"], t) in texts:
            raise ValueError("neg_duplicate_text")
        ids.add(r["row_id"]); texts.add((r["language"], t))
        tmpl.setdefault(r["template_id"], r["language"])
        if tmpl[r["template_id"]] != r["language"]:
            raise ValueError("neg_template_language")


def load_negative_file(path, forbid_ids=()):
    """Return (rows, binding). binding = counts + sha256 of the file bytes; value-free."""
    raw = open(path, "rb").read()
    try:
        rows = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    except (ValueError, UnicodeDecodeError):
        raise ValueError("neg_unparseable") from None
    check_rows(rows, forbid_ids)
    return rows, {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "per_language": counts(rows),
                  "templates": len({r["template_id"] for r in rows})}
