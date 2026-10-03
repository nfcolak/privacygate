#!/usr/bin/env python3
"""Frozen, deterministic DEVELOPMENT fixtures; stdlib only, no detection or model work.

Only aggregate counts/hashes reach stdout. The synthetic JSONL is ignored by Git.
Gold is assembled with labelled slots, never recovered by substring search.
"""
import ast
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/augmentation/masking-stress-dev.jsonl"
MANIFEST = ROOT / "artifacts/masking-stress/manifest.json"
VERSION = "masking-stress-v1"
LANGS = ("en", "de", "fr", "it", "es")
FAMILIES = (
    "names", "phone", "identity", "full_address", "username", "account",
    "personalref", "multiple_entities", "repeated_values", "long_text", "clean",
)
LABELS = frozenset((
    "PERSONNAME", "TELEPHONENUM", "IDCARDNUM", "PASSPORTNUM", "DRIVERLICENSENUM",
    "ADDRESS", "USERNAME", "ACCOUNTNUM", "PERSONALREF", "EMAIL",
))
KEYS = frozenset(("case_id", "language", "family", "text", "gold", "split"))
SPAN_KEYS = frozenset(("start", "end", "label"))
MAX_CHARS = 12000
VARIANTS = 2
SOURCE_GENERATORS = (
    "scripts/make_positives.py", "scripts/make_challenge.py",
    "scripts/make_negatives.py", "privacygate/negative_data.py",
)
# These are entirely impersonal linking phrases; personal values appear ONLY in slots.
CUES = {
    "en": ("Invented-person diagnostic record", "owner", "also recorded as", "telephone", "identity card", "passport", "driving licence", "complete home address", "personal username", "personal membership account", "person-linked delivery reference", "personal email", "repeated entry"),
    "de": ("Diagnoseeintrag für eine erfundene Person", "Inhaber", "auch eingetragen als", "Telefon", "Personalausweis", "Reisepass", "Führerschein", "vollständige Wohnanschrift", "persönlicher Benutzername", "persönliches Mitgliedskonto", "personenbezogene Lieferreferenz", "persönliche E-Mail", "wiederholter Eintrag"),
    "fr": ("Fiche diagnostique pour une personne inventée", "titulaire", "également inscrit comme", "téléphone", "carte d'identité", "passeport", "permis de conduire", "adresse personnelle complète", "nom d'utilisateur personnel", "compte personnel d'adhérent", "référence de livraison liée à la personne", "courriel personnel", "entrée répétée"),
    "it": ("Scheda diagnostica per una persona inventata", "titolare", "registrato anche come", "telefono", "carta d'identità", "passaporto", "patente di guida", "indirizzo di casa completo", "nome utente personale", "conto personale di adesione", "riferimento di consegna collegato alla persona", "email personale", "voce ripetuta"),
    "es": ("Ficha diagnóstica de una persona inventada", "titular", "también registrado como", "teléfono", "documento de identidad", "pasaporte", "permiso de conducir", "dirección personal completa", "nombre de usuario personal", "cuenta personal de socio", "referencia de entrega vinculada a la persona", "correo personal", "entrada repetida"),
}
# No people, narrative, addresses, identifiers, references or identifying combinations.
FILLER = {
    "en": "A prism separates light into a spectrum. A smooth surface reflects light. The description concerns only abstract geometric shapes and optical properties. ",
    "de": "Ein Prisma zerlegt Licht in ein Spektrum. Eine glatte Oberfläche reflektiert Licht. Die Beschreibung betrifft nur abstrakte geometrische Formen und optische Eigenschaften. ",
    "fr": "Un prisme sépare la lumière en un spectre. Une surface lisse réfléchit la lumière. La description concerne uniquement des formes géométriques abstraites et des propriétés optiques. ",
    "it": "Un prisma separa la luce in uno spettro. Una superficie liscia riflette la luce. La descrizione riguarda soltanto forme geometriche astratte e proprietà ottiche. ",
    "es": "Un prisma separa la luz en un espectro. Una superficie lisa refleja la luz. La descripción trata únicamente de formas geométricas abstractas y propiedades ópticas. ",
}
CLEAN_TAIL = {
    "en": "The prose describes material properties, not people or their possessions.",
    "de": "Der Text beschreibt Materialeigenschaften, keine Personen oder deren Besitz.",
    "fr": "Le texte décrit des propriétés matérielles, pas des personnes ou leurs biens.",
    "it": "Il testo descrive proprietà dei materiali, non persone o i loro beni.",
    "es": "El texto describe propiedades materiales, no personas ni sus posesiones.",
}
ADDRESS_WORDS = {
    "en": ("Qelvori Lane", "apartment", "Vezulon", "United Kingdom"),
    "de": ("Qelvoristraße", "Wohnung", "Vezulingen", "Deutschland"),
    "fr": ("rue de Qelvori", "appartement", "Vézulonne", "France"),
    "it": ("via Qelvori", "interno", "Vezulonia", "Italia"),
    "es": ("calle Qelvori", "apartamento", "Vezulonia", "España"),
}
EXTENSION = {"en": "ext.", "de": "Durchwahl", "fr": "poste", "it": "interno", "es": "extensión"}
# Character-placement targets, NOT verified tokenizer-window boundaries.
LONG_TARGETS = ((1000, 2200, 3900, 5800, 8100), (1250, 2550, 4250, 6150, 8350))


