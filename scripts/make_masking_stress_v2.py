#!/usr/bin/env python3
"""Deterministic DEVELOPMENT validation fixtures v2 for rule-based span refinement; stdlib only.

Formats deliberately differ from stress v1: Swiss "CH-8xxx City", postcode-before-street, c/o lines,
floor/Stock/etage units, x123 / Apparat 12 / DW 34 extensions, "-12" DE-style phone suffix, multi-line
addresses, two addresses split by a sentence, plus clean near-miss controls. Invented street/city/person
values; country words are real (they are the rule vocabulary). No model, no detector, no predictions.

Only aggregate counts/hashes reach stdout. The JSONL is git-ignored; the value-free manifest is committed.
Usage: make_masking_stress_v2.py [--verify]
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_masking_stress import CUES, FILLER, LANGS, MAX_CHARS, StressError, assemble, canonical, require, sha, slot  # noqa: E402

DATA = ROOT / "data/augmentation/masking-stress-v2-dev.jsonl"
MANIFEST = ROOT / "docs/masking-stress-v2/manifest.json"
VERSION = "masking-stress-v2"
KEYS = frozenset(("case_id", "language", "family", "text", "gold", "split"))
FAMILIES = ("full_address", "phone", "long_text", "clean")
POSITIVE_KINDS = (
    "addr_ch_postcode", "addr_ch_postcode_country", "addr_postcode_first_country", "addr_c_o_line", "addr_floor_unit",
    "addr_multiline_country", "phone_x_ext", "phone_word_ext", "phone_dw_ext", "phone_dash_suffix", "two_addresses_sentence",
    "long_text_phone_address",
)
CONTROL_KINDS = ("country_prose", "measurement_x", "ext_inside_words", "city_prose_far")

# Invented names/places per language; real country words only where the rule vocabulary needs them.
GIVEN = {"en": "Tavrel", "de": "Mörda", "fr": "Quenir", "it": "Fiolo", "es": "Zabrín"}
SURNAME = {"en": "Brelquist", "de": "Hanzelmüll", "fr": "Vorquenet", "it": "Dalmorezzi", "es": "Quirbenda"}
CO_NAME = {"en": "Ilvor Nask", "de": "Ilvor Nask", "fr": "Ilvor Nask", "it": "Ilvor Nask", "es": "Ilvor Nask"}
CITY = {"en": "Quillenmoor", "de": "Zelvenau", "fr": "Moravaux", "it": "Tormavesco", "es": "Zorvaleda"}
STREET = {"en": "Orvane Street", "de": "Tilmerweg", "fr": "rue des Orvanes", "it": "via Talmori", "es": "calle Zorvena"}
PHONE_PREFIX = {"en": "+44 7", "de": "+49 30", "fr": "+33 6", "it": "+39 3", "es": "+34 6"}
CH = {"en": "Switzerland", "de": "Schweiz", "fr": "Suisse", "it": "Svizzera", "es": "Suiza"}
AT = {"en": "Austria", "de": "Österreich", "fr": "Autriche", "it": "Austria", "es": "Austria"}
DE = {"en": "Germany", "de": "Deutschland", "fr": "Allemagne", "it": "Germania", "es": "Alemania"}
FLOOR = {"en": "floor 3", "de": "3. Stock", "fr": "étage 2", "it": "piano 2", "es": "piso 4, puerta C"}
WORD_EXT = {"en": "extn 12", "de": "Apparat 12", "fr": "app. 12", "it": "int. 12", "es": "anexo 12"}
DW_EXT = {"en": "Ext 34", "de": "DW 34", "fr": "Poste 34", "it": "Int. 34", "es": "Ext. 34"}
SENTENCE = {
    "en": "The courier then redirected the parcel to a different site by road.",
    "de": "Der Kurier leitete das Paket anschließend auf dem Landweg an einen anderen Ort um.",
    "fr": "Le coursier a ensuite réacheminé le colis par la route vers un autre site.",
    "it": "Il corriere ha poi reindirizzato il pacco su strada verso un altro sito.",
    "es": "El mensajero redirigió después el paquete por carretera hacia otro lugar.",
}
CONTROL_TEXT = {
    "country_prose": {
        "en": "Our workshop ships optical samples to Switzerland, Germany and France, and customs forms are handled in bulk.",
        "de": "Unsere Werkstatt liefert optische Muster in die Schweiz, nach Deutschland und Frankreich; Zollformulare werden gesammelt bearbeitet.",
        "fr": "Notre atelier expédie des échantillons optiques en Suisse, en Allemagne et en France, et les formulaires douaniers sont traités en lot.",
        "it": "La nostra officina spedisce campioni ottici in Svizzera, in Germania e in Francia, e i moduli doganali sono gestiti in blocco.",
        "es": "Nuestro taller envía muestras ópticas a Suiza, Alemania y Francia, y los formularios de aduana se tramitan en bloque.",
    },
    "measurement_x": {
        "en": "The panel measures 2 x 3 m and the sample tray is 40 x 60 cm; the lid is 3x5 mm thick at the rim.",
        "de": "Die Platte misst 2 x 3 m und das Probenblech 40 x 60 cm; der Deckel ist am Rand 3x5 mm dick.",
        "fr": "Le panneau mesure 2 x 3 m et le plateau d'échantillons 40 x 60 cm ; le couvercle fait 3x5 mm au bord.",
        "it": "Il pannello misura 2 x 3 m e il vassoio dei campioni 40 x 60 cm; il coperchio è spesso 3x5 mm al bordo.",
        "es": "El panel mide 2 x 3 m y la bandeja de muestras 40 x 60 cm; la tapa tiene 3x5 mm de grosor en el borde.",
    },
    "ext_inside_words": {
        "en": "The extra context about the texture of the coating was extended in the external text, with no external contact.",
        "de": "Der extra Kontext zur Textur der Beschichtung wurde im externen Text erweitert, ganz ohne externen Kontakt.",
        "fr": "Le contexte supplémentaire sur la texture du revêtement a été étendu dans le texte externe, sans contact externe.",
        "it": "Il contesto extra sulla texture del rivestimento è stato esteso nel testo esterno, senza alcun contatto esterno.",
        "es": "El contexto extra sobre la textura del recubrimiento se amplió en el texto externo, sin contacto externo.",
    },
    "city_prose_far": {
        "en": "A rail line near Quillenmoor was closed for track repair, and the timetable for the whole region was revised.",
        "de": "Eine Bahnstrecke bei Zelvenau war wegen Gleisarbeiten gesperrt, und der Fahrplan der ganzen Region wurde überarbeitet.",
        "fr": "Une ligne ferroviaire près de Moravaux a été fermée pour des travaux de voie, et l'horaire de toute la région a été révisé.",
        "it": "Una linea ferroviaria vicino a Tormavesco è stata chiusa per lavori sui binari, e l'orario dell'intera regione è stato rivisto.",
        "es": "Una línea ferroviaria cerca de Zorvaleda fue cerrada por obras en la vía, y se revisó el horario de toda la región.",
    },
}


def street_line(lang, bld):
    return {"en": bld + " " + STREET[lang], "fr": bld + " " + STREET[lang]}.get(lang, STREET[lang] + " " + bld)


def phone_number(lang, k):
    tail = {"en": "{a} {b}", "de": "{a} {b}", "fr": "{a} {b}", "it": "{a} {b}", "es": "{a} {b}"}[lang]
    a, b = str(5120 + k * 7 + LANGS.index(lang)), str(310 + k * 13 + LANGS.index(lang))
    return PHONE_PREFIX[lang] + " " + tail.format(a=a[:2] + " " + a[2:], b=b[:1] + " " + b[1:])


def addr_ch_postcode(lang):
    return street_line(lang, str(14 + LANGS.index(lang))) + ", CH-" + str(8410 + LANGS.index(lang) * 3) + " " + CITY[lang]


def addr_ch_postcode_country(lang):
    return street_line(lang, str(21 + LANGS.index(lang)) + "a") + ", CH-" + str(8420 + LANGS.index(lang) * 3) + " " + CITY[lang] + ", " + CH[lang]


def addr_postcode_first_country(lang):
    return str(1720 + LANGS.index(lang) * 3) + " " + CITY[lang] + ", " + street_line(lang, str(7 + LANGS.index(lang))) + ", " + AT[lang]


def addr_c_o_line(lang):
    return "c/o " + CO_NAME[lang] + ", " + street_line(lang, str(33 + LANGS.index(lang))) + ", " + str(8530 + LANGS.index(lang) * 2) + " " + CITY[lang]


def addr_floor_unit(lang):
    return street_line(lang, str(52 + LANGS.index(lang))) + ", " + FLOOR[lang] + ", " + str(8610 + LANGS.index(lang)) + " " + CITY[lang]


def addr_multiline_country(lang):
    return street_line(lang, str(9 + LANGS.index(lang))) + "\n" + str(10711 + LANGS.index(lang) * 7) + " " + CITY[lang] + "\n" + DE[lang]


ADDRESS_BUILDERS = {
    "addr_ch_postcode": addr_ch_postcode, "addr_ch_postcode_country": addr_ch_postcode_country,
    "addr_postcode_first_country": addr_postcode_first_country, "addr_c_o_line": addr_c_o_line,
    "addr_floor_unit": addr_floor_unit, "addr_multiline_country": addr_multiline_country,
}


def head(lang, kind_cue_index, extra=None):
    c = CUES[lang]
    return [c[0], " - ", c[1], ": ", slot("PERSONNAME", GIVEN[lang] + " " + SURNAME[lang]), ". "]


def positive_parts(kind, lang):
    c = CUES[lang]
    parts = head(lang, 0)
    if kind in ADDRESS_BUILDERS:
        parts += [c[7], ": ", slot("ADDRESS", ADDRESS_BUILDERS[kind](lang)), "."]
        return parts
    base = phone_number(lang, POSITIVE_KINDS.index(kind))
    if kind == "phone_x_ext":
        value = base + " x" + str(100 + LANGS.index(lang) * 11 + 23)
    elif kind == "phone_word_ext":
        value = base + " " + WORD_EXT[lang]
    elif kind == "phone_dw_ext":
        value = base + " " + DW_EXT[lang]
    elif kind == "phone_dash_suffix":
        value = base + "-" + str(10 + LANGS.index(lang) * 2)
    elif kind == "two_addresses_sentence":
        first, second = addr_ch_postcode_country(lang), addr_postcode_first_country(lang)
        return parts + [c[7], ": ", slot("ADDRESS", first), ". ", SENTENCE[lang], " ", c[7], ": ", slot("ADDRESS", second), "."]
    elif kind == "long_text_phone_address":
        parts += [FILLER[lang] * 4, c[3], ": ", slot("TELEPHONENUM", base + " x" + str(400 + LANGS.index(lang))), ". ", FILLER[lang] * 6,
                  c[7], ": ", slot("ADDRESS", addr_ch_postcode_country(lang)), ". ", FILLER[lang]]
        return parts
    else:
        raise StressError("stress_v2_kind_invalid")
    return parts + [c[3], ": ", slot("TELEPHONENUM", value), "."]


def family_of(kind):
    if kind.startswith("phone"):
        return "phone"
    return {"long_text_phone_address": "long_text", "two_addresses_sentence": "full_address"}.get(kind, "full_address")


def generate():
    rows, skeletons = [], {}
    for kind in POSITIVE_KINDS:
        for lang in LANGS:
            case_id = ":".join((VERSION, kind, lang))
            text, gold, skeleton = assemble(positive_parts(kind, lang))
            rows.append({"case_id": case_id, "language": lang, "family": family_of(kind), "text": text, "gold": gold, "split": "dev"})
            skeletons[case_id] = skeleton
    for kind in CONTROL_KINDS:
        for lang in LANGS:
            case_id = ":".join((VERSION, "control_" + kind, lang))
            rows.append({"case_id": case_id, "language": lang, "family": "clean", "text": CONTROL_TEXT[kind][lang], "gold": [], "split": "dev"})
    validate(rows)
    return rows


def validate(rows):
    require(type(rows) is list and bool(rows), "stress_v2_rows_invalid")
    ids, texts = set(), set()
    for row in rows:
        require(type(row) is dict and set(row) == KEYS, "stress_v2_row_schema")
        require(row["language"] in LANGS and row["family"] in FAMILIES and row["split"] == "dev", "stress_v2_row_fields")
        require(0 < len(row["text"]) <= MAX_CHARS, "stress_v2_text_invalid")
        require(row["case_id"] not in ids and row["text"] not in texts, "stress_v2_duplicate")
        ids.add(row["case_id"])
        texts.add(row["text"])
        prev = 0
        for s in row["gold"]:
            require(set(s) == {"start", "end", "label"} and type(s["start"]) is int and type(s["end"]) is int, "stress_v2_span_schema")
            require(prev <= s["start"] < s["end"] <= len(row["text"]), "stress_v2_span_bounds")
            require(s["label"] in ("PERSONNAME", "ADDRESS", "TELEPHONENUM"), "stress_v2_span_label")
            prev = s["end"]
        require(bool(row["gold"]) == (row["family"] != "clean"), "stress_v2_clean_mismatch")


def manifest_of(rows, data):
    per_label, per_language, per_family = Counter(), Counter(), Counter()
    gold_chars = 0
    for row in rows:
        per_language[row["language"]] += 1
        per_family[row["family"]] += 1
        for s in row["gold"]:
            per_label[s["label"]] += 1
            gold_chars += s["end"] - s["start"]
    positives = sum(bool(r["gold"]) for r in rows)
    return {
        "version": VERSION, "schema": "masking-stress-six-field-v1", "split": "dev",
        "purpose": "bounded synthetic DEVELOPMENT validation of rule-based span refinement; never training or held-out final evaluation",
        "dataset": {"path": DATA.relative_to(ROOT).as_posix(), "sha256": sha(data), "bytes": len(data), "rows": len(rows)},
        "generator": {"path": "scripts/make_masking_stress_v2.py", "sha256": sha(Path(__file__).read_bytes()), "deterministic": True,
                      "randomness": False, "model_or_predictions_used": False},
        "counts": {"positive_rows": positives, "clean_rows": len(rows) - positives, "gold_spans": sum(per_label.values()),
                   "gold_original_characters": gold_chars, "per_language": dict(sorted(per_language.items())),
                   "per_family": dict(sorted(per_family.items())), "per_label": dict(sorted(per_label.items()))},
        "positive_formats": {k: len(LANGS) for k in POSITIVE_KINDS},
        "clean_control_formats": {k: len(LANGS) for k in CONTROL_KINDS},
        "format_notes": [
            "Formats not used in stress v1: CH-postcode lines, postcode-before-street, c/o lines, floor/Stock/etage units, x123/Apparat/DW extensions, '-12' DE phone suffix, multi-line addresses, two addresses split by a sentence.",
            "Gold ADDRESS spans cover the whole contiguous address including unit, c/o line, separators and country; gold TELEPHONENUM spans include the extension.",
            "Clean controls are near misses for the refinement rules (country prose, 'x' in measurements, 'ext' inside words, a city name in prose); no detector-based filtering.",
        ],
        "limitations": [
            "Invented street/city/person values may collide accidentally with real ones; country names are real by design (rule vocabulary).",
            "Rules were designed with v1 failure shapes in view; v2 formats were chosen from the rule vocabulary and general real-world conventions, not from model outputs on v2.",
            "Annotation is mechanical per inserted slot; unannotated personal information may exist. Development diagnostic only, no privacy guarantee.",
        ],
    }


def execute(verify):
    rows = generate()
    data = b"".join(canonical(r) for r in rows)
    manifest = manifest_of(rows, data)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if verify:
        require(DATA.is_file() and MANIFEST.is_file(), "stress_v2_artifact_missing")
        require(DATA.read_bytes() == data, "stress_v2_dataset_mismatch")
        require(MANIFEST.read_bytes() == manifest_bytes, "stress_v2_manifest_mismatch")
    else:
        require(not DATA.exists() and not MANIFEST.exists(), "stress_v2_refuses_overwrite")
        DATA.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_bytes(data)
        MANIFEST.write_bytes(manifest_bytes)
    print(json.dumps({"status": "VERIFIED" if verify else "GENERATED", "rows": len(rows), "positive_rows": manifest["counts"]["positive_rows"],
                      "clean_rows": manifest["counts"]["clean_rows"], "gold_spans": manifest["counts"]["gold_spans"],
                      "sha256": sha(data), "no_model_loaded": True}, sort_keys=True))


def main():
    if sys.argv[1:] not in ([], ["--verify"]):
        print("masking_stress_v2_invalid_arguments", file=sys.stderr)
        return 2
    try:
        execute(bool(sys.argv[1:]))
    except StressError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("masking_stress_v2_operation_failed_input_not_shown", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
