#!/usr/bin/env python3
"""Freeze independent synthetic blind v4; stdlib only, aggregate-only output.

The custodian read only the shared task/policy, v3 manifest and masking_metrics.py.
No detector, training generator/data, model, predictions or research is imported.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path("data/augmentation/masking-stress-v4.jsonl")
MANIFEST_PATH = Path("docs/masking-stress-v4/manifest.json")
GENERATOR_PATH = Path("scripts/make_masking_stress_v4.py")
VALIDATOR_PATH = Path("privacygate/masking_metrics.py")
SEED = 202610034817
LANGUAGES = ("en", "de", "fr", "it", "es")
LABELS = frozenset({
    "PERSONNAME", "ADDRESS", "EMAIL", "USERNAME", "TELEPHONENUM", "IBAN",
    "ACCOUNTNUM", "CREDITCARDNUMBER", "PASSPORTNUM", "IDCARDNUM",
    "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "PERSONALREF", "DATEOFBIRTH", "AGE",
})
RESERVED = frozenset({
    "form_records", "chat_lines", "signature_blocks", "mixed_language", "ocr_noise",
})
STANDARD = frozenset({
    "names", "full_address", "phone", "account", "identity", "personalref",
    "username", "biography", "long_text",
})
CLEAN = frozenset({
    "clean_near_miss_twins", "clean_calendar", "clean_dimensions", "clean_catalog",
    "clean_organisations", "clean_places", "clean_facilities", "clean_numeric",
})

# Fresh, authored pools. No comparison to prior source/data is claimed: the v3
# manifest describes categories, but does not expose its literals or templates.
GIVEN = {
    "en": ("Elowen", "Tavian", "Orlena", "Corvin", "Maelis", "Rovian"),
    "de": ("Alwina", "Tassilo", "Edeltra", "Volmar", "Fridolin", "Ottilie"),
    "fr": ("Soléane", "Amaury", "Liorine", "Noham", "Éliane", "Cléor"),
    "it": ("Altea", "Nerio", "Elviana", "Silvano", "Fiorella", "Terenzio"),
    "es": ("Ainara", "Beltrán", "Eliria", "Nereo", "Amalia", "Teodoro"),
}
SURNAMES = {
    "en": ("Fenwicke", "Briarcombe", "Doveshall", "Thornmere", "Wrenfall", "Hollowfen"),
    "de": ("Falkenried", "Silberwehn", "Eichenroth", "Wolkenstein", "Lindenbach", "Tannhof"),
    "fr": ("Brumeval", "Clairvigne", "Ormebois", "Rivefleur", "Sablereau", "Montelune"),
    "it": ("Valcereto", "Fontelago", "Roccavela", "Pratolume", "Montefiore", "Bellacosta"),
    "es": ("Valdelirio", "Montesenda", "Robleduna", "Luzcampo", "Villaronda", "Cerrobrisa"),
}
TITLES = {"en": "Dr.", "de": "Herr", "fr": "Mme", "it": "Sig.ra", "es": "Sr."}
PARTICLES = {
    "en": ("van", "von"), "de": ("von", "van"), "fr": ("du", "le", "la"),
    "it": ("di", "da", "del"), "es": ("de", "dos"),
}
STREETS = {
    "en": ("Amberquill Walk", "Willowglass Crescent", "Copperfern Lane", "Morrowleaf Rise"),
    "de": ("Bernsteinfarnweg", "Kupferauenstraße", "Silberquellgasse", "Morgenlauballee"),
    "fr": ("allée des Plumes Dorées", "rue des Saules Verts", "chemin du Cuivre", "impasse du Matin"),
    "it": ("via delle Felci Dorate", "viale del Salice Chiaro", "vicolo del Rame", "via delle Foglie"),
    "es": ("calle del Helecho Dorado", "avenida del Sauce Claro", "pasaje del Cobre", "calle del Alba"),
}
TOWNS = {"en": "Bristol", "de": "Potsdam", "fr": "Dijon", "it": "Parma", "es": "Burgos"}
COUNTRIES = {"en": "United Kingdom", "de": "Deutschland", "fr": "France", "it": "Italia", "es": "España"}
POSTCODES = {"en": "BS7 4QZ", "de": "14471", "fr": "21000", "it": "43121", "es": "09003"}
REGIONS = {"en": "Avon", "de": "Brandenburg", "fr": "Bourgogne", "it": "Emilia-Romagna", "es": "Castilla y León"}

# Each tuple contains translated field cues, salutations, narrative templates,
# signature cues, letter filler and non-personal contexts. Placeholders are
# assembled structurally, not found by substring search.
COPY = {
    "en": {
        "fields": ("Full name", "Home postal address", "Personal telephone", "Personal email", "My handle", "My bank IBAN", "My account", "My payment card", "My passport", "My identity card", "My driving licence", "My tax number", "My social security number", "My patient reference", "My date of birth", "My age"),
        "salutation": "Dear ", "name": "The person authorised to speak on my behalf is ",
        "address": "Please redirect my personal post to ", "phone": "For a private callback, dial ",
        "account": "For my own banking record, the ", "identity": "The identity document belonging to me has ",
        "reference": "The reference assigned to me personally is ", "online": "My private contact details are ",
        "bio": "For my personal biography: ", "birth": "I was born on ", "age": " and my age is ",
        "signature": "Private correspondence\n", "chat": ("visitor", "coordinator", "Please use my private details: "),
        "letter_open": "I am writing privately about the arrangement we discussed. ",
        "letter_close": "Thank you for keeping this correspondence in the personal file.",
        "filler": ("The proposed schedule remains provisional until the review of the available materials is complete. ", "A separate discussion will resolve the sequence of the work without changing the agreed scope. ", "This paragraph summarises the process, and no final approval is implied by the current draft. ", "The next revision should explain the alternatives in ordinary language and preserve the earlier rationale. "),
        "twins": ("An inventory product code, not an identifier of a person, is ", "The public exhibition opens on ", "The shipment contains "),
        "calendar": "The open-air exhibition runs from {date} at {time}; no individual booking is involved.",
        "dimensions": "The panel measures {a} × {b} × {c} mm; the carton holds {q} identical spacers.",
        "catalog": "Catalogue SKU QV-{code}; purchase order ORD-{order}; invoice INV-{invoice}, all for a stock replenishment without customer details.",
        "organisations": "The fictional brand {brand} and the organisation {org} publish technical specifications only.",
        "places": "The public guide describes {place} as a general visitor attraction, not anyone's home.",
        "facilities": "The unoccupied exhibition hall has room {room}, gate {gate} and storage rack {rack}.",
        "numeric": "The component costs EUR {price}; firmware version {version}; sample size {sample}; pass rate {rate}%.",
    },
    "de": {
        "fields": ("Vollständiger Name", "Private Postanschrift", "Meine Telefonnummer", "Private E-Mail", "Mein Benutzername", "Meine IBAN", "Meine Kontonummer", "Meine Kartennummer", "Mein Reisepass", "Mein Personalausweis", "Mein Führerschein", "Meine Steuernummer", "Meine Sozialversicherungsnummer", "Meine Patientennummer", "Mein Geburtsdatum", "Mein Alter"),
        "salutation": "Sehr geehrte ", "name": "Die von mir bevollmächtigte Person heißt ",
        "address": "Meine private Post bitte an folgende Anschrift umleiten: ", "phone": "Für einen privaten Rückruf wählen Sie ",
        "account": "In meiner persönlichen Bankakte lautet die Angabe ", "identity": "Das mir gehörende Identitätsdokument trägt ",
        "reference": "Die mir persönlich zugeordnete Referenz lautet ", "online": "Meine privaten Kontaktdaten sind ",
        "bio": "Für meine persönliche Biografie: ", "birth": "Ich wurde geboren am ", "age": " und mein Alter beträgt ",
        "signature": "Private Korrespondenz\n", "chat": ("besucher", "koordination", "Bitte meine privaten Angaben verwenden: "),
        "letter_open": "Ich schreibe Ihnen privat wegen der besprochenen Vereinbarung. ",
        "letter_close": "Bitte legen Sie diesen Brief in meiner persönlichen Akte ab.",
        "filler": ("Der vorgesehene Ablauf bleibt vorläufig, bis die Prüfung der verfügbaren Unterlagen abgeschlossen ist. ", "Eine gesonderte Besprechung klärt die Reihenfolge der Arbeit ohne Änderung des vereinbarten Umfangs. ", "Dieser Absatz erläutert das Verfahren und stellt noch keine endgültige Genehmigung dar. ", "Die nächste Fassung soll die Möglichkeiten verständlich erläutern und die bisherige Begründung erhalten. "),
        "twins": ("Ein Artikelcode im Warenlager, keine persönliche Kennung, lautet ", "Die öffentliche Ausstellung beginnt am ", "Die Lieferung enthält "),
        "calendar": "Die öffentliche Freiluftausstellung beginnt am {date} um {time}; es gibt keine personenbezogene Buchung.",
        "dimensions": "Die Platte misst {a} × {b} × {c} mm; im Karton liegen {q} gleiche Abstandhalter.",
        "catalog": "Katalog-SKU QV-{code}; Bestellung ORD-{order}; Rechnung INV-{invoice}, ausschließlich für Waren ohne Kundenangaben.",
        "organisations": "Die erfundene Marke {brand} und die Organisation {org} veröffentlichen nur technische Spezifikationen.",
        "places": "Der öffentliche Reiseführer beschreibt {place} als allgemeines Ausflugsziel, nicht als Wohnort.",
        "facilities": "Die unbesetzte Ausstellungshalle enthält Raum {room}, Tor {gate} und Lagerregal {rack}.",
        "numeric": "Das Bauteil kostet EUR {price}; Firmware-Version {version}; Stichprobe {sample}; Erfolgsquote {rate}%.",
    },
    "fr": {
        "fields": ("Nom complet", "Adresse postale privée", "Mon téléphone", "Courriel personnel", "Mon pseudonyme", "Mon IBAN", "Mon compte bancaire", "Ma carte bancaire", "Mon passeport", "Ma carte d’identité", "Mon permis de conduire", "Mon numéro fiscal", "Mon numéro de sécurité sociale", "Ma référence patient", "Ma date de naissance", "Mon âge"),
        "salutation": "Bonjour ", "name": "La personne que j'autorise à me représenter est ",
        "address": "Merci de réexpédier mon courrier personnel à ", "phone": "Pour me rappeler en privé, composez ",
        "account": "Pour mon dossier bancaire personnel, la mention est ", "identity": "Le document d'identité qui m'appartient porte ",
        "reference": "La référence qui m'est attribuée personnellement est ", "online": "Mes coordonnées privées sont ",
        "bio": "Pour ma biographie personnelle : ", "birth": "Ma naissance a eu lieu le ", "age": " et mon âge est ",
        "signature": "Correspondance privée\n", "chat": ("visiteur", "coordination", "Veuillez utiliser mes coordonnées privées : "),
        "letter_open": "Je vous écris à titre privé concernant notre arrangement. ",
        "letter_close": "Merci de conserver cette lettre dans mon dossier personnel.",
        "filler": ("Le calendrier proposé reste provisoire jusqu'à la fin de l'examen des documents disponibles. ", "Une discussion distincte fixera la succession des travaux sans modifier le périmètre convenu. ", "Ce paragraphe présente la procédure sans constituer une approbation définitive du projet actuel. ", "La prochaine version devra exposer les possibilités clairement et conserver la justification initiale. "),
        "twins": ("Un code article du stock, sans lien avec une personne, est ", "L'exposition publique ouvre le ", "La livraison contient "),
        "calendar": "L'exposition publique en plein air ouvre le {date} à {time}, sans réservation individuelle.",
        "dimensions": "Le panneau mesure {a} × {b} × {c} mm ; le carton contient {q} entretoises identiques.",
        "catalog": "SKU du catalogue QV-{code} ; commande ORD-{order} ; facture INV-{invoice}, pour le stock sans coordonnées de client.",
        "organisations": "La marque fictive {brand} et l'organisation {org} publient uniquement des spécifications techniques.",
        "places": "Le guide public décrit {place} comme un lieu de visite général, jamais comme un domicile.",
        "facilities": "Le hall d'exposition inoccupé possède la salle {room}, la porte {gate} et le rayonnage {rack}.",
        "numeric": "La pièce coûte EUR {price} ; version du micrologiciel {version} ; échantillon {sample} ; réussite {rate}%.",
    },
    "it": {
        "fields": ("Nome completo", "Indirizzo postale privato", "Mio telefono", "Email personale", "Mio nome utente", "Mio IBAN", "Mio conto bancario", "Mia carta di pagamento", "Mio passaporto", "Mia carta d’identità", "Mia patente", "Mio codice fiscale", "Mio numero previdenziale", "Mio riferimento paziente", "Mia data di nascita", "Mia età"),
        "salutation": "Gentile ", "name": "La persona autorizzata a rappresentarmi è ",
        "address": "La mia posta privata deve essere inoltrata a ", "phone": "Per richiamarmi privatamente, comporre ",
        "account": "Per il mio fascicolo bancario personale, il dato è ", "identity": "Il documento di identità che mi appartiene riporta ",
        "reference": "Il riferimento assegnato a me personalmente è ", "online": "I miei recapiti privati sono ",
        "bio": "Per la mia biografia personale: ", "birth": "La mia nascita risale al ", "age": " e la mia età è ",
        "signature": "Corrispondenza privata\n", "chat": ("visitatore", "coordinamento", "Usare i miei recapiti privati: "),
        "letter_open": "Scrivo privatamente riguardo all'accordo discusso. ",
        "letter_close": "Conservare questa lettera nel mio fascicolo personale.",
        "filler": ("Il programma proposto resta provvisorio fino al completamento della revisione dei materiali disponibili. ", "Una discussione separata chiarirà la sequenza dei lavori senza cambiare l'ambito concordato. ", "Questo paragrafo descrive la procedura e non costituisce un'approvazione definitiva della bozza. ", "La prossima revisione dovrebbe spiegare le alternative con chiarezza e mantenere la motivazione iniziale. "),
        "twins": ("Un codice articolo di magazzino, senza legame con una persona, è ", "La mostra pubblica apre il ", "La spedizione contiene "),
        "calendar": "La mostra pubblica all'aperto inizia il {date} alle {time}, senza prenotazioni individuali.",
        "dimensions": "Il pannello misura {a} × {b} × {c} mm; la scatola contiene {q} distanziatori identici.",
        "catalog": "SKU di catalogo QV-{code}; ordine ORD-{order}; fattura INV-{invoice}, per scorte senza dati del cliente.",
        "organisations": "Il marchio inventato {brand} e l'organizzazione {org} pubblicano solo specifiche tecniche.",
        "places": "La guida pubblica descrive {place} come attrazione generale, non come domicilio personale.",
        "facilities": "Il padiglione vuoto dispone della sala {room}, del cancello {gate} e dello scaffale {rack}.",
        "numeric": "Il componente costa EUR {price}; versione firmware {version}; campione {sample}; successo {rate}%.",
    },
    "es": {
        "fields": ("Nombre completo", "Dirección postal privada", "Mi teléfono", "Correo personal", "Mi usuario", "Mi IBAN", "Mi cuenta bancaria", "Mi tarjeta de pago", "Mi pasaporte", "Mi documento de identidad", "Mi permiso de conducir", "Mi número fiscal", "Mi número de seguridad social", "Mi referencia de paciente", "Mi fecha de nacimiento", "Mi edad"),
        "salutation": "Estimado ", "name": "La persona autorizada para representarme es ",
        "address": "Mi correspondencia privada debe remitirse a ", "phone": "Para devolverme una llamada privada, marque ",
        "account": "Para mi expediente bancario personal, el dato es ", "identity": "El documento de identidad que me pertenece lleva ",
        "reference": "La referencia asignada a mí personalmente es ", "online": "Mis datos de contacto privados son ",
        "bio": "Para mi biografía personal: ", "birth": "Mi nacimiento fue el ", "age": " y mi edad es ",
        "signature": "Correspondencia privada\n", "chat": ("visitante", "coordinación", "Utilice mis datos privados: "),
        "letter_open": "Le escribo de forma privada sobre el acuerdo comentado. ",
        "letter_close": "Conserve esta carta en mi expediente personal.",
        "filler": ("El calendario propuesto sigue siendo provisional hasta terminar la revisión de los materiales disponibles. ", "Una conversación aparte aclarará el orden de los trabajos sin cambiar el alcance acordado. ", "Este párrafo explica el procedimiento y no supone la aprobación definitiva del borrador actual. ", "La próxima revisión deberá explicar las alternativas con claridad y conservar la justificación inicial. "),
        "twins": ("Un código de artículo del almacén, sin vínculo con una persona, es ", "La exposición pública abre el ", "El envío contiene "),
        "calendar": "La exposición pública al aire libre abre el {date} a las {time}, sin reservas individuales.",
        "dimensions": "El panel mide {a} × {b} × {c} mm; la caja contiene {q} separadores idénticos.",
        "catalog": "SKU de catálogo QV-{code}; pedido ORD-{order}; factura INV-{invoice}, para existencias sin datos de clientes.",
        "organisations": "La marca ficticia {brand} y la organización {org} publican únicamente especificaciones técnicas.",
        "places": "La guía pública describe {place} como atracción general, no como domicilio de nadie.",
        "facilities": "El pabellón vacío tiene sala {room}, puerta {gate} y estante {rack}.",
        "numeric": "El componente cuesta EUR {price}; versión de firmware {version}; muestra {sample}; éxito {rate}%.",
    },
}


class BuildError(ValueError):
    """Fixed value-free failures only."""


def require(condition, code):
    if not condition:
        raise BuildError(code)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


class Builder:
    """Track gold while appending; never infer boundaries from final text."""
    def __init__(self):
        self.parts = []
        self.gold = []
        self.length = 0

    def prose(self, text):
        self.parts.append(text)
        self.length += len(text)
        return self

    def value(self, label, value):
        require(label in LABELS and bool(value), "v4_value_schema")
        self.gold.append({"start": self.length, "end": self.length + len(value), "label": label})
        return self.prose(value)

    def finish(self, language, family, ordinal):
        return {
            "case_id": f"v4-{language}-{ordinal:04d}", "family": family,
            "gold": self.gold, "language": language, "split": "dev",
            "text": "".join(self.parts),
        }


def person(language, index, style=0):
    given = GIVEN[language][index % 6]
    surname = SURNAMES[language][(index * 5 + 1) % 6]
    other = SURNAMES[language][(index + 3) % 6]
    particle = PARTICLES[language][index % len(PARTICLES[language])]
    forms = (
        f"{TITLES[language]} {given} {surname}",
        f"Prof. {given[0]}. {surname}",
        f"{given} {particle} {surname}",
        f"{given}-{GIVEN[language][(index + 2) % 6]} {surname}-{other}",
        f"{surname}, {given}",
        f"{given[0]}. {GIVEN[language][(index + 1) % 6][0]}. {particle} {surname}",
    )
    return forms[style % len(forms)]


def address(language, index, variant=0):
    recipient = person(language, index, 2)
    street = STREETS[language][index % 4]
    number = 37 + index * 3
    unit = {
        "en": f"floor 3, flat {index + 4}B", "de": f"3. OG, Wohnung {index + 4}B",
        "fr": f"3e étage, appartement {index + 4}B", "it": f"piano 3, interno {index + 4}B",
        "es": f"planta 3, piso {index + 4}B",
    }[language]
    box = {"en": "PO Box", "de": "Postfach", "fr": "BP", "it": "Casella postale", "es": "Apartado postal"}[language]
    route = f"{POSTCODES[language]} {TOWNS[language]}, {REGIONS[language]}, {COUNTRIES[language]}"
    delivery = f"{number} {street}" if language in {"en", "fr"} else f"{street} {number}"
    if variant % 4 == 0:
        return f"c/o {recipient}, {delivery}, {unit}, {route}"
    if variant % 4 == 1:
        return f"c/o {recipient}, {box} {280 + index}, {route}"
    if variant % 4 == 2:
        return f"{delivery}, {unit}, {route}"
    return f"c/o {recipient}\n{delivery}\n{unit}\n{route}"


def phone(language, index, variant=0):
    bases = {
        "en": f"+44 (0)1632 960 {index % 1000:03d}",
        "de": f"+49 (0)331 684 {index % 1000:03d}",
        "fr": f"+33 (0)3 69 84 {index % 100:02d} {(index * 7) % 100:02d}",
        "it": f"+39 0521 684 {index % 1000:03d}",
        "es": f"+34 947 68 {index % 100:02d} {(index * 7) % 100:02d}",
    }
    ext = {"en": "extension", "de": "Durchwahl", "fr": "poste", "it": "interno", "es": "extensión"}[language]
    base = bases[language]
    if variant % 3 == 1:
        base = base.replace(" ", ".").replace(".(0).", ".")
    elif variant % 3 == 2:
        base = base.replace(" ", "\u00a0")
    return f"{base} {ext} {index + 41}"


def iban(language, index):
    country, bban = {
        "en": ("GB", f"QYVX{93841700000000 + index:014d}"),
        "de": ("DE", f"{783619400000000000 + index:018d}"),
        "fr": ("FR", f"{59381006740000000000021 + index:023d}"),
        "it": ("IT", f"Q{7836100248000000000000 + index:022d}"),
        "es": ("ES", f"{78361940007000000000 + index:020d}"),
    }[language]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in bban + country + "00")
    raw = country + f"{98 - int(numeric) % 97:02d}" + bban
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def card(index):
    prefix = f"{468271903840000 + index:015d}"
    weighted = sum((2 * int(c) - 9 if int(c) > 4 else 2 * int(c)) if i % 2 == 0 else int(c)
                   for i, c in enumerate(prefix))
    raw = prefix + str((-weighted) % 10)
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def values(language, index):
    country = LANGUAGES.index(language) + 1
    n = 481000 + country * 1100 + index
    return {
        "PERSONNAME": person(language, index, index),
        "ADDRESS": address(language, index, index),
        "TELEPHONENUM": phone(language, index, index),
        "EMAIL": f"{GIVEN[language][index % 6].lower()}.{SURNAMES[language][index % 6].lower()}.{index}@private-v4.example.invalid",
        "USERNAME": f"@fern_{language}_{index}_quill",
        "IBAN": iban(language, index),
        "ACCOUNTNUM": f"{n:06d} / {739184 + index:06d} / {country:02d}",
        "CREDITCARDNUMBER": card(country * 100 + index),
        "PASSPORTNUM": f"QV{country}{n:06d}",
        "IDCARDNUM": f"K{country}-{n:06d}-L",
        "DRIVERLICENSENUM": f"DL{country}/{n:06d}/V4",
        "TAXNUM": f"{country}{n:06d}/{5820 + index:04d}",
        "SOCIALNUM": f"{country}{n:06d}-{2190 + index:04d}-{country:02d}",
        "PERSONALREF": f"PT-{language.upper()}-{n:06d}/Q",
        "DATEOFBIRTH": f"{4 + index % 19:02d}/{1 + index % 12:02d}/{1964 + index % 31}",
        "AGE": str(27 + index % 39),
    }


def field(builder, language, label, value, suffix="\n"):
    order = tuple(values(language, 0))
    cue = COPY[language]["fields"][order.index(label)]
    return builder.prose(cue + ": ").value(label, value).prose(suffix)


def ocr(value, label, index):
    # Corrupt separators only, preserving a single annotated whole value.
    if label in {"IBAN", "CREDITCARDNUMBER", "ACCOUNTNUM", "TELEPHONENUM"}:
        cut = max(3, len(value) // 2)
        return value[:cut] + "\n" + value[cut:]
    if label == "PERSONNAME":
        return value.replace(" ", "", 1) if index % 2 else value.replace(" ", "\n", 1)
    if label == "ADDRESS":
        return value.replace(", ", "\n", 1).replace("c/o ", "c/o", 1)
    if label in {"EMAIL", "USERNAME", "PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "PERSONALREF", "DATEOFBIRTH"}:
        cut = max(2, len(value) // 2)
        return value[:cut] + "\n" + value[cut:]
    return value


def reserved_row(language, family, index):
    b = Builder()
    copy = COPY[language]
    v = values(language, 100 + index)
    bundles = (
        ("PERSONNAME", "ADDRESS", "TELEPHONENUM"),
        ("PERSONNAME", "EMAIL", "USERNAME"),
        ("PERSONNAME", "IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER"),
        ("PERSONNAME", "PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM"),
        ("PERSONNAME", "TAXNUM", "SOCIALNUM", "PERSONALREF"),
        ("PERSONNAME", "DATEOFBIRTH", "AGE", "ADDRESS"),
    )
    labels = bundles[index % 6]
    if family == "form_records":
        b.prose(copy["bio"] + "\n")
        for label in labels:
            field(b, language, label, v[label])
    elif family == "chat_lines":
        visitor, coordinator, request = copy["chat"]
        b.prose(f"[09:{17 + index:02d}] {visitor}: {request}\n")
        for label in labels:
            b.prose(f"[09:{24 + index:02d}] {visitor}: ")
            field(b, language, label, v[label], ".\n")
        b.prose(f"[09:{36 + index:02d}] {coordinator}: OK.")
    elif family == "signature_blocks":
        # A signature, not a table: vary the identifier in the footer.
        b.prose(copy["signature"] + "--\n").value("PERSONNAME", v["PERSONNAME"]).prose("\n")
        b.value("ADDRESS", v["ADDRESS"]).prose("\n")
        b.value("TELEPHONENUM", v["TELEPHONENUM"]).prose("\n")
        b.value("EMAIL", v["EMAIL"]).prose("\n")
        extra = ("USERNAME", "IBAN", "PASSPORTNUM", "SOCIALNUM", "PERSONALREF", "DATEOFBIRTH")[index]
        field(b, language, extra, v[extra])
    elif family == "mixed_language":
        other = LANGUAGES[(LANGUAGES.index(language) + 1 + index % 4) % 5]
        foreign = values(other, 180 + index)
        b.prose(copy["address"]).value("ADDRESS", foreign["ADDRESS"]).prose(". ")
        b.prose(copy["phone"]).value("TELEPHONENUM", foreign["TELEPHONENUM"]).prose(". ")
        field(b, language, "IBAN", foreign["IBAN"], ". ")
        field(b, language, "PASSPORTNUM", foreign["PASSPORTNUM"], ".")
    elif family == "ocr_noise":
        b.prose(copy["bio"] + "\n")
        for label in labels:
            field(b, language, label, ocr(v[label], label, index))
    else:
        raise BuildError("v4_family")
    return b


def paragraph(builder, language, rng, target):
    start = builder.length
    while builder.length - start < target:
        builder.prose(rng.choice(COPY[language]["filler"]))
    builder.prose("\n\n")


def standard_rows(language, rng):
    c = COPY[language]
    out = []
    twin_values = []
    for i in range(6):
        b = Builder().prose(c["salutation"] if i == 0 else c["name"])
        b.value("PERSONNAME", person(language, 20 + i, i)).prose(",\n" if i == 0 else ".")
        out.append(("names", b))
    for i in range(4):
        b = Builder().prose(c["address"]).value("ADDRESS", address(language, 24 + i, i)).prose(".")
        out.append(("full_address", b))
    for i in range(3):
        b = Builder().prose(c["phone"]).value("TELEPHONENUM", phone(language, 31 + i, i)).prose(".")
        out.append(("phone", b))
    for i, label in enumerate(("IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER", "ACCOUNTNUM")):
        value = values(language, 40 + i)[label]
        b = Builder().prose(c["account"])
        field(b, language, label, value, ".")
        out.append(("account", b))
        if i in {1, 2}:
            twin_values.append((label, value))
    for i, label in enumerate(("PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM")):
        value = values(language, 50 + i)[label]
        b = Builder().prose(c["identity"])
        field(b, language, label, value, ".")
        out.append(("identity", b))
        twin_values.append((label, value))
    for i in range(2):
        value = values(language, 60 + i)["PERSONALREF"]
        b = Builder().prose(c["reference"]).value("PERSONALREF", value).prose(".")
        out.append(("personalref", b))
        if i == 0:
            twin_values.append(("PERSONALREF", value))
    for i, label in enumerate(("EMAIL", "USERNAME")):
        b = Builder().prose(c["online"]).value(label, values(language, 70 + i)[label]).prose(".")
        out.append(("username", b))
    for i in range(2):
        v = values(language, 80 + i)
        b = Builder().prose(c["bio"]).prose(c["birth"]).value("DATEOFBIRTH", v["DATEOFBIRTH"])
        b.prose(c["age"]).value("AGE", v["AGE"]).prose(".")
        out.append(("biography", b))
        twin_values.extend((label, v[label]) for label in ("DATEOFBIRTH", "AGE"))
    for i in range(2):
        v = values(language, 90 + i)
        b = Builder().prose(c["salutation"]).value("PERSONNAME", person(language, 90 + i, 0))
        b.prose(",\n\n" + c["letter_open"]).prose(c["reference"]).value("PERSONALREF", v["PERSONALREF"]).prose(".\n\n")
        paragraph(b, language, rng, 930 + i * 110)
        b.prose(c["address"]).value("ADDRESS", v["ADDRESS"]).prose(". ")
        b.prose(c["phone"]).value("TELEPHONENUM", v["TELEPHONENUM"]).prose(".\n\n")
        paragraph(b, language, rng, 1040 + i * 140)
        b.prose(c["online"]).value("EMAIL", v["EMAIL"]).prose(". ")
        b.prose(c["reference"]).value("PERSONALREF", v["PERSONALREF"]).prose(".\n\n")
        paragraph(b, language, rng, 840 + i * 100)
        b.prose(c["phone"]).value("TELEPHONENUM", v["TELEPHONENUM"]).prose(". ")
        b.prose(c["letter_close"] + "\n").value("PERSONNAME", person(language, 90 + i, 0)).prose("\n")
        out.append(("long_text", b))
    require(len(out) == 30 and len(twin_values) == 12, "v4_standard_counts")
    return out, twin_values


def clean_rows(language, twin_values):
    c = COPY[language]
    out = []
    for label, value in twin_values:
        if label == "DATEOFBIRTH":
            text = c["twins"][1] + value + "."
        elif label == "AGE":
            nouns = {"en": " identical screws.", "de": " gleiche Schrauben.", "fr": " vis identiques.", "it": " viti identiche.", "es": " tornillos idénticos."}
            text = c["twins"][2] + value + nouns[language]
        else:
            text = c["twins"][0] + value + "."
        out.append(("clean_near_miss_twins", Builder().prose(text)))
    for family in ("calendar", "dimensions", "catalog", "organisations", "places", "facilities", "numeric"):
        for i in range(4):
            country = LANGUAGES.index(language)
            substitutions = {
                "date": f"{12 + i:02d}/11/2028", "time": f"{10 + i:02d}:45",
                "a": 230 + i * 13, "b": 74 + i * 7, "c": 8 + i, "q": 36 + i * 5,
                "code": f"{48173 + country * 91 + i}-R", "order": 730218 + i,
                "invoice": 840713 + i, "brand": ("QuillForge", "MossArc", "CopperKite", "FernScope")[i],
                "org": ("Ivory Lens Laboratory", "Open Gear Institute", "Cobalt Draft Alliance", "Willow Beam Cooperative")[i],
                "place": ("Grand Canyon", "Museo del Prado", "Lac Léman", "Brandenburger Tor")[i],
                "room": f"{210 + i}B", "gate": f"{17 + i}C", "rack": f"R-{39 + i}",
                "price": f"{73 + i}.95", "version": f"4.{17 + i}.3", "sample": 137 + i * 13,
                "rate": f"{81 + i}.7",
            }
            out.append(("clean_" + family, Builder().prose(c[family].format(**substitutions))))
    require(len(out) == 40, "v4_clean_counts")
    return out


def generate_rows():
    rng = random.Random(SEED)
    rows = []
    for language in LANGUAGES:
        items = []
        for family in sorted(RESERVED):
            items.extend((family, reserved_row(language, family, i)) for i in range(6))
        standard, twins = standard_rows(language, rng)
        items.extend(standard)
        items.extend(clean_rows(language, twins))
        require(len(items) == 100, "v4_language_count")
        rows.extend(b.finish(language, family, i + 1) for i, (family, b) in enumerate(items))
    rng.shuffle(rows)
    return rows


def schema_validator():
    # Only the allowed validator source is read. No package import, scorer,
    # detector, tokenizer or model is executed. Preserve the validator body;
    # provide the policy-v1 label allowlist including newly canonical DATEOFBIRTH.
    source = (ROOT / VALIDATOR_PATH).read_bytes()
    tree = ast.parse(source.decode("utf-8"))
    wanted = {"MaskingError", "_integer", "_length", "validate_spans"}
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in wanted]
    require({node.name for node in selected} == wanted, "v4_validator_source")
    nodes: list[ast.stmt] = list(selected)
    namespace = {"LABELS": LABELS, "GOLD_DIAGNOSTIC_LABELS": frozenset()}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "v4-schema-validator", "exec"), namespace)
    return namespace["validate_spans"], digest(source)


def validate_rows(rows):
    validator, validator_hash = schema_validator()
    require(len(rows) == 500, "v4_row_count")
    ids, texts = set(), set()
    per_language = Counter()
    per_family = Counter()
    per_label = Counter()
    breakdown = {}
    long_lengths = []
    positive = reserved = gold_chars = gold_alnum = 0
    twins_by_language = {language: [] for language in LANGUAGES}
    positive_values = {language: set() for language in LANGUAGES}
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"case_id", "family", "gold", "language", "split", "text"}, "v4_row_schema")
        language, family, text, gold = row["language"], row["family"], row["text"], row["gold"]
        require(language in LANGUAGES and family in RESERVED | STANDARD | CLEAN, "v4_row_category")
        require(row["split"] == "dev" and isinstance(text, str) and 0 < len(text) <= 32000, "v4_row_content")
        require(isinstance(row["case_id"], str) and row["case_id"].startswith("v4-" + language + "-"), "v4_case_schema")
        require(row["case_id"] not in ids and text not in texts, "v4_duplicate")
        ids.add(row["case_id"])
        texts.add(text)
        require(isinstance(gold, list) and bool(gold) == (family not in CLEAN), "v4_gold_presence")
        require(all(isinstance(g, dict) and set(g) == {"start", "end", "label"} for g in gold), "v4_gold_schema")
        try:
            validator(gold, len(text), gold=True)
        except Exception:
            raise BuildError("v4_span_validation") from None
        require(gold == sorted(gold, key=lambda g: (g["start"], g["end"])), "v4_gold_order")
        per_language[language] += 1
        per_family[family] += 1
        positive += bool(gold)
        reserved += family in RESERVED
        entry = breakdown.setdefault(language, {"rows": 0, "positive_rows": 0, "clean_rows": 0, "reserved_positive_rows": 0, "per_family": Counter(), "per_label": Counter()})
        entry["rows"] += 1
        entry["positive_rows"] += bool(gold)
        entry["clean_rows"] += not gold
        entry["reserved_positive_rows"] += family in RESERVED
        entry["per_family"][family] += 1
        for g in gold:
            value = text[g["start"]:g["end"]]
            require(value == value.strip(), "v4_gold_whitespace")
            require(not value.endswith((".", ",", ";", ":", "!", "?")), "v4_gold_punctuation")
            per_label[g["label"]] += 1
            entry["per_label"][g["label"]] += 1
            gold_chars += len(value)
            gold_alnum += sum(c.isalnum() for c in value)
            positive_values[language].add(value)
        if family == "clean_near_miss_twins":
            # Extract from the structural clean wrappers, never print or retain
            # these temporary values in manifests/diagnostics.
            prefixes = COPY[language]["twins"]
            prefix = next((p for p in prefixes if text.startswith(p)), None)
            if prefix is None:
                raise BuildError("v4_twin_structure")
            value = text[len(prefix):-1]
            if prefix == prefixes[2]:
                value = value.split(" ", 1)[0]
            twins_by_language[language].append(value)
        if family == "long_text":
            long_lengths.append(len(text))
            require(3000 <= len(text) <= 6000, "v4_long_length")
            repetition = Counter(text[g["start"]:g["end"]] for g in gold)
            require(sum(n > 1 for n in repetition.values()) >= 3, "v4_long_repetition")
            require(gold[0]["start"] < len(text) // 5 and gold[-1]["end"] > len(text) * 4 // 5, "v4_long_positions")
            require(any(len(text) // 3 < g["start"] < len(text) * 2 // 3 for g in gold), "v4_long_middle")
    require(positive == 300 and len(rows) - positive == 200, "v4_balance")
    require(per_language == Counter({language: 100 for language in LANGUAGES}), "v4_language_balance")
    require(reserved >= positive * 0.4 and reserved == 150, "v4_reserved_balance")
    require(set(per_label) == LABELS, "v4_label_coverage")
    require(len(long_lengths) == 10, "v4_long_count")
    require(per_family["clean_near_miss_twins"] == 60, "v4_twin_count")
    for language in LANGUAGES:
        require(len(twins_by_language[language]) == 12 and all(v in positive_values[language] for v in twins_by_language[language]), "v4_twin_pairing")
        entry = breakdown[language]
        require((entry["positive_rows"], entry["clean_rows"], entry["reserved_positive_rows"]) == (60, 40, 30), "v4_language_subcounts")
    return {
        "counts": {
            "rows": len(rows), "positive_rows": positive, "clean_rows": len(rows) - positive,
            "reserved_positive_rows": reserved, "reserved_positive_fraction": reserved / positive,
            "near_miss_twin_clean_rows": per_family["clean_near_miss_twins"],
            "gold_spans": sum(per_label.values()), "gold_original_characters": gold_chars,
            "gold_unicode_alphanumeric_characters": gold_alnum,
            "per_language": dict(sorted(per_language.items())),
            "per_family": dict(sorted(per_family.items())), "per_label": dict(sorted(per_label.items())),
        },
        "per_language_breakdown": breakdown,
        "long_letters": {"rows": len(long_lengths), "min_characters": min(long_lengths), "max_characters": max(long_lengths), "repeated_values_per_row_minimum": 3, "early_middle_late_gold_checked": True, "tokenizer_or_window_crossings_claimed": False},
        "validator_sha256": validator_hash,
    }


def serialize(rows):
    return b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for row in rows)


def make_manifest(blob, summary):
    validator_hash = summary.pop("validator_sha256")
    return {
        "version": "masking-stress-v4", "policy_version": "privacy-policy-v1",
        "schema": "masking-stress-six-field-v1", "split": "dev",
        "purpose": "Independent frozen synthetic blind diagnostic; not training data or the corpus test split.",
        "measurement_rule": "measure once per profile+model; never tune on v4",
        "dataset": {"path": DATA_PATH.as_posix(), "sha256": digest(blob), "bytes": len(blob), "rows": 500},
        "generator": {"path": GENERATOR_PATH.as_posix(), "sha256": digest((ROOT / GENERATOR_PATH).read_bytes()), "seed": SEED, "stdlib_only": True, "deterministic": True, "refuses_existing_data_or_manifest": True},
        "blind_status": {
            "generated_without_seeing_detector_code_training_data_or_predictions": True,
            "detector_code_read": False, "training_generators_or_data_read": False,
            "research_reports_read": False, "predictions_or_measurement_files_read": False,
            "model_or_detector_run_on_v4": False, "shared_batch_problem_description_known": True,
            "permitted_reference_reads": ["shared contract and privacy policy v1", "docs/masking-stress-v3/manifest.json", VALIDATOR_PATH.as_posix()],
            "measurement_owner": "integrator", "status": "frozen_unmeasured_by_custodian",
        },
        "reserved_families": sorted(RESERVED),
        "annotations": {
            "boundaries": "Half-open Python Unicode code-point offsets on original text, ordered and non-overlapping; entire values including internal separators, attached titles, phone extensions, c/o recipients and postal routing; prose, salutations and sentence punctuation excluded.",
            "address_policy": "One complete postal region; nested recipient names are not separately overlapped.",
            "ocr_policy": "Inserted line breaks or removed spaces inside values remain within the gold region.",
            "clean_policy": "Only explicit non-personal constructions; no personal emails, handles or bank IBANs in clean controls. Numeric/code look-alikes are explicitly stock product codes, public calendar dates or screw quantities.",
            "near_miss_twins": "60 clean rows reuse exactly one annotated positive value each in an explicit non-personal construction; 12 pairs per language, authored before detection.",
        },
        "validation": {
            "schema": "passed: exact AST-extracted validate_spans implementation plus strict six-field row checks; validator namespace uses canonical policy-v1 labels (including DATEOFBIRTH), not the legacy scorer allowlist.",
            "validator_source_sha256": validator_hash, "unique_texts_and_ids": True,
            "ordered_nonoverlapping_gold": True, "all_canonical_labels_present": True,
            "paired_twins_checked": True, "deterministic_byte_replay": True,
            "verify": "Rebuilds in memory, validates stored rows, compares exact data and manifest bytes; performs no detection.",
        },
        "novelty": {
            "templates_and_value_pools": "Newly authored without access to prior template/value literals; v3 manifest categories alone were consulted.",
            "v3_source_or_rows_read": False, "exact_literal_disjointness_proven": False,
            "semantic_or_translation_independence_proven": False,
        },
        "limitations": [
            "Synthetic authored contexts are not a real-data sample or a privacy/legal guarantee.",
            "Invented names and numeric identifiers can accidentally coincide with real ones; only example.invalid mail domains and UK drama-range phones have special-use conventions. No assignment lookup or external validation was performed.",
            "IBAN outer length/mod97 and card Luhn checksums are constructed; issuer, bank routing and national identifier checksums are not authority-validated.",
            "OCR cases are controlled separator perturbations, not sampled scan errors.",
            "Novel templates and pools were authored independently; exact disjointness cannot be proved from the permitted v3 manifest alone.",
            "Long letters repeat procedural filler; no tokenizer length or exact sliding-window crossing claim is made.",
        ],
        **summary,
    }


def freeze_or_verify(verify=False):
    data_file, manifest_file = ROOT / DATA_PATH, ROOT / MANIFEST_PATH
    if not verify:
        require(not data_file.exists() and not manifest_file.exists(), "v4_refuses_overwrite")
    rows = generate_rows()
    summary = validate_rows(rows)
    blob = serialize(rows)
    manifest = make_manifest(blob, summary)
    manifest_blob = json_bytes(manifest)
    if verify:
        require(data_file.is_file() and manifest_file.is_file(), "v4_missing_frozen_artifact")
        stored_blob = data_file.read_bytes()
        stored_rows = [json.loads(line) for line in stored_blob.decode("utf-8").splitlines()]
        validate_rows(stored_rows)
        require(stored_blob == blob, "v4_dataset_replay_mismatch")
        require(manifest_file.read_bytes() == manifest_blob, "v4_manifest_replay_mismatch")
    else:
        data_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents race-based accidental overwrites, too.
        with data_file.open("xb") as stream:
            stream.write(blob)
        with manifest_file.open("xb") as stream:
            stream.write(manifest_blob)
        require(data_file.read_bytes() == blob and manifest_file.read_bytes() == manifest_blob, "v4_write_verification")
    counts = manifest["counts"]
    print(json.dumps({"status": "verified" if verify else "frozen", "rows": counts["rows"], "positive_rows": counts["positive_rows"], "clean_rows": counts["clean_rows"], "reserved_positive_rows": counts["reserved_positive_rows"], "near_miss_twins": counts["near_miss_twin_clean_rows"], "per_language": counts["per_language"], "dataset_sha256": manifest["dataset"]["sha256"]}, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Validate and byte-replay frozen artifacts without writing")
    args = parser.parse_args(argv)
    try:
        freeze_or_verify(args.verify)
    except BuildError as error:
        print("ERROR " + str(error), file=sys.stderr)
        return 1
    except Exception:
        # JSON errors and filesystem errors can echo text/paths: never emit them.
        print("ERROR v4_operation_failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