class StressError(Exception):
    """Fixed, value-free error code; never includes input or exception details."""


def require(ok, code):
    if not ok:
        raise StressError(code) from None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def iban_mod97(value):
    rearranged = value[4:] + value[:4]
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(digits) % 97


def values(language, variant):
    """Invented compositions only; neither uniqueness in reality nor unassignment is claimed."""
    li = LANGS.index(language)
    serial = 730000 + li * 100 + variant * 11
    # Accents and hyphens are deliberate. These names may collide accidentally.
    given = ("Zéq", "Vöq", "Qéz", "Zìq", "Qúz")[li] + ("aveli", "oranu")[variant]
    surname = ("Qelvorn", "Züvrel", "Véqorin", "Qelvarì", "Vezúqel")[li] + "-Xorvani"
    name = given + " " + surname
    other = given + "-Zeqali " + surname
    phone_digits = str(620000000 + li * 1000 + variant * 73)
    prefix = ("44", "49", "33", "39", "34")[li]
    if variant == 0:
        phone = "+" + prefix + " (" + phone_digits[:3] + ") " + phone_digits[3:6] + "-" + phone_digits[6:]
    else:
        phone = "00" + prefix + " " + phone_digits[:3] + "." + phone_digits[3:6] + "." + phone_digits[6:]
    phone += " " + EXTENSION[language] + " " + str(810 + li * 10 + variant)
    street, apartment, city, country = ADDRESS_WORDS[language]
    building, postal = str(860 + li * 10 + variant), str(87000 + li * 100 + variant)
    unit = str(71 + li * 2 + variant) + ("B", "C")[variant]
    # A single contiguous ADDRESS span contains street, building, unit, postcode,
    # locality, country AND the internal separators. Owner names remain outside it.
    address = (building + " " + street + ", " + apartment + " " + unit + "; " + postal + " " + city + ", " + country) if variant == 0 else (street + " " + building + " / " + apartment + " " + unit + "\n" + postal + " " + city + " — " + country)
    username = ("@zeqvori_", "zeqvori.")[variant] + language + str(serial)
    account = ("QX-" + str(serial) + "-" + str(61 + li)) if variant == 0 else (str(serial)[:3] + " " + str(serial)[3:] + "/" + str(61 + li))
    reference = "ZQ/" + str(serial) + "/" + language.upper()
    if variant == 1:
        # Intentionally invalid checksum does not negate explicit person linkage.
        digits = str(serial) + "831752046195"
        compact = "DE00" + digits
        if iban_mod97(compact) == 1:
            compact = "DE99" + digits
        require(iban_mod97(compact) != 1, "stress_checksum_invariant")
        reference = " ".join(compact[i:i + 4] for i in range(0, len(compact), 4))
    return {
        "name": name, "other_name": other, "phone": phone, "address": address,
        "idcard": "QZ-" + str(serial)[:3] + "/" + str(serial)[3:],
        "passport": "VQ " + str(serial) + "-R",
        "licence": "XQ/" + str(serial) + "/L",
        "username": username, "account": account, "reference": reference,
        "email": "zeqvori." + language + str(serial) + "@diagnostic.invalid",
    }


def slot(label, value):
    require(label in LABELS and type(value) is str and bool(value), "stress_slot_invalid")
    return (label, value)


