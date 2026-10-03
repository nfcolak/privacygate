#!/usr/bin/env python3
"""Deterministic DEVELOPMENT fixture: personal-information spans that cross an ACTUAL sliding-window cut.

Question the fixture serves: when a span is cut by the end of an mBERT window, does the overlapping next window
still see it whole and does it end up fully masked? Placement is verified with the real tokenizer and the real
privacygate.mbert_data.encode (510 content tokens per window, step 382, overlap 128); a row whose placement did
not verify is regenerated with a different filler rotation, and generation fails (fixed code) if none works.

Families (5 languages x 2 variants each = 10 rows per family):
  cut_phone, cut_address, cut_name, cut_identifier  - every gold span starts before the end of window k and ends after it
  mid_window                                        - matched control: SAME values, same row length, but every span lies
                                                      fully inside the unique middle of one window (far from every cut)
Variant 0 carries 3 spans (cuts 1,2,3), variant 1 carries 2 spans (cuts 2,4); cut k = end of window k (token 510+382k).

Invented values only; no model, no detector, no predictions. Only aggregate counts/hashes reach stdout; the JSONL is
git-ignored and the value-free manifest is committed. Errors are fixed codes and never echo input.
Usage: make_window_cut_fixture.py [--verify]
"""
import hashlib
import json
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from make_masking_stress import CUES, LANGS  # noqa: E402
from privacygate import mbert_data  # noqa: E402

DATA = ROOT / "data/augmentation/window-cut-dev.jsonl"
MANIFEST = ROOT / "artifacts/window-cut/manifest.json"
VERSION = "window-cut-v1"
KEYS = frozenset(("case_id", "language", "family", "text", "gold", "split"))
CUT_FAMILIES = ("cut_phone", "cut_address", "cut_name", "cut_identifier")
CONTROL = "mid_window"
VARIANT_CUTS = {0: (1, 2, 3), 1: (2, 4)}  # window index k whose END is crossed by the span
SIZE, STEP = mbert_data.MAX_LEN - 2, mbert_data.MAX_LEN - 2 - mbert_data.STRIDE  # 510, 382
MID_MARGIN_TOKENS = 60
MAX_CHARS = 12000
MAX_ATTEMPTS = 24
CUE_INDEX = {"PERSONNAME": 1, "TELEPHONENUM": 3, "IDCARDNUM": 4, "ADDRESS": 7, "USERNAME": 8, "ACCOUNTNUM": 9}


class WindowCutError(Exception):
    """Fixed, value-free error code; never includes input or exception details."""


