#!/usr/bin/env python3
"""Independent synthetic blind v6. Stdlib only; never reads models or older sets.

Gold is assembled from typed literal fragments, not inferred from a detector.
All personal values are invented; emails use the reserved .invalid namespace.
Verification is value-free and binds exact UTF-8 bytes, source, policy and counts.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/augmentation/masking-stress-v6.jsonl"
MANIFEST = ROOT / "artifacts/masking-stress-v6/manifest.json"
POLICY = ROOT / "configs/privacy-policy-v1.json"
SEED = 177979086192380403614846588701761420077
LANGUAGES = ("en", "de", "fr", "it", "es")
LABELS = ("PERSONNAME", "ADDRESS", "EMAIL", "USERNAME", "TELEPHONENUM", "IBAN",
          "ACCOUNTNUM", "CREDITCARDNUMBER", "PASSPORTNUM", "IDCARDNUM",
          "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "PERSONALREF", "DATEOFBIRTH", "AGE")
RESERVED = {
    "v6_intake_slips": "form-style key/value records",
    "v6_lobby_dialogues": "chat/messaging lines",
    "v6_correspondence_footers": "email signature blocks",
    "v6_crossborder_handoffs": "mixed-language documents",
    "v6_scan_transcriptions": "OCR-like noise inside values",
}
CLEAN = {"v6_stock_grids": 60, "v6_measurement_notebooks": 60,
         "v6_object_lookalikes": 100, "v6_process_bulletins": 80}
HISTORICAL_NAMES = frozenset((
    "account", "biography", "chat_lines", "clean_calendar", "clean_catalog",
    "clean_dimensions", "clean_facilities", "clean_near_miss_twins", "clean_numeric",
    "clean_organisations", "clean_places", "form_records", "full_address", "identity",
    "long_text", "mixed_language", "names", "ocr_noise", "personalref", "phone",
    "signature_blocks", "username", "adjacent_contact", "birth_age", "clean_near_miss",
    "clean_other", "digital", "financial", "long_letters", "official_ids",
    "personal_refs", "phones", "whole_addresses"))
# These small pools and all surrounding prose were authored independently for v6.
LEX = {
    "en": {
        "given": ("Vellin", "Orlith", "Nerava", "Tessune"),
        "surname": ("Marnwick", "Quessle", "Dovren", "Fellovar"),
        "title": "Dr.", "particle": "van", "city": "Quillmere",
        "street": "Lattice Lantern Walk", "country": "United Kingdom",
        "postcode": "QZ7 4VX", "floor": "floor 3, flat 8", "box": "PO Box",
        "care": "c/o", "hello": "Dear", "person": "Resident", "born": "born on",
        "age": ("aged {}", "{} years old", "age: {}", "({})", "{} years of age", "I am {}"),
        "age_words": ("twenty-seven", "thirty-two", "forty-six", "sixty-one"),
        "fields": ("Name", "Home address", "Contact telephone", "Email", "User handle",
                   "IBAN", "Account", "Payment card", "Passport", "Identity card",
                   "Driving licence", "Tax identifier", "Social insurance", "Member reference",
                   "Birth date", "Age"),
        "contact": "Please retain these private contact details for the volunteer.",
        "chat": "The waiting room is open; this participant identifies as",
        "receipt": "The clerk recorded this applicant's credentials for the rehearsal.",
        "account": "The participant supplied these personal payment details.",
        "preamble": "This is a synthetic rehearsal letter about the lending workshop.",
        "paragraphs": (
            "The shutters will remain open while the repair team checks the borrowed lamps. No booking can be confirmed until the equipment has passed a second visual inspection.",
            "Please keep the spare fasteners in the dry cupboard and mark the damaged trays with removable tape. The notice board must describe the revised collection procedure clearly.",
            "The demonstration should start with a quiet explanation of the safety sequence. If the room becomes noisy, pause the exercise rather than shortening the final inspection.",
            "A written receipt is required for every borrowed tool, even when it returns unused. The team will compare the shelf inventory with the issue ledger before closing."),
        "stock": "Material inventory; columns describe objects, not people",
        "numeric": "Bench measurements and machine calibration; no personal records",
        "object": "Object-only technical register; no human identifiers or contact details",
        "bulletin": "Workshop operating notice", "unit": "pieces", "public": "public test dock",
        "kinds": ("calibration grouping", "equipment inspection date", "coating lifetime",
                  "pigment trade name", "public loading location", "spool batch code",
                  "ceramic specimen code", "tool serial", "shelf stock code", "sensor barcode"),
    },
    "de": {
        "given": ("Fennika", "Ulvaro", "Kelmina", "Sörvel"),
        "surname": ("Tannquell", "Wolkenried", "Nebelzorn", "Kiesfalter"),
        "title": "Prof.", "particle": "von", "city": "Falterquell",
        "street": "Zinnlaternenweg", "country": "Deutschland", "postcode": "08473",
        "floor": "3. Stock, Wohnung 8", "box": "Postfach", "care": "c/o",
        "hello": "Sehr geehrte", "person": "Bewohner", "born": "geboren am",
        "age": ("{} Jahre alt", "im Alter von {}", "Alter: {}", "[{}]", "{} Lebensjahre", "ich bin {}"),
        "age_words": ("siebenundzwanzig", "zweiunddreißig", "sechsundvierzig", "einundsechzig"),
        "fields": ("Name", "Wohnanschrift", "Telefon", "E-Mail", "Benutzername", "IBAN",
                   "Konto", "Karte", "Reisepass", "Personalausweis", "Führerschein",
                   "Steuernummer", "Sozialnummer", "Mitgliedsreferenz", "Geburtsdatum", "Alter"),
        "contact": "Bitte die privaten Kontaktdaten der teilnehmenden Person hinterlegen.",
        "chat": "Der Warteraum ist offen; diese Person verwendet das Pseudonym",
        "receipt": "Die Sachbearbeitung erfasste die Ausweisdaten dieser antragstellenden Person.",
        "account": "Die teilnehmende Person nennt ihre privaten Zahlungsangaben.",
        "preamble": "Dies ist ein erfundener Übungsbrief zur Werkzeugausleihe.",
        "paragraphs": (
            "Die Fenster bleiben offen, während das Team die ausgeliehenen Lampen prüft. Eine Reservierung gilt erst nach der zweiten Sichtprüfung als bestätigt.",
            "Die Ersatzteile gehören in den trockenen Schrank. Beschädigte Schalen werden mit ablösbarem Klebeband markiert, damit die geänderte Ausgabe verständlich bleibt.",
            "Die Vorführung beginnt mit einer ruhigen Erklärung der Sicherheitsfolge. Bei starkem Lärm wird die Übung unterbrochen und die letzte Prüfung nicht verkürzt.",
            "Für jedes ausgeliehene Werkzeug ist ein Beleg erforderlich, auch bei unbenutzter Rückgabe. Vor dem Schließen werden Regalbestand und Ausgabebuch verglichen."),
        "stock": "Materialtabelle; nur Gegenstände, keine Personen",
        "numeric": "Messbank und Maschinenkalibrierung; keine Personendaten",
        "object": "Reines Objektregister; keine menschlichen Kennungen oder Kontaktdaten",
        "bulletin": "Werkstattablauf", "unit": "Stück", "public": "öffentlicher Prüfkai",
        "kinds": ("Kalibriergruppen", "Prüfdatum der Anlage", "Lebensdauer der Beschichtung",
                  "Pigmenthandelsname", "öffentliche Ladestelle", "Spulencharge",
                  "Keramikprobencode", "Werkzeugserie", "Regalartikel", "Sensorbarcode"),
    },
    "fr": {
        "given": ("Élorine", "Vassiel", "Maurelle", "Nivélio"),
        "surname": ("Brumelac", "Clairfève", "Vernossin", "Tisseronce"),
        "title": "Mme", "particle": "de", "city": "Brumerive",
        "street": "allée des Lanternes d'Étain", "country": "France", "postcode": "03782",
        "floor": "étage 3, appartement 8", "box": "BP", "care": "chez",
        "hello": "Bonjour", "person": "Résident", "born": "né le",
        "age": ("âgé de {} ans", "{} ans", "âge : {}", "({})", "j'ai {} ans", "à l'âge de {}"),
        "age_words": ("vingt-sept", "trente-deux", "quarante-six", "soixante et un"),
        "fields": ("Nom", "Adresse privée", "Téléphone", "Courriel", "Pseudonyme", "IBAN",
                   "Compte", "Carte", "Passeport", "Carte d'identité", "Permis",
                   "Numéro fiscal", "Sécurité sociale", "Référence adhérent", "Naissance", "Âge"),
        "contact": "Merci de conserver les coordonnées privées de cette personne bénévole.",
        "chat": "La salle d'attente est ouverte ; cette personne se présente sous le pseudo",
        "receipt": "Le secrétariat a noté les pièces de cette personne pour la répétition.",
        "account": "La personne participante transmet ses coordonnées de paiement privées.",
        "preamble": "Voici une lettre fictive pour la répétition de l'atelier de prêt.",
        "paragraphs": (
            "Les volets restent ouverts pendant la vérification des lampes prêtées. Une réservation ne peut être confirmée avant la seconde inspection visuelle du matériel.",
            "Les fixations de rechange restent dans le placard sec. Les plateaux abîmés sont marqués avec un ruban amovible pour rendre la nouvelle procédure lisible.",
            "La démonstration commence par une explication calme des étapes de sécurité. Si la salle devient bruyante, il faut suspendre l'exercice sans raccourcir le contrôle final.",
            "Chaque outil emprunté nécessite un reçu, même s'il revient inutilisé. L'équipe compare le stock des étagères au registre des sorties avant la fermeture."),
        "stock": "Catalogue de matériaux ; objets uniquement, aucune personne",
        "numeric": "Mesures de banc et étalonnage de machines ; aucune fiche personnelle",
        "object": "Registre technique d'objets ; aucun identifiant humain ni contact",
        "bulletin": "Consigne d'atelier", "unit": "pièces", "public": "quai public d'essai",
        "kinds": ("groupes d'étalonnage", "date de contrôle de machine", "durée du revêtement",
                  "nom commercial du pigment", "chargement public", "lot de bobines",
                  "code d'échantillon céramique", "série d'outil", "code de rayon", "code de capteur"),
    },
    "it": {
        "given": ("Serivio", "Almirea", "Terenza", "Olivesso"),
        "surname": ("Vetravalle", "Nebbiorto", "Lunacesta", "Fiorcavo"),
        "title": "Sig.ra", "particle": "di", "city": "Vetranube",
        "street": "via delle Lanterne di Stagno", "country": "Italia", "postcode": "07183",
        "floor": "piano 3, interno 8", "box": "Casella postale", "care": "presso",
        "hello": "Gentile", "person": "Residente", "born": "nato il",
        "age": ("di {} anni", "{} anni di età", "età: {}", "[{}]", "ho {} anni", "all'età di {}"),
        "age_words": ("ventisette", "trentadue", "quarantasei", "sessantuno"),
        "fields": ("Nome", "Indirizzo privato", "Telefono", "Email", "Nome utente", "IBAN",
                   "Conto", "Carta", "Passaporto", "Carta d'identità", "Patente",
                   "Codice fiscale", "Numero sociale", "Riferimento socio", "Data di nascita", "Età"),
        "contact": "Conservare i recapiti privati della persona volontaria.",
        "chat": "La sala d'attesa è aperta; questa persona usa lo pseudonimo",
        "receipt": "La segreteria ha registrato i documenti della persona per la prova.",
        "account": "La persona partecipante comunica i propri dati privati di pagamento.",
        "preamble": "Questa lettera inventata riguarda la prova del laboratorio di prestito.",
        "paragraphs": (
            "Le finestre restano aperte durante il controllo delle lampade prestate. La prenotazione non viene confermata prima della seconda ispezione visiva del materiale.",
            "I ricambi vanno nell'armadio asciutto e i vassoi danneggiati ricevono nastro rimovibile. La bacheca deve spiegare chiaramente la nuova procedura di consegna.",
            "La dimostrazione inizia con una spiegazione calma della sequenza di sicurezza. Se la stanza diventa rumorosa, si sospende la prova senza abbreviare il controllo finale.",
            "Ogni attrezzo prestato richiede una ricevuta, anche se restituito inutilizzato. Prima della chiusura il gruppo confronta gli scaffali con il registro delle uscite."),
        "stock": "Catalogo di materiali; soltanto oggetti, nessuna persona",
        "numeric": "Misure di banco e taratura delle macchine; nessuna scheda personale",
        "object": "Registro tecnico di oggetti; nessun identificativo umano o contatto",
        "bulletin": "Avviso operativo", "unit": "pezzi", "public": "molo pubblico di prova",
        "kinds": ("gruppi di taratura", "data di verifica della macchina", "durata del rivestimento",
                  "nome commerciale del pigmento", "carico pubblico", "lotto di bobine",
                  "codice campione ceramico", "serie attrezzo", "codice scaffale", "codice sensore"),
    },
    "es": {
        "given": ("Nerelia", "Valunio", "Esmara", "Solvén"),
        "surname": ("Brumacanto", "Luzarce", "Fresnolar", "Cendalrío"),
        "title": "Sr.", "particle": "del", "city": "Lumbracauce",
        "street": "calle de los Faroles de Estaño", "country": "España", "postcode": "04783",
        "floor": "planta 3, puerta 8", "box": "Apartado", "care": "a cargo de",
        "hello": "Estimado", "person": "Residente", "born": "nació el",
        "age": ("de {} años", "{} años de edad", "edad: {}", "({})", "tengo {} años", "a los {} años"),
        "age_words": ("veintisiete", "treinta y dos", "cuarenta y seis", "sesenta y uno"),
        "fields": ("Nombre", "Domicilio privado", "Teléfono", "Correo", "Usuario", "IBAN",
                   "Cuenta", "Tarjeta", "Pasaporte", "Documento de identidad", "Permiso",
                   "Número fiscal", "Número social", "Referencia de socio", "Nacimiento", "Edad"),
        "contact": "Guardar los datos privados de contacto de la persona voluntaria.",
        "chat": "La sala de espera está abierta; esta persona utiliza el alias",
        "receipt": "La oficina anotó los documentos de esta persona para el ensayo.",
        "account": "La persona participante facilita sus datos privados de pago.",
        "preamble": "Esta carta inventada trata del ensayo del taller de préstamo.",
        "paragraphs": (
            "Las ventanas quedan abiertas mientras se revisan las lámparas prestadas. No se confirma ninguna reserva hasta terminar la segunda inspección visual del material.",
            "Los repuestos permanecen en el armario seco y las bandejas dañadas llevan cinta removible. El tablón debe explicar claramente el nuevo procedimiento de entrega.",
            "La demostración empieza con una explicación tranquila de la secuencia de seguridad. Si hay demasiado ruido, se pausa el ejercicio sin acortar la revisión final.",
            "Cada herramienta prestada requiere un recibo, aunque vuelva sin usar. Antes del cierre, el equipo compara los estantes con el registro de salidas."),
        "stock": "Catálogo de materiales; solo objetos, ninguna persona",
        "numeric": "Medidas de banco y calibración de máquinas; sin registros personales",
        "object": "Registro técnico de objetos; sin identificadores humanos ni contactos",
        "bulletin": "Aviso del taller", "unit": "piezas", "public": "muelle público de ensayo",
        "kinds": ("grupos de calibración", "fecha de revisión de máquina", "duración del revestimiento",
                  "nombre comercial de pigmento", "carga pública", "lote de bobinas",
                  "código de muestra cerámica", "serie de herramienta", "código estante", "código sensor"),
    },
}


class FreezeError(ValueError):
    """Only fixed aggregate-free error codes leave the generator."""


def require(condition, code):
    if not condition:
        raise FreezeError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def field(lang, label):
    return LEX[lang]["fields"][LABELS.index(label)]


class Row:
    def __init__(self, lang, family, serial, formats):
        self.data: dict[str, Any] = dict(case_id=f"blind-v6-{lang}-{serial:03d}", family=family,
                                       gold=[], language=lang, split="blind", text="")
        self.formats = formats

    def add(self, text):
        self.data["text"] += text
        return self

    def value(self, label, value, form):
        require(label in LABELS and isinstance(value, str) and value.strip() == value,
                "literal_value_rule")
        start = len(self.data["text"])
        self.add(value)
        self.data["gold"].append(dict(start=start, end=start + len(value), label=label))
        self.formats[f"{label}/{form}"] += 1
        return self

    def entries(self, values, labels, forms, delimiter="\n"):
        for label in labels:
            self.add(field(self.data["language"], label) + " = ")
            self.value(label, values[label], forms[label]).add(delimiter)
        return self


def invented_values(lang, serial, style, rng):
    x = LEX[lang]
    given, surname = rng.choice(x["given"]), rng.choice(x["surname"])
    other = rng.choice(tuple(s for s in x["surname"] if s != surname))
    names = (f"{given} {surname}", f"{x['title']} {given} {surname}",
             f"{given[0]}. {surname}", f"{x['title']} {given[0]}. {surname}",
             f"{given} {x['particle']} {surname}", f"{given}-{rng.choice(x['given'])} {surname}-{other}",
             f"{surname}, {given}", f"{given} {surname}".upper())
    n = 410 + serial
    street = f"{x['street']} {n}"
    routing = f"{x['postcode']} {x['city']}"
    addresses = (
        f"{street}, {x['floor']}, {routing}, {x['country']}",
        f"{street}\n{x['floor']}\n{routing}\n{x['country']}",
        f"{x['care']} {given} {surname}; {street}; {routing}; {x['country']}",
        f"{x['box']} {n}, {routing}, {x['country']}",
        f"{routing} / {street} / {x['floor']} / {x['country']}",
        f"{n}, {x['street']} — {x['floor']} — {routing} — {x['country']}",
        f"{x['care']} {given} {surname}\n{street}\n{x['floor']}\n{routing}\n{x['country']}",
        f"{street} | {x['floor']} | {routing} | {x['country']}")
    country = dict(en="44", de="49", fr="33", it="39", es="34")[lang]
    ext = dict(en="extension", de="Durchwahl", fr="poste", it="interno", es="extensión")[lang]
    digits = f"000{serial:04d}"
    phone_shapes = (f"+{country} (0) 700 {digits[:3]} {digits[3:]}",
                    f"00{country}-700-{digits}", f"0700/{digits[:3]}/{digits[3:]}",
                    f"(+{country}) 700.{digits[:3]}.{digits[3:]}",
                    f"+{country} 700 {digits} {ext} 82", f"0700 {digits} {ext} 19",
                    f"+{country}\u00a0700\u00a0{digits}", f"+{country}700{digits}")
    suffix = f"{rng.randrange(10**8, 10**9):09d}"
    handle = f"quartzling_{lang}_{suffix}"
    handles = ("@" + handle, handle.replace("_", "."), handle.replace("_", "-"),
               "@" + handle.replace("_", "."), handle.upper(), "@" + handle + "_arc",
               handle + "#" + str(4100 + serial), handle)
    # Plausible domestic layouts; all values are invented, never source-derived.
    bban = {"en": "QVEX" + suffix[:6] + suffix[:8], "de": suffix + "000000003",
            "fr": suffix + "00000000000018", "it": "Q" + suffix + "0000000000019",
            "es": suffix + "00000000018"}[lang]
    prefix = dict(en="GB", de="DE", fr="FR", it="IT", es="ES")[lang]
    check_input = bban + prefix + "00"
    numeric = "".join(c if c.isdigit() else str(ord(c) - 55) for c in check_input)
    compact = prefix + f"{98 - int(numeric) % 97:02d}" + bban
    iban = (compact, " ".join(compact[i:i+4] for i in range(0, len(compact), 4)),
            "-".join(compact[i:i+4] for i in range(0, len(compact), 4)),
            compact[:8] + "\n" + compact[8:])[style % 4]
    card_head = "9" + suffix + f"{serial:05d}"
    doubled = [int(c) * (2 if i % 2 == 0 else 1) for i, c in enumerate(card_head)]
    card = card_head + str((-sum(d - 9 if d > 9 else d for d in doubled)) % 10)
    # Alternate checksum-correct and deliberately mismatched values: both are gold.
    if style % 2:
        card = card[:-1] + str((int(card[-1]) + 1) % 10)
    account = f"{suffix}00{serial:04d}"
    def separated(value, width):
        return (value, " ".join(value[i:i+width] for i in range(0, len(value), width)),
                "-".join(value[i:i+width] for i in range(0, len(value), width)),
                value[:width] + "/" + value[width:])[style % 4]
    values = dict(PERSONNAME=names[style % 8], ADDRESS=addresses[style % 8],
                  TELEPHONENUM=phone_shapes[style % 8], USERNAME=handles[style % 8],
                  EMAIL=f"{handle}@postbox-v6.invalid", IBAN=iban,
                  ACCOUNTNUM=separated(account, 4), CREDITCARDNUMBER=separated(card, 4))
    domestic = {
        "en": (suffix, "QV" + suffix, "MARNE" + suffix[:6] + "VQ" + suffix[:3],
               suffix + "7", "QQ" + suffix[:6] + "Q", "MEM" + suffix),
        "de": ("QV" + suffix[:7], "Z" + suffix[:8], "L" + suffix + "Q",
               suffix + "07", suffix[:8] + "Q" + suffix[:3], "PAT" + suffix),
        "fr": (suffix[:2] + "QV" + suffix[:5], suffix + "017", suffix + "017",
               suffix + "0017", "1" + suffix + "00107", "DOS" + suffix),
        "it": ("QV" + suffix[:7], "ZX" + suffix[:5] + "QV", "LV" + suffix[:7] + "Q",
               "VTRSRV" + "87Q17" + "Z" + suffix[:3] + "Q", suffix + "017",
               "SOC" + suffix),
        "es": ("QVZ" + suffix[:6], suffix[:8] + "Q", suffix[:8] + "V",
               "Q" + suffix[:7] + "Z", suffix + "017", "CAS" + suffix),
    }
    for label, stem in zip(LABELS[8:14], domestic[lang]):
        values[label] = separated(stem, 3)
    values["DATEOFBIRTH"] = (f"198{serial % 10}-0{serial % 8 + 1}-17",
                            f"17.0{serial % 8 + 1}.198{serial % 10}",
                            f"17/0{serial % 8 + 1}/198{serial % 10}",
                            f"17 · 0{serial % 8 + 1} · 198{serial % 10}")[style % 4]
    values["AGE"] = str((27, 32, 46, 61)[style % 4])
    forms = {label: f"layout_{style % (8 if label in ('PERSONNAME', 'ADDRESS', 'TELEPHONENUM', 'USERNAME') else 4)}"
             for label in LABELS}
    return values, forms


DIGITAL_CONTEXTS = {
    "en": ("Chat speaker", "Forum author", "Gaming lobby nickname", "Social profile alias",
           "Message sender", "Mentioned participant", "Display username", "Email local part used as login"),
    "de": ("Chat-Absender", "Forenautor", "Spielername", "Alias im sozialen Profil",
           "Nachrichtenabsender", "Erwähnte Person", "Anzeigename", "E-Mail-Lokalteil als Login"),
    "fr": ("Auteur du chat", "Auteur du forum", "Pseudo de jeu", "Alias du profil social",
           "Expéditeur du message", "Personne mentionnée", "Nom affiché", "Partie locale du courriel comme login"),
    "it": ("Mittente in chat", "Autore del forum", "Nickname di gioco", "Alias del profilo sociale",
           "Mittente del messaggio", "Persona menzionata", "Nome visualizzato", "Parte locale email usata come login"),
    "es": ("Autor del chat", "Autor del foro", "Alias de juego", "Alias del perfil social",
           "Remitente del mensaje", "Persona mencionada", "Usuario visible", "Parte local del correo como acceso"),
}


def positive_specs():
    yield from (("v6_contact_ribbons", i) for i in range(6))
    yield from (("v6_lending_letters", i) for i in range(2))
    for family, count in zip(RESERVED, (4, 4, 4, 3, 3)):
        yield from ((family, i) for i in range(count))
    for family, count in (("v6_screen_identities", 8), ("v6_life_stage_cards", 8),
                          ("v6_introduction_cues", 6), ("v6_delivery_instructions", 4),
                          ("v6_payment_memos", 4), ("v6_document_wallets", 4)):
        yield from ((family, i) for i in range(count))


def make_positive(lang, serial, family, variant, rng, formats):
    x = LEX[lang]
    style = variant
    if family == "v6_introduction_cues":
        style += 2  # Dedicated name rows plus ribbons cover all eight layouts.
    if family == "v6_delivery_instructions":
        style += 4
    if family == "v6_lending_letters":
        style += 6  # Cover compact and nonbreaking-space telephone formats too.
    source_lang = LANGUAGES[(LANGUAGES.index(lang) + 1) % 5] if family == "v6_crossborder_handoffs" else lang
    values, forms = invented_values(source_lang, serial, style, rng)
    row = Row(lang, family, serial, formats)
    if family == "v6_contact_ribbons":
        row.add(x["contact"] + "\n")
        for i, label in enumerate(("PERSONNAME", "ADDRESS", "TELEPHONENUM")):
            row.value(label, values[label], forms[label])
            row.add((" | ", "\n", " ; ", "\t", " — ", " / ")[variant] if i < 2 else "\n")
    elif family == "v6_lending_letters":
        row.add(x["hello"] + " ").value("PERSONNAME", values["PERSONNAME"], forms["PERSONNAME"]).add(",\n\n")
        row.add(x["preamble"] + "\n\n")
        for block in range(4):
            for offset in range(4):
                row.add(x["paragraphs"][(offset + variant + block) % 4] + "\n\n")
            if block == 0:
                row.add(x["contact"] + "\n").entries(values, ("ADDRESS", "TELEPHONENUM"), forms)
            elif block == 1:
                row.entries(values, ("EMAIL", "USERNAME"), forms)
            elif block == 2:
                row.entries(values, ("PERSONALREF", "DATEOFBIRTH"), forms)
        row.add(x["person"] + ": ").value("PERSONNAME", values["PERSONNAME"], forms["PERSONNAME"]).add("\n")
    elif family == "v6_intake_slips":
        # Four different administrative layouts, each covers a different label quartet.
        row.add(x["contact"] + "\n" + ("[ ] ", "┌───┐\n", ":: ", "« ")[variant])
        labels = LABELS[variant * 4:variant * 4 + 4]
        row.entries(values, labels, forms, ("\n[ ] ", "\n│ ", " ; ", " »\n« ")[variant])
    elif family == "v6_lobby_dialogues":
        row.add(x["chat"] + " ").value("USERNAME", values["USERNAME"], forms["USERNAME"]).add("\n> ")
        row.entries(values, ("PERSONNAME", "AGE", "EMAIL" if variant % 2 else "TELEPHONENUM"), forms, " ; ")
    elif family == "v6_correspondence_footers":
        row.add(x["preamble"] + "\n\n—\n")
        row.value("PERSONNAME", values["PERSONNAME"], forms["PERSONNAME"]).add("\n")
        row.entries(values, ("ADDRESS", "TELEPHONENUM", "EMAIL", "USERNAME"), forms, "\n↳ ")
    elif family == "v6_crossborder_handoffs":
        row.add(x["receipt"] + "\n" + x["contact"] + "\n")
        row.entries(values, ("PERSONNAME", "ADDRESS", "TELEPHONENUM", "IBAN", "PASSPORTNUM"), forms)
    elif family == "v6_scan_transcriptions":
        row.add(x["receipt"] + "\n¦  ")
        labels = (("PERSONNAME", "ADDRESS", "TELEPHONENUM"),
                  ("IDCARDNUM", "TAXNUM", "SOCIALNUM"),
                  ("USERNAME", "EMAIL", "IBAN"))[variant]
        for label in labels:
            value = values[label]
            if label == "PERSONNAME":
                value = value.replace(" ", "", 1)
                form = "ocr_missing_space"
            else:
                at = max(2, len(value) // 2)
                value = value[:at] + "\n" + value[at:]
                form = "ocr_internal_newline"
            row.add(field(lang, label) + " : ").value(label, value, form).add("\n¦  ")
    elif family == "v6_screen_identities":
        context = DIGITAL_CONTEXTS[lang][variant]
        row.add(context + " [").value("USERNAME", values["USERNAME"], "context_" + str(variant)).add("]\n")
        if variant == 0:
            row.add("<").value("USERNAME", values["USERNAME"], "repeated_chat_speaker").add("> ")
        row.entries(values, ("EMAIL",), forms)
    elif family == "v6_life_stage_cards":
        row.add(x["person"] + " ").value("PERSONNAME", values["PERSONNAME"], forms["PERSONNAME"]).add("; ")
        age = x["age_words"][variant // 2] if variant % 2 else str((27, 32, 46, 61)[variant // 2])
        template = x["age"][variant % 6]
        before, after = template.split("{}")
        row.add(before).value("AGE", age, "words" if variant % 2 else "digits").add(after + "; ")
        row.add(x["born"] + " ").value("DATEOFBIRTH", values["DATEOFBIRTH"], forms["DATEOFBIRTH"]).add(".\n")
    elif family == "v6_introduction_cues":
        row.add(x["hello"] + " ").value("PERSONNAME", values["PERSONNAME"], forms["PERSONNAME"]).add(",\n")
        row.add(x["preamble"] + "\n")
    elif family == "v6_delivery_instructions":
        row.add(x["contact"] + "\n").entries(values, ("ADDRESS",), forms)
    elif family == "v6_payment_memos":
        row.add(x["account"] + "\n").entries(values, ("IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER"), forms)
    elif family == "v6_document_wallets":
        row.add(x["receipt"] + "\n").entries(values, LABELS[8:14], forms, " ; ")
    else:
        raise FreezeError("unknown_positive_family")
    return row.data


def make_clean(lang, serial, family, variant, formats):
    x = LEX[lang]
    row = Row(lang, family, serial, formats)
    if family == "v6_stock_grids":
        sep = (" | ", "\t", ";", " / ")[variant % 4]
        row.add(x["stock"] + f"; {variant + 1}\n")
        row.add(sep.join(("SKU", x["unit"], "mm", "g")) + "\n")
        for j in range(4):
            row.add(sep.join((f"SLAB-{lang.upper()}-{variant:02d}-{j}",
                              str(variant * 7 + j + 2), f"{j+1}.25", f"{variant+2}.50")) + "\n")
    elif family == "v6_measurement_notebooks":
        row.add(x["numeric"] + f"; {variant + 1}\n")
        details = (
            f"{120 + variant} mm × {72 + variant} mm × 4 mm; 3.750 kg; ±0.25 mm",
            f"2027-04-{variant + 10:02d} 14:32:08; UTC+02:00; 240 s; 60 Hz",
            f"2.4e-6 A; 9.81 m/s²; {18 + variant}.5 °C; 101.325 kPa",
            f"[{variant}, {variant+1}, {variant+2}]; 1:4; 25%; 0.004 mol/L",
            f"range {variant*10}–{variant*10+25} µm; lot 000-{variant:03d}; 8 × 12 grid",
            f"07:15 → 09:45; cycle {variant+1}; 00:02:30; 480 rpm")
        row.add(details[variant % 6] + "\n")
    elif family == "v6_object_lookalikes":
        kind = variant % 10
        edition = variant // 10
        serial_digits = f"{710000000 + serial * 103 + edition:09d}"
        # Personal-value shapes, with explicit object/public-location linkage.
        # No valid email, actual IBAN, person, user account or personal reference.
        shapes = (
            f"+00 (0) 000 {serial_digits[:3]} {serial_digits[3:]} mV",
            f"198{edition + 2}-07-{17 + edition}",
            x["age"][1].format(x["age_words"][edition]),
            ("Vellora Quensteel", "Nerovin Paleglass")[edition],
            f"{x['public']}: {x['street']} {900+serial}, {x['postcode']} {x['city']}, {x['country']}",
            " ".join(("9" + serial_digits + "000017")[i:i+4] for i in range(0, 16, 4)),
            "YY71 " + serial_digits[:4] + " " + serial_digits[4:] + " 0000 0071",
            "QV-" + serial_digits[:3] + "-" + serial_digits[3:],
            serial_digits[:4] + "/" + serial_digits[4:] + "/07",
            serial_digits[:3] + "-" + serial_digits[3:5] + "-" + serial_digits[5:])
        row.add(x["object"] + ".\n" + x["kinds"][kind] + " = " + shapes[kind] + "\n")
        formats["clean_lookalike/" + str(kind)] += 1
    elif family == "v6_process_bulletins":
        row.add(x["bulletin"] + f" [{variant + 1}]\n")
        row.add(x["paragraphs"][variant % 4] + "\n")
        row.add(x["paragraphs"][(variant // 4 + 1) % 4] + "\n")
    else:
        raise FreezeError("unknown_clean_family")
    return row.data


def build_rows():
    rng, rows, formats = random.Random(SEED), [], Counter()
    specs = list(positive_specs())
    require(len(specs) == 60, "positive_plan_count")
    for lang in LANGUAGES:
        for serial, (family, variant) in enumerate(specs):
            rows.append(make_positive(lang, serial, family, variant, rng, formats))
        serial = len(specs)
        for family, total in CLEAN.items():
            for variant in range(total // len(LANGUAGES)):
                rows.append(make_clean(lang, serial, family, variant, formats))
                serial += 1
        require(serial == 120, "language_plan_count")
    rng.shuffle(rows)
    return rows, dict(sorted(formats.items()))


def encode_rows(rows):
    return b"".join((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                    for row in rows)


def read_policy():
    policy = json.loads(POLICY.read_bytes())
    require(policy.get("policy_version") == "privacy-policy-v1", "policy_version")
    require(policy.get("synthetic_only") is True, "policy_synthetic")
    require(tuple(policy.get("labels", ())) == LABELS, "policy_labels")
    require(set(policy.get("row_schema", ())) == {"case_id", "family", "gold", "language", "split", "text"},
            "policy_row_schema")
    require(set(policy.get("gold_span_schema", ())) == {"start", "end", "label"}, "policy_span_schema")
    rules = policy.get("gold_boundaries", {})
    require(rules.get("ordered") is True and rules.get("non_overlapping") is True, "policy_gold_rules")
    require(rules.get("uncertain_person_linkage") == "mask", "policy_linkage")
    require(rules.get("checksum_confidence_or_detector_disagreement_declassifies") is False, "policy_checksum")
    require(policy.get("reserved_v4_families") == list(RESERVED.values()), "policy_reserved")
    return policy


def validate_gold_value(text, span):
    a, b, label = span["start"], span["end"], span["label"]
    value = text[a:b]
    require(value and value == value.strip(), "gold_outer_whitespace")
    require(not value.endswith((",", ";", ":", ".", "!", "?")), "gold_sentence_punctuation")
    # A value cannot be clipped within a Unicode letter/number token.
    require(not (a > 0 and text[a-1].isalnum() and value[0].isalnum()), "gold_start_clipped")
    require(not (b < len(text) and text[b].isalnum() and value[-1].isalnum()), "gold_end_clipped")
    compact = re.sub(r"[\s/-]", "", value)
    if label == "EMAIL":
        require(re.fullmatch(r"[A-Za-z0-9_.-]+@postbox-v6\.invalid", re.sub(r"\s", "", value)) is not None,
                "gold_email_rule")
    elif label == "USERNAME":
        require(re.fullmatch(r"@?[A-Za-z0-9_.#-]+", compact) is not None, "gold_username_rule")
        require("quartzling" in compact.lower(), "gold_username_pool")
        require(a == 0 or text[a-1] != "@", "gold_handle_sigil")
    elif label == "AGE":
        words = {word for x in LEX.values() for word in x["age_words"]}
        require(value in words or (value.isdecimal() and 1 <= int(value) <= 130), "gold_age_rule")
    elif label == "IBAN":
        lengths = {"GB": 22, "DE": 22, "FR": 27, "IT": 27, "ES": 24}
        require(re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]+", compact) is not None, "gold_iban_shape")
        require(len(compact) == lengths.get(compact[:2]), "gold_iban_length")
    elif label in ("ACCOUNTNUM", "CREDITCARDNUMBER"):
        require(compact.isdecimal(), "gold_financial_shape")
        require(len(compact) == (16 if label == "CREDITCARDNUMBER" else 15), "gold_financial_length")
    elif label in LABELS[8:14]:
        require(compact.isalnum() and any(c.isdigit() for c in compact), "gold_identifier_rule")
    elif label == "DATEOFBIRTH":
        require(re.fullmatch(r"(?:\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4}|\d{2} · \d{2} · \d{4})", value) is not None,
                "gold_birthdate_rule")
    elif label == "TELEPHONENUM":
        require(sum(c.isdecimal() for c in value) >= 10, "gold_phone_rule")
        # Extension phrases are inside the literal and therefore inside the gold.
        extensions = ("extension", "Durchwahl", "poste", "interno", "extensión")
        tail = text[b:]
        require(not any(tail.startswith(" " + ext) for ext in extensions), "gold_phone_extension")
    elif label == "ADDRESS":
        flat = "".join(value.split())
        require(any("".join(x["city"].split()) in flat and "".join(x["country"].split()) in flat
                    for x in LEX.values()), "gold_address_route")
        require(any("".join(x["street"].split()) in flat or "".join(x["box"].split()) in flat
                    for x in LEX.values()), "gold_address_complete")
    elif label == "PERSONNAME":
        require(any(s in value or s.upper() in value for x in LEX.values() for s in x["surname"]), "gold_name_pool")


def validate_rows(rows: list[dict[str, Any]], policy: dict[str, Any], formats: dict[str, int]) -> dict[str, Any]:
    require(isinstance(rows, list) and len(rows) == 600, "row_count")
    ids, texts = set(), set()
    labels, languages, families = Counter(), Counter(), Counter()
    breakdown: dict[str, dict[str, Any]] = {
        lang: dict(rows=0, positive_rows=0, clean_rows=0, per_label=Counter(), per_family=Counter())
        for lang in LANGUAGES}
    positive = reserved = adjacent = letters = 0
    expected_families = {family for family, _ in positive_specs()} | set(CLEAN)
    require(not expected_families & HISTORICAL_NAMES, "historical_family_reuse")
    for row in rows:
        require(type(row) is dict and set(row) == set(policy["row_schema"]), "row_schema")
        lang, family, text = row["language"], row["family"], row["text"]
        require(type(lang) is str and lang in LANGUAGES and row["split"] == "blind", "row_language_split")
        require(type(family) is str and family in expected_families, "row_family")
        require(type(row["case_id"]) is str and re.fullmatch(r"blind-v6-" + lang + r"-\d{3}", row["case_id"]), "case_id_schema")
        require(row["case_id"] not in ids, "case_id_duplicate")
        ids.add(row["case_id"])
        require(type(text) is str and text and text not in texts, "text_empty_or_duplicate")
        texts.add(text)
        gold = row["gold"]
        require(type(gold) is list, "gold_list")
        previous: Any = 0
        for span in gold:
            require(type(span) is dict and set(span) == set(policy["gold_span_schema"]), "span_schema")
            a, b, label = span["start"], span["end"], span["label"]
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(text), "span_offsets")
            require(a >= previous and type(label) is str and label in LABELS, "span_order_label")
            previous = b
            validate_gold_value(text, span)
            labels[label] += 1
            breakdown[lang]["per_label"][label] += 1
        is_positive = bool(gold)
        require(is_positive == (family not in CLEAN), "family_gold_status")
        positive += is_positive
        reserved += is_positive and family in RESERVED
        languages[lang] += 1
        families[family] += 1
        breakdown[lang]["rows"] += 1
        breakdown[lang]["positive_rows" if is_positive else "clean_rows"] += 1
        breakdown[lang]["per_family"][family] += 1
        if family == "v6_contact_ribbons":
            require([s["label"] for s in gold] == ["PERSONNAME", "ADDRESS", "TELEPHONENUM"], "adjacent_three_spans")
            require(all(text[left["end"]:right["start"]] in (" | ", "\n", " ; ", "\t", " — ", " / ")
                        for left, right in zip(gold, gold[1:])), "adjacent_separator")
            adjacent += 1
        if family == "v6_lending_letters":
            require(len(text) >= 2000, "long_letter_length")
            names = [text[s["start"]:s["end"]] for s in gold if s["label"] == "PERSONNAME"]
            require(len(names) == 2 and names[0] == names[1], "repeated_name_occurrences")
            letters += 1
        if not is_positive:
            require("@" not in text, "clean_no_email_or_handle")
            require(text.startswith(LEX[lang][{"v6_stock_grids": "stock", "v6_measurement_notebooks": "numeric",
                                             "v6_object_lookalikes": "object", "v6_process_bulletins": "bulletin"}[family]]),
                    "clean_object_context")
    require(positive == 300 and reserved == 90, "positive_reserved_counts")
    require(adjacent == 30 and letters == 10, "special_row_counts")
    require(set(labels) == set(LABELS) and min(labels.values()) >= 20, "label_minimum")
    require(dict(languages) == dict.fromkeys(LANGUAGES, 120), "language_counts")
    require(all(b["positive_rows"] == b["clean_rows"] == 60 for b in breakdown.values()), "language_balance")
    require({family: families[family] for family in CLEAN} == CLEAN, "clean_quota")
    require({family: families[family] for family in RESERVED} == dict(zip(RESERVED, (20, 20, 20, 15, 15))), "reserved_quota")
    for label in ("PERSONNAME", "ADDRESS", "TELEPHONENUM"):
        require(all(formats.get(f"{label}/layout_{i}", 0) >= 5 for i in range(8)), "eight_value_layouts")
    require(all(formats.get(f"USERNAME/context_{i}", 0) == 5 for i in range(8)), "username_contexts")
    require(formats.get("AGE/words") == formats.get("AGE/digits") == 20, "age_word_digit_counts")
    require(all(formats.get(f"clean_lookalike/{i}", 0) == 10 for i in range(10)), "lookalike_shape_counts")
    return dict(rows=len(rows), positive_rows=positive, clean_rows=len(rows) - positive,
                gold_spans=sum(labels.values()), per_label=dict(sorted(labels.items())),
                per_language=dict(sorted(languages.items())), per_family=dict(sorted(families.items())),
                per_language_breakdown=breakdown, reserved_positive_rows=reserved,
                adjacent_contact_rows=adjacent, long_letter_rows=letters)


def frozen_manifest(blob, counts, formats, policy):
    return {
        "dataset": "masking-stress-v6", "schema_version": 1,
        "path": str(DATA.relative_to(ROOT)), "sha256": digest(blob), "bytes": len(blob),
        "generator": str(Path(__file__).resolve().relative_to(ROOT)),
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "seed": SEED, "policy": str(POLICY.relative_to(ROOT)),
        "policy_sha256": digest(POLICY.read_bytes()), "policy_version": policy["policy_version"],
        "split": "blind", "blind_status": "frozen_unmeasured", "synthetic_only": True,
        "usage_rule": "measure once per profile+model; never tune on v6",
        "counts": counts, "per_format_spans": formats,
        "reserved_family_mapping": RESERVED, "clean_family_counts": CLEAN,
        "gold_rules": policy["gold_boundaries"],
        "annotation_method": "Typed whole-value literals; original Python str offsets; no detector or model assistance.",
        "email_local_part_rule": "Whole email is EMAIL only; a separately stated login is USERNAME; no nested spans.",
        "address_rule": "Complete routing region including c/o recipient, floor/unit and country; no nested name span.",
        "age_rule": "Digits or complete number-word phrase; age cue words and outer brackets excluded.",
        "checksum_rule": "Invalid checksums do not declassify person-linked identifiers; both card variants are present.",
        "independence": {
            "authored_for": "v6", "templates_and_value_pools": "new independently invented synthetic literals",
            "historical_access": "v4/v5 manifest family/format names only, used solely to avoid family-name reuse",
            "prohibited_access": "No training generators, prior set generators, run artifacts or model outputs read.",
            "generation_inputs": ["this generator", "configs/privacy-policy-v1.json"],
        },
        "verification": "Exact deterministic JSONL bytes, manifest, hashes, schema, gold boundaries, label/language/family quotas and format coverage.",
    }


def verify():
    require(DATA.is_file() and MANIFEST.is_file() and not DATA.is_symlink() and not MANIFEST.is_symlink(),
            "freeze_files_missing_or_symlink")
    policy = read_policy()
    blob = DATA.read_bytes()
    require(blob.endswith(b"\n") and b"\r" not in blob, "jsonl_byte_rules")
    lines = blob.decode("utf-8").splitlines()
    require(len(lines) == 600 and all(lines), "jsonl_line_count")
    rows = [json.loads(line) for line in lines]
    expected, formats = build_rows()
    counts = validate_rows(rows, policy, formats)
    # Reassembly checks semantic boundary fidelity including internal separators,
    # attached titles, sigils, phone extensions and repeated mentions.
    require(rows == expected and blob == encode_rows(expected), "deterministic_bytes_or_gold")
    manifest = json.loads(MANIFEST.read_bytes())
    require(manifest == frozen_manifest(blob, counts, formats, policy), "manifest_binding")
    return counts


def create():
    # A committed manifest can recreate an absent ignored JSONL, but neither
    # an existing dataset nor a frozen manifest is ever overwritten.
    require(not DATA.exists() and not DATA.is_symlink() and not MANIFEST.is_symlink(), "refuse_overwrite")
    policy = read_policy()
    rows, formats = build_rows()
    counts = validate_rows(rows, policy, formats)
    blob = encode_rows(rows)
    manifest = frozen_manifest(blob, counts, formats, policy)
    reuse_manifest = MANIFEST.exists()
    if reuse_manifest:
        require(MANIFEST.is_file() and json.loads(MANIFEST.read_bytes()) == manifest, "manifest_binding")
    DATA.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation guards concurrent custodians too. A partial failure stays
    # visible and cannot be silently regenerated or overwritten.
    with DATA.open("xb") as output:
        output.write(blob)
    if not reuse_manifest:
        with MANIFEST.open("xb") as output:
            output.write((json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Read-only verification of the frozen JSONL and manifest")
    args = parser.parse_args()
    try:
        counts = verify() if args.verify else create()
    except FreezeError as exc:
        print("V6 ERROR: " + str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        # Never log paths, rows, values, spans or parser fragments on failures.
        print("V6 ERROR: freeze_io_or_schema", file=sys.stderr)
        return 1
    print(("V6 VERIFY OK" if args.verify else "V6 FREEZE OK") +
          f": rows={counts['rows']} positive={counts['positive_rows']} clean={counts['clean_rows']}"
          f" languages=5x120 labels=16 minimum_spans={min(counts['per_label'].values())}"
          f" reserved={counts['reserved_positive_rows']} adjacent={counts['adjacent_contact_rows']}"
          f" long_letters={counts['long_letter_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