def assemble(parts):
    """Offset accounting is incremental; repeated values get independent gold spans."""
    text_parts, gold, skeleton, cursor = [], [], [], 0
    counts = Counter()
    for part in parts:
        if type(part) is str:
            text_parts.append(part)
            skeleton.append(part)
            cursor += len(part)
        else:
            require(type(part) is tuple and len(part) == 2, "stress_part_invalid")
            label, value = part
            require(label in LABELS and type(value) is str and bool(value), "stress_slot_invalid")
            start = cursor
            text_parts.append(value)
            cursor += len(value)
            gold.append({"start": start, "end": cursor, "label": label})
            counts[label] += 1
            skeleton.append("{" + label + ":" + str(counts[label]) + "}")
    return "".join(text_parts), gold, "".join(skeleton)


def row_parts(language, family, variant):
    c, v = CUES[language], values(language, variant)
    if family == "clean":
        return [FILLER[language] * (variant + 1), CLEAN_TAIL[language]]
    opening, closing = ((" [", "]"), (" (", ")"))[variant]
    parts = [c[0], opening, c[1], ":", slot("PERSONNAME", v["name"]), closing]

    def add(cue, label, key, punct="; "):
        parts.extend([punct, cue, "=", slot(label, v[key])])

    if family == "names":
        add(c[2], "PERSONNAME", "other_name", ";(")
        parts.append(")")
        add(c[12], "PERSONNAME", "name", ";[")
        parts.append("]")
    elif family == "phone":
        add(c[3], "TELEPHONENUM", "phone")
    elif family == "identity":
        add(c[4], "IDCARDNUM", "idcard")
        add(c[5], "PASSPORTNUM", "passport")
        add(c[6], "DRIVERLICENSENUM", "licence")
    elif family == "full_address":
        add(c[7], "ADDRESS", "address")
    elif family == "username":
        add(c[8], "USERNAME", "username")
    elif family == "account":
        add(c[9], "ACCOUNTNUM", "account")
    elif family == "personalref":
        add(c[10], "PERSONALREF", "reference")
    elif family == "multiple_entities":
        # No whitespace is required between punctuation and adjacent personal slots.
        add(c[3], "TELEPHONENUM", "phone", ";(")
        parts.append(")")
        add(c[4], "IDCARDNUM", "idcard", ",[")
        parts.append("]")
        add(c[8], "USERNAME", "username", "/{")
        parts.append("}")
        add(c[7], "ADDRESS", "address", ";[")
        parts.append("]")
        add(c[11], "EMAIL", "email", ",(")
        parts.append(")")
        add(c[10], "PERSONALREF", "reference", ";{")
        parts.append("}")
    elif family == "repeated_values":
        add(c[12], "PERSONNAME", "name")
        for _ in range(2):
            add(c[8], "USERNAME", "username")
            add(c[3], "TELEPHONENUM", "phone")
        add(c[12], "PERSONNAME", "name")
    elif family == "long_text":
        # Five labelled placements plus the early owner. Character targets are
        # deliberately varied; no tokenizer is imported or boundary claim made.
        sequence = (
            (c[3], "TELEPHONENUM", "phone"),
            (c[7], "ADDRESS", "address"),
            (c[10], "PERSONALREF", "reference"),
            (c[8], "USERNAME", "username"),
            (c[12], "PERSONNAME", "name"),
        )
        length = sum(len(p) if type(p) is str else len(p[1]) for p in parts)
        for target, (cue, label, key) in zip(LONG_TARGETS[variant], sequence):
            while length < target:
                parts.append(" " + FILLER[language])
                length += 1 + len(FILLER[language])
            addition = ["; ", cue, "=", slot(label, v[key]), ". "]
            parts.extend(addition)
            length += sum(len(p) if type(p) is str else len(p[1]) for p in addition)
        parts.append(FILLER[language])
    else:
        raise StressError("stress_family_invalid")
    parts.append(".")
    return parts


