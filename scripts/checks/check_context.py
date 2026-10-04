"""One small offline check on invented contrastive strings; aggregates only."""
import copy
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from privacygate.rules.context import decide


def _candidate(text, value, label, **changes):
    start = text.index(value)
    cand = {
        "start": start, "end": start + len(value), "label": label,
        "source": "mbert", "score": 0.93, "validation": "unknown",
        "context": "unknown", "protected": False, "stage": "raw",
    }
    cand.update(changes)
    return cand


def _decision(text, cand, cands=None):
    cands = [cand] if cands is None else cands
    before = copy.deepcopy((cand, cands))
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        result = decide(text, cand, cands)
    if (before != (cand, cands) or output.getvalue() or errors.getvalue()
            or result[0] not in {"accept", "reject", "unresolved"}):
        raise ValueError("context_contract_failed")
    return result


def _fixtures():
    # All values and templates are invented here, not loaded from any dataset.
    locales = (
        ("Dimensions", "Volume", "Mass", "Meeting", "Opening hours", "Deadline",
         "Order", "Invoice", "SKU", "Article", "Room", "Gate", "Platform", "Seat",
         "Brand", "Company", "April", "my record"),
        ("Maße", "Volumen", "Masse", "Termin", "Öffnungszeiten", "Frist",
         "Bestell-Nr.", "Rechnung", "SKU", "Art.-Nr.", "Zimmer", "Gate", "Gleis", "Sitz",
         "Marke", "Unternehmen", "April", "mein Datensatz"),
        ("Dimensions", "Volume", "Masse", "Réunion", "Horaires d'ouverture", "Échéance",
         "Commande", "Facture", "SKU", "Réf. produit", "Salle", "Gate", "Quai", "Siège",
         "Marque", "Société", "avril", "mon dossier"),
        ("Dimensioni", "Volume", "Massa", "Riunione", "Orari di apertura", "Scadenza",
         "Ordine", "Fattura", "SKU", "Codice articolo", "Sala", "Gate", "Binario", "Posto",
         "Marca", "Azienda", "aprile", "mio documento"),
        ("Dimensiones", "Volumen", "Masa", "Reunión", "Horario de apertura", "Plazo",
         "Pedido", "Factura", "SKU", "Referencia", "Aula", "Gate", "Andén", "Asiento",
         "Marca", "Empresa", "abril", "mi registro"),
    )
    for locale in locales:
        (dim, volume, mass, meeting, opening, deadline, order, invoice, sku, article,
         room, gate, platform, seat, brand, company, month, owner) = locale
        specs = (
            (dim, "12 x 30 cm", "ZIPCODE"),
            (dim, "4×6", "TELEPHONENUM"),
            (volume, "250 ml", "ACCOUNTNUM"),
            (mass, "3,5 kg", "AGE"),
            (meeting, "2036-04-18", "DATEOFBIRTH"),
            (opening, "09:45", "TIME"),
            (deadline, f"18 {month} 2036", "AGE"),
            (order, "OR-4729", "PERSONALREF"),
            (invoice, "INV-6842", "ACCOUNTNUM"),
            (sku, "PF-7305", "ZIPCODE"),
            (article, "AR-9817", "PERSONALREF"),
            (room, "12B", "ZIPCODE"),
            (gate, "A12", "AGE"),
            (platform, "7", "TELEPHONENUM"),
            (seat, "24C", "PERSONALREF"),
            (brand, "Zelvara", "ORG"),
            (company, "Felmora Works", "ORGANIZATION"),
        )
        for cue, value, label in specs:
            clean = f"{cue}: {value}."
            # Keep exactly the same clean construction; only add a person link.
            personal = f"{owner} — {clean}"
            yield clean, personal, value, label


