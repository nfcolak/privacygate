#!/usr/bin/env python3
"""One small, aggregate-only proof on newly invented strings, never datasets.

Run with the existing train venv (phonenumberslite==9.0.40). No installs,
network, model, dataset reads, or value-bearing failure output are needed.
These examples are synthetic format probes, not privacy/accuracy guarantees.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from privacygate.rules.structured import check, detect
from privacygate.rules.context import decide

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
        positives.append(("mon permis: ", "QX" + separator + "518736294", "DRIVERLICENSENUM"))
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


def _round4():
    from privacygate.rules.refine import refine, _word_completion, _extend_address
    positives, twins = [], []
    phones = ('(+1) 202.684.2751', '(0049) 30 684 2751', '(+33) 1.68.42.75.13',
              '(+39) 06 6842 7513', '(0034) 612 68 42 75')
    contacts = ('Phone', 'Telefon', 'Téléphone', 'Telefono', 'Teléfono')
    headers = (('Part', 'Quantity', 'Price'), ('Artikel', 'Menge', 'Preis'),
               ('Pièce', 'Quantité', 'Prix'), ('Articolo', 'Quantità', 'Prezzo'),
               ('Pieza', 'Cantidad', 'Precio'))
    for contact, roles, value in zip(contacts, headers, phones):
        for delimiter in (' | ', '\t', ' / '):
            prefix = delimiter.join((roles[0], contact, roles[2])) + '\n' + 'RVT' + delimiter
            positives.append((prefix, value, 'TELEPHONENUM', delimiter + '7.25'))
            twins.append(delimiter.join(roles) + '\n' + delimiter.join(('RVT', value, '7.25')))
        for code in ('RVT-' + '202-684-2751', 'QH/202/6842751'):
            positives.append((contact + ': ', value, 'TELEPHONENUM', '; end.'))
            twins.append('Inventory serial: ' + code + '; end.')
    births = ('DOB', 'birth date', 'date of birth', 'Geburtsdatum', 'geboren am',
              'Naissance', 'date de naissance', 'né le', 'data di nascita', 'nato il',
              'Nacimiento', 'fecha de nacimiento')
    for i, key in enumerate(births):
        for date in ('24 · 07 · 1983', '24/07/1983', '1983-07-24'):
            gap = (': ', ' = ', '\n')[i % 3]
            positives.append((key + gap, date, 'DATEOFBIRTH', '; end.'))
            twins.append('Manufacturing date' + gap + date + '; end.')
    for key, date in (('born on', '24 July 1983'), ('Geburtsdatum', '24 Juli 1983'),
                      ('né le', '24 juillet 1983'), ('nato il', '24 luglio 1983'),
                      ('nacido el', '24 julio 1983')):
        positives.append((key + ': ', date, 'DATEOFBIRTH', '; end.'))
        twins.append('Calendar date: ' + date + '; end.')
    aliases = (('tax identification number', 'TAXNUM'), ('Tax\nidentifier', 'TAXNUM'),
               ('Steueridentifikationsnummer', 'TAXNUM'), ('identifiant fiscal', 'TAXNUM'),
               ('número fiscal', 'TAXNUM'), ('driving permit', 'DRIVERLICENSENUM'),
               ('permis de\nconduire', 'DRIVERLICENSENUM'), ('permiso de conducir', 'DRIVERLICENSENUM'),
               ('numero di socio', 'PERSONALREF'), ('número de\nsocio', 'PERSONALREF'),
               ('numéro de membre', 'PERSONALREF'), ('membership number', 'PERSONALREF'))
    for key, label in aliases:
        for value in ('QV8 684 275 13R', '684 27\n5 138 2'):
            positives.append(('my document; ' + key + ' = ', value, label, '; end.'))
            twins.append('Order code: ' + value + '; end.')
    for key, label in (('permit', 'DRIVERLICENSENUM'), ('permiso', 'DRIVERLICENSENUM'),
                       ('permis', 'DRIVERLICENSENUM'), ('fiscal', 'TAXNUM'), ('member', 'PERSONALREF')):
        positives.append(('my personal document — ' + key + ' = ', 'QVR 684 275', label, '; end.'))
        twins.append('Inventory specification — ' + key + ' = QVR 684 275; end.')
    # Invalid-but-explicit contact values and standalone uncertain values stay.
    for key in contacts:
        positives.append((key + ': ', '+99 684 275 1382', 'TELEPHONENUM', '; end.'))
        twins.append('Lot: +99 684 275 1382; end.')
    failures, personal_rejected, clean_masked = Counter(), 0, 0
    for prefix, value, label, tail in positives:
        text = prefix + value + tail
        candidates = detect(text)
        a, b = len(prefix), len(prefix) + len(value)
        exact = [c for c in candidates if (c['start'], c['end'], c['label']) == (a, b, label)]
        if not exact:
            failures[label] += 1
        personal_rejected += sum(decide(text, c, candidates)[0] == 'reject' for c in exact)
    for text in twins:
        candidates = detect(text)
        clean_masked += any(decide(text, c, candidates)[0] != 'reject' for c in candidates)
    # Seed coverage stays, but numeric refinement cannot absorb product letters.
    for label in ('TELEPHONENUM', 'AGE', 'ACCOUNTNUM', 'ZIPCODE'):
        text = 'SKU: RVT-202-6842751'
        a = text.index('202')
        seed = {'start': a, 'end': len(text), 'label': label, 'source': 'mbert'}
        if _word_completion(text, [seed]) != [seed]:
            raise RuntimeError('round4_numeric_code_growth_failed')
    # A balanced country prefix is the envelope, not an outer commentary bracket.
    text = 'Phone: (note) (+1) 202.684.2751 (verified)'
    value = '(+1) 202.684.2751'
    if not any(text[c['start']:c['end']] == value for c in detect(text)):
        raise RuntimeError('round4_phone_wrapper_failed')
    for separator in (' | ', ' / '):
        value = 'Pine Road 38, 8426 Velora' + separator + 'Switzerland'
        for field, expected in (('Address: ', True), ('Street | House | Town | Country\n', False)):
            text = field + value
            parts = [{'label': label, 'start': text.index(part), 'end': text.index(part) + len(part), 'source': 'mbert'}
                     for label, part in (('STREET', 'Pine Road'), ('BUILDINGNUM', '38'),
                                         ('ZIPCODE', '8426'), ('CITY', 'Velora'))]
            result = refine(text, parts)
            covered_country = any(c['end'] == len(text) for c in result)
            if covered_country != expected:
                raise RuntimeError('round4_postal_field_failed')
    print(f'round4_struct_complete={len(positives) - sum(failures.values())}/{len(positives)}')
    print(f'round4_clean_masked={clean_masked}/{len(twins)}')
    print(f'round4_personal_rejected={personal_rejected}')
    for label, count in sorted(failures.items()):
        print(f'round4_incomplete_label={label} count={count}')
    if len(positives) < 40 or len(twins) < 40 or failures or clean_masked or personal_rejected:
        raise RuntimeError('round4_structured_failed')


def _steuer_id(body):
    product = 10
    for d in body:
        total = (int(d) + product) % 10 or 10
        product = (2 * total) % 11
    return body + str((11 - product) % 11 % 10)


def _round6():
    """Cue-free ID detectors and cue-bound code shapes on invented strings and clean twins."""
    from privacygate.rules import structured
    dni = lambda body: body + "TRWAGMYFPDXBNJZSQVHLCKE"[int(body) % 23]
    wrong = lambda value: value[:-1] + ("A" if value[-1] != "A" else "B")
    nir_body = "2910443217650"
    nir = nir_body + str(97 - int(nir_body) % 97).zfill(2)
    nir_group = group(nir[:1] + nir[1:], (1, 2, 2, 2, 3, 3, 2), " ")
    steuer = _steuer_id("4710382954")
    steuer_bad = steuer[:-1] + str((int(steuer[-1]) + 1) % 10)
    nino = "AB123456C"
    ahv_body = "756381472916"
    ahv = ahv_body + str(-sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(ahv_body)) % 10)
    ahv_dotted = ahv[:3] + "." + ahv[3:7] + "." + ahv[7:11] + "." + ahv[11:]
    cf = fiscal_code("VRXMQT75C12L219")
    cases = (  # (detector, label, positive value, clean look-alike twins)
        ("es_dni_nie", "IDCARDNUM", dni("38172946"), (wrong(dni("38172946")), "38172946", "Y381729", "38172946 EUR")),
        ("es_dni_nie", "IDCARDNUM", "X" + "3817294"[:7] + "TRWAGMYFPDXBNJZSQVHLCKE"[int("0" + "3817294") % 23],
         ("X3817294" + "!", "Q3817294R")),
        ("it_codice_fiscale", "TAXNUM", cf, (wrong(cf), "VRXMQT75C12L219", "VRXMQT75C12L2199X")),
        ("fr_nir", "SOCIALNUM", nir, (nir[:-2] + str((int(nir[-2:]) + 1) % 97).zfill(2), "3" + nir[1:], nir[:-1])),
        ("fr_nir", "SOCIALNUM", nir_group, ("2 91 04 43 217 650 00",)),
        ("de_steuer_idnr", "TAXNUM", steuer, (steuer_bad, "0" + steuer[1:], "12345678901", "11111111111")),
        ("de_steuer_idnr", "TAXNUM", steuer[:2] + " " + steuer[2:5] + " " + steuer[5:8] + " " + steuer[8:],
         ("+49 30 " + steuer[2:],)),
        ("gb_nino", "SOCIALNUM", nino, ("BG123456C", "ZZ123456C", "AB123456E", "DA123456C")),
        ("gb_nino", "SOCIALNUM", "AB 12 34 56 C", ("QQ 12 34 56 C",)),
        ("us_ssn", "SOCIALNUM", "518-73-4294", ("000-73-4294", "666-73-4294", "918-73-4294", "518-00-4294", "518-73-0000")),
        ("ch_ahv", "SOCIALNUM", ahv_dotted, (ahv_dotted[:-1] + str((int(ahv[-1]) + 1) % 10), "755.3814.7291.64")),
    )
    previous = structured.ENABLED
    structured.ENABLED = frozenset(structured.ID_DETECTORS)
    failures, twin_masked, twin_total, personal_rejected = Counter(), 0, 0, 0
    leads = ("Notes: ", "Ich habe ", "Nota: ", "J'ai noté ", "He apuntado ")
    try:
        for index, (name, label, value, twins) in enumerate(cases):
            lead = leads[index % len(leads)]
            text = lead + value + ", and nothing else."
            found = [c for c in detect(text) if (c["start"], c["end"], c["label"]) == (len(lead), len(lead) + len(value), label)]
            if not found:
                failures[name] += 1
            personal_rejected += sum(decide(text, c, detect(text))[0] == "reject" for c in found)
            for twin in twins:
                twin_total += 1
                text = lead + twin + ", and nothing else."
                twin_masked += any(c["label"] == label and decide(text, c, detect(text))[0] != "reject"
                                   for c in detect(text) if c["source"] == "structured"
                                   and c["validation"] == "valid")
        # Operational codes and plain business numbers never trigger the cue-free set.
        for field in ("Order", "Invoice", "SKU", "Rechnung", "Bestellung", "Pedido"):
            for value in (dni("38172946"), steuer, nir, nino, cf, ahv_dotted, "518-73-4294"):
                twin_total += 1
                text = field + " no.: " + value + "; paid."
                twin_masked += any(decide(text, c, detect(text))[0] != "reject" for c in detect(text))
        for text in ("Total 38172946 EUR, 12 pieces.", "Dimensions 3817 x 2946 mm.", "Date: 2031-04-05.",
                     "Room 4710 is free on 2031-04-05.", "Price: 4,710.38 CHF.", "Ref 4710382954 shipped."):
            twin_total += 1
            twin_masked += bool(detect(text))
    finally:
        structured.ENABLED = previous
    # Cue-bound shapes: a document-type cue is required; the same shape after an operational cue is not.
    cued = (("PASSPORTNUM", "Passport number is ", "QZ2748162"), ("PASSPORTNUM", "Reisepass lautet ", "C01X00T47"),
            ("PASSPORTNUM", "pasaporte nº ", "Q27481625"), ("IDCARDNUM", "Identity card no. ", "NX 274 816 253"),
            ("IDCARDNUM", "Personalausweis: ", "L01X00T471"), ("DRIVERLICENSENUM", "driving licence number ", "QV27481625394"),
            ("DRIVERLICENSENUM", "permis de conduire : ", "QV 2748-16253"), ("DRIVERLICENSENUM", "patente di guida ", "QV2748162539"),
            ("SOCIALNUM", "Social insurance ", "SN 274 816 253"), ("SOCIALNUM", "Sozialversicherung: ", "SN-2748-16253"),
            ("SOCIALNUM", "previdenza sociale ", "SN2748162539"), ("TAXNUM", "Tax identifier ", "TX 274 816 2539"),
            ("TAXNUM", "Steuerkennung: ", "TX2748162539"), ("TAXNUM", "identificador fiscal ", "TX-274816-2539"),
            ("PERSONALREF", "Patient reference ", "PAT 274 816 253"), ("PERSONALREF", "Patientenreferenz: ", "PAT-27481625"),
            ("PERSONALREF", "medical record number ", "MR274816253"), ("PERSONALREF", "health plan number ", "HP 274 816 253"),
            ("PERSONALREF", "référence patient ", "PAT 274 816 253"), ("PERSONALREF", "riferimento paziente: ", "PAT27481625"))
    previous = structured.ENABLED
    structured.ENABLED = frozenset(structured.ID_DETECTORS)
    cued_failures = 0
    try:
        for label, key, value in cued:
            text = "Synthetic record; " + key + value + "; end."
            start = len("Synthetic record; " + key)
            hit = [c for c in detect(text) if (c["start"], c["end"], c["label"]) == (start, start + len(value), label)]
            cued_failures += not hit
            personal_rejected += sum(decide(text, c, detect(text))[0] == "reject" for c in hit)
        for key in ("Invoice number is ", "Order no. ", "Product reference ", "Artikelnummer: ", "Room ", "Quantity ",
                    "Passport expires ", "Passport photo size ", "Driving licence valid for ", "Tax identifier changes in ",
                    "Patient reference year "):
            for value in ("QZ2748162", "PAT 274 816 253", "2031", "12 x 15", "4,710.38"):
                twin_total += 1
                text = "Synthetic record; " + key + value + "; end."
                twin_masked += any(c["label"] in {"PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM", "TAXNUM", "PERSONALREF"}
                                   and decide(text, c, detect(text))[0] != "reject" for c in detect(text))
    finally:
        structured.ENABLED = previous
    total = len(cases) + len(cued)
    print("round6_struct_complete=" + str(total - sum(failures.values()) - cued_failures) + "/" + str(total))
    print("round6_clean_masked=" + str(twin_masked) + "/" + str(twin_total))
    print("round6_personal_rejected=" + str(personal_rejected))
    for name, count in sorted(failures.items()):
        print("round6_incomplete_detector=" + name + " count=" + str(count))
    if failures or cued_failures or twin_masked or personal_rejected or twin_total < 80:
        raise RuntimeError("round6_structured_failed")


def _legacy_extension_regression():
    from privacygate.rules.refine import refine, _word_completion
    base = '+49 (030) 684-2751'
    keywords = ('ext.', 'extension', 'extn', 'Durchwahl', 'durchw.',
                'poste', 'interno', 'anexo', 'int.', 'app.', 'apparat', 'interne')
    prefixes = ('Phone: ', 'My contact is ', 'Part | Phone | Price\nQVP | ')
    checked = clean_rejected = 0
    for prefix in prefixes:
        tail = ' | 8.75' if '\n' in prefix else '; end.'
        for keyword in keywords:
            value = base + ' ' + keyword + ' 46'
            for fragment_tail in ('46', '. 46') if keyword.endswith('.') else ('46',):
                text = prefix + value + tail
                start, end = len(prefix), len(prefix) + len(value)
                cut = start + len(base) + 1 + 2
                number_start = text.index(fragment_tail, cut)
                seeds = [{'start': start, 'end': cut, 'label': 'TELEPHONENUM', 'source': 'mbert'},
                         {'start': number_start, 'end': end, 'label': 'TELEPHONENUM', 'source': 'mbert'}]
                covered = {i for c in refine(text, seeds) for i in range(c['start'], c['end'])}
                if not set(range(start, end)) <= covered:
                    raise RuntimeError('legacy_phone_extension_incomplete')
                # The identical phone-like syntax belongs to an operational
                # field in the twin. Neither keyword growth nor validity may
                # manufacture ownership for that field.
                clean_prefix = 'Inventory serial: '
                clean = clean_prefix + value + '; end.'
                clean_seed = dict(seeds[0], start=len(clean_prefix),
                                  end=len(clean_prefix) + cut - start)
                if _word_completion(clean, [clean_seed]) != [clean_seed]:
                    raise RuntimeError('legacy_operational_extension_growth')
                candidates = detect(clean)
                if any(decide(clean, c, candidates)[0] != 'reject' for c in candidates):
                    raise RuntimeError('legacy_operational_extension_masked')
                clean_rejected += 1
                checked += 1
    # Missing digits or arbitrary letters are not extension syntax. Retain the
    # numeric seed, but never absorb a product-code suffix or unrelated word.
    for tail in (' ext.', ' extras', ' ext. QVP'):
        text = 'Phone: ' + base + tail
        cut = len('Phone: ' + base + ' ') + 2
        seed = {'start': len('Phone: '), 'end': cut, 'label': 'TELEPHONENUM', 'source': 'mbert'}
        if _word_completion(text, [seed]) != [seed]:
            raise RuntimeError('legacy_extension_syntax_boundary')
    print(f'legacy_extension_complete={checked}/{checked}')
    print(f'legacy_extension_clean_unmasked={clean_rejected}/{checked}')


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
    _round4()
    _round6()
    _legacy_extension_regression()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("check_structured_failed", file=sys.stderr)
        sys.exit(1)