def validate(rows: Any):
    require(type(rows) is list and bool(rows), "stress_rows_invalid")
    ids, texts = set(), set()
    coverage = Counter()
    positive = clean = 0
    for raw_row in rows:
        require(type(raw_row) is dict and set(raw_row) == KEYS, "stress_row_schema")
        row = cast(dict[str, Any], raw_row)
        require(type(row["case_id"]) is str and bool(row["case_id"]), "stress_id_invalid")
        require(type(row["language"]) is str and row["language"] in LANGS, "stress_language_invalid")
        require(type(row["family"]) is str and row["family"] in FAMILIES, "stress_family_invalid")
        require(type(row["split"]) is str and row["split"] == "dev", "stress_split_invalid")
        require(type(row["text"]) is str and 0 < len(row["text"]) <= MAX_CHARS, "stress_text_invalid")
        require(type(row["gold"]) is list, "stress_gold_invalid")
        require(row["case_id"] not in ids, "stress_duplicate_id")
        require(row["text"] not in texts, "stress_duplicate_text")
        ids.add(row["case_id"])
        texts.add(row["text"])
        previous_end = 0
        for raw_span in row["gold"]:
            require(type(raw_span) is dict and set(raw_span) == SPAN_KEYS, "stress_span_schema")
            span = cast(dict[str, Any], raw_span)
            require(type(span["start"]) is int and type(span["end"]) is int, "stress_offset_type")
            require(0 <= span["start"] < span["end"] <= len(row["text"]), "stress_offset_bounds")
            require(span["start"] >= previous_end, "stress_overlap_or_order")
            require(type(span["label"]) is str and span["label"] in LABELS, "stress_label_invalid")
            previous_end = span["end"]
        require(bool(row["gold"]) == (row["family"] != "clean"), "stress_clean_positive_mismatch")
        # Full address is one contiguous diagnostic region, never component spans.
        if row["family"] == "full_address":
            require(Counter(s["label"] for s in row["gold"]) == {"PERSONNAME": 1, "ADDRESS": 1}, "stress_address_shape")
        coverage[row["family"], row["language"]] += 1
        positive += bool(row["gold"])
        clean += not bool(row["gold"])
    require(positive > 0 and clean > 0, "stress_positive_clean_required")
    require(coverage == Counter({(f, l): VARIANTS for f in FAMILIES for l in LANGS}), "stress_coverage_incomplete")


def generate():
    rows, templates = [], {}
    for family in FAMILIES:
        for language in LANGS:
            for variant in range(VARIANTS):
                case_id = ":".join((VERSION, family, language, str(variant)))
                text, gold, skeleton = assemble(row_parts(language, family, variant))
                rows.append({"case_id": case_id, "language": language, "family": family, "text": text, "gold": gold, "split": "dev"})
                templates[case_id] = skeleton
    validate(rows)
    require(len(set(templates.values())) == len(templates), "stress_duplicate_template")
    return rows, templates


def source_disjointness(templates, rows):
    """Read generator source only, via AST; no corpus/frozen data or imports.

    Compare exact skeletons and rendered texts to all string literals (a superset
    of static templates). Check IDs against literals and the positive generator's
    actual formatted template IDs. This is lexical evidence, not semantic independence.
    """
    literals, template_ids, bindings = set(), set(), {}
    for relative in SOURCE_GENERATORS:
        data = (ROOT / relative).read_bytes()
        tree = ast.parse(data)
        bindings[relative] = {"sha256": sha(data)}
        strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and type(n.value) is str}
        literals.update(strings)
        bindings[relative]["string_literal_count"] = len(strings)
        if relative == "scripts/make_positives.py":
            t = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(a, ast.Name) and a.id == "T" for a in n.targets))
            table = ast.literal_eval(t)
            tid_assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(a, ast.Name) and a.id == "tid" for a in n.targets))
            call = tid_assignment.value
            require(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "format" and isinstance(call.func.value, ast.Constant), "stress_source_id_shape")
            pattern = call.func.value.value
            # Read the exact source-defined split suffix instead of assuming one.
            require(len(call.args) == 4 and isinstance(call.args[2], ast.IfExp), "stress_source_id_shape")
            suffixes = (ast.literal_eval(call.args[2].body), ast.literal_eval(call.args[2].orelse))
            for family, langs in table.items():
                for language, pools in langs.items():
                    for suffix, pool in zip(suffixes, pools):
                        template_ids.update(pattern.format(family, language, suffix, i) for i in range(len(pool)))
    require(not set(templates.values()) & literals, "stress_existing_template_collision")
    require(not {row["text"] for row in rows} & literals, "stress_existing_text_collision")
    require(not set(templates) & (literals | template_ids), "stress_existing_id_collision")
    require(all(VERSION not in literal for literal in literals), "stress_existing_prefix_collision")
    return {
        "exact_skeleton_vs_source_string_literals_disjoint": True,
        "rendered_texts_vs_source_string_literals_disjoint": True,
        "ids_vs_literals_and_positive_template_ids_disjoint": True,
        "new_id_prefix_absent_from_existing_source_literals": True,
        "positive_template_ids_checked": len(template_ids),
        "source_bindings": bindings,
        "existing_generated_texts_compared": False,
        "held_out_files_read": False,
        "semantic_or_translation_independence_proven": False,
        "scope": "exact source-literal/skeleton and source-reconstructed positive-template ID checks only",
    }