def _invariants():
    text, value = "Order: ZX-4729.", "ZX-4729"
    for label in (
        "PERSONNAME", "GIVENNAME", "SURNAME", "EMAIL", "USERNAME", "IBAN",
        "PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM",
        "CREDITCARDNUMBER",
    ):
        if _decision(text, _candidate(text, value, label))[0] != "accept":
            raise ValueError("sensitive_label_failed")
    for changes in (
        {"protected": True}, {"protected": None},
        {"source": "structured", "validation": "valid"},
        {"source": "coverage"}, {"stage": "coverage"},
    ):
        if _decision(text, _candidate(text, value, "ACCOUNTNUM", **changes))[0] != "accept":
            raise ValueError("anchor_failed")
    for changes in ({"context": "personal"},):
        if _decision(text, _candidate(text, value, "ACCOUNTNUM", **changes))[0] != "unresolved":
            raise ValueError("personal_context_failed")
    # Nearby names and overlapping independent protected evidence override clean cues.
    named = "Ada Zorin — Order: ZX-4729."
    code = _candidate(named, value, "ACCOUNTNUM")
    name = _candidate(named, "Ada Zorin", "PERSONNAME")
    if _decision(named, code, [code, name])[0] != "unresolved":
        raise ValueError("name_link_failed")
    for changes in ({"protected": True}, {"source": "structured", "validation": "valid"}):
        anchor = _candidate(text, "4729", "TELEPHONENUM", **changes)
        code = _candidate(text, value, "PERSONALREF")
        if _decision(text, code, [code, anchor])[0] != "unresolved":
            raise ValueError("overlapping_anchor_failed")
    # Every listed personal cue blocks a clean-looking reference, with whole words.
    for cue in (
        "my", "me", "mein", "meine", "mon", "mio", "mi", "customer", "Kunde",
        "client", "cliente", "patient", "Patient", "paziente", "paciente",
        "born", "geboren", "né le 19/02/1981", "nato", "nacido", "age: 28", "Alter: 28",
        "âge: 28", "età: 28", "edad: 28", "28 years old", "28 Jahre alt",
        "28 ans", "28 anni", "28 años", "Lena's record",
    ):
        linked = f"{cue} — {text}"
        if _decision(linked, _candidate(linked, value, "PERSONALREF"))[0] != "unresolved":
            raise ValueError("cue_link_failed")
    # Lack of a benign construction, a too-wide span, or cross-field cues cannot veto.
    for raw, part, label in (
        ("ZX-4729.", value, "PERSONALREF"),
        ("Date: 2036-04-18.", "2036-04-18", "DATEOFBIRTH"),
        ("Meeting: 09:45.", "09:45", "ZIPCODE"),
        ("Meeting: 2036-04-18.", "2036-04-18", "ORG"),
        ("Meeting\nDate: 2036-04-18.", "2036-04-18", "DATEOFBIRTH"),
        ("Meeting; Date: 2036-04-18.", "2036-04-18", "DATEOFBIRTH"),
        ("Roommate: 12.", "12", "AGE"),
        ("Brand: Zelvara.", "Zelvara", "ZIPCODE"),
        ("Order: ZX-4729.", "Order: ZX-4729", "PERSONALREF"),
        ("Order: ZX-4729 pending.", "ZX-4729 pending", "PERSONALREF"),
    ):
        if _decision(raw, _candidate(raw, part, label))[0] != "accept":
            raise ValueError("narrow_scope_failed")
    for raw, part, label in (
        ("Room no. 12.", "12", "AGE"),
        ("Bestellnummer: AB-4729.", "AB-4729", "PERSONALREF"),
        ("Bestell-Nr.: AB-4729.", "AB-4729", "PERSONALREF"),
        ("Invoice n° AB-4729.", "AB-4729", "ACCOUNTNUM"),
        ("Myriad objects. Order: ZX-4729.", "ZX-4729", "PERSONALREF"),
        ("Deadline: 18.04.2036.", "18.04.2036", "DATEOFBIRTH"),
        ("Réunion: 18/04/2036.", "18/04/2036", "DATEOFBIRTH"),
        ("Meeting: April 18, 2036.", "April 18, 2036", "DATEOFBIRTH"),
        ("Opening hours: 9 am.", "9 am", "TIME"),
        ("Order: ZX-4729.", "4729", "PERSONALREF"),
    ):
        if _decision(raw, _candidate(raw, part, label))[0] != "reject":
            raise ValueError("bounded_construction_failed")
    invalid = _candidate(text, value, "PERSONALREF", validation="invalid")
    if _decision(text, invalid)[0] != "reject":
        raise ValueError("validator_not_a_veto_failed")
    linked = "customer — unknown reference ZX-4729."
    invalid = _candidate(linked, value, "ACCOUNTNUM", validation="invalid")
    if _decision(linked, invalid)[0] != "accept":
        raise ValueError("invalid_personal_preserved_failed")
    for changes in ({"start": -1}, {"end": len(text) + 1}, {"start": True}):
        if _decision(text, _candidate(text, value, "PERSONALREF", **changes))[0] != "unresolved":
            raise ValueError("invalid_candidate_failed")


