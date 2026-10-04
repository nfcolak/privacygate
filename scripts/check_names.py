#!/usr/bin/env python3
"""Small invented-only, model-free proof of the names candidate contract.

No dataset is read. No surfaces, row identifiers, offsets, or exception payloads
are printed. Completeness requires exact whole-name boundaries, including titles,
initial periods, particles and internal punctuation; incidental excess additions
also fail the check. Seeded checks exercise boundary repair, not learned recall.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from privacygate.names import assemble, propagate


_FIELDS = {"start", "end", "label", "source", "score", "validation", "context", "protected", "stage"}


def seed(text, surface, label="SURNAME", *, stage="raw", context="unknown"):
    a = text.index(surface)
    return {"start": a, "end": a + len(surface), "label": label, "source": "invented",
            "score": 0.9, "validation": "n/a", "context": context, "protected": False, "stage": stage}


def expected(text, surfaces):
    # Fixtures are fully invented and held in memory only.
    spans = {(m.start(), m.end()) for surface in surfaces for m in re.finditer(re.escape(surface), text)}
    return [span for span in sorted(spans) if not any(a <= span[0] < span[1] <= b
            and (a, b) != span for a, b in spans)]


def contract(text, outputs, stage):
    for cand in outputs:
        if (set(cand) != _FIELDS or type(cand["start"]) is not int or type(cand["end"]) is not int
                or not 0 <= cand["start"] < cand["end"] <= len(text)
                or cand["label"] != "PERSONNAME" or cand["source"] != "names"
                or cand["stage"] != stage or cand["score"] is not None
                or cand["validation"] != "n/a" or cand["protected"] is not False
                or cand["context"] not in {"personal", "unknown"}):
            raise AssertionError("name candidate contract failed")
    if len({(c["start"], c["end"]) for c in outputs}) != len(outputs):
        raise AssertionError("name candidate deduplication failed")


def run_names(text, inputs, mode):
    saved = deepcopy(inputs)
    added = [] if mode == "propagate" else assemble(text, inputs)
    contract(text, added, "assembled")
    repeated = propagate(text, inputs + added) if mode in {"full", "propagate"} else []
    contract(text, repeated, "propagated")
    if inputs != saved:
        raise AssertionError("name inputs were modified")
    if mode != "propagate" and added != assemble(text, inputs):
        raise AssertionError("name assembly is nondeterministic")
    if repeated != (propagate(text, inputs + added) if mode in {"full", "propagate"} else []):
        raise AssertionError("name propagation is nondeterministic")
    return added + repeated


def fixtures():
    positives, negatives = [], []

    def pos(family, text, value, specs=(), mode="assemble"):
        values = [value] if isinstance(value, str) else value
        inputs = [seed(text, *spec) for spec in specs]
        positives.append((family, text, inputs, expected(text, values), mode))

    def neg(text, specs=()):
        negatives.append((text, [seed(text, *spec) for spec in specs]))

    # Every language includes explicit person context, salutation exclusion,
    # dotted initials, reverse order and an OOV double-surname-shaped core.
    language_scopes = (
        ("en", "my name is", "Dear", "Name:", "Mr."),
        ("de", "ich heiße", "Sehr geehrte", "Name:", "Frau"),
        ("fr", "je m'appelle", "Bonjour", "Nom:", "Mme"),
        ("it", "mi chiamo", "Gentile", "Nome:", "Sig.ra"),
        ("es", "me llamo", "Estimado", "Nombre:", "Sr."),
    )
    for language, intro, greeting, field, title in language_scopes:
        pos("languages", f"{intro} Neris Velkor.", "Neris Velkor")
        pos("languages", f"{greeting} {title} Neris Velkor, welcome.", f"{title} Neris Velkor")
        pos("languages", f"{field} Neris Velkor.", "Neris Velkor", (("Velkor", "SURNAME"),))
        pos("languages", f"{field} J. R. R. Velkor.", "J. R. R. Velkor", (("Velkor", "SURNAME"),))
        pos("languages", f"{field} Velkor, Neris.", "Velkor, Neris", (("Velkor", "SURNAME"),))
        pos("languages", f"{field} Neris Velkor Tavren.", "Neris Velkor Tavren", (("Velkor", "SURNAME"),))
        pos("languages", f"{intro} Neris Avelin Velkor Tavren.", "Neris Avelin Velkor Tavren")

    for title in (
        "Dr.", "Prof.", "Dipl.-Ing.", "Herr", "Frau", "Mr", "Mrs", "Ms", "Mme", "M.",
        "Mlle", "Sig.", "Sig.ra", "Dott.", "Sr.", "Sra.", "Dña.", "Don", "Doña",
        "Mme.", "Mrs.", "Mr.", "Ms.", "Dott.ssa", "Sig.na",
    ):
        pos("titles", f"{title} Neris Velkor arrived.", f"{title} Neris Velkor")

    for particle in (
        "van", "van der", "von", "von der", "de", "de la", "del", "della", "di", "da",
        "dos", "du", "le", "la", "ten", "ter", "zu", "van den", "de los", "de las", "des",
    ):
        pos("particles", f"Name: Neris {particle} Velkor.", f"Neris {particle} Velkor", (("Velkor", "SURNAME"),))

    specials = (
        ("Name: Herr Dr. Prof. Neris Velkor.", "Herr Dr. Prof. Neris Velkor", (("Neris", "GIVENNAME"),)),
        ("Signed: Prof. J.-P. Velkor.", "Prof. J.-P. Velkor", (("Velkor", "SURNAME"),)),
        ("gez. Dipl.-Ing. J.R.R. Velkor.", "Dipl.-Ing. J.R.R. Velkor", (("Velkor", "SURNAME"),)),
        ("Firma Neris Velkor.", "Neris Velkor", ()),
        ("Name: Neris-Luvan Velkor-Tavren.", "Neris-Luvan Velkor-Tavren", (("Luvan", "GIVENNAME"),)),
        ("Nom: Neris O'Velkor.", "Neris O'Velkor", (("Velkor", "SURNAME"),)),
        ("Nom: Neris O’Velkor.", "Neris O’Velkor", (("Velkor", "SURNAME"),)),
        ("Nome: Neris d’Avrel.", "Neris d’Avrel", (("Avrel", "SURNAME"),)),
        ("Nome: Neris dell'Avrel.", "Neris dell'Avrel", (("Avrel", "SURNAME"),)),
        ("Nombre: Velkor Tavren, Neris.", "Velkor Tavren, Neris", (("Velkor", "SURNAME"), ("Tavren", "SURNAME"))),
        ("Name: Velkor, Neris J.", "Velkor, Neris J.", (("Velkor", "SURNAME"),)),
        ("Velkor, Neris arrived.", "Velkor, Neris", (("Velkor", "SURNAME"),)),
        ("Dear Neris Velkor, thank you.", "Neris Velkor", (("Neris", "GIVENNAME"),)),
        ("Liebe Frau Neris Velkor, danke.", "Frau Neris Velkor", ()),
        ("Bonjour M. Neris Velkor, merci.", "M. Neris Velkor", ()),
        ("Gentile Dott. Neris Velkor, grazie.", "Dott. Neris Velkor", ()),
        ("Estimada Sra. Neris Velkor, gracias.", "Sra. Neris Velkor", ()),
        ("Name: Nérys Vélkor.", "Nérys Vélkor", (("Vélkor", "SURNAME"),)),
        ("Nom: Ne\u0301rys Ve\u0301lkor.", "Ne\u0301rys Ve\u0301lkor", (("Ve\u0301lkor", "SURNAME"),)),
        ("Nome: NERIS VAN DER VELKOR.", "NERIS VAN DER VELKOR", (("VELKOR", "SURNAME"),)),
        ("Name: Neris\u00a0Velkor.", "Neris\u00a0Velkor", (("Velkor", "SURNAME"),)),
        ("Name: Neris\tVelkor.", "Neris\tVelkor", (("Velkor", "SURNAME"),)),
        ("Name: Neris\nVelkor\nmanager", "Neris\nVelkor", (("Neris", "GIVENNAME"),)),
        ("Name: Neris‐Luvan Velkor‑Tavren.", "Neris‐Luvan Velkor‑Tavren", (("Luvan", "GIVENNAME"),)),
        ("Neris Velkor. Tomorrow we leave.", "Neris Velkor", (("Neris", "GIVENNAME"),)),
        ("Name: Neris Velkor; note follows.", "Neris Velkor", (("Velkor", "SURNAME"),)),
        ("Name: Neris Velkor! Goodbye.", "Neris Velkor", (("Velkor", "SURNAME"),)),
        ("Name: Neris Velkor 42 is a reference.", "Neris Velkor", (("Velkor", "SURNAME"),)),
        ("Dear Neris Velkor\nSupport department", "Neris Velkor", (("Velkor", "SURNAME"),)),
        ("Dear Neris Velkor, Torin Avrel.", "Neris Velkor", (("Neris", "GIVENNAME"),)),
        ("Mira Velnor arrived.", "Mira Velnor", (("Mira", "GIVENNAME"), ("Velnor", "MIDDLENAME"))),
        ("Dr. Neris Velkor arrived.", "Dr. Neris Velkor", (("Dr.", "TITLE"),)),
    )
    for text, value, specs in specials:
        pos("boundaries", text, value, specs)

    for _, intro, _, _, title in language_scopes:
        text = (f"{title} Neris Velkor arrived. " + "This paragraph contains ordinary invented prose. " * 100
                + "Neris Velkor returned. " + "A second paragraph is deliberately uneventful. " * 100
                + f"{title} Velkor replied. Neris Velkor left.")
        pos("propagation", text, [f"{title} Neris Velkor", "Neris Velkor", f"{title} Velkor"],
            ((f"{title} Neris Velkor", "PERSONNAME"),), "propagate")

    pos("propagation", "Neris Velkor left. Name: Neris Velkor. Herr Velkor returned.",
        ["Neris Velkor", "Herr Velkor"], (("Neris Velkor", "PERSONNAME"),), "propagate")
    pos("propagation", "Name: Neris van der Velkor. Mme van der Velkor arrived. Neris van der Velkor left.",
        ["Neris van der Velkor", "Mme van der Velkor"], (("Neris van der Velkor", "PERSONNAME"),), "propagate")
    pos("propagation", "Name: Velkor, Neris. Velkor, Neris left. Herr Velkor replied.",
        ["Velkor, Neris", "Herr Velkor"], (("Velkor, Neris", "PERSONNAME"),), "propagate")
    pos("propagation", "Name: Neris Velkor Tavren. Sr. Velkor Tavren arrived.",
        ["Neris Velkor Tavren", "Sr. Velkor Tavren"],
        (("Neris Velkor Tavren", "PERSONNAME"), ("Velkor Tavren", "SURNAME")), "propagate")
    pos("propagation", "Name: Neris Velkor. Neris Velkor left. Mme Velkor returned.",
        ["Neris Velkor", "Mme Velkor"], (("Velkor", "SURNAME"),), "full")

    # Brands/eponyms, streets and products: deliberately supply component false
    # seeds too, so zero NEW name masks is not merely lack of model evidence.
    for prefix in ("brand", "product", "model", "marque", "produit", "modèle", "Marke", "Produkt", "Modell",
                   "marca", "prodotto", "modello", "producto", "modelo", "company", "department"):
        neg(f"The {prefix} Neris Velkor is available.", (("Velkor", "SURNAME"),))
    for prefix in ("street", "rue", "via", "calle", "Straße", "avenida", "piazza", "museum", "university", "park"):
        neg(f"The {prefix} Neris Velkor is public.", (("Velkor", "SURNAME"),))
    for suffix in ("Street", "Road", "GmbH", "Inc.", "Ltd.", "Systems", "Museum", "Hotel"):
        neg(f"Neris Velkor {suffix} is open.", (("Neris", "GIVENNAME"),))
    for text in (
        "Dear Customer, welcome.", "Sehr geehrte Kunden, willkommen.", "Bonjour Service Client.",
        "Gentile Cliente, grazie.", "Estimado Cliente, gracias.", "signed Sales Manager",
        "Dr. software is a product.", "Prof. 42 is a room code.", "Mme service est disponible.",
        "Sig.ra prodotto disponibile.", "Sr. modelo disponible.", "my name is inventory management.",
        "je m'appelle service client.", "mi chiamo servizio clienti.", "me llamo soporte técnico.",
        "ich heiße technische abteilung.", "The Clear Amber option is enabled.",
        "Neris Velkor is a product heading without personal context.", "Dr.", "Herr", "Ms.",
        "Dear Sir or Madam", "Name: Velkor Systems.", "product Dr. Neris Velkor is on sale.",
        "rue Dr. Neris Velkor is a public place.", "my name is @NerisVelkor.",
        "Nom: neris.velkor@example.invalid.", "Name: Velkor42.", "Name: 42Velkor.",
    ):
        neg(text)
    return positives, negatives


def mechanics():
    """Boundary/alias safety properties, without exposing fixture identifiers."""
    text = "Neris Velkor left. Name: Neris Velkor. Neris Velkor returned."
    initial = seed(text, "Neris Velkor", "PERSONNAME")
    second = list(re.finditer(re.escape("Neris Velkor"), text))[1]
    initial.update(start=second.start(), end=second.end())
    repeated = propagate(text, [initial])
    if len(repeated) != 2 or not any(c["end"] < initial["start"] for c in repeated):
        raise AssertionError("earlier or later exact mention was missed")

    text = "Name: Neris Velkor. Name: Torin Velkor. Herr Velkor arrived. Neris Velkor left."
    inputs = [seed(text, "Neris Velkor", "PERSONNAME"), seed(text, "Torin Velkor", "PERSONNAME")]
    new = propagate(text, inputs)
    ambiguous = expected(text, ["Herr Velkor"])
    if any((c["start"], c["end"]) in ambiguous for c in new):
        raise AssertionError("ambiguous surname was propagated")

    text = "Name: Neris Velkor. brand Neris Velkor is available. Neris Velkor Street is public. @NerisVelkor"
    inputs = [seed(text, "Neris Velkor", "PERSONNAME")]
    if propagate(text, inputs):
        raise AssertionError("nonpersonal alias was propagated")

    text = "Name: Neris Velkor. Velkor was a code. Velkor@example.invalid is a mailbox. @Velkor is a handle."
    if propagate(text, [seed(text, "Neris Velkor", "PERSONNAME")]):
        raise AssertionError("bare surname or contact was propagated")

    text = "May is a calendar word. May may vary."
    if propagate(text, [seed(text, "May", "PERSONNAME")]):
        raise AssertionError("single common word was propagated")

    text = "Dr. Velkor replied. Velkor replied. Herr Velkor replied."
    initial = seed(text, "Dr. Velkor", "PERSONNAME")
    results = propagate(text, [initial])
    if {(c["start"], c["end"]) for c in results} != set(expected(text, ["Herr Velkor"])):
        raise AssertionError("title-only alias rule failed")
    if propagate("Neris Velkor", []):
        raise AssertionError("cross-document name state escaped")
    if propagate(text, [dict(initial, stage="propagated")]):
        raise AssertionError("recursive propagation occurred")

    text = "Neris Velkor\nTorin Avrel"
    inputs = [seed(text, "Neris", "GIVENNAME"), seed(text, "Torin", "GIVENNAME")]
    outputs = assemble(text, inputs)
    if any("\n" in text[c["start"]:c["end"]] for c in outputs):
        raise AssertionError("separate person lines were joined")

    text = "Name: Neris Velkor; email: Neris Velkor@example.invalid"
    contact = seed(text, "Neris Velkor@example.invalid", "EMAIL")
    contact["protected"] = True
    outputs = assemble(text, [seed(text, "Neris", "GIVENNAME"), contact])
    if any(c["start"] < contact["end"] and contact["start"] < c["end"] for c in outputs):
        raise AssertionError("protected value boundary crossed")

    for bad in ([{"start": -1, "end": 2, "label": "PERSONNAME"}],
                [{"start": True, "end": 2, "label": "PERSONNAME"}],
                [{"start": 0, "end": 999, "label": "PERSONNAME"}], [None]):
        for function in (assemble, propagate):
            try:
                function("invented", bad)
            except ValueError as error:
                if str(error) != "invalid name candidates":
                    raise AssertionError("name error is not value-free") from None
            else:
                raise AssertionError("invalid name candidates admitted")


def round3_cases():
    """Fresh recipient typography plus narrow ADDRESS arbitration, all invented."""
    cues = ("Recipient", "Empfänger", "Destinataire", "Destinatario", "Contact person",
            "Privatkontakt:", "Contatto privato:", "Contacto privado:")
    positives = []
    for cue in cues:
        for value in ("N. Q. Zévran", "N.\nQ. Zévran", "Néra\nZévran",
                      "Zévran,\nNéra", "Dr.Zévran-Ruv Néra"):
            positives.append((cue + " " + value + "; note follows.", value, []))
    for title in ("Dr.", "Dott.", "Sig.ra", "Sr.", "Sra.", "Prof."):
        value = title + "Zévran"
        positives.append((value + " arrived.", value, []))
    for cue in cues:
        value = "N. Q. Zévran"
        text = "12 Qévnar Lane, VQ8 2ZX Vezford; " + cue + " " + value + "; email: q@invented.invalid"
        broad = seed(text, text[:-len("; email: q@invented.invalid")], "ADDRESS")
        positives.append((text, value, [broad]))
    for box in ("Postfach 82", "PO Box 826", "Casella postale 826"):
        value = "Néra Zévran"
        text = "Recipient: " + value + ", " + box + ", 73162 Vezara"
        positives.append((text, value, [seed(text, text, "ADDRESS")]))
    for value in ("Dr.\nZévran van Ruvorn", "Dott.\r\nNéra Zévran", "Zévran,\r\nNéra"):
        text = "Destinatario: " + value + "\nEmail: q@invented.invalid"
        positives.append((text, value, []))
    clean = (
        "brand Dr.Zévran is available.", "Product: Recipient Dr.Zévran is a model.",
        "street Dr.Zévran is public.", "rue Dott.Zévran is public.",
        "marca Sig.raZévran is on sale.", "department Sr.Zévran is a heading.",
        "Recipient Sales Manager", "Empfänger Support Department", "Destinataire Service Client",
        "Destinatario Ufficio", "Contact person Routing Desk", "Privatkontakt: Abteilung",
        "Contatto privato: Dipartimento", "Contacto privado: Departamento",
        "Recipient 73145 Vezford", "Empfänger VQ8 2ZX", "Destinataire: 75001, Vézford",
        "Destinatario: Zévran Street", "Contact person: Zévran Systems",
        "Privatkontakt:\n\nNéra Zévran", "Routing: send to recipient address only.",
        "Dr.zévran is a product token.", "Xyz.Zévran is an abbreviation.",
    )
    complete = excess = 0
    for text, value, inputs in positives:
        outputs = run_names(text, inputs, "assemble")
        gold = expected(text, [value])
        exact = {(c["start"], c["end"]) for c in outputs}
        complete += all(span in exact for span in gold)
        excess += any(not any(a <= c["start"] < c["end"] <= b for a, b in gold) for c in outputs)
    masked = sum(bool(run_names(text, [], "full")) for text in clean)
    # ADDRESS is never ignored in an uncued, untitled name; a lexical street
    # remains a barrier even when the model's ADDRESS encompasses the whole field.
    text = "Néra Zévran"
    safety = not assemble(text, [seed(text, text, "ADDRESS"), seed(text, "Zévran", "SURNAME")])
    text = "Recipient: Dr.Zévran Road 12, VQ8 2ZX Vezford"
    safety &= not assemble(text, [seed(text, text, "ADDRESS")])
    for gap in ("\n\n", "\r\n \r\n"):
        text = "Recipient: Néra" + gap + "Zévran"
        safety &= all(gap not in text[c["start"]:c["end"]] for c in assemble(text, []))
    text = "Recipient: Néra\nZévran\nRuvorn"
    safety &= all(text[c["start"]:c["end"]].count("\n") <= 1 for c in assemble(text, []))
    print(f"round3_name_complete={complete}/{len(positives)}")
    print(f"round3_name_clean_masked={masked}/{len(clean)}")
    print(f"round3_name_excess={excess} arbitration_barriers_ok={int(safety)}")
    return complete == len(positives) and not masked and not excess and safety


def main():
    positives, negatives = fixtures()
    complete = 0
    excess = 0
    groups = Counter()
    group_success = Counter()
    for family, text, inputs, gold, mode in positives:
        outputs = run_names(text, inputs, mode)
        all_spans = outputs + inputs
        exact = {(c["start"], c["end"]) for c in all_spans}
        passed = all(span in exact for span in gold)
        complete += passed
        groups[family] += 1
        group_success[family] += passed
        excess += any(not any(a <= c["start"] < c["end"] <= b for a, b in gold) for c in outputs)
    negatives_masked = sum(bool(run_names(text, inputs, "full")) for text, inputs in negatives)
    print(f"name_complete={complete}/{len(positives)}")
    print(f"negatives_masked={negatives_masked}")
    print(f"negative_snippets={len(negatives)} excess_positive_rows={excess}")
    # Aggregate family counters only, useful for mechanical failures without raw
    # examples, row identifiers, values or offsets.
    if complete != len(positives):
        print("family_complete=" + " ".join(f"{key}:{group_success[key]}/{groups[key]}" for key in sorted(groups)))
    mechanics()
    round3_ok = round3_cases()
    if (len(positives) < 60 or len(negatives) < 25 or complete != len(positives)
            or negatives_masked or excess or not round3_ok):
        return 1
    print("name_mechanics=ok")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        print("name_check=failed")
        code = 1
    sys.exit(code)