def sanity_assertions(rows):
    """One compact assembler/schema sanity group; no scoring framework."""
    text, gold, _ = assemble(["é", slot("PERSONNAME", "Ω-ë"), "!", slot("PERSONNAME", "Ω-ë")])
    require(len(text) == 8 and [(s["start"], s["end"]) for s in gold] == [(1, 4), (5, 8)], "stress_unicode_assembly")
    mutations = (
        ("extra_key", lambda r: r.update(extra=True)),
        ("bool_offset", lambda r: r["gold"][0].update(start=True)),
        ("end_bounds", lambda r: r["gold"][0].update(end=len(r["text"]) + 1)),
        ("empty_span", lambda r: r["gold"][0].update(end=r["gold"][0]["start"])),
        ("overlap", lambda r: r["gold"].insert(1, dict(r["gold"][0]))),
        ("bad_split", lambda r: r.update(split="train")),
        ("bad_language", lambda r: r.update(language="xx")),
        ("nested_key", lambda r: r["gold"][0].update(extra=True)),
    )
    for _, mutate in mutations:
        bad = copy.deepcopy(rows)
        mutate(bad[0])
        try:
            validate(bad)
        except StressError:
            pass
        else:
            raise StressError("stress_rejection_sanity_failed")
    return {"unicode_slot_offset_check": "passed", "invalid_structure_rejections": len(mutations)}