def _round3():
    from scripts.checks.check_structured import group, iban
    # Fresh invented serials with independently calculated valid checksums.
    serials = (
        group(iban("DE", "639182745061928374"), (4,), " "),
        group(iban("GB", "QXRT63918274506192"), (4,), " "),
        group(iban("IT", "Z" + "6391827450" + "619283745061"), (4,), " "),
    )
    from privacygate.rules.structured import check
    if any(check(value, _candidate(value, value, "IBAN"))["validation"] != "valid" for value in serials):
        raise ValueError("round3_checksum_fixture_failed")
    fixtures = []
    for cue in ("Product serial", "Produktseriencode", "série produit", "seriale prodotto", "de serie",
                "Order code", "Bestellcode", "non attribué", "non assegnato", "sin asignar"):
        for value in serials:
            fixtures.append((cue, value, "IBAN"))
        for value in ("+49 (0)30 639 1827", "+33\n1 63 91 82 74 ext. 36", "QXT / RP / 6391827"):
            fixtures.append((cue, value, "TELEPHONENUM" if value.startswith("+") else "PERSONALREF"))
    for cue in ("Manufacturing date", "Maintenance date", "Herstelldatum", "Wartungskalender",
                "Date de fabrication", "Fecha de fabricación", "Calendrier public d'entretien",
                "Data di manutenzione", "Fecha de mantenimiento", "fabrication"):
        for value in ("23.09.2038", "2038-09-23"):
            fixtures.append((cue, value, "TELEPHONENUM"))
    clean_rejected, personal_rejected, checked = 0, 0, 0
    for cue, value, label in fixtures:
        clean = cue + ": " + value + "; end."
        personal = "my personal record — " + clean
        for source in ("regex", "structured", "mbert"):
            for status in ("valid", "invalid", "unknown"):
                candidate = _candidate(clean, value, label, source=source, validation=status)
                # An overlapping checksum-valid structured proposal is not ownership.
                other = _candidate(clean, value, label, source="structured", validation="valid")
                result = _decision(clean, candidate, [candidate, other])
                clean_rejected += result[0] == "reject"
                linked = _candidate(personal, value, label, source=source, validation=status)
                personal_rejected += _decision(personal, linked)[0] == "reject"
                checked += 1
                if result[0] != "reject" or _decision(personal, linked)[0] == "reject":
                    raise ValueError("round3_contrast_failed")
        # Every strict fragment is bound to its complete independently cued value.
        if value.startswith("+"):
            fragment = value[1:]
            if _decision(clean, _candidate(clean, fragment, label, source="mbert"))[0] != "reject":
                raise ValueError("round3_plus_fragment_failed")
    # Explicit personal fields, names and protected evidence still win.
    value = serials[0]
    for owner in ("IBAN:", "Telephone:", "Telefon:", "Téléphone:", "Telefono:", "Teléfono:",
                  "patient", "Kunde", "mon compte", "mio documento", "mi registro", "born"):
        text = owner + " Product serial: " + value + "; end."
        if _decision(text, _candidate(text, value, "IBAN"))[0] == "reject":
            raise ValueError("round3_personal_field_failed")
    clean = "Product serial: " + value + "; end."
    for changes in ({"protected": True}, {"protected": None}, {"context": "personal"},
                    {"source": "coverage"}, {"stage": "coverage"}):
        if _decision(clean, _candidate(clean, value, "IBAN", **changes))[0] == "reject":
            raise ValueError("round3_protection_failed")
    candidate = _candidate(clean, value, "IBAN")
    protected = _candidate(clean, value[-2:], "ACCOUNTNUM", protected=True)
    if _decision(clean, candidate, [candidate, protected])[0] == "reject":
        raise ValueError("round3_overlap_failed")
    named = "Nora Velkin — " + clean
    if _decision(named, _candidate(named, value, "IBAN"),
                 [_candidate(named, value, "IBAN"), _candidate(named, "Nora Velkin", "PERSONNAME")])[0] == "reject":
        raise ValueError("round3_name_failed")
    for status in ("invalid", "unknown"):
        if _decision(value, _candidate(value, value, "IBAN", validation=status))[0] != "accept":
            raise ValueError("round3_validation_not_clean_failed")
    # Neither over-wide candidates nor cross-field/newline evidence is clean.
    for text, part in ((clean, "Product serial: " + value),
                       ("Product serial; IBAN: " + value, value),
                       ("Product serial\nIBAN: " + value, value),
                       ("Order code: +49\n\n30 639 1827", "+49\n\n30 639 1827")):
        if _decision(text, _candidate(text, part, "IBAN"))[0] == "reject":
            raise ValueError("round3_narrow_scope_failed")
    print(f"round3_clean_rejected={clean_rejected}/{checked}")
    print(f"round3_personal_rejected={personal_rejected}")
    print(f"round3_contrastive_pairs={len(fixtures)}")
    if len(fixtures) < 30 or clean_rejected != checked or personal_rejected:
        raise ValueError("round3_context_failed")