def require(ok, code):
    if not ok:
        raise WindowCutError(code) from None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon_line(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def shape(value):
    return "".join("a" if c.isalpha() else "9" if c.isdigit() else c for c in value)


# ---- neutral filler prose (no people, numbers, places or identifying combinations) --------------------------------
FILLER = {
    "en": ("A prism separates light into a spectrum.", "A smooth surface reflects light evenly.",
           "The description concerns only abstract geometric shapes and optical properties.",
           "A lens bends rays so that they meet at a single focal point.",
           "Clear glass lets most light pass, while frosted glass scatters it.",
           "The thickness of a coating changes which colours are reflected.",
           "A flat mirror forms an image that appears behind the surface.",
           "Polished metal reflects more light than rough stone.",
           "Rays that enter a prism at a steep angle bend more strongly.",
           "A diffraction grating splits light into many narrow beams.",
           "Shadows grow sharper as the source of light becomes smaller.",
           "The material tests compare how different samples transmit light."),
    "de": ("Ein Prisma zerlegt Licht in ein Spektrum.", "Eine glatte Oberfläche reflektiert Licht gleichmäßig.",
           "Die Beschreibung betrifft nur abstrakte geometrische Formen und optische Eigenschaften.",
           "Eine Linse bricht Strahlen so, dass sie sich in einem Brennpunkt treffen.",
           "Klares Glas lässt das meiste Licht durch, mattes Glas streut es.",
           "Die Dicke einer Beschichtung verändert, welche Farben zurückgeworfen werden.",
           "Ein ebener Spiegel erzeugt ein Bild, das hinter der Fläche zu liegen scheint.",
           "Polierte Metalle werfen mehr Licht zurück als raue Steine.",
           "Strahlen, die in einem steilen Winkel in ein Prisma eintreten, werden stärker gebrochen.",
           "Ein Beugungsgitter teilt Licht in viele schmale Strahlen.",
           "Schatten werden schärfer, je kleiner die Lichtquelle ist.",
           "Die Materialprüfungen vergleichen, wie verschiedene Proben Licht durchlassen."),
    "fr": ("Un prisme sépare la lumière en un spectre.", "Une surface lisse réfléchit la lumière de façon uniforme.",
           "La description concerne uniquement des formes géométriques abstraites et des propriétés optiques.",
           "Une lentille dévie les rayons pour qu'ils se rejoignent en un seul point focal.",
           "Le verre transparent laisse passer presque toute la lumière, tandis que le verre dépoli la diffuse.",
           "L'épaisseur d'un revêtement change les couleurs qui sont réfléchies.",
           "Un miroir plan forme une image qui semble se trouver derrière la surface.",
           "Le métal poli réfléchit davantage de lumière que la pierre brute.",
           "Les rayons qui entrent dans un prisme sous un angle prononcé sont plus fortement déviés.",
           "Un réseau de diffraction divise la lumière en de nombreux faisceaux étroits.",
           "Les ombres deviennent plus nettes lorsque la source lumineuse est plus petite.",
           "Les essais de matériaux comparent la façon dont différents échantillons transmettent la lumière."),
    "it": ("Un prisma separa la luce in uno spettro.", "Una superficie liscia riflette la luce in modo uniforme.",
           "La descrizione riguarda soltanto forme geometriche astratte e proprietà ottiche.",
           "Una lente piega i raggi in modo che si incontrino in un unico punto focale.",
           "Il vetro trasparente lascia passare quasi tutta la luce, mentre il vetro opaco la diffonde.",
           "Lo spessore di un rivestimento cambia i colori che vengono riflessi.",
           "Uno specchio piano forma un'immagine che sembra trovarsi dietro la superficie.",
           "Il metallo lucidato riflette più luce della pietra grezza.",
           "I raggi che entrano in un prisma con un angolo ripido si piegano di più.",
           "Un reticolo di diffrazione divide la luce in molti fasci stretti.",
           "Le ombre diventano più nitide quando la sorgente di luce è più piccola.",
           "Le prove sui materiali confrontano il modo in cui campioni diversi trasmettono la luce."),
    "es": ("Un prisma separa la luz en un espectro.", "Una superficie lisa refleja la luz de manera uniforme.",
           "La descripción trata únicamente de formas geométricas abstractas y propiedades ópticas.",
           "Una lente desvía los rayos para que se junten en un único punto focal.",
           "El vidrio transparente deja pasar casi toda la luz, mientras que el vidrio esmerilado la dispersa.",
           "El grosor de un recubrimiento cambia los colores que se reflejan.",
           "Un espejo plano forma una imagen que parece estar detrás de la superficie.",
           "El metal pulido refleja más luz que la piedra rugosa.",
           "Los rayos que entran en un prisma con un ángulo pronunciado se desvían más.",
           "Una red de difracción divide la luz en muchos haces estrechos.",
           "Las sombras se vuelven más nítidas cuanto más pequeña es la fuente de luz.",
           "Las pruebas de materiales comparan cómo distintas muestras transmiten la luz."),
}
PAD_CANDIDATES = {  # candidate single-token fillers; kept only if the real tokenizer gives exactly one token
    "en": ("light", "glass", "lens", "prism", "edge", "angle", "shape", "beam"),
    "de": ("Licht", "Glas", "Linse", "Form", "Kante", "Winkel", "Strahl", "Prisma"),
    "fr": ("verre", "lentille", "forme", "bord", "angle", "rayon", "prisme", "miroir"),
    "it": ("luce", "vetro", "lente", "forma", "bordo", "angolo", "raggio", "prisma"),
    "es": ("luz", "vidrio", "lente", "forma", "borde", "ángulo", "rayo", "prisma"),
}

# ---- invented values ------------------------------------------------------------------------------------------------
GIVEN = {"en": ("Tavrel", "Quenlow", "Brisvane", "Ormelith", "Zandrel"), "de": ("Mörda", "Kelvric", "Thürwin", "Ostrael", "Lüvane"),
         "fr": ("Quenir", "Maldrec", "Brévane", "Odrilon", "Sylvaric"), "it": ("Fiolo", "Marvino", "Ghelda", "Orsenzo", "Tavilia"),
         "es": ("Zabrín", "Quirelo", "Mavenda", "Ordulfo", "Teluvia")}
SURNAME = {"en": ("Brelquist", "Hanvorth", "Velquine", "Marsolk", "Dorquell"), "de": ("Hanzelmüll", "Brogenrath", "Vülkemann", "Schorndal", "Zwenkelmeier"),
           "fr": ("Vorquenet", "Delmarquière", "Tourvelle", "Sauvarenc", "Belquerais"), "it": ("Dalmorezzi", "Gherlanti", "Tormovesi", "Squarzelli", "Ovetrani"),
           "es": ("Quirbenda", "Zamorvelo", "Trescavilla", "Olvarenque", "Bruzaldez")}
STREET = {"en": ("Orvane Street", "Quillen Road", "Marrowick Lane", "Tavish Court", "Dorvel Avenue"),
          "de": ("Tilmerweg", "Orvanstraße", "Quellenhofgasse", "Brenzelallee", "Vorstelplatz"),
          "fr": ("rue des Orvanes", "avenue Mortelin", "impasse Quivarel", "rue Belvenac", "boulevard Tarsolin"),
          "it": ("via Talmori", "corso Vemarino", "vicolo Orsanti", "piazza Quelvi", "via Brosenza"),
          "es": ("calle Zorvena", "avenida Tamorvel", "plaza Quirseda", "paseo Olvarín", "camino Brezuelo")}
CITY = {"en": ("Quillenmoor", "Harrowick", "Dunvarel", "Thistlemarsh", "Orvenby"), "de": ("Zelvenau", "Brohnstadt", "Kirmeshagen", "Tallendorf", "Vorsbach"),
        "fr": ("Moravaux", "Saint-Quervil", "Trelombe", "Vaudrenne", "Belcourtin"), "it": ("Tormavesco", "Brosenzano", "Calvarello", "Orsevale", "Mazzorina"),
        "es": ("Zorvaleda", "Villamorquén", "Trebolanda", "Quirasena", "Almorvedo")}
UNIT = {"en": "apartment", "de": "Wohnung", "fr": "appartement", "it": "interno", "es": "apartamento"}
COUNTRY = {"en": "United Kingdom", "de": "Deutschland", "fr": "France", "it": "Italia", "es": "España"}
DIAL = {"en": "44", "de": "49", "fr": "33", "it": "39", "es": "34"}


def digits(li, k, width, salt):
    return str(10 ** (width - 1) + (li * 7919 + k * 104729 + salt * 1303) % (9 * 10 ** (width - 1)))


def make_phone(lang, k):
    li, d, cc = LANGS.index(lang), digits(LANGS.index(lang), k, 9, 1), DIAL[lang]
    a, b, c = d[:3], d[3:6], d[6:]
    return (f"+{cc} {a} {b} {c}", f"+{cc} ({a}) {b}-{c}", f"00{cc} {a}.{b}.{c}", f"+{cc}-{a}-{b}{c}", f"0{a} {b} {c}")[k % 5]


def make_address(lang, k):
    li = LANGS.index(lang)
    street, city = STREET[lang][k % 5], CITY[lang][(k + li) % 5]
    num = str(11 + li * 3 + k * 5)
    unit = UNIT[lang] + " " + str(3 + k + li) + "AB"[k % 2]
    zipc = digits(li, k, 5, 2)
    first = f"{num} {street}" if lang in ("en", "fr") else f"{street} {num}"
    if k % 3 == 0:
        return f"{first}, {unit}, {zipc} {city}, {COUNTRY[lang]}"
    if k % 3 == 1:
        return f"{first}, {unit}\n{zipc} {city}\n{COUNTRY[lang]}"
    return f"{first}; {unit}; {zipc} {city}; {COUNTRY[lang]}"


def make_name(lang, k):
    return GIVEN[lang][k % 5] + " " + SURNAME[lang][(k + 2) % 5]


def make_identifier(lang, kind, variant):
    li, serial = LANGS.index(lang), digits(LANGS.index(lang), variant + 1, 6, 3 + (kind == "ACCOUNTNUM"))
    if kind == "IDCARDNUM":
        return ("VK-" + serial[:3] + "/" + serial[3:] + "0", "ID " + serial[:4] + " " + serial[4:] + " K")[variant]
    if kind == "ACCOUNTNUM":
        return ("WD-" + serial + "-" + str(41 + li), serial[:3] + " " + serial[3:] + "/" + str(41 + li))[variant]
    return ("@vorlund_" + lang + serial, "kelmora." + lang + serial)[variant]


def plan_for(family, lang, variant):
    """[(label, value)] in text order for a cut family; the control reuses the identical list."""
    n = len(VARIANT_CUTS[variant])
    if family == "cut_phone":
        return [("TELEPHONENUM", make_phone(lang, variant * 3 + i)) for i in range(n)]
    if family == "cut_address":
        return [("ADDRESS", make_address(lang, variant * 3 + i)) for i in range(n)]
    if family == "cut_name":
        return [("PERSONNAME", make_name(lang, variant * 3 + i)) for i in range(n)]
    kinds = (("IDCARDNUM", "ACCOUNTNUM", "USERNAME"), ("USERNAME", "ACCOUNTNUM"))[variant]
    return [(kind, make_identifier(lang, kind, variant)) for kind in kinds]


# ---- tokenizer helpers ----------------------------------------------------------------------------------------------
def ntok(tok, s):
    return len(tok(s, add_special_tokens=False, truncation=False, verbose=False)["input_ids"])


class Builder:
    """Grows text one sentence / one single-token pad word at a time so token positions are exact."""

    def __init__(self, tok, lang, rotation):
        self.tok, self.lang, self.text, self.n = tok, lang, "", 0
        self.sent = [(s + " ", ntok(tok, s)) for s in FILLER[lang]]
        self.pad = [w + " " for w in PAD_CANDIDATES[lang] if ntok(tok, w) == 1]
        require(len(self.pad) >= 3 and all(c > 0 for _, c in self.sent), "pad_words_unavailable")
        self.cursor, self.padcur = rotation % len(self.sent), rotation % len(self.pad)

    def fill_to(self, target, tail=""):
        """Append filler until tokens(text + tail) == target exactly (tail = cue that follows, token-additive)."""
        tail_n = ntok(self.tok, tail) if tail else 0
        require(self.n + tail_n <= target, "placement_overshoot")
        while self.n + tail_n < target:
            s, c = self.sent[self.cursor]
            if self.n + c + tail_n <= target:
                self.text += s
                self.n += c
                self.cursor = (self.cursor + 1) % len(self.sent)
            else:
                self.text += self.pad[self.padcur]
                self.n += 1
                self.padcur = (self.padcur + 1) % len(self.pad)
        require(self.n + tail_n == target, "placement_mismatch")

    def add_span(self, label, value, cue, start_token):
        """Place cue+value so the value's first token index is start_token; returns gold span."""
        self.fill_to(start_token, cue)
        self.text += cue
        self.n += ntok(self.tok, cue)
        gold = {"start": len(self.text), "end": len(self.text) + len(value), "label": label}
        self.text += value
        self.n += ntok(self.tok, value)
        self.text += ". "
        self.n += 1
        return gold


def cue_for(lang, label):
    return CUES[lang][CUE_INDEX[label]] + ": "


def build_row(tok, family, lang, variant, mode, attempt, plan, total_tokens=None):
    ks, li, fam_i = VARIANT_CUTS[variant], LANGS.index(lang), (CUT_FAMILIES + (CONTROL,)).index(family)
    b = Builder(tok, lang, rotation=li * 3 + fam_i * 5 + variant * 2 + attempt * 7)
    gold = []
    for i, ((label, value), k) in enumerate(zip(plan, ks)):
        n = ntok(tok, value)
        require(n >= 3, "value_too_short_to_cut")
        if mode == "cut":
            depth = min(max(n // 2 + ((li + i + variant + attempt) % 3 - 1), 1), n - 1)
            start = SIZE + STEP * k - depth  # value tokens [start, start+n) straddle window k's end
        else:
            start = STEP * k + SIZE // 2 - n // 2  # centred in the unique middle of window k
        gold.append(b.add_span(label, value, cue_for(lang, label), start))
    if total_tokens is None:
        total_tokens = b.n + 140 + ((li + variant) % 4) * 45
    b.fill_to(total_tokens)
    return b.text.rstrip(" "), gold, total_tokens


# ---- verification with the REAL encode ------------------------------------------------------------------------------
def span_tokens(offsets, s, e):
    idx = [i for i, (a, b) in enumerate(offsets) if a < e and b > s]
    return (idx[0], idx[-1]) if idx else None


def verify_row(tok, text, gold, mode):
    """Value-free verification of every gold span against mbert_data.encode windows. Returns per-span dicts."""
    wins = mbert_data.encode(tok, text)
    wchars = []  # per window: (first content char start, last content char end)
    for ids, offs in wins:
        content = [o for o in offs if o is not None]
        require(bool(content), "empty_window")
        wchars.append((content[0][0], content[-1][1]))
    g = [tuple(o) for o in tok(text, add_special_tokens=False, return_offsets_mapping=True, verbose=False)["offset_mapping"]]
    out = []
    for sp in gold:
        s, e = sp["start"], sp["end"]
        tk = span_tokens(g, s, e)
        require(tk is not None, "span_without_tokens")
        crossed = [w for w, (_, end_w) in enumerate(wchars[:-1]) if s < end_w < e]  # real window end inside the span
        touching = [w for w in range(len(wins)) if wchars[w][0] < e and wchars[w][1] > s]
        whole = [w for w, (a, b) in enumerate(wchars) if a <= s and e <= b]
        margin = None
        if len(touching) == 1:
            w = touching[0]
            lo = tk[0] - w * STEP if w > 0 else 10 ** 6
            hi = (w * STEP + SIZE - 1 - tk[1]) if w < len(wins) - 1 else 10 ** 6
            margin = min(lo, hi)
        out.append({"label": sp["label"], "cut_windows": crossed, "touching": len(touching), "whole_in_some_window": bool(whole),
                    "margin_tokens": margin, "span_tokens": tk[1] - tk[0] + 1})
    return out, len(wins), len(g)


def verified(res, mode):
    if mode == "cut":
        return all(len(r["cut_windows"]) == 1 and r["touching"] >= 2 and r["whole_in_some_window"] for r in res)
    return all(not r["cut_windows"] and r["touching"] == 1 and r["whole_in_some_window"]
               and r["margin_tokens"] is not None and r["margin_tokens"] >= MID_MARGIN_TOKENS for r in res)


def make_rows(tok):
    rows, stats = [], []
    for family in CUT_FAMILIES:
        for lang in LANGS:
            for variant in (0, 1):
                plan = plan_for(family, lang, variant)
                for attempt in range(MAX_ATTEMPTS):
                    try:
                        text, gold, total = build_row(tok, family, lang, variant, "cut", attempt, plan)
                        require(len(text) <= MAX_CHARS, "text_too_long")
                        res, nwin, ntokens = verify_row(tok, text, gold, "cut")
                    except WindowCutError:
                        continue
                    if verified(res, "cut") and ntokens == total:
                        break
                else:
                    raise WindowCutError("cut_placement_failed")
                rows.append({"case_id": f"{family}-{lang}-{variant + 1}", "language": lang, "family": family, "text": text, "gold": gold, "split": "dev"})
                stats.append((family, "cut", res, nwin, ntokens, len(text)))
                # matched control: identical values/lengths, every span mid-window, same total token length
                for cattempt in range(MAX_ATTEMPTS):
                    try:
                        ctext, cgold, _ = build_row(tok, CONTROL, lang, variant, "mid", cattempt, plan, total_tokens=total)
                        require(len(ctext) <= MAX_CHARS, "text_too_long")
                        cres, cwin, cntok = verify_row(tok, ctext, cgold, "mid")
                    except WindowCutError:
                        continue
                    if verified(cres, "mid") and cntok == total:
                        break
                else:
                    raise WindowCutError("mid_placement_failed")
                short = family[len("cut_"):]
                rows.append({"case_id": f"{CONTROL}-{short}-{lang}-{variant + 1}", "language": lang, "family": CONTROL, "text": ctext, "gold": cgold, "split": "dev"})
                stats.append((CONTROL, short, cres, cwin, cntok, len(ctext)))
    cuts = [r for r in rows if r["family"] != CONTROL]
    ctrl = [r for r in rows if r["family"] == CONTROL]
    return cuts + ctrl, stats


def check_rows(rows):
    ids, texts = set(), set()
    for r in rows:
        require(isinstance(r, dict) and r.keys() == KEYS and r["split"] == "dev" and r["language"] in LANGS, "row_schema")
        require(r["case_id"] not in ids and r["text"] not in texts, "row_duplicate")
        ids.add(r["case_id"]); texts.add(r["text"])
        prev = 0
        for sp in r["gold"]:
            require(type(sp["start"]) is int and type(sp["end"]) is int and prev <= sp["start"] < sp["end"] <= len(r["text"]), "span_bounds")
            prev = sp["end"]


def tokenizer_files():
    snap = Path(os.environ.get("HF_HOME", "")) / "hub" / "models--google-bert--bert-base-multilingual-cased" / "snapshots" / mbert_data.MODEL_REVISION
    names = ("config.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt")
    return {n: sha((snap / n).read_bytes()) for n in names if (snap / n).exists()}


def manifest_of(rows, stats, raw):
    per = {}
    for fam, kind, res, nwin, ntokens, nchars in stats:
        d = per.setdefault(fam, {"rows": 0, "gold_spans": 0, "verified_crossing_spans": 0, "crossing_seen_whole_by_some_window": 0,
                                 "verified_mid_window_spans": 0, "cut_window_index_histogram": Counter(), "labels": Counter()})
        d["rows"] += 1
        d["gold_spans"] += len(res)
        for r in res:
            d["labels"][r["label"]] += 1
            if fam != CONTROL:
                d["verified_crossing_spans"] += len(r["cut_windows"]) == 1 and r["touching"] >= 2
                d["crossing_seen_whole_by_some_window"] += len(r["cut_windows"]) == 1 and r["whole_in_some_window"]
                d["cut_window_index_histogram"].update(str(w) for w in r["cut_windows"])
            else:
                d["verified_mid_window_spans"] += (not r["cut_windows"] and r["touching"] == 1 and r["margin_tokens"] is not None
                                                   and r["margin_tokens"] >= MID_MARGIN_TOKENS)
    ctrl_by_family = Counter(kind for fam, kind, *_ in stats if fam == CONTROL)
    for d in per.values():
        d["cut_window_index_histogram"] = dict(sorted(d["cut_window_index_histogram"].items()))
        d["labels"] = dict(sorted(d["labels"].items()))
    per[CONTROL]["rows_by_matched_family"] = dict(sorted(ctrl_by_family.items()))
    shapes = {}
    for r in rows:
        for sp in r["gold"]:
            shapes.setdefault(sp["label"], set()).add(shape(r["text"][sp["start"]:sp["end"]]))
    tokens = [s[4] for s in stats]
    chars = [s[5] for s in stats]
    spans = sum(len(r["gold"]) for r in rows)
    cut_spans = sum(d["verified_crossing_spans"] for f, d in per.items() if f != CONTROL)
    return {
        "version": VERSION, "split": "dev", "synthetic_only": True, "aggregate_only": True, "training": False, "test_evaluated": False,
        "dataset": {"path": "data/augmentation/window-cut-dev.jsonl (git-ignored)", "sha256": sha(raw), "bytes": len(raw), "rows": len(rows), "gold_spans": spans},
        "windowing": {"source": "privacygate.mbert_data.encode", "content_tokens_per_window": SIZE, "step": STEP, "overlap": mbert_data.STRIDE,
                      "variant_cut_window_indices": {str(k): list(v) for k, v in VARIANT_CUTS.items()},
                      "cut_definition": "span starts before and ends after the char end of window k's last content token (real encode offsets)",
                      "mid_window_margin_tokens_min": MID_MARGIN_TOKENS},
        "verified_cut_crossing_spans_total": cut_spans,
        "families": per,
        "row_shape": {"tokens_min": min(tokens), "tokens_median": statistics.median(tokens), "tokens_max": max(tokens),
                      "chars_min": min(chars), "chars_max": max(chars), "windows_min": min(s[3] for s in stats), "windows_max": max(s[3] for s in stats)},
        "distinct_value_shapes_per_label": {k: len(v) for k, v in sorted(shapes.items())},
        "tokenizer": {"model_id": mbert_data.MODEL_ID, "revision": mbert_data.MODEL_REVISION, "file_sha256": tokenizer_files()},
        "generator_sha256": sha(Path(__file__).read_bytes()),
        "limitations": [
            "Synthetic, small (40 cut + 40 control rows); invented values may collide with real ones by accident.",
            "Filler is repetitive neutral optics prose with exact single-token padding; real long documents differ.",
            "Controls match values, lengths and total tokens, not surrounding filler text; context wording around spans differs slightly.",
            "Gold PERSONNAME and ADDRESS are diagnostic labels; coverage scoring is label-agnostic.",
        ],
    }


def main():
    try:
        verify = "--verify" in sys.argv[1:]
        require(set(sys.argv[1:]) <= {"--verify"}, "arguments")
        tok = mbert_data.load_tokenizer()
        rows, stats = make_rows(tok)
        check_rows(rows)
        raw = b"".join(canon_line(r) for r in rows)
        manifest = manifest_of(rows, stats, raw)
        require(manifest["verified_cut_crossing_spans_total"] >= 80, "too_few_crossings")
        if verify:
            require(DATA.exists() and sha(DATA.read_bytes()) == manifest["dataset"]["sha256"], "dataset_mismatch")
            committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
            require(committed["dataset"]["sha256"] == manifest["dataset"]["sha256"], "manifest_mismatch")
            print("window_cut_verify_ok sha=" + manifest["dataset"]["sha256"])
            return 0
        DATA.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_bytes(raw)
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print("window_cut_written rows={} spans={} verified_cut_crossings={} sha={}".format(
            len(rows), manifest["dataset"]["gold_spans"], manifest["verified_cut_crossing_spans_total"], manifest["dataset"]["sha256"]))
        return 0
    except WindowCutError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print("window_cut_operation_failed_input_not_shown", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