def manifest_of(rows, templates, data):
    matrix = {f: {l: {"rows": 0, "positive_rows": 0, "clean_rows": 0, "gold_spans": 0, "per_label": {}} for l in LANGS} for f in FAMILIES}
    per_label, per_language, per_family = Counter(), Counter(), Counter()
    gold_chars = gold_alnum = gold_spans = invalid_references = 0
    long_lengths, long_positions = [], []
    for row in rows:
        cell = matrix[row["family"]][row["language"]]
        cell["rows"] += 1
        cell["positive_rows"] += bool(row["gold"])
        cell["clean_rows"] += not bool(row["gold"])
        labels = Counter(s["label"] for s in row["gold"])
        cell["gold_spans"] += len(row["gold"])
        for label, count in labels.items():
            cell["per_label"][label] = cell["per_label"].get(label, 0) + count
        per_label.update(labels)
        per_language[row["language"]] += 1
        per_family[row["family"]] += 1
        gold_spans += len(row["gold"])
        for s in row["gold"]:
            gold_chars += s["end"] - s["start"]
            value = row["text"][s["start"]:s["end"]]
            gold_alnum += sum(c.isalnum() for c in value)
            if s["label"] == "PERSONALREF" and value.replace(" ", "").startswith("DE"):
                require(iban_mod97(value.replace(" ", "")) != 1, "stress_checksum_invariant")
                invalid_references += 1
        if row["family"] == "long_text":
            long_lengths.append(len(row["text"]))
            long_positions.extend(s["start"] for s in row["gold"][1:])
    positive_rows = sum(bool(r["gold"]) for r in rows)
    return {
        "version": VERSION, "schema": "masking-stress-six-field-v1", "split": "dev",
        "purpose": "bounded synthetic DEVELOPMENT literal-masking diagnostic; never training or held-out final evaluation",
        "dataset": {"path": DATA.relative_to(ROOT).as_posix(), "sha256": sha(data), "bytes": len(data), "rows": len(rows)},
        "generator": {"path": "scripts/make_masking_stress.py", "sha256": sha(Path(__file__).read_bytes()), "deterministic": True, "randomness": False, "model_or_predictions_used": False},
        "template_rules": {"templates": len(templates), "template_set_sha256": sha(canonical(templates)), "variants_per_family_language": VARIANTS, "frozen_before_predictions": True, "case_selection_uses_predictions": False},
        "counts": {"positive_rows": positive_rows, "clean_rows": len(rows) - positive_rows, "gold_spans": gold_spans, "gold_original_characters": gold_chars, "gold_unicode_alphanumeric_characters": gold_alnum, "per_language": dict(sorted(per_language.items())), "per_family": dict(sorted(per_family.items())), "per_label": dict(sorted(per_label.items())), "checksum_invalid_personal_reference_occurrences": invalid_references},
        "family_language_label_matrix": matrix,
        "long_text": {"rows": len(long_lengths), "insertions_after_owner_per_row": len(LONG_TARGETS[0]), "min_characters": min(long_lengths), "max_characters": max(long_lengths), "max_allowed_characters": MAX_CHARS, "post_owner_slot_start_min": min(long_positions), "post_owner_slot_start_max": max(long_positions), "character_targets": LONG_TARGETS, "actual_tokenizer_window_boundary_verification": "pending; no tokenizer or model loaded", "sliding_window_boundary_crossings_proven": False},
        "validation": {"exact_schema": True, "allowed_languages_and_dev_only": True, "bool_offsets_rejected": True, "in_bounds_sorted_nonoverlapping_gold": True, "unique_ids_and_exact_texts": True, "every_family_language_covered": True, "positive_and_clean_rows_present": True, "all_declared_personal_slots_annotated_during_concatenation": True, "whole_address_one_contiguous_span": True, "sanity_assertions": sanity_assertions(rows)},
        "source_disjointness": source_disjointness(templates, rows),
        "limitations": [
            "Invented names, codes, addresses and phone numbers can accidentally collide with real values; no number is verified unassigned.",
            "Country names are public; synthetic street/locality spellings and national-looking formats are artificial and not authority-validated.",
            "Clean prose is deliberately impersonal geometry/optics, not ambiguous generic identifier codes; no detector-based filtering occurs.",
            "Diagnostic PERSONNAME and ADDRESS labels need not exist in a checkpoint; unsupported labels do not make examples negative.",
            "Every inserted slot is annotated mechanically; automated offset validation does not prove complete semantic annotation of all possible personal information.",
            "Whitespace/punctuation inside whole addresses, names, phones and formatted codes are gold characters; separators left visible can fail complete-span coverage despite full alphanumeric coverage.",
            "All-character and Unicode-alphanumeric masking must be reported separately by the integrator; neither proves privacy on real data.",
            "No substring-disappearance argument, masking metric, model scoring, threshold tuning, training, held-out inspection or production/privacy guarantee is provided.",
        ],
    }


def execute(verify):
    rows, templates = generate()
    data = b"".join(canonical(row) for row in rows)
    manifest = manifest_of(rows, templates, data)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if verify:
        require(DATA.is_file() and MANIFEST.is_file() and not DATA.is_symlink() and not MANIFEST.is_symlink(), "stress_artifact_missing_or_symlink")
        actual = DATA.read_bytes()
        require(actual == data and sha(actual) == manifest["dataset"]["sha256"], "stress_dataset_bytes_mismatch")
        try:
            loaded = [json.loads(line) for line in actual.decode("utf-8").splitlines()]
        except Exception:
            raise StressError("stress_dataset_parse_error") from None
        validate(loaded)
        require(MANIFEST.read_bytes() == manifest_bytes, "stress_manifest_mismatch")
    else:
        # No overwrites: once materialized, verification is the only admitted action.
        require(not DATA.exists() and not MANIFEST.exists(), "stress_refuses_overwrite")
        DATA.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with DATA.open("xb") as handle:
            handle.write(data)
        with MANIFEST.open("xb") as handle:
            handle.write(manifest_bytes)
    print(json.dumps({"status": "VERIFIED" if verify else "GENERATED", "rows": len(rows), "positive_rows": manifest["counts"]["positive_rows"], "clean_rows": manifest["counts"]["clean_rows"], "gold_spans": manifest["counts"]["gold_spans"], "sha256": sha(data), "boundary_verification": "pending", "no_model_loaded": True}, sort_keys=True))


def main():
    if sys.argv[1:] not in ([], ["--verify"]):
        print("masking_stress_invalid_arguments", file=sys.stderr)
        return 2
    try:
        execute(bool(sys.argv[1:]))
    except StressError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("masking_stress_operation_failed_input_not_shown", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