def _round4():
    from scripts.checks.check_structured import group, iban
    fixtures = []
    serial = group(iban('IT', 'H' + '6842751382' + '751382684275'), (4,), ' ')
    # Homographic surface words do not become ownership without grammar.
    languages = (
        ('Il controllo verifica il pezzo, né copia né assegnazione; ', 'seriale prodotto', 'mio documento'),
        ('Los resultados son estables; ', 'Product serial', 'mi documento'),
        ('Le catalogue classe le lot; ', 'série produit', 'mon dossier'),
    )
    for prose, key, owner in languages:
        for value, label in ((serial, 'IBAN'), ('+39 06 6842 7513', 'TELEPHONENUM'),
                              ('+99 (0) 684 275 1382', 'TELEPHONENUM')):
            for suffix in ('', ' no.', ' code'):
                clean = prose + key + suffix + ': ' + value + '; end.'
                personal = prose + owner + ' — ' + key + suffix + ': ' + value + '; end.'
                fixtures.append((clean, personal, value, label))
    for key, owner in (('SKU', 'my record'), ('Lote', 'mi registro'),
                        ('Seriennummer', 'mein Dokument'), ('Stock', 'mon dossier'),
                        ('Inventario', 'mio documento')):
        for value in ('+1 202 684 2751', '202-684-2751', '+99 684 275 1382'):
            clean = key + ': ' + value + '; end.'
            fixtures.append((clean, owner + ' — ' + clean, value, 'TELEPHONENUM'))
    for roles, contact in ((('Part', 'Quantity', 'Price'), 'Phone'),
                           (('Artikel', 'Menge', 'Preis'), 'Telefon'),
                           (('Pièce', 'Quantité', 'Prix'), 'Téléphone'),
                           (('Articolo', 'Quantità', 'Prezzo'), 'Telefono'),
                           (('Pieza', 'Cantidad', 'Precio'), 'Teléfono')):
        for delimiter in (' | ', '\t', ' / '):
            value = '+99 684 275 1382'
            clean = delimiter.join(roles) + '\n' + delimiter.join(('RVT', value, '7.25'))
            personal = delimiter.join((roles[0], contact, roles[2])) + '\n' + delimiter.join(('RVT', value, '7.25'))
            fixtures.append((clean, personal, value, 'TELEPHONENUM'))
    rejected = personal_rejected = 0
    for clean, personal, value, label in fixtures:
        cand = _candidate(clean, value, label, source='structured', validation='valid')
        action = _decision(clean, cand)[0]
        linked = _candidate(personal, value, label, source='structured', validation='valid')
        # An inherited explicit contact header supplies personal context even
        # when the invalid numeric shape is not independent lexical ownership.
        if '\n' in personal:
            linked['context'] = 'personal'
        rejected += action == 'reject'
        personal_rejected += _decision(personal, linked)[0] == 'reject'
    # Preserve authentic French subject/possessive/birth constructions despite
    # an operational field in the same clause; neither checksum nor shape wins.
    for owner in ('il communique', 'elle utilise', 'son téléphone', 'sa date de naissance',
                  'né le 24/07/1983', 'née à Velora', 'né en Suisse'):
        text = owner + ' — série produit: ' + serial + '; end.'
        if _decision(text, _candidate(text, serial, 'IBAN'))[0] == 'reject':
            raise ValueError('round4_french_ownership_failed')
    # Headers do not leak ownership into adjacent numeric stock/price cells.
    text = 'Phone | Quantity | Price\n+1 202 684 2751 | 2026842751 | 6842751382'
    for value in ('2026842751', '6842751382'):
        if _decision(text, _candidate(text, value, 'TELEPHONENUM'))[0] != 'reject':
            raise ValueError('round4_table_cell_scope_failed')
    print(f'round4_clean_rejected={rejected}/{len(fixtures)}')
    print(f'round4_personal_rejected={personal_rejected}')
    print(f'round4_contrastive_pairs={len(fixtures)}')
    if len(fixtures) < 40 or rejected != len(fixtures) or personal_rejected:
        raise ValueError('round4_context_failed')


def main():
    fixtures = list(_fixtures())
    clean_rejected = personal_rejected = 0
    for clean, personal, value, label in fixtures:
        clean_result = _decision(clean, _candidate(clean, value, label))
        personal_result = _decision(personal, _candidate(personal, value, label))
        clean_rejected += clean_result[0] == "reject"
        personal_rejected += personal_result[0] == "reject"
        if personal_result[0] != "unresolved":
            raise ValueError("matched_personal_conflict_failed")
    _invariants()
    total = len(fixtures)
    print(f"clean_rejected={clean_rejected}/{total}")
    print(f"personal_rejected={personal_rejected}")
    print(f"personal_checked={total}")
    if total < 50 or clean_rejected * 5 < total * 4 or personal_rejected:
        raise ValueError("context_acceptance_failed")
    _round3()
    _round4()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("context_check_failed", file=sys.stderr)
        sys.exit(1)
