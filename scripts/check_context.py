"""One small offline check on invented contrastive strings; aggregates only."""
import copy
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from privacygate.context import decide


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
        "born", "geboren", "né", "nato", "nacido", "age: 28", "Alter: 28",
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


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("context_check_failed", file=sys.stderr)
        sys.exit(1)
