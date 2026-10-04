#!/usr/bin/env python3
"""One small, aggregate-only proof on newly invented strings, never datasets.

Run with the existing train venv (phonenumberslite==9.0.40). No installs,
network, model, dataset reads, or value-bearing failure output are needed.
These examples are synthetic format probes, not privacy/accuracy guarantees.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from privacygate.structured import check, detect
from privacygate.context import decide

_FIELDS = {
    "PASSPORTNUM": ("passport no.", "Pass-Nr.", "n° de passeport", "numero passaporto", "pasaporte n.º"),
    "IDCARDNUM": ("ID card no.", "Ausweis-Nr.", "carte d'identité", "carta d'identità", "DNI"),
    "DRIVERLICENSENUM": ("driving licence no.", "Führerschein-Nr.", "permis de conduire", "patente", "permiso de conducir"),
    "TAXNUM": ("tax ID", "Steuer-ID", "numéro fiscal", "codice fiscale", "tax number"),
    "SOCIALNUM": ("SSN", "SVNr.", "NIR", "NSS", "NUSS"),
    "ACCOUNTNUM": ("account no.", "Kontonummer", "compte", "conto", "cuenta"),
    "CREDITCARDNUMBER": ("credit card number", "Kreditkartennummer", "carte bancaire", "carta di credito", "tarjeta bancaria"),
    "PERSONALREF": ("customer no.", "Kundennummer", "n° client", "codice cliente", "n.º de cliente"),
    "TELEPHONENUM": ("phone", "Telefon", "téléphone", "telefono", "teléfono"),
    "IBAN": ("IBAN",) * 5,
}
_LEADS = ("I noted the ", "Ich notierte die ", "Je note le ", "Ho annotato il ", "Anoté el ")
_TAILS = (", and stopped.", "; danach endete es.", "; puis terminé.", "; poi finito.", "; después terminé.")


def iban(country, bban):
    moved = bban + country + "00"
    digits = "".join(c if c.isdigit() else str(ord(c) - 55) for c in moved)
    return country + str(98 - int(digits) % 97).zfill(2) + bban


def card_number(body):
    # Independent left-to-right Luhn generation for a 15-digit body.
    total = sum((int(c) * 2 - 9 if int(c) >= 5 else int(c) * 2) if i % 2 == 0
                else int(c) for i, c in enumerate(body))
    return body + str((-total) % 10)


def fiscal_code(body):
    odd = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                   (1, 0, 5, 7, 9, 13, 15, 17, 19, 21,
                    1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18,
                    20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23)))
    total = sum(odd[c] if i % 2 == 0 else (int(c) if c.isdigit() else ord(c) - 65)
                for i, c in enumerate(body))
    return body + chr(65 + total % 26)


def group(value, sizes, separator):
    parts, pos, index = [], 0, 0
    while pos < len(value):
        size = sizes[index % len(sizes)]
        parts.append(value[pos:pos + size])
        pos += size
        index += 1
    return separator.join(parts)


def _round3():
    positives, clean_cases = [], []
    age_keys = ("age", "Alter", "âge", "età", "edad")
    units = ("years", "Jahre", "ans", "anni", "años")
    for key, unit, verb in zip(age_keys, units, ("is", "beträgt", "est", "è", "es")):
        for connector in (": ", " = ", " " + verb + " ", ":\n"):
            positives.append((key + connector, "47 " + unit, "AGE"))
    positives.extend((("aged ", "47", "AGE"), ("Alter: ", "47", "AGE")))
    for key in ("Case", "Fall", "Dossier", "Caso"):
        for separator in (" / ", "/", " - "):
            positives.append((key + ": ", separator.join(("QRT", "ZX", "5187362")), "PERSONALREF"))
    for key in ("Sozialversicherungsnummer", "sécurité sociale", "previdenza",
                "seguridad social", "social security"):
        for separator in (" ", "-", ".", ""):
            positives.append((key + ": ", separator.join(("518", "736", "294", "861")), "SOCIALNUM"))
    for separator in (" / ", "/"):
        positives.append(("permis: ", "QX" + separator + "518736294", "DRIVERLICENSENUM"))
        positives.append(("mon permis ", "QX" + separator + "518736294", "DRIVERLICENSENUM"))
        positives.append(("Mon passeport, puis permis ", "QX" + separator + "518736294", "DRIVERLICENSENUM"))
    for key, prefix, body in (
        ("Telephone", "+1", "202 518 7362"), ("Telefon", "+49", "(0)30 518 7362"),
        ("Téléphone", "+33", "1 51 87 36 29"), ("Telefono", "+39", "06 5187 3629"),
        ("Teléfono", "+34", "612 51 87 36"),
    ):
        for ending in ("", " ext. 29"):
            positives.append((key + ": ", prefix + "\n" + body + ending, "TELEPHONENUM"))
            atoms = body.split(" ", 1)
            positives.append((key + ": ", prefix + " " + atoms[0] + "\n" + atoms[1] + ending,
                              "TELEPHONENUM"))
    positive_failures, personal_rejected = Counter(), 0
    for prefix, value, label in positives:
        text = "Synthetic record; " + prefix + value + "; end."
        start = len("Synthetic record; " + prefix)
        candidates = detect(text)
        exact = [c for c in candidates if (c["start"], c["end"], c["label"])
                 == (start, start + len(value), label)]
        if not exact:
            positive_failures[label] += 1
        personal_rejected += sum(decide(text, c, candidates)[0] == "reject" for c in candidates)
    serial = group(iban("DE", "518736294861275938"), (4,), " ")
    ops = ("Product serial", "Produktseriencode", "série produit", "seriale prodotto", "de serie",
           "Order code", "Bestellcode", "non attribué", "non assegnato", "sin asignar")
    for key in ops:
        for value in (serial, "+49 (0)30 518 7362", "QRT / ZX / 5187362"):
            clean_cases.append((key + ": ", value))
    for key in ("Manufacturing date", "Herstelldatum", "Date de fabrication", "Fecha de fabricación",
                "Wartungskalender", "Calendrier public d'entretien", "Data di manutenzione",
                "Fecha de mantenimiento", "Maintenance date", "fabrication"):
        clean_cases.append((key + ": ", "17.08.2037"))
    masked_clean = 0
    for prefix, value in clean_cases:
        text = "Synthetic inventory; " + prefix + value + "; end."
        candidates = detect(text)
        masked_clean += any(decide(text, c, candidates)[0] != "reject" for c in candidates)
    # Nonpersonal age/duration prose must not acquire AGE candidates.
    for prefix in ("Product age: ", "Produkt Alter: ", "Produit âge: ", "Prodotto età: ", "Producto edad: "):
        if any(c["label"] == "AGE" for c in detect(prefix + "47 years; end.")):
            raise RuntimeError("round3_nonpersonal_age_failed")
    # Blank lines/new field headings cannot become one OCR phone envelope.
    for value in ("+49\n\n30 518 7362", "+49\nTelephone: 30 518 7362", "+49\n30\n518 7362"):
        text = "Telefon: " + value + "; end."
        if any(c["start"] == 9 and c["end"] == 9 + len(value) for c in detect(text)):
            raise RuntimeError("round3_phone_barrier_failed")
    print("round3_struct_complete=" + str(len(positives) - sum(positive_failures.values())) + "/" + str(len(positives)))
    print("round3_clean_masked=" + str(masked_clean) + "/" + str(len(clean_cases)))
    print("round3_personal_rejected=" + str(personal_rejected))
    for label, count in sorted(positive_failures.items()):
        print("round3_incomplete_label=" + label + " count=" + str(count))
    if len(positives) < 30 or len(clean_cases) < 30 or positive_failures or masked_clean or personal_rejected:
        raise RuntimeError("round3_structured_failed")


def main():
    positives, negatives = [], []

    def positive(label, value, lang=0, field=None, shape="anchored"):
        prefix = _LEADS[lang] + (field if field is not None else _FIELDS[label][lang]) + ": "
        text = prefix + value + _TAILS[lang]
        positives.append((text, len(prefix), len(prefix) + len(value), label, shape))

    def negative(text, shape):
        negatives.append((text, shape))

    ibans = {
        "DE": iban("DE", "274816253947182635"),
        "AT": iban("AT", "2748162539471826"),
        "CH": iban("CH", "27481" + "625394718263"),
        "FR": iban("FR", "2748162539" + "47182635274" + "81"),
        "IT": iban("IT", "Q" + "2748162539" + "471826352748"),
        "ES": iban("ES", "27481625394718263527"),
        "NL": iban("NL", "QZTP" + "2748162539"),
        "BE": iban("BE", "274816253947"),
        "LU": iban("LU", "274" + "8162539471826"),
        "PT": iban("PT", "274816253947182635274"),
        "GB": iban("GB", "QZTP" + "27481625394718"),
        "IE": iban("IE", "QZTP" + "27481625394718"),
        "PL": iban("PL", "274816253947182635274816"),
    }
    card = card_number("472816253947182")
    cf = fiscal_code("QZTPLM82D17H501")
    dni_body = "27481625"
    dni = dni_body + "TRWAGMYFPDXBNJZSQVHLCKE"[int(dni_body) % 23]
    nie_body = "Y2748162"
    nie = nie_body + "TRWAGMYFPDXBNJZSQVHLCKE"[int("1" + nie_body[1:]) % 23]
    nir_body = "1840727481625"
    nir = nir_body + str(97 - int(nir_body) % 97).zfill(2)
    ahv_body = "756274816253"
    ahv = ahv_body + str(-sum(int(c) * (1 if i % 2 == 0 else 3)
                             for i, c in enumerate(ahv_body)) % 10)

    values = {
        "PASSPORTNUM": ("274816253", "Q27481625", "27-48-16253", "QZ 2748162", "QZ/2748162"),
        "IDCARDNUM": ("QZ-274816", "Q 274 816 25", "27.48.1625", "QZ2748162", dni),
        "DRIVERLICENSENUM": ("QZ27481625", "QZ-2748-1625", "27 48 16 25", "QZ/274816", "27.481.625"),
        "TAXNUM": ("274-81-6253", "27481625394", "274 816 253 9471", cf, dni),
        "SOCIALNUM": ("274-81-6253", "2748 162537", group(nir, (1, 2, 2, 2, 3, 3, 2), " "), "27/48162539/47", "274816253947"),
        "ACCOUNTNUM": ("2748-1625-3947", "274 816 253", "27.48.16.25.39", "2748/1625/3947", "27 4816 2539 47"),
        "CREDITCARDNUMBER": tuple(group(card, (size,), sep) for size, sep in ((4, " "), (4, "-"), (2, "."), (5, " "), (3, "-"))),
        "PERSONALREF": ("QZ-274816", "27/48/1625", "QZ 274 816", "QZ.2748.1625", "QZ-27-48-16"),
        "TELEPHONENUM": ("+1 (202) 748-1625 ext. 17", "+49 (0)30 2749 8162 Durchwahl 17", "+33 1.74.28.61.52 poste 17", "+39 06 2748 1625 interno 17", "+34 612 48 16 25 ext. 17"),
        "IBAN": tuple(group(ibans["DE"], (size,), sep) for size, sep in ((4, " "), (3, "."), (2, "-"), (5, "\u00a0"), (1, "\u202f"))),
    }
    for label, language_values in values.items():
        for lang, value in enumerate(language_values):
            positive(label, value, lang)
    for index, value in enumerate(ibans.values()):
        for sizes, sep in (((4,), " "), ((2, 5, 3), "."), ((3,), "-"), ((5,), "\u202f")):
            positive("IBAN", group(value.lower(), sizes, sep), index % 5, shape="iban-grouping")
    phone_forms = (
        ("+43 (0)1 274 8162 DW 17", 1), ("+41 (0)44 274 81 62 int. 17", 1),
        ("+44 (0)20 3748 1625 x17", 0), ("(030) 2749 8162", 1),
        ("030.2749.8162 DW 17", 1), ("01 274 8162", 1),
        ("044 274 81 62", 1), ("01.74.28.61.52 poste 17", 2),
        ("06 2748 1625 interno 17", 3), ("612 48 16 25 ext. 17", 4),
        ("(020) 3748 1625 int. 17", 0), ("(202) 748-1625 x 17", 0),
        ("+1 202 048 1625 extension 17", 0), ("+49 30 2749 8162 ext. 17", 0),
        ("+33 1 74 28 61 52 anexo 17", 4), ("+39 06 2748 1625 ext. 17", 3),
    )
    for value, lang in phone_forms:
        positive("TELEPHONENUM", value, lang, shape="phone-boundary")
    positive("IDCARDNUM", nie, 4, field="NIE", shape="nie")
    positive("IDCARDNUM", dni[:-1] + ("A" if dni[-1] != "A" else "B"), 4, shape="checksum-typo")
    positive("CREDITCARDNUMBER", card[:-1] + str((int(card[-1]) + 1) % 10), shape="checksum-typo")
    positive("TAXNUM", group(cf, (6, 2, 1, 2, 1, 3, 1), " "), 3, shape="fiscal-grouping")
    positive("TAXNUM", cf[:-1] + ("A" if cf[-1] != "A" else "B"), 3, shape="checksum-typo")
    positive("SOCIALNUM", group(ahv, (3, 4, 4, 2), "."), 1, field="AHV", shape="ahv")
    positive("SOCIALNUM", "ZZ 27 48 16 C", field="NI number", shape="unsupported-format")
    positive("PERSONALREF", "QZ/2748/1625", field="case no.", shape="case-reference")
    positive("PERSONALREF", "QZ-274816", field="patient no.", shape="patient-reference")
    positive("PERSONALREF", "QZ-274816", field="membership no.", shape="membership-reference")
    positive("PASSPORTNUM", "QZ - 2748 / 1625", 1, field="Reisepass", shape="spaced-separators")
    positive("IBAN", "ZZ27 4816 2539 4718", shape="unsupported-country")
    positive("IBAN", "DE00 2748 1625 3947 1826 35", shape="checksum-typo")
    positive("IBAN", "DE27 4816 2539", shape="short-personal-value")
    for label, value in (("IBAN", ibans["GB"]), ("TELEPHONENUM", "+49 30 2749 8162")):
        prefix = "We received "
        positives.append((prefix + value + "; end.", len(prefix), len(prefix) + len(value), label, "unanchored"))

    for field in ("Order number", "Invoice no.", "SKU", "Product number", "Rechnungsnummer",
                  "Bestellung", "Facture", "Commande", "Fattura", "Ordine", "Factura", "Pedido"):
        negative(field + ": 202 748 1625; paid.", "nonpersonal-code")
        negative(field + ": " + group(card, (4,), " ") + "; paid.", "luhn-code")
    for text, shape in (
        ("Dimensions: 49 30 2749 8162 mm.", "dimensions"),
        ("Abmessungen: 20.274.816.25 mm.", "dimensions"),
        ("Date: 2026-10-03.", "calendar-date"),
        ("Datum: 03.10.2026.", "calendar-date"),
        ("The meeting is on 2026-10-03 at 10:30.", "calendar-date"),
        ("Room number: 202 748 1625.", "room"),
        ("Zimmer: 030.2749.8162.", "room"),
        ("Quantity: 27 481 625 units.", "quantity"),
        ("Price: 202 748 1625 EUR.", "price"),
        ("Preis: 49.302.748.1625 EUR.", "price"),
        ("Dimensions: 12 x 34 x 56 cm.", "dimensions"),
        ("Product no.: QZ-2748-1625.", "product-code"),
        ("Invoice no.: +49 30 2749 8162.", "phone-code"),
        ("Order no.: (202) 748-1625.", "phone-code"),
        ("Nothing numerical is here.", "clean-prose"),
        ("Room: 274.", "room"),
    ):
        negative(text, shape)

    candidate_keys = {"start", "end", "label", "source", "score", "validation", "context", "protected", "stage"}
    failures, complete, excess = Counter(), 0, 0
    for text, start, end, label, shape in positives:
        found = detect(text)
        matching = [c for c in found if (c["start"], c["end"], c["label"]) == (start, end, label)]
        if matching:
            complete += 1
        else:
            failures[label + ":" + shape] += 1
        excess += any(c["start"] < start or c["end"] > end for c in found)
        for cand in found:
            if (set(cand) != candidate_keys or cand["source"] != "structured" or cand["stage"] != "raw"
                    or cand["score"] is not None or not 0 <= cand["start"] < cand["end"] <= len(text)
                    or cand["validation"] not in ("valid", "invalid", "unknown", "n/a")
                    or cand["context"] not in ("personal", "nonpersonal", "unknown")
                    or type(cand["protected"]) is not bool):
                raise RuntimeError("check_structured_candidate_contract_failed")
            before = dict(cand)
            verified = check(text, cand)
            if verified is cand or cand != before or set(verified) != candidate_keys:
                raise RuntimeError("check_structured_copy_contract_failed")
    negatives_detected, negative_shapes = 0, Counter()
    for text, shape in negatives:
        if detect(text):
            negatives_detected += 1
            negative_shapes[shape] += 1

    # Check validation independently of candidate assembly, including veto safety.
    validation_checks = (("IBAN", ibans["DE"], "valid"), ("IBAN", "DE00" + ibans["DE"][4:], "invalid"),
                         ("IBAN", "ZZ2748162539", "unknown"), ("CREDITCARDNUMBER", card, "valid"),
                         ("CREDITCARDNUMBER", card[:-1] + str((int(card[-1]) + 1) % 10), "invalid"),
                         ("TAXNUM", cf, "valid"), ("TAXNUM", cf[:-1] + ("A" if cf[-1] != "A" else "B"), "invalid"),
                         ("IDCARDNUM", dni, "valid"), ("IDCARDNUM", nie, "valid"),
                         ("SOCIALNUM", ahv, "valid"), ("SOCIALNUM", nir, "valid"),
                         ("TELEPHONENUM", "+49 (0)30 2749 8162 Durchwahl 17", "valid"),
                         ("PERSONNAME", "Invented", "n/a"))
    for label, value, expected in validation_checks:
        cand = {"start": 0, "end": len(value), "label": label, "source": "mbert", "score": 0.5,
                "validation": "unknown", "context": "unknown", "protected": False, "stage": "raw"}
        result = check(value, cand)
        if result["validation"] != expected or cand["validation"] != "unknown" or result["protected"]:
            raise RuntimeError("check_structured_validation_failed")
    for invalid_input in (None, 7, {}, []):
        try:
            detect(invalid_input)
        except ValueError as error:
            if str(error) != "structured_invalid_input":
                raise RuntimeError("check_structured_error_contract_failed") from None
        else:
            raise RuntimeError("check_structured_error_contract_failed")
    if len(positives) < 60 or len(negatives) < 25 or set(values) != set(_FIELDS):
        raise RuntimeError("check_structured_fixture_contract_failed")
    print("struct_complete=" + str(complete) + "/" + str(len(positives)))
    print("negatives_detected=" + str(negatives_detected))
    print("negative_total=" + str(len(negatives)))
    print("positive_excess_rows=" + str(excess))
    print("validation_checks=" + str(len(validation_checks)))
    for shape, count in sorted(failures.items()):
        print("incomplete_shape=" + shape + " count=" + str(count))
    for shape, count in sorted(negative_shapes.items()):
        print("negative_shape=" + shape + " count=" + str(count))
    if complete * 10 < len(positives) * 9 or negatives_detected > 2:
        return 1
    _round3()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("check_structured_failed", file=sys.stderr)
        sys.exit(1)
