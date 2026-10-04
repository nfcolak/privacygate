#!/usr/bin/env python3
"""Independent synthetic blind v7. No model, predecessor generator or network use."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/augmentation/masking-stress-v7.jsonl"
MANIFEST = ROOT / "artifacts/masking-stress-v7/manifest.json"
POLICY = ROOT / "configs/privacy-policy-v1.json"
SEED = 731904627
LANGUAGES = ("en", "de", "fr", "it", "es")
LABELS = ("PERSONNAME", "ADDRESS", "EMAIL", "USERNAME", "TELEPHONENUM", "IBAN",
          "ACCOUNTNUM", "CREDITCARDNUMBER", "PASSPORTNUM", "IDCARDNUM",
          "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "PERSONALREF", "DATEOFBIRTH", "AGE")
SCHEMA = {"case_id", "family", "gold", "language", "split", "text"}
SPAN_SCHEMA = {"start", "end", "label"}
CUSTODY = "measure once per profile+model; never tune on v7"
RESERVED = {
    "v7_registration_panels": "form-style key/value records",
    "v7_helpdesk_turns": "chat/messaging lines",
    "v7_signoff_tiles": "email signature blocks",
    "v7_translation_enclosures": "mixed-language documents",
    "v7_damaged_carbon_copies": "OCR-like noise inside values",
}
CLEAN_COUNTS = {"v7_unassigned_shapes": 80, "v7_material_ledgers": 70,
                "v7_laboratory_equations": 70, "v7_public_manuals": 80}
# Invented syllables and fictional routing vocabulary, authored only for v7.
GIVEN = ("Velmira", "Osnelo", "Quenali", "Ruvesso", "Talvini", "Zelmora", "Pevrilo", "Nuvessa")
SURNAMES = ("Drelvane", "Qostelli", "Vensarou", "Belquino", "Trumavel", "Zorpendi", "Kelvossa", "Nestravo")
STREETS = ("Violet Gear Lane", "Kupferfalterweg", "allée des Lentilles Bleues",
           "via delle Ruote Viola", "calle del Engranaje Azul")
TOWNS = ("Quorhaven", "Feldquorin", "Valquorine", "Quoravalle", "Quorabella")
TITLES = ("Dr.", "Herr", "Mme", "Sig.ra", "Sr.")
PARTICLES = ("van", "von", "de", "di", "del")
MONTHS = ("October", "Oktober", "octobre", "ottobre", "octubre")
AGE_WORDS = ("forty-seven", "siebenundvierzig", "quarante-sept", "quarantasette", "cuarenta y siete")
AGE_UNITS = ("years", "Jahre", "ans", "anni", "años")
CUES = {
    "en": ("Full name", "Postal destination", "Telephone", "Birth date", "Age", "User handle", "Email"),
    "de": ("Vollständiger Name", "Postanschrift", "Telefon", "Geburtsdatum", "Alter", "Benutzername", "E-Mail"),
    "fr": ("Nom complet", "Adresse postale", "Téléphone", "Date de naissance", "Âge", "Identifiant", "Courriel"),
    "it": ("Nome completo", "Recapito postale", "Telefono", "Data di nascita", "Età", "Nome utente", "Email"),
    "es": ("Nombre completo", "Dirección postal", "Teléfono", "Fecha de nacimiento", "Edad", "Usuario", "Correo"),
}
ID_CUES = {
    "en": ("Passport", "Identity card", "Driving licence", "Tax identifier", "Social insurance", "Patient reference"),
    "de": ("Reisepass", "Personalausweis", "Führerschein", "Steuerkennung", "Sozialversicherung", "Patientenreferenz"),
    "fr": ("Passeport", "Carte d'identité", "Permis de conduire", "Identifiant fiscal", "Sécurité sociale", "Référence patient"),
    "it": ("Passaporto", "Carta d'identità", "Patente", "Codice fiscale", "Previdenza sociale", "Riferimento paziente"),
    "es": ("Pasaporte", "Documento de identidad", "Permiso de conducir", "Identificador fiscal", "Seguridad social", "Referencia paciente"),
}
FIN_CUES = {
    "en": ("Personal IBAN", "Personal account", "Payment card"),
    "de": ("Private IBAN", "Privates Konto", "Zahlungskarte"),
    "fr": ("IBAN personnel", "Compte personnel", "Carte de paiement"),
    "it": ("IBAN personale", "Conto personale", "Carta di pagamento"),
    "es": ("IBAN personal", "Cuenta personal", "Tarjeta de pago"),
}


class ValidationError(Exception):
    pass


def require(condition, code):
    if not condition:
        raise ValidationError(code)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Composer:
    """Offsets arise from explicit typed insertions, never substring searching."""
    def __init__(self):
        self.parts, self.gold, self.formats = [], [], Counter()
        self.length = 0

    def literal(self, text):
        self.parts.append(text)
        self.length += len(text)

    def value(self, label, value, form):
        start = self.length
        self.literal(value)
        self.gold.append({"start": start, "end": self.length, "label": label})
        self.formats[label + "/" + form] += 1

    def field(self, cue, label, value, form, ending="\n"):
        self.literal(cue + ": ")
        self.value(label, value, form)
        self.literal(ending)


def grouped(digits, sizes, separator):
    pieces, offset = [], 0
    for size in sizes:
        pieces.append(digits[offset:offset + size])
        offset += size
    if offset < len(digits):
        pieces.append(digits[offset:])
    return separator.join(pieces)


def iban(country, bban):
    # Valid mod-97 check digits without connecting a synthetic account to a bank.
    expanded = "".join(str(ord(c) - 55) if c.isalpha() else c for c in bban + country + "00")
    return country + str(98 - int(expanded) % 97).zfill(2) + bban


def card(digits):
    total = 0
    for index, value in enumerate(reversed(digits)):
        digit = int(value) * (2 if index % 2 == 0 else 1)
        total += digit // 10 + digit % 10
    return digits + str((-total) % 10)


def values(rng, language, index):
    li = LANGUAGES.index(language)
    given = GIVEN[(index + li * 3) % len(GIVEN)]
    last = SURNAMES[(index * 3 + li) % len(SURNAMES)]
    other = SURNAMES[(index * 3 + li + 1) % len(SURNAMES)]
    names = ((given + " " + last, "plain_full"),
             (TITLES[li] + " " + given + " " + last, "titled_person"),
             (given[0] + ". " + last, "initial_surname"),
             (given + "-" + GIVEN[(index + 1) % 8] + " " + last + "-" + other, "double_hyphen"),
             (given + " " + PARTICLES[li] + " " + last, "particle_person"),
             ((given + " " + last).upper(), "capital_person"),
             (last + ", " + given, "surname_first"),
             (TITLES[li] + " " + given[0] + ". " + PARTICLES[li] + " " + last, "title_initial_particle"))
    number = str(17 + index * 3)
    postcode = str(73000 + li * 300 + index)
    street, town = STREETS[li], TOWNS[li]
    address_base = street + " " + number
    country = ("Fictional North Isles", "Fiktive Nordinseln", "Îles du Nord fictives", "Isole Nord fittizie", "Islas Norte ficticias")[li]
    layouts = ((address_base + ", " + postcode + " " + town, "routing_inline"),
               (address_base + "\n" + postcode + " " + town + "\n" + country, "routing_three_lines"),
               ("PO Box " + number + ", " + postcode + " " + town, "routing_postbox"),
               ("c/o " + given + " " + last + "\n" + address_base + "\n" + postcode + " " + town, "routing_careof"),
               ("Building Quor-C, floor 4, unit " + number + "; " + address_base + "; " + postcode + " " + town, "routing_building_floor"),
               (number + " " + street + ", flat B7, " + town + " " + postcode + ", " + country, "routing_number_first"))
    d = "".join(str(rng.randrange(10)) for _ in range(22))
    # National and international fictional phone shapes; no real contact lookup.
    phones = (("+44 (0)1632 960 " + d[:3] + " ext. " + d[3:6], "dial_trunk_extension"),
              ("+49 030/" + d[:7], "dial_country_slash"),
              ("+33 (0)1 " + grouped(d[:8], (2, 2, 2, 2), " "), "dial_pair_groups"),
              ("+39 06 " + d[:4] + " " + d[4:8] + " interno " + d[8:10], "dial_italian_extension"),
              ("+34 " + grouped(d[:9], (3, 3, 3), "-"), "dial_hyphen_groups"),
              ("(202) 555-01" + d[:2], "dial_parenthesized_area"))
    age_number = 47 if index % 2 else 31 + index % 39
    birth_year = str(2026 - age_number - 1)  # October birthdays, as of 2026-10-04.
    dates = ((birth_year + "-10-" + str(11 + index % 15), "birth_iso"),
             (str(11 + index % 15) + ".10." + birth_year, "birth_dotted"),
             ("10/" + str(11 + index % 15) + "/" + birth_year, "birth_month_first"),
             (str(11 + index % 15) + " " + MONTHS[li] + " " + birth_year, "birth_spelled_month"),
             (MONTHS[li] + " " + str(11 + index % 15) + ", " + birth_year, "birth_month_leading"))
    result = {"PERSONNAME": names[index % len(names)], "ADDRESS": layouts[index % len(layouts)],
              "TELEPHONENUM": phones[index % len(phones)], "DATEOFBIRTH": dates[index % len(dates)],
              "AGE": ((AGE_WORDS[li] if index % 2 else str(31 + index % 39)) + " " + AGE_UNITS[li],
                      "age_word_unit" if index % 2 else "age_digit_unit"),
              "EMAIL": (given.lower() + "." + last.lower() + str(index) + "@quorpost.example", "mail_dot_person"),
              "USERNAME": ("@" + given.lower() + "_" + str(index) + ".qx", "handle_sigil_dot")}
    separators = (" ", "-", "/", ".", "")
    sep = separators[index % len(separators)]
    countries = ("GB", "DE", "FR", "IT", "ES")
    bbans = ("QVOR" + d[:14], d[:18], d + "7", "Q" + d, d[:20])
    result["IBAN"] = (grouped(iban(countries[li], bbans[li]), (4, 4, 4, 4, 4), sep),
                      "iban_" + ("spaced", "hyphens", "slashes", "dots", "solid")[index % 5])
    result["ACCOUNTNUM"] = (grouped(d[:12], (3, 5, 4), sep), "account_segment_" + str(index % 5))
    prefixes = ("4917", "5358", "3739", "6011", "4532")
    size = 10 if index % 5 == 2 else 11
    cc = card(prefixes[index % 5] + d[:size])
    result["CREDITCARDNUMBER"] = (grouped(cc, (4, 6, 5) if len(cc) == 15 else (4, 4, 4, 4), sep),
                                  "card_segment_" + str(index % 5))
    for label, prefix, length in (("PASSPORTNUM", "QZ", 7), ("IDCARDNUM", "NX", 9),
                                  ("DRIVERLICENSENUM", "QV", 12), ("TAXNUM", "TX", 11),
                                  ("SOCIALNUM", "SN", 10), ("PERSONALREF", "PAT", 8)):
        value = prefix + sep + grouped(d[:length], (3, 3), sep)
        if index % 5 == 1:
            value = grouped(d[:length], (3, 3), " ")
        elif index % 5 == 3:
            value = d[:4] + "-" + prefix + "-" + d[4:length]
        result[label] = (value, "credential_segment_" + str(index % 5))
    if index % 5 == 2:
        result["SOCIALNUM"] = (grouped(d[:9], (3, 2, 4), "-"), "social_three_two_four")
        result["TAXNUM"] = ("QV" + d[:4] + "R" + d[4:6] + "T" + d[6:8] + "Q" + d[8:11] + "X", "tax_alphanumeric_record")
    return result


INTRO = (
    "The following private details belong to the applicant, not to an organization.",
    "Die folgenden privaten Angaben gehören zur antragstellenden Person, nicht zu einer Organisation.",
    "Les renseignements privés suivants concernent la personne inscrite, et non une organisation.",
    "I seguenti dati privati riguardano la persona iscritta, non un'organizzazione.",
    "Los siguientes datos privados pertenecen a la persona inscrita, no a una organización.",
)
LETTERS = (
    ("Dear review team,", "I am sending my own contact details for the private registration.",
     "The workshop has replaced the old sorting tray with a reversible insert. The assembly instructions describe only objects; the revised insert fits the shallow compartment and can be removed without a tool.",
     "Please use the personal details below for this registration only.", "With thanks,"),
    ("Sehr geehrtes Prüfungsteam,", "Ich übermittle meine eigenen Kontaktdaten für die private Anmeldung.",
     "Die Werkstatt hat die alte Sortierschale durch einen umkehrbaren Einsatz ersetzt. Die Montageanleitung betrifft nur Gegenstände; der neue Einsatz passt in das flache Fach und lässt sich ohne Werkzeug herausnehmen.",
     "Bitte verwenden Sie meine folgenden persönlichen Angaben nur für diese Anmeldung.", "Mit freundlichen Grüßen,"),
    ("Bonjour à l'équipe de contrôle,", "Je transmets mes propres coordonnées pour cette inscription privée.",
     "L'atelier a remplacé le plateau de tri par une pièce réversible. Les instructions de montage concernent uniquement des objets; la nouvelle pièce tient dans le compartiment peu profond et se retire sans outil.",
     "Veuillez utiliser mes renseignements personnels ci-dessous pour cette inscription seulement.", "Avec mes remerciements,"),
    ("Gentile gruppo di revisione,", "Invio i miei recapiti personali per questa iscrizione privata.",
     "Il laboratorio ha sostituito il vecchio vassoio con un inserto reversibile. Le istruzioni di montaggio riguardano soltanto oggetti; il nuovo inserto entra nel vano poco profondo e si rimuove senza attrezzi.",
     "Utilizzate i seguenti dati personali soltanto per questa iscrizione.", "Con ringraziamenti,"),
    ("Estimado equipo de revisión,", "Envío mis propios datos de contacto para esta inscripción privada.",
     "El taller ha sustituido la bandeja de clasificación por una pieza reversible. Las instrucciones de montaje describen únicamente objetos; la pieza nueva cabe en el compartimento poco profundo y se retira sin herramientas.",
     "Utilicen los siguientes datos personales solo para esta inscripción.", "Con agradecimiento,"),
)


def emit_fields(c, cues, labels, vals, ending="\n"):
    for cue, label in zip(cues, labels):
        c.field(cue, label, *vals[label], ending=ending)


def positive(rng, language, index):
    li = LANGUAGES.index(language)
    cues, vals, c = CUES[language], values(rng, language, index), Composer()
    c.literal(INTRO[li] + "\n")
    if index < 6:
        family = "v7_private_contact_stanzas"
        c.literal(("Reach this applicant at", "Diese Person erreichen Sie unter", "Joindre cette personne à",
                   "Contattare questa persona a", "Contactar con esta persona en")[li] + ":\n")
        for label in ("PERSONNAME", "ADDRESS", "TELEPHONENUM"):
            c.value(label, *vals[label])
            c.literal("\n")
    elif index < 8:
        family = "v7_workshop_appeal_letters"
        salutation, intro, paragraph, request, closing = LETTERS[li]
        c.literal(salutation + "\n\n" + intro + "\n")
        c.field(cues[0], "PERSONNAME", *vals["PERSONNAME"])
        for turn in range(24):
            c.literal("\n" + paragraph + "\n")
            if turn == 8:
                c.literal(request + "\n")
                emit_fields(c, cues[1:3], ("ADDRESS", "TELEPHONENUM"), vals)
            if turn == 17:
                emit_fields(c, cues[3:5], ("DATEOFBIRTH", "AGE"), vals)
        c.literal("\n" + closing + "\n")
        c.value("PERSONNAME", *vals["PERSONNAME"])
        c.literal("\n")
        emit_fields(c, cues[5:7], ("USERNAME", "EMAIL"), vals)
    elif index < 13:
        family = "v7_personal_document_envelopes"
        c.field(cues[0], "PERSONNAME", *vals["PERSONNAME"])
        emit_fields(c, ID_CUES[language], LABELS[8:14], vals, ending=" ; ")
    elif index < 18:
        family = "v7_private_payment_authorizations"
        c.field(cues[0], "PERSONNAME", *vals["PERSONNAME"])
        emit_fields(c, FIN_CUES[language], ("IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER"), vals)
    elif index < 23:
        family = "v7_birth_attestation_fragments"
        emit_fields(c, (cues[0], cues[3], cues[4]), ("PERSONNAME", "DATEOFBIRTH", "AGE"), vals)
    elif index == 23:
        family = "v7_personal_portal_invitations"
        emit_fields(c, (cues[0], cues[5], cues[6]), ("PERSONNAME", "USERNAME", "EMAIL"), vals)
    elif index < 32:
        family = "v7_registration_panels"
        c.literal("╔══════════════════╗\n")
        emit_fields(c, cues, ("PERSONNAME", "ADDRESS", "TELEPHONENUM", "DATEOFBIRTH", "AGE", "USERNAME", "EMAIL"), vals,
                    ending="\n├──────────────────┤\n")
        emit_fields(c, ID_CUES[language][-1:], ("PERSONALREF",), vals)
        c.literal("╚══════════════════╝\n")
    elif index < 39:
        family = "v7_helpdesk_turns"
        prompt = ("Please identify yourself for this private request.", "Bitte identifizieren Sie sich für diese private Anfrage.",
                  "Identifiez-vous pour cette demande privée.", "Identificati per questa richiesta privata.",
                  "Identifíquese para esta solicitud privada.")[li]
        c.literal("[09:12] support> " + prompt + "\n[09:13] ")
        c.value("USERNAME", *vals["USERNAME"])
        c.literal("> ")
        c.value("PERSONNAME", *vals["PERSONNAME"])
        c.literal("\n[09:14] ")
        c.value("USERNAME", *vals["USERNAME"])
        c.literal("> ")
        emit_fields(c, (cues[2], cues[3], cues[4], cues[6]), ("TELEPHONENUM", "DATEOFBIRTH", "AGE", "EMAIL"), vals, ending=" | ")
    elif index < 46:
        family = "v7_signoff_tiles"
        c.literal(("Regards,", "Viele Grüße,", "Bien cordialement,", "Cordiali saluti,", "Saludos cordiales,")[li] + "\n--\n")
        for label in ("PERSONNAME", "ADDRESS", "TELEPHONENUM", "EMAIL", "USERNAME"):
            c.value(label, *vals[label])
            c.literal("\n")
    elif index < 53:
        family = "v7_translation_enclosures"
        foreign = LANGUAGES[(li + 2) % len(LANGUAGES)]
        foreign_values = values(rng, foreign, index + 7)
        c.literal(("Private translated enclosure", "Private übersetzte Anlage", "Annexe privée traduite",
                   "Allegato privato tradotto", "Anexo privado traducido")[li] + "\n")
        emit_fields(c, CUES[foreign], ("PERSONNAME", "ADDRESS", "TELEPHONENUM", "DATEOFBIRTH", "AGE", "USERNAME", "EMAIL"), foreign_values)
        emit_fields(c, FIN_CUES[language], ("IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER"), vals)
    else:
        family = "v7_damaged_carbon_copies"
        c.literal(("Transcribed personal record", "Abgeschriebener Personeneintrag", "Fiche personnelle transcrite",
                   "Scheda personale trascritta", "Registro personal transcrito")[li] + " [scan ░▒]\n")
        noisy = dict(vals)
        noisy["PERSONNAME"] = (vals["PERSONNAME"][0].replace(" ", "", 1), "carbon_missing_gap")
        for label in ("EMAIL", "USERNAME", "IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER",
                      "PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "PERSONALREF", "TELEPHONENUM"):
            value = vals[label][0]
            middle = len(value) // 2
            noisy[label] = (value[:middle] + "\n" + value[middle:], "carbon_linefracture")
        emit_fields(c, cues[:3] + cues[5:7], ("PERSONNAME", "ADDRESS", "TELEPHONENUM", "USERNAME", "EMAIL"), noisy)
        emit_fields(c, ID_CUES[language], LABELS[8:14], noisy)
        emit_fields(c, FIN_CUES[language], ("IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER"), noisy)
    return family, c


CLEAN_HEAD = (
    ("Object labels only; no person, account or delivery record.", "Warehouse grid: objects and prices only.",
     "Laboratory note: non-human materials and measurements.", "Public equipment manual; no personal details."),
    ("Nur Objektkennungen; keine Person, kein Konto und keine Lieferanschrift.", "Lagerliste: nur Gegenstände und Preise.",
     "Labornotiz: nichtmenschliche Materialien und Messungen.", "Öffentliche Geräteanleitung ohne persönliche Angaben."),
    ("Étiquettes d'objets seulement; aucune personne, aucun compte ni adresse de livraison.", "Grille de stock: objets et prix seulement.",
     "Note de laboratoire: matériaux non humains et mesures.", "Manuel public d'équipement sans renseignements personnels."),
    ("Solo etichette di oggetti; nessuna persona, conto o indirizzo di consegna.", "Tabella di magazzino: solo oggetti e prezzi.",
     "Nota di laboratorio: materiali non umani e misure.", "Manuale pubblico di apparecchi senza dati personali."),
    ("Solo etiquetas de objetos; ninguna persona, cuenta o dirección de entrega.", "Cuadrícula de almacén: solo objetos y precios.",
     "Nota de laboratorio: materiales no humanos y mediciones.", "Manual público de equipos sin datos personales."),
)
MANUAL = (
    ("Rotate the empty tray before inserting the guide.", "The indicator turns violet when the hatch is closed.",
     "A diagram marks the public paths around the reservoir.", "The timetable lists opening hours for the exhibition.",
     "The filter can be rinsed with plain water.", "A spare spring is stored beneath the removable cover.",
     "The assembly has no remote communication module.", "All demonstration parts are marked as non-sale samples."),
    ("Drehen Sie die leere Schale vor dem Einsetzen der Führung.", "Die Anzeige wird violett, sobald die Klappe geschlossen ist.",
     "Ein Plan zeigt die öffentlichen Wege am Speicherbecken.", "Der Zeitplan nennt die Öffnungszeiten der Ausstellung.",
     "Der Filter lässt sich mit klarem Wasser spülen.", "Eine Ersatzfeder liegt unter der abnehmbaren Abdeckung.",
     "Die Baugruppe besitzt kein Fernkommunikationsmodul.", "Alle Vorführteile sind als unverkäufliche Muster gekennzeichnet."),
    ("Tournez le plateau vide avant de placer le guide.", "Le voyant devient violet lorsque la trappe est fermée.",
     "Un schéma indique les chemins publics autour du réservoir.", "Le calendrier indique les horaires de l'exposition.",
     "Le filtre peut être rincé à l'eau claire.", "Un ressort de rechange est rangé sous le couvercle amovible.",
     "L'assemblage ne comporte aucun module de communication distante.", "Les pièces de démonstration sont marquées comme échantillons hors vente."),
    ("Ruotare il vassoio vuoto prima di inserire la guida.", "La spia diventa viola quando lo sportello è chiuso.",
     "Un diagramma indica i sentieri pubblici intorno al bacino.", "Il calendario elenca gli orari di apertura della mostra.",
     "Il filtro si può risciacquare con acqua pulita.", "Una molla di ricambio è conservata sotto il coperchio rimovibile.",
     "L'insieme non contiene moduli di comunicazione remota.", "Tutti i pezzi dimostrativi sono campioni non destinati alla vendita."),
    ("Gire la bandeja vacía antes de insertar la guía.", "El indicador se vuelve violeta cuando la compuerta está cerrada.",
     "Un diagrama señala los caminos públicos alrededor del depósito.", "El calendario enumera los horarios de la exposición.",
     "El filtro se puede enjuagar con agua limpia.", "Un resorte de repuesto está debajo de la cubierta desmontable.",
     "El conjunto no tiene módulo de comunicación remota.", "Todas las piezas de demostración son muestras no destinadas a la venta."),
)


def clean(rng, language, index):
    li, c = LANGUAGES.index(language), Composer()
    d = "".join(str(rng.randrange(10)) for _ in range(18))
    if index < 16:
        family = "v7_unassigned_shapes"
        c.literal(CLEAN_HEAD[li][0] + "\n")
        # An explicit non-person object context is part of each lookalike.
        shapes = (
            ("part/SKU", "QX-" + d[:9]), ("model", "NX " + d[:3] + "-" + d[3:9]),
            ("lot", grouped(d[:16], (4, 4, 4, 4), " ")),
            ("batch", grouped(d[:9], (3, 2, 4), "-")),
            ("firmware release", "19.10.1983"), ("version", "v47.11.2031"),
            ("casting mold", "(202) 555-01" + d[:2]),
            ("inspection lot", "QZ " + d[:3] + " / " + d[3:7]),
            ("circuit-board revision", "TX-" + d[:3] + "-" + d[3:11]),
            ("public park name", STREETS[li] + " Gardens"),
            ("retail business name", STREETS[li] + " Tool Shop"),
            ("public exhibition title", "VELMIRA QUOR GEARS"),
            ("product series", "PAT/" + d[:3] + "/" + d[3:8]),
            ("machine runtime", "47 " + AGE_UNITS[li]),
            ("polymer lot", "DE" + d[:2] + " " + grouped(d[:18], (4, 4, 4, 4), " ")),
            ("sensor part", "+34-" + d[:3] + "-" + d[3:6] + "-" + d[6:9]),
        )
        # Labels are technical object classes, not names of natural persons.
        cue, shape = shapes[index]
        c.literal("[" + cue + "] " + shape + "\n")
    elif index < 30:
        family = "v7_material_ledgers"
        c.literal(CLEAN_HEAD[li][1] + "\n")
        header = (("part | stock | unit price | width", "Teil | Bestand | Stückpreis | Breite",
                   "pièce | stock | prix unitaire | largeur", "pezzo | scorte | prezzo | larghezza",
                   "pieza | stock | precio | anchura")[li])
        c.literal(header + "\n" + "─" * 45 + "\n")
        for line in range(8):
            code = "QX" + str(index) + "/" + d[line:line + 6]
            c.literal(f"{code} | {rng.randrange(1, 900)} | {rng.randrange(2, 350)}.{rng.randrange(100):02d} EUR | {line + 11}.{index} mm\n")
        c.literal("Σ | " + str(index * 13) + " | — | —\n")
    elif index < 44:
        family = "v7_laboratory_equations"
        c.literal(CLEAN_HEAD[li][2] + "\n")
        formulas = (
            f"x = {index}.004 × 10^-6 mol/L; u(x) = 0.00017 mol/L; n = 512.",
            f"A = [[{index}, -3.7, 0], [11, {index + 5}, 2.4]]; det(B) = -64.25.",
            f"λ = {index * 11}.5 nm; f = 8.12e14 Hz; t = 0.003 s; ΔT = -21.7 K.",
            f"r = {index}.09 mm; h = 72.3 mm; V = πr²h; tolerance ±0.025 mm.",
            f"pH = 7.32; ρ = 1.071 g/cm³; concentration = {index}.002%; batch replicate n = 17.",
            f"log₂({index * 128}) = y; domain [0.001, 4.800]; residual = -3.25e-9.",
            f"T = -{index}.5 °C; P = 102.73 kPa; mass = 0.0042 kg; yield = 98.21%.",
        )
        c.literal(formulas[index % len(formulas)] + "\n")
        c.literal(f"Spectrum: [{index}.1, 0.003, -4.07, 2.91e-5]; object trial QX-{index}.\n")
    else:
        family = "v7_public_manuals"
        c.literal(CLEAN_HEAD[li][3] + "\n")
        c.literal(MANUAL[li][index % 8] + "\n" + MANUAL[li][(index + 3) % 8] + "\n")
        c.literal(("Panel", "Tafel", "Panneau", "Pannello", "Panel")[li] + " " + str(index - 40) + "; "
                  + ("revision", "Fassung", "révision", "revisione", "revisión")[li] + " 2026-03-17.\n")
    return family, c


def generate():
    rng, rows, formats = random.Random(SEED), [], Counter()
    for language in LANGUAGES:
        for kind, factory in (("p", positive), ("c", clean)):
            for index in range(60):
                family, composer = factory(rng, language, index)
                rows.append({"case_id": f"v7-{language}-{kind}-{index:03d}", "family": family,
                             "gold": composer.gold, "language": language, "split": "blind",
                             "text": "".join(composer.parts)})
                formats.update(composer.formats)
    rng.shuffle(rows)
    return rows, dict(sorted(formats.items()))


def data_bytes(rows):
    return ("\n".join(encoded(row) for row in rows) + "\n").encode("utf-8")


def validate(rows, formats):
    policy = json.loads(POLICY.read_bytes())
    require(policy["labels"] == list(LABELS) and set(policy["row_schema"]) == SCHEMA
            and set(policy["gold_span_schema"]) == SPAN_SCHEMA, "v7_policy_schema")
    require(len(rows) == 600, "v7_row_count")
    ids, texts = set(), set()
    languages, labels, families, clean_families = Counter(), Counter(), Counter(), Counter()
    language_cells = {lang: {"rows": 0, "positive_rows": 0, "clean_rows": 0,
                             "per_label": Counter(), "per_family": Counter()} for lang in LANGUAGES}
    positives = reserved = adjacent = letters = 0
    age_pattern = r"(?:[0-9]{1,3}|" + "|".join(re.escape(x) for x in AGE_WORDS) + r") (?:" + "|".join(AGE_UNITS) + r")"
    for row in rows:
        require(isinstance(row, dict) and set(row) == SCHEMA, "v7_row_schema")
        require(all(isinstance(row[key], str) and row[key] for key in SCHEMA - {"gold"}), "v7_row_types")
        require(row["language"] in LANGUAGES and row["split"] == "blind", "v7_blind_language")
        require(row["case_id"] not in ids and row["text"] not in texts, "v7_duplicate")
        require(re.fullmatch(r"v7-(en|de|fr|it|es)-[pc]-[0-9]{3}", row["case_id"]), "v7_case_id")
        require(isinstance(row["gold"], list), "v7_gold_type")
        ids.add(row["case_id"])
        texts.add(row["text"])
        text, previous = row["text"], 0
        for span in row["gold"]:
            require(isinstance(span, dict) and set(span) == SPAN_SCHEMA, "v7_span_schema")
            start, end, label = span["start"], span["end"], span["label"]
            require(type(start) is int and type(end) is int and type(label) is str, "v7_span_types")
            require(previous <= start < end <= len(text) and label in LABELS, "v7_span_bounds")
            value = text[start:end]
            require(value == value.strip() and any(char.isalnum() for char in value), "v7_whole_value")
            require(end == len(text) or not text[end].isalnum(), "v7_truncated_value")
            if label == "AGE":
                require(re.fullmatch(age_pattern, value), "v7_age_number_unit_only")
            if label == "USERNAME":
                require(value.startswith("@"), "v7_handle_sigil")
            if label == "ADDRESS":
                require(any(town in value for town in TOWNS), "v7_complete_routing_region")
            if label == "TELEPHONENUM" and "ext." in value:
                require(re.search(r"ext\. [0-9]+$", value), "v7_phone_extension")
            previous = end
            labels[label] += 1
            language_cells[row["language"]]["per_label"][label] += 1
        lang, family = row["language"], row["family"]
        languages[lang] += 1
        families[family] += 1
        cell = language_cells[lang]
        cell["rows"] += 1
        cell["per_family"][family] += 1
        positive_row = bool(row["gold"])
        require(("-p-" in row["case_id"]) == positive_row, "v7_positive_identity")
        cell["positive_rows" if positive_row else "clean_rows"] += 1
        positives += positive_row
        if not positive_row:
            clean_families[family] += 1
        if family in RESERVED:
            require(positive_row, "v7_reserved_linkage")
            reserved += 1
        if family == "v7_private_contact_stanzas":
            require([span["label"] for span in row["gold"]] == ["PERSONNAME", "ADDRESS", "TELEPHONENUM"], "v7_contact_triplet")
            require(all(text[a["end"]:b["start"]] == "\n" for a, b in zip(row["gold"], row["gold"][1:])), "v7_contact_adjacency")
            adjacent += 1
        if family == "v7_workshop_appeal_letters":
            require(len(text) >= 4500 and row["gold"][0]["start"] < 500
                    and row["gold"][-1]["end"] > len(text) - 250, "v7_long_letter_extent")
            letters += 1
    require(positives == 300 and len(rows) - positives == 300, "v7_balance")
    require(dict(languages) == {lang: 120 for lang in LANGUAGES}, "v7_language_balance")
    require(all(c["positive_rows"] == c["clean_rows"] == 60 for c in language_cells.values()), "v7_language_class_balance")
    require(set(labels) == set(LABELS) and min(labels.values()) >= 20, "v7_label_coverage")
    require(dict(clean_families) == CLEAN_COUNTS, "v7_clean_partition")
    require(reserved == 180 and adjacent == 30 and letters == 10, "v7_special_counts")
    require(set(RESERVED) <= set(families), "v7_reserved_coverage")
    required_formats = {
        "PERSONNAME": ("plain_full", "titled_person", "initial_surname", "double_hyphen", "particle_person", "capital_person", "surname_first", "title_initial_particle"),
        "ADDRESS": ("routing_inline", "routing_three_lines", "routing_postbox", "routing_careof", "routing_building_floor", "routing_number_first"),
        "DATEOFBIRTH": ("birth_iso", "birth_dotted", "birth_month_first", "birth_spelled_month", "birth_month_leading"),
        "AGE": ("age_word_unit", "age_digit_unit"),
    }
    require(all(formats.get(label + "/" + form, 0) > 0 for label, forms in required_formats.items() for form in forms), "v7_format_coverage")
    return {"rows": len(rows), "positive_rows": positives, "clean_rows": len(rows) - positives,
            "gold_spans": sum(labels.values()), "per_label": dict(sorted(labels.items())),
            "per_language": dict(sorted(languages.items())), "per_family": dict(sorted(families.items())),
            "language_details": language_cells, "clean_family_counts": dict(sorted(clean_families.items())),
            "reserved_rows": reserved, "reserved_fraction_all_rows": reserved / len(rows),
            "adjacent_contact_rows": adjacent, "long_letters": letters, "per_format_spans": formats}


def manifest_for(rows, formats):
    stats = validate(rows, formats)
    raw = data_bytes(rows)
    return {"version": "v7", "seed": SEED, "synthetic_only": True, "blind": True,
            "blind_status": "frozen_unmeasured", "split": "blind", "custody": CUSTODY,
            "dataset_path": str(DATA.relative_to(ROOT)), "sha256": digest(raw),
            "dataset_sha256": digest(raw), "generator": "scripts/make_masking_stress_v7.py",
            "generator_sha256": digest(Path(__file__).read_bytes()),
            "policy": "configs/privacy-policy-v1.json", "policy_version": "privacy-policy-v1",
            "policy_sha256": digest(POLICY.read_bytes()), "row_schema": sorted(SCHEMA),
            "gold_span_schema": sorted(SPAN_SCHEMA), "counts": stats,
            "reserved_family_mapping": RESERVED,
            "independence": {"predecessor_content_read": False, "model_outputs_read": False,
                             "training_content_read": False, "predecessor_family_format_names_only": True},
            "gold_rules": {"offsets": "half-open Python str indices", "whole_values": True,
                           "internal_separators_included": True, "age": "number or number words plus directly following unit; exclude cue",
                           "ordered_non_overlapping": True, "repeated_mentions": "separate spans",
                           "address": "one whole routing region, including c/o, floor and country"},
            "limitations": ["synthetic annotation-relative challenge, not a privacy or legal guarantee",
                            "shared grammars limit population inference; never tune on this blind set"]}


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "v7_duplicate_json_key")
        result[key] = value
    return result


def verify(dataset=DATA):
    """Read only own frozen set; regeneration checks every gold boundary and byte."""
    dataset = Path(dataset)
    require(dataset.resolve() == DATA.resolve(), "v7_dataset_path")
    require(dataset.is_file() and MANIFEST.is_file(), "v7_frozen_missing")
    raw = dataset.read_bytes()
    rows = [json.loads(line, object_pairs_hook=strict_object) for line in raw.decode("utf-8").splitlines()]
    expected_rows, formats = generate()
    validate(rows, formats)
    require(raw == data_bytes(expected_rows), "v7_bytes_or_gold_changed")
    manifest = json.loads(MANIFEST.read_bytes(), object_pairs_hook=strict_object)
    require(manifest == manifest_for(expected_rows, formats), "v7_manifest_binding_changed")
    require(MANIFEST.read_bytes() == (encoded(manifest) + "\n").encode(), "v7_manifest_bytes_changed")
    return rows, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            rows, manifest = verify()
        else:
            # Neither artifact can pre-exist; exclusive creation also defeats races.
            require(not DATA.exists() and not MANIFEST.exists(), "v7_refuses_overwrite")
            rows, formats = generate()
            manifest = manifest_for(rows, formats)
            DATA.parent.mkdir(parents=True, exist_ok=True)
            MANIFEST.parent.mkdir(parents=True, exist_ok=True)
            with DATA.open("xb") as stream:
                stream.write(data_bytes(rows))
            with MANIFEST.open("xb") as stream:
                stream.write((encoded(manifest) + "\n").encode())
            verify()
        print("v7 {} rows={} positive={} clean={} labels={} minimum_spans={} reserved={} adjacent={} long_letters={}".format(
            "VERIFIED" if args.verify else "FROZEN", len(rows), manifest["counts"]["positive_rows"],
            manifest["counts"]["clean_rows"], len(manifest["counts"]["per_label"]),
            min(manifest["counts"]["per_label"].values()), manifest["counts"]["reserved_rows"],
            manifest["counts"]["adjacent_contact_rows"], manifest["counts"]["long_letters"]))
        return 0
    except Exception as error:
        print(str(error) if isinstance(error, ValidationError) else "v7_failed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
