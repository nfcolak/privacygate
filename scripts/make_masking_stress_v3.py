#!/usr/bin/env python3
"""Frozen blind synthetic DEVELOPMENT stress v3; stdlib only, never detects or scores.

Only aggregates and hashes are printed. Whole values are annotated during assembly.
The existing stress validator is extracted with AST to avoid model-bearing imports.
Usage: env -u PYTHONPATH python3 scripts/make_masking_stress_v3.py [--verify]
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/augmentation/masking-stress-v3-dev.jsonl"
MANIFEST = ROOT / "artifacts/masking-stress-v3/manifest.json"
VERSION = "masking-stress-v3"
SEED = 202610031503
LANGS = ("en", "de", "fr", "it", "es")
SOURCES = (
    "scripts/make_masking_stress.py", "scripts/make_masking_stress_v2.py",
    "scripts/make_window_cut_fixture.py", "scripts/make_positives.py",
)
VALIDATOR_SOURCES = (
    "scripts/measure_masking.py", "privacygate/masking_metrics.py",
    "privacygate/positive_data.py",
)
KINDS = (
    "name_particle", "name_compound", "name_initials", "name_title", "name_reversed",
    "address_routed", "address_box", "address_reverse", "address_unit",
    "phone_trunk", "phone_parenthesized", "phone_dotted",
    "identity_card", "identity_passport", "identity_licence",
    "account_iban", "account_grouped", "online_mail", "online_handle",
    "personal_reference", "repeated_contact", "long_correspondence",
)
CONTROL_KINDS = (
    "product", "order", "invoice", "calendar", "dimensions", "rooms", "brands", "public_places",
)
FAMILY = {
    **{k: "names" for k in KINDS if k.startswith("name_")},
    **{k: "full_address" for k in KINDS if k.startswith("address_")},
    **{k: "phone" for k in KINDS if k.startswith("phone_")},
    **{k: "identity" for k in KINDS if k.startswith("identity_")},
    "account_iban": "account", "account_grouped": "account",
    "online_mail": "multiple_entities", "online_handle": "username",
    "personal_reference": "personalref", "repeated_contact": "repeated_values",
    "long_correspondence": "long_text",
}
# Invented pools, not drawn from any old generator or dataset. Accidental real-world
# collisions remain possible. Public places/brands in clean controls are not people.
GIVEN = {
    "en": ("Aevlina", "Ushavor", "Xelthira", "Isphelwen"),
    "de": ("Äsdrike", "Uspfried", "Eschlinde", "Ösquard"),
    "fr": ("Ébrélyne", "Isphéon", "Aesprielle", "Ushévin"),
    "it": ("Isqelina", "Asprunio", "Esvellia", "Usharino"),
    "es": ("Añesvira", "Isquelio", "Asprunda", "Ushavina"),
}
SURNAME = {
    "en": ("Rhespwick", "Ushcairn", "Ispherton", "Aesquell"),
    "de": ("Oszquardt", "Eschbrück", "Ushwieser", "Äsquenthal"),
    "fr": ("Tréspivaux", "Ushérande", "Isquelonne", "Aesprémont"),
    "it": ("Frascuelli", "Usharenti", "Isquelotti", "Aespraldi"),
    "es": ("Ñervazul", "Ushavides", "Isquelosa", "Aespruel"),
}
STREET = {
    "en": "Eshbracken Crescent", "de": "Feskquarzstieg",
    "fr": "allée des Esquilles", "it": "salita Fesquilari", "es": "travesía Esquilanda",
}
CITY = {"en": "Eshwickmere", "de": "Fesklingen", "fr": "Esquillâtre", "it": "Esquilvento", "es": "Esquilonda"}
PARTICLE = {"en": "van der", "de": "von der", "fr": "de la", "it": "della", "es": "de los"}
TITLES = {"en": ("Dr.", "Prof."), "de": ("Frau", "Prof. Dr."), "fr": ("Mme", "Dr"), "it": ("Sig.ra", "Prof.ssa"), "es": ("Dra.", "Prof.")}
UNIT = {"en": "floor 5 / flat 8C", "de": "Etage 5 / Wohnung 8C", "fr": "5e étage / appt 8C", "it": "quinto piano / int. 8C", "es": "planta quinta / puerta 8C"}
BOX = {"en": "PO Box", "de": "Postfach", "fr": "boîte postale", "it": "casella postale", "es": "apartado postal"}
COUNTRY = {"en": "Ireland", "de": "Luxemburg", "fr": "Belgique", "it": "San Marino", "es": "Andorra"}
DIAL = {"en": "44", "de": "49", "fr": "33", "it": "39", "es": "34"}
IBAN_CC = {"en": "GB", "de": "DE", "fr": "FR", "it": "IT", "es": "ES"}
IBAN_LENGTH = {"en": 22, "de": 22, "fr": 27, "it": 27, "es": 24}
HANDLE = {"en": "ashenbadger", "de": "aschendachs", "fr": "blaireaucendre", "it": "tassocenere", "es": "tejonceniza"}

# Each tuple is EN/DE/FR/IT/ES. No v1/v2 diagnostic opening or optics filler is reused.
TEMPLATES = {
    "name_particle": (
        "The fictional witness signs the final paragraph as {name}; the preceding draft contains no signature.",
        "Die erfundene Zeugin unterschreibt den letzten Absatz mit {name}; im Entwurf fehlt die Unterschrift.",
        "La témoin fictive signe le dernier paragraphe sous le nom {name} ; le brouillon reste sans signature.",
        "La testimone inventata firma l'ultimo paragrafo come {name}; la bozza resta senza firma.",
        "La testigo inventada firma el párrafo final como {name}; el borrador queda sin firma.",
    ),
    "name_compound": (
        "Within this invented dialogue, the speaker introduces herself as {name} before discussing the weather.",
        "In diesem erfundenen Dialog stellt sich die Sprecherin als {name} vor, bevor sie über das Wetter spricht.",
        "Dans ce dialogue inventé, la locutrice se présente comme {name} avant de parler du temps.",
        "In questo dialogo inventato, la voce si presenta come {name} prima di parlare del tempo.",
        "En este diálogo inventado, la hablante se presenta como {name} antes de hablar del tiempo.",
    ),
    "name_initials": (
        "The personal signature on the imagined consent note reads {name}, with abbreviated given names.",
        "Die persönliche Unterschrift auf der erfundenen Einwilligung lautet {name}, mit abgekürzten Vornamen.",
        "La signature personnelle sur le consentement imaginaire est {name}, avec les prénoms abrégés.",
        "La firma personale sul consenso immaginario è {name}, con i nomi abbreviati.",
        "La firma personal del consentimiento imaginario dice {name}, con los nombres abreviados.",
    ),
    "name_title": (
        "The salutation in a letter to the invented individual is addressed to {name}; retain neither title nor name.",
        "Die Anrede im Brief an die erfundene Einzelperson richtet sich an {name}; weder Titel noch Name sollen bleiben.",
        "La formule d'appel de la lettre à la personne inventée s'adresse à {name} ; ni titre ni nom ne doivent rester.",
        "L'intestazione della lettera alla persona inventata è rivolta a {name}; non conservare titolo o nome.",
        "El saludo de la carta a la persona inventada va dirigido a {name}; no conservar título ni nombre.",
    ),
    "name_reversed": (
        "The invented applicant's personal signature is transcribed in surname-first order: {name}; this is not a catalogue entry.",
        "Die persönliche Unterschrift der erfundenen Antragstellerin wird mit Nachnamen zuerst übertragen: {name}; kein Katalogeintrag.",
        "La signature personnelle de la candidate inventée est transcrite avec le patronyme en premier : {name} ; ce n'est pas un catalogue.",
        "La firma personale della candidata inventata è trascritta con il cognome prima: {name}; non è un catalogo.",
        "La firma personal de la solicitante inventada se transcribe con el apellido primero: {name}; no es un catálogo.",
    ),
    "address_routed": (
        "For the invented tenant's private letters, copy the entire routing destination {address} into the sealed envelope.",
        "Für private Briefe an die erfundene Mieterin wird das gesamte Zustellziel {address} auf den verschlossenen Umschlag kopiert.",
        "Pour les lettres privées de la locataire inventée, recopier toute la destination {address} sur l'enveloppe fermée.",
        "Per le lettere private dell'inquilina inventata, copiare tutta la destinazione {address} sulla busta chiusa.",
        "Para las cartas privadas de la inquilina inventada, copiar todo el destino {address} en el sobre cerrado.",
    ),
    "address_box": (
        "The invented resident receives personal correspondence exclusively at {address}, rather than at a street door.",
        "Die erfundene Bewohnerin erhält persönliche Korrespondenz ausschließlich unter {address}, nicht an einer Haustür.",
        "La résidente inventée reçoit sa correspondance personnelle uniquement à {address}, et non à une porte de rue.",
        "La residente inventata riceve la corrispondenza personale soltanto presso {address}, non a un portone.",
        "La residente inventada recibe correspondencia personal únicamente en {address}, no en una puerta de calle.",
    ),
    "address_reverse": (
        "Her invented home destination, written from country down to apartment, is {address}; it is a single mailing address.",
        "Ihr erfundenes Wohnziel, vom Land bis zur Wohnung geschrieben, lautet {address}; es ist eine einzige Postanschrift.",
        "Son domicile inventé, écrit du pays jusqu'à l'appartement, est {address} ; il s'agit d'une seule adresse postale.",
        "Il suo domicilio inventato, scritto dal paese all'appartamento, è {address}; è un unico indirizzo postale.",
        "Su domicilio inventado, escrito desde el país hasta la vivienda, es {address}; es una sola dirección postal.",
    ),
    "address_unit": (
        "In the imagined relocation letter, her complete new home is given as {address}, including the floor and unit.",
        "Im erfundenen Umzugsbrief wird ihre vollständige neue Wohnung als {address} angegeben, einschließlich Etage und Einheit.",
        "Dans la lettre de déménagement imaginaire, son nouveau domicile complet est {address}, étage et logement compris.",
        "Nella lettera di trasloco immaginaria, la sua nuova abitazione completa è {address}, compresi piano e unità.",
        "En la carta de mudanza imaginaria, su nuevo domicilio completo es {address}, incluidos planta y vivienda.",
    ),
    "phone_trunk": (
        "A fictional individual requested a private callback on {phone}; include the optional trunk notation and extension.",
        "Eine erfundene Einzelperson bat um privaten Rückruf unter {phone}; die optionale Vorwahl und Durchwahl gehören dazu.",
        "Une personne fictive demande un rappel privé au {phone} ; la notation de préfixe facultatif et le poste font partie du numéro.",
        "Una persona fittizia richiede una chiamata privata al {phone}; prefisso facoltativo e interno fanno parte del numero.",
        "Una persona ficticia solicita una llamada privada al {phone}; el prefijo opcional y la extensión forman parte del número.",
    ),
    "phone_parenthesized": (
        "The imagined resident whispered her private telephone as {phone} and then ended the conversation.",
        "Die erfundene Bewohnerin nannte ihr privates Telefon leise als {phone} und beendete dann das Gespräch.",
        "La résidente imaginaire a murmuré son téléphone privé {phone} puis a terminé la conversation.",
        "La residente immaginaria ha sussurrato il telefono privato {phone} e poi ha chiuso la conversazione.",
        "La residente imaginaria susurró su teléfono privado {phone} y terminó la conversación.",
    ),
    "phone_dotted": (
        "For a fictional personal appointment, the return-call number was dictated as {phone}, not as a stock code.",
        "Für einen erfundenen persönlichen Termin wurde die Rückrufnummer als {phone} diktiert, nicht als Artikelcode.",
        "Pour un rendez-vous personnel fictif, le numéro de rappel a été dicté comme {phone}, et non comme une référence produit.",
        "Per un appuntamento personale fittizio, il numero da richiamare è stato dettato come {phone}, non come codice articolo.",
        "Para una cita personal ficticia, el número de devolución de llamada se dictó como {phone}, no como código de producto.",
    ),
    "identity_card": (
        "The fictional applicant privately copied her identity-card number {idcard} from the document into the reply.",
        "Die erfundene Antragstellerin übertrug ihre Personalausweisnummer {idcard} privat aus dem Dokument in die Antwort.",
        "La candidate fictive a recopié en privé le numéro de sa carte d'identité {idcard} dans sa réponse.",
        "La candidata fittizia ha copiato privatamente il numero della carta d'identità {idcard} nella risposta.",
        "La solicitante ficticia copió en privado el número de su documento de identidad {idcard} en la respuesta.",
    ),
    "identity_passport": (
        "In the imagined application, her own passport is identified by {passport}; the punctuation is part of its number.",
        "Im erfundenen Antrag wird ihr eigener Reisepass durch {passport} bezeichnet; die Satzzeichen gehören zur Nummer.",
        "Dans la demande imaginaire, son passeport personnel est identifié par {passport} ; la ponctuation appartient au numéro.",
        "Nella domanda immaginaria, il suo passaporto personale è identificato da {passport}; la punteggiatura appartiene al numero.",
        "En la solicitud imaginaria, su pasaporte personal se identifica por {passport}; la puntuación pertenece al número.",
    ),
    "identity_licence": (
        "The invented driver included the personal driving-licence identifier {licence} in a confidential note.",
        "Die erfundene Fahrerin nahm die persönliche Führerscheinkennung {licence} in eine vertrauliche Notiz auf.",
        "La conductrice inventée a inscrit son identifiant personnel de permis de conduire {licence} dans une note confidentielle.",
        "La conducente inventata ha inserito l'identificativo personale della patente {licence} in una nota riservata.",
        "La conductora inventada incluyó su identificador personal del permiso de conducir {licence} en una nota confidencial.",
    ),
    "account_iban": (
        "In the fictional reimbursement request, the private bank account of {name} is written as IBAN {iban} for the transfer.",
        "Im erfundenen Erstattungsantrag wird das private Bankkonto von {name} für die Überweisung als IBAN {iban} angegeben.",
        "Dans la demande fictive de remboursement, le compte bancaire privé de {name} est écrit IBAN {iban} pour le virement.",
        "Nella richiesta fittizia di rimborso, il conto bancario privato di {name} è scritto come IBAN {iban} per il bonifico.",
        "En la solicitud ficticia de reembolso, la cuenta bancaria privada de {name} se escribe como IBAN {iban} para la transferencia.",
    ),
    "account_grouped": (
        "The imagined individual linked her private savings account {account} to the signed request, preserving its spaces.",
        "Die erfundene Einzelperson verknüpfte ihr privates Sparkonto {account} mit dem unterschriebenen Antrag, einschließlich Leerzeichen.",
        "La personne imaginaire a lié son compte d'épargne privé {account} à la demande signée, en conservant les espaces.",
        "La persona immaginaria ha collegato il conto di risparmio privato {account} alla richiesta firmata, conservando gli spazi.",
        "La persona imaginaria vinculó su cuenta de ahorro privada {account} a la solicitud firmada, conservando los espacios.",
    ),
    "online_mail": (
        "After the fictional conversation, {name} asked for a private reply at {email} instead of a public announcement.",
        "Nach dem erfundenen Gespräch bat {name} um eine private Antwort an {email} statt einer öffentlichen Bekanntmachung.",
        "Après la conversation fictive, {name} a demandé une réponse privée à {email} plutôt qu'une annonce publique.",
        "Dopo la conversazione fittizia, {name} ha chiesto una risposta privata a {email} invece di un annuncio pubblico.",
        "Tras la conversación ficticia, {name} pidió una respuesta privada a {email} en vez de un anuncio público.",
    ),
    "online_handle": (
        "In this fictional diary, the writer uses the personal login {handle} when signing in, not a product label.",
        "In diesem erfundenen Tagebuch benutzt die Verfasserin beim Anmelden den persönlichen Login {handle}, keine Produktbezeichnung.",
        "Dans ce journal fictif, l'autrice utilise la connexion personnelle {handle}, et non une étiquette de produit.",
        "In questo diario fittizio, l'autrice usa l'accesso personale {handle}, non un'etichetta di prodotto.",
        "En este diario ficticio, la autora usa el acceso personal {handle}, no una etiqueta de producto.",
    ),
    "personal_reference": (
        "The fictional individual's personal appeal is filed under {reference}; the reference points to that person's case.",
        "Der persönliche Einspruch der erfundenen Einzelperson wird unter {reference} geführt; die Referenz gehört zu ihrem Fall.",
        "Le recours personnel de la personne fictive est classé sous {reference} ; cette référence désigne son dossier.",
        "Il ricorso personale della persona fittizia è archiviato sotto {reference}; il riferimento riguarda la sua pratica.",
        "El recurso personal de la persona ficticia se archiva bajo {reference}; la referencia corresponde a su expediente.",
    ),
    "repeated_contact": (
        "The invented note first calls the signatory {name}, records the private callback {phone}, then repeats {name} and {phone} verbatim.",
        "Die erfundene Notiz nennt die Unterzeichnerin zunächst {name}, notiert den privaten Rückruf {phone} und wiederholt {name} sowie {phone} wörtlich.",
        "La note inventée nomme d'abord la signataire {name}, inscrit le rappel privé {phone}, puis répète {name} et {phone} à l'identique.",
        "La nota inventata chiama prima la firmataria {name}, registra la chiamata privata {phone}, poi ripete {name} e {phone} alla lettera.",
        "La nota inventada nombra primero a la firmante {name}, registra la llamada privada {phone} y repite {name} y {phone} literalmente.",
    ),
}
SLOTS = {
    "name": "PERSONNAME", "address": "ADDRESS", "phone": "TELEPHONENUM",
    "idcard": "IDCARDNUM", "passport": "PASSPORTNUM", "licence": "DRIVERLICENSENUM",
    "iban": "IBAN", "account": "ACCOUNTNUM", "email": "EMAIL",
    "handle": "USERNAME", "reference": "PERSONALREF",
}
# Unambiguously non-personal controls: orders are unassigned stock-restocking
# batches, invoices are impersonal examples, rooms/building ages are not human ages.
CONTROLS = {
    "product": (
        "In the catalogue, product code PX/84-702.6 names a replacement hinge; batch SKU 4938 1702 6650 is warehouse stock, not an identity document.",
        "Im Katalog bezeichnet Produktcode PX/84-702.6 ein Ersatzscharnier; Charge SKU 4938 1702 6650 ist Lagerware, kein Ausweisdokument.",
        "Dans le catalogue, le code produit PX/84-702.6 désigne une charnière ; le lot SKU 4938 1702 6650 est du stock, pas un document d'identité.",
        "Nel catalogo, il codice prodotto PX/84-702.6 indica una cerniera; il lotto SKU 4938 1702 6650 è merce, non un documento d'identità.",
        "En el catálogo, el código de producto PX/84-702.6 identifica una bisagra; el lote SKU 4938 1702 6650 es existencias, no un documento de identidad.",
    ),
    "order": (
        "Unassigned warehouse replenishment order WH-673/802-19 contains screws; internal order number 8304 6291 7745 refers only to stock, with no customer attached.",
        "Der unzugeordnete Lager-Nachfüllauftrag WH-673/802-19 enthält Schrauben; interne Bestellnummer 8304 6291 7745 betrifft nur Ware, ohne Kundenbezug.",
        "La commande anonyme de réassort WH-673/802-19 contient des vis ; le numéro interne 8304 6291 7745 concerne uniquement le stock, sans client associé.",
        "L'ordine non assegnato di rifornimento WH-673/802-19 contiene viti; il numero interno 8304 6291 7745 riguarda soltanto scorte, senza cliente.",
        "El pedido sin asignar de reposición WH-673/802-19 contiene tornillos; el número interno 8304 6291 7745 se refiere solo a existencias, sin cliente asociado.",
    ),
    "invoice": (
        "The impersonal invoice arithmetic example has subtotal EUR 1,847.35, tax EUR 369.47 and total EUR 2,216.82; it identifies no buyer or payee.",
        "Das unpersönliche Rechnungsbeispiel hat Zwischensumme EUR 1.847,35, Steuer EUR 369,47 und Gesamt EUR 2.216,82; ohne Käufer oder Empfänger.",
        "L'exemple impersonnel de facture a un sous-total de 1 847,35 EUR, une taxe de 369,47 EUR et un total de 2 216,82 EUR ; aucun acheteur ni bénéficiaire.",
        "L'esempio impersonale di fattura ha imponibile EUR 1.847,35, imposta EUR 369,47 e totale EUR 2.216,82; nessun compratore o beneficiario.",
        "El ejemplo impersonal de factura tiene subtotal EUR 1.847,35, impuesto EUR 369,47 y total EUR 2.216,82; no identifica comprador ni beneficiario.",
    ),
    "calendar": (
        "The public release calendar lists 18/11/2026 at 07:45 UTC for software version 6.14.2, followed by build 2026.11.18; these are not personal dates.",
        "Der öffentliche Veröffentlichungsplan nennt den 18.11.2026 um 07:45 UTC für Softwareversion 6.14.2, danach Build 2026.11.18; keine persönlichen Daten.",
        "Le calendrier public annonce le 18/11/2026 à 07:45 UTC pour la version logicielle 6.14.2, puis la compilation 2026.11.18 ; aucune date personnelle.",
        "Il calendario pubblico indica il 18/11/2026 alle 07:45 UTC per la versione software 6.14.2, poi la build 2026.11.18; non sono date personali.",
        "El calendario público indica 18/11/2026 a las 07:45 UTC para la versión 6.14.2, seguida de la compilación 2026.11.18; no son fechas personales.",
    ),
    "dimensions": (
        "The fabric sample is 40x60 cm, its crate is 48×72×16 cm and the gauge reads 0.875 mm; these are dimensions of objects, never telephone numbers.",
        "Die Stoffprobe misst 40x60 cm, ihre Kiste 48×72×16 cm und die Lehre 0,875 mm; Objektmaße, niemals Telefonnummern.",
        "L'échantillon textile mesure 40x60 cm, sa caisse 48×72×16 cm et la jauge 0,875 mm ; dimensions d'objets, jamais des téléphones.",
        "Il campione di tessuto misura 40x60 cm, la cassa 48×72×16 cm e il calibro 0,875 mm; dimensioni di oggetti, mai numeri telefonici.",
        "La muestra de tela mide 40x60 cm, la caja 48×72×16 cm y el calibre 0,875 mm; dimensiones de objetos, nunca teléfonos.",
    ),
    "rooms": (
        "The museum has 17 exhibition rooms and 6 staircases; its oldest building is 143 years old and the newer annex is 28 years old, not a person's age.",
        "Das Museum hat 17 Ausstellungsräume und 6 Treppenhäuser; das älteste Gebäude ist 143 Jahre alt, der Anbau 28 Jahre, keine Personenalter.",
        "Le musée possède 17 salles et 6 escaliers ; le plus vieux bâtiment a 143 ans et l'annexe 28 ans, pas l'âge d'une personne.",
        "Il museo ha 17 sale e 6 scale; l'edificio più antico ha 143 anni e l'annesso 28 anni, non età di persone.",
        "El museo tiene 17 salas y 6 escaleras; el edificio más antiguo tiene 143 años y el anexo 28 años, no edades de personas.",
    ),
    "brands": (
        "This invented catalogue mentions the fictional brands Eshforge Tools and Ushgrain Ceramics; brand labels identify products, not natural persons.",
        "Dieser erfundene Katalog nennt die fiktiven Marken Eshforge Tools und Ushgrain Ceramics; Marken bezeichnen Produkte, keine natürlichen Personen.",
        "Ce catalogue inventé mentionne les marques fictives Eshforge Tools et Ushgrain Ceramics ; les marques désignent des produits, pas des personnes.",
        "Questo catalogo inventato cita i marchi fittizi Eshforge Tools e Ushgrain Ceramics; i marchi indicano prodotti, non persone fisiche.",
        "Este catálogo inventado menciona las marcas ficticias Eshforge Tools y Ushgrain Ceramics; las marcas identifican productos, no personas físicas.",
    ),
    "public_places": (
        "The public geography exhibit compares Edinburgh Castle, Lake Bled and the Baltic Sea; none is a private residence or a person's location record.",
        "Die öffentliche Geografieausstellung vergleicht Edinburgh Castle, den Bleder See und die Ostsee; keine Privatwohnung oder persönliche Standortaufzeichnung.",
        "L'exposition publique de géographie compare Edinburgh Castle, le lac de Bled et la mer Baltique ; aucun domicile ni relevé de position personnelle.",
        "La mostra pubblica di geografia confronta Edinburgh Castle, il lago di Bled e il Mar Baltico; nessuna abitazione o registrazione di posizione personale.",
        "La exposición pública de geografía compara Edinburgh Castle, el lago de Bled y el mar Báltico; no son domicilios ni registros de ubicación personal.",
    ),
}
# More than 512 whitespace-delimited words, therefore long under ordinary wordpiece
# tokenization, without loading a tokenizer or asserting exact window-cut placement.
FILLER = {
    "en": "Dry clay absorbs water slowly while wet clay bends easily. A rough lump becomes smooth with gentle pressure. These sentences explain pottery materials and contain no account of a person. ",
    "de": "Trockener Ton nimmt Wasser langsam auf und feuchter Ton bleibt weich. Ein rauer Klumpen wird durch sanften Druck glatt. Diese Sätze erklären keramisches Material und beschreiben keine Person. ",
    "fr": "La terre sèche absorbe doucement le liquide et la terre humide reste souple. Une motte rugueuse devient lisse sous une pression légère. Ces phrases décrivent la poterie et aucune personne. ",
    "it": "La terra secca assorbe piano il liquido e la terra umida resta morbida. Un pezzo ruvido diventa liscio sotto una pressione lieve. Queste frasi descrivono la ceramica e nessuna persona. ",
    "es": "La arcilla seca absorbe lentamente el agua y la arcilla húmeda se dobla fácilmente. Un trozo rugoso queda liso bajo presión suave. Estas frases explican la cerámica y no describen ninguna persona. ",
}
LONG_SECTIONS = (
    (
        "The fictional sender signs this private draft as {name}. ",
        "Die erfundene Absenderin unterschreibt diesen privaten Entwurf als {name}. ",
        "L'expéditrice fictive signe ce brouillon privé comme {name}. ",
        "La mittente fittizia firma questa bozza privata come {name}. ",
        "La remitente ficticia firma este borrador privado como {name}. ",
    ),
    (
        "Inside the same private draft, her callback is {phone} and her home destination is {address}. ",
        "Im selben privaten Entwurf lautet ihr Rückruf {phone} und ihr Wohnziel {address}. ",
        "Dans le même brouillon privé, son rappel est {phone} et son domicile {address}. ",
        "Nella stessa bozza privata, la chiamata di ritorno è {phone} e il domicilio {address}. ",
        "En el mismo borrador privado, su llamada de retorno es {phone} y su domicilio {address}. ",
    ),
    (
        "At the very end she repeats her private reply destination {email} and personal case reference {reference}. ",
        "Ganz am Ende wiederholt sie ihr privates Antwortziel {email} und ihr persönliches Aktenzeichen {reference}. ",
        "Tout à la fin elle répète sa destination privée {email} et sa référence personnelle {reference}. ",
        "Alla fine ripete la destinazione privata {email} e il riferimento personale {reference}. ",
        "Al final repite su destino privado {email} y la referencia personal {reference}. ",
    ),
)


class StressV3Error(ValueError):
    """Fixed, value-free errors only."""


def require(condition, code):
    if not condition:
        raise StressV3Error(code) from None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value, pretty=False):
    if pretty:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    else:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (rendered + "\n").encode("utf-8")


def validator():
    """Execute ONLY schema constants/functions, never a source module's imports.

    This runs the exact check_stress_rows + validate_spans implementations with
    their source-defined constants. No hybrid/refine/inference/model is imported.
    """
    def extract(relative, names, namespace):
        tree = ast.parse((ROOT / relative).read_bytes())
        selected, found = [], set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                assigned = {n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name)}
                if assigned & names:
                    selected.append(node)
                    found.update(assigned & names)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
                selected.append(node)
                found.add(node.name)
        require(found == names, "stress_v3_validator_source_shape")
        exec(compile(ast.Module(body=selected, type_ignores=[]), relative, "exec"), namespace)

    positive = {}
    extract("privacygate/positive_data.py", {
        "LANGS", "MASK_KEYS", "MAX_ROWS", "MAX_ANNOTATIONS", "MAX_ID_CHARS",
        "MAX_LINE_BYTES", "MAX_FILE_BYTES",
    }, positive)
    namespace = {"positive_data": SimpleNamespace(**{k: v for k, v in positive.items() if not k.startswith("__")})}
    extract("privacygate/masking_metrics.py", {
        "LABELS", "GOLD_DIAGNOSTIC_LABELS", "STRESS_FAMILIES", "MaskingError",
        "_integer", "_length", "validate_spans",
    }, namespace)
    extract("scripts/measure_masking.py", {"STRESS_KEYS", "STRESS_MAX_CHARS", "check_stress_rows"}, namespace)
    require(LANGS == namespace["positive_data"].LANGS, "stress_v3_language_binding")
    return namespace


def digits(rng, width):
    return str(rng.randrange(1, 10)) + "".join(rng.choice("0123456789") for _ in range(width - 1))


def make_iban(rng, lang):
    cc = IBAN_CC[lang]
    n = IBAN_LENGTH[lang]
    if lang == "en":
        bban = "ESHQ" + digits(rng, n - 8)
    elif lang == "it":
        bban = "Q" + digits(rng, n - 5)
    else:
        bban = digits(rng, n - 4)
    def remainder(compact):
        rearranged = compact[4:] + compact[:4]
        return int("".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)) % 97
    compact = cc + str(98 - remainder(cc + "00" + bban)).zfill(2) + bban
    require(len(compact) == n and remainder(compact) == 1, "stress_v3_iban_construction")
    # NBSP groups alternate with ASCII groups: new separator combination, checksum valid.
    groups = [compact[i:i + 4] for i in range(0, n, 4)]
    return "".join(("" if i == 0 else ("\u00a0" if i % 2 else " ")) + group for i, group in enumerate(groups))


def values(lang, kind):
    rng = random.Random(f"{SEED}:{VERSION}:{lang}:{kind}")
    li, ki = LANGS.index(lang), KINDS.index(kind)
    g = GIVEN[lang][rng.randrange(len(GIVEN[lang]))]
    s = SURNAME[lang][rng.randrange(len(SURNAME[lang]))]
    other = SURNAME[lang][(SURNAME[lang].index(s) + 1) % len(SURNAME[lang])]
    particle = PARTICLE[lang]
    name = g + " " + particle + " " + s + "-" + other
    if kind == "name_compound":
        name = g + "-" + GIVEN[lang][(GIVEN[lang].index(g) + 1) % len(GIVEN[lang])] + " " + s + "–" + other
    elif kind == "name_initials":
        name = g[0] + ". " + GIVEN[lang][(GIVEN[lang].index(g) + 1) % len(GIVEN[lang])][0] + ". " + particle + " " + s
    elif kind == "name_title":
        name = TITLES[lang][0] + " " + name
    elif kind == "name_reversed":
        name = TITLES[lang][1] + " " + particle + " " + s + "-" + other + ", " + g
    house, postal = str(241 + ki * 3 + li) + "d", digits(rng, 5)
    host = GIVEN[lang][(GIVEN[lang].index(g) + 2) % len(GIVEN[lang])] + " " + other
    location = CITY[lang] + " " + postal
    line = house + " " + STREET[lang] if lang in ("en", "fr") else STREET[lang] + " " + house
    address = location + " | c/o " + host + " | " + UNIT[lang] + " | " + line + " | " + COUNTRY[lang]
    if kind == "address_box":
        address = COUNTRY[lang] + " / " + location + " / " + BOX[lang] + " " + str(621 + li * 7) + "-D"
    elif kind == "address_reverse":
        address = COUNTRY[lang] + "\n" + location + "\n" + line + "\n(" + UNIT[lang] + ")"
    elif kind == "address_unit":
        address = line + " (" + UNIT[lang] + "); " + location + "; " + COUNTRY[lang]
    d = digits(rng, 10)
    extension = "Durchwahl" if lang == "de" else "ext."
    ext = digits(rng, 3)
    phone = "+" + DIAL[lang] + " (0)" + d[:2] + "." + d[2:6] + "." + d[6:] + " " + extension + " " + ext
    if kind == "phone_parenthesized":
        phone = "(+" + DIAL[lang] + ") (" + d[:3] + ")." + d[3:6] + "." + d[6:] + " " + extension + ": " + ext
    elif kind == "phone_dotted":
        phone = "00 " + DIAL[lang] + " (0) " + ".".join(d[i:i + 2] for i in range(0, len(d), 2)) + " " + extension + " " + ext
    number = digits(rng, 8)
    return {
        "name": name, "address": address, "phone": phone,
        "idcard": "EX" + number[:2] + "." + number[2:5] + " / " + number[5:] + "-Q",
        "passport": "UQ/" + number[:3] + " " + number[3:6] + "." + number[6:] + "–Z",
        "licence": "FQ " + number[:2] + "-" + number[2:5] + "/" + number[5:] + ".K",
        "iban": make_iban(rng, lang),
        "account": number[:2] + "\u00a0" + number[2:5] + " " + number[5:] + " / " + digits(rng, 4),
        "email": HANDLE[lang] + "+private." + digits(rng, 3) + "@letters.example.invalid",
        "handle": "@" + HANDLE[lang] + "-" + digits(rng, 2) + ".draft",
        "reference": "APL " + number[:2] + " / " + number[2:5] + "-" + number[5:] + "." + lang.upper(),
    }


def render(template, mapping):
    text, gold, skeleton = [], [], []
    cursor = 0
    for part in re.split(r"(\{[a-z]+\})", template):
        if part.startswith("{") and part.endswith("}"):
            key = part[1:-1]
            require(key in SLOTS and key in mapping, "stress_v3_slot_unknown")
            value = mapping[key]
            label = SLOTS[key]
            require(bool(value) and value == value.strip(), "stress_v3_slot_empty_or_padding")
            gold.append({"start": cursor, "end": cursor + len(value), "label": label})
            text.append(value)
            skeleton.append("{" + label + "}")
            cursor += len(value)
        else:
            require("{" not in part and "}" not in part, "stress_v3_template_syntax")
            text.append(part)
            skeleton.append(part)
            cursor += len(part)
    return "".join(text), gold, "".join(skeleton)


def generate():
    rows, skeletons = [], []
    for kind in KINDS:
        for li, lang in enumerate(LANGS):
            if kind == "long_correspondence":
                # Two 14-paragraph filler sections yield >512 words and ~5-6k chars.
                template = LONG_SECTIONS[0][li] + FILLER[lang] * 14 + LONG_SECTIONS[1][li] + FILLER[lang] * 14 + LONG_SECTIONS[2][li]
            else:
                template = TEMPLATES[kind][li]
            text, gold, skeleton = render(template, values(lang, kind))
            rows.append({"case_id": f"{VERSION}:{kind}:{lang}", "language": lang, "family": FAMILY[kind], "text": text, "gold": gold, "split": "dev"})
            skeletons.append(skeleton)
    for kind in CONTROL_KINDS:
        for li, lang in enumerate(LANGS):
            text = CONTROLS[kind][li]
            rows.append({"case_id": f"{VERSION}:control_{kind}:{lang}", "language": lang, "family": "clean", "text": text, "gold": [], "split": "dev"})
            skeletons.append(text)
    return rows, skeletons


def validate(rows, namespace):
    namespace["check_stress_rows"](rows)
    p = namespace["positive_data"]
    require(len(rows) == 150 and sum(bool(r["gold"]) for r in rows) == 110, "stress_v3_positive_count")
    require(sum(not r["gold"] for r in rows) == 40, "stress_v3_clean_count")
    require(Counter(r["language"] for r in rows) == Counter({lang: 30 for lang in LANGS}), "stress_v3_language_count")
    require(len({r["text"] for r in rows}) == len(rows), "stress_v3_duplicate_text")
    require({r["family"] for r in rows} == namespace["STRESS_FAMILIES"], "stress_v3_family_coverage")
    for row in rows:
        require(len(canonical(row)) <= p.MAX_LINE_BYTES, "stress_v3_line_bounds")
        previous = 0
        for span in row["gold"]:
            require(span["start"] >= previous, "stress_v3_gold_order")
            previous = span["end"]
        if row["family"] == "full_address":
            require(len(row["gold"]) == 1 and row["gold"][0]["label"] == "ADDRESS", "stress_v3_whole_address")
        if row["family"] == "long_text":
            require(3000 <= len(row["text"]) <= 6000 and len(row["text"].split()) > 512, "stress_v3_long_bounds")
            # Check early/middle/late presence internally; never emit individual offsets.
            starts = [s["start"] / len(row["text"]) for s in row["gold"]]
            require(starts[0] < 0.1 and any(0.4 < x < 0.65 for x in starts) and starts[-1] > 0.9, "stress_v3_long_placements")


def source_novelty(skeletons):
    literals, source_texts, bindings = set(), [], {}
    for relative in SOURCES:
        raw = (ROOT / relative).read_bytes()
        tree = ast.parse(raw)
        literals.update(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str))
        source_texts.append(raw.decode("utf-8"))
        bindings[relative] = sha(raw)
    pools = [v for table in (GIVEN, SURNAME) for group in table.values() for v in group]
    pools += list(STREET.values()) + list(CITY.values()) + list(HANDLE.values())
    require(all(all(v not in source for source in source_texts) for v in pools), "stress_v3_existing_pool_collision")
    require(not set(skeletons) & literals, "stress_v3_existing_template_collision")
    require(len(set(skeletons)) == len(skeletons), "stress_v3_duplicate_template")
    return {
        "prior_generator_source_sha256": bindings,
        "exact_skeletons_vs_prior_source_literals_disjoint": True,
        "new_pool_entries_absent_from_prior_source_text": True,
        "source_only_comparison": True, "old_generated_datasets_read": False,
        "model_predictions_read": False, "refinement_diagnostics_read": False,
        "semantic_independence_proven": False,
    }


def manifest_of(rows, skeletons, raw):
    per_label = Counter(s["label"] for r in rows for s in r["gold"])
    long_rows = [r for r in rows if r["family"] == "long_text"]
    matrix = {}
    for lang in LANGS:
        selected = [r for r in rows if r["language"] == lang]
        matrix[lang] = {
            "rows": len(selected), "positive_rows": sum(bool(r["gold"]) for r in selected),
            "clean_rows": sum(not r["gold"] for r in selected),
            "gold_spans": sum(len(r["gold"]) for r in selected),
            "per_family": dict(sorted(Counter(r["family"] for r in selected).items())),
            "per_label": dict(sorted(Counter(s["label"] for r in selected for s in r["gold"]).items())),
        }
    return {
        "version": VERSION, "schema": "masking-stress-six-field-v1", "split": "dev",
        "purpose": "Frozen blind synthetic development diagnostic for one integrator measurement, not training or the corpus test split.",
        "dataset": {"path": DATA.relative_to(ROOT).as_posix(), "sha256": sha(raw), "bytes": len(raw), "rows": len(rows)},
        "generator": {
            "path": "scripts/make_masking_stress_v3.py", "sha256": sha(Path(__file__).read_bytes()),
            "seed": SEED, "deterministic": True, "stdlib_only": True,
            "model_or_predictions_used": False, "rule_engine_imported_or_run": False,
        },
        "blind_status": {
            "generated_before_any_model_or_rule_saw_v3": True,
            "case_selection_uses_predictions": False, "clean_controls_filtered_by_detector": False,
            "previous_generators_read_only_to_avoid_reuse": True,
            "shared_batch_problem_description_known": True,
            "single_blind_measurement_owner": "integrator", "measurement_performed_by_generator": False,
            "scope": "Blind to predictions and rule implementation on v3, not to the requested stress categories or shared batch context.",
        },
        "counts": {
            "positive_rows": sum(bool(r["gold"]) for r in rows), "clean_rows": sum(not r["gold"] for r in rows),
            "gold_spans": sum(per_label.values()),
            "gold_original_characters": sum(s["end"] - s["start"] for r in rows for s in r["gold"]),
            "gold_unicode_alphanumeric_characters": sum(c.isalnum() for r in rows for s in r["gold"] for c in r["text"][s["start"]:s["end"]]),
            "per_language": dict(sorted(Counter(r["language"] for r in rows).items())),
            "per_family": dict(sorted(Counter(r["family"] for r in rows).items())),
            "per_label": dict(sorted(per_label.items())),
        },
        "per_language_breakdown": matrix,
        "positive_formats": {kind: len(LANGS) for kind in KINDS},
        "clean_control_formats": {kind: len(LANGS) for kind in CONTROL_KINDS},
        "template_set_sha256": sha(canonical(skeletons)),
        "long_text": {
            "rows": len(long_rows), "min_characters": min(len(r["text"]) for r in long_rows),
            "max_characters": max(len(r["text"]) for r in long_rows),
            "min_whitespace_delimited_words": min(len(r["text"].split()) for r in long_rows),
            "max_whitespace_delimited_words": max(len(r["text"].split()) for r in long_rows),
            "early_middle_late_gold_placements_checked": True,
            "tokenizer_loaded": False, "exact_model_token_count_verified": False,
            "window_boundary_crossings_proven": False,
        },
        "validation": {
            "check_stress_rows": "passed: exact AST-extracted implementation without module imports",
            "validator_source_sha256": {p: sha((ROOT / p).read_bytes()) for p in VALIDATOR_SOURCES},
            "unique_texts_and_ids": True, "ordered_nonoverlapping_whole_value_gold": True,
            "all_stress_families_present": True, "dev_only": True, "line_and_file_byte_limits_checked": True,
        },
        "source_novelty": source_novelty(skeletons),
        "format_notes": [
            "Whole PERSONNAME values include internal spaces, particles, initials, compound surnames and, in two formats, the salutation title.",
            "Each ADDRESS is one span including c/o host, postal routing, floor/unit, PO box, separators and country when present; nested names are not separately overlapped.",
            "Phone spans include optional trunk notation, dotted/parenthesized groups and the entire extension phrase and number.",
            "IBAN spans have valid mod97 checksums and country-specific lengths, with alternating ASCII/NBSP groups; account and identity spans include mixed separators.",
            "Clean controls are deliberately non-personal contextual look-alikes; they are not selected by detector results. Dates and building ages have empty gold.",
        ],
        "limitations": [
            "Invented values may accidentally coincide with real ones; phone numbers and bank identifiers are not verified unassigned, and IBAN bank/routing codes are not authority-validated.",
            "Novelty checks compare source strings and new pools, not old generated files; semantic or translation independence is not proven.",
            "Long texts exceed 512 whitespace-delimited words, but no exact tokenizer length or sliding-window boundary placement is claimed.",
            "Mechanically annotated synthetic stress only; no real-data, production privacy or legal guarantee. Shared batch aims were known before construction.",
        ],
    }


def execute(verify):
    namespace = validator()
    rows, skeletons = generate()
    validate(rows, namespace)
    raw = b"".join(canonical(row) for row in rows)
    require(len(raw) <= namespace["positive_data"].MAX_FILE_BYTES, "stress_v3_file_bounds")
    manifest = manifest_of(rows, skeletons, raw)
    frozen = canonical(manifest, pretty=True)
    if verify:
        require(DATA.is_file() and MANIFEST.is_file() and not DATA.is_symlink() and not MANIFEST.is_symlink(), "stress_v3_artifact_missing_or_symlink")
        require(DATA.read_bytes() == raw, "stress_v3_dataset_bytes_mismatch")
        require(MANIFEST.read_bytes() == frozen, "stress_v3_manifest_bytes_mismatch")
    else:
        # lexists semantics, including dangling symlinks; exclusive opens prevent overwrite races.
        require(not DATA.exists() and not DATA.is_symlink() and not MANIFEST.exists() and not MANIFEST.is_symlink(), "stress_v3_refuses_overwrite")
        DATA.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with DATA.open("xb") as handle:
            handle.write(raw)
        with MANIFEST.open("xb") as handle:
            handle.write(frozen)
    print(json.dumps({
        "status": "VERIFIED" if verify else "GENERATED", "rows": len(rows),
        "positive_rows": manifest["counts"]["positive_rows"], "clean_rows": manifest["counts"]["clean_rows"],
        "gold_spans": manifest["counts"]["gold_spans"], "sha256": sha(raw),
        "check_stress_rows": "passed", "no_model_loaded": True,
    }, sort_keys=True))


def main():
    if sys.argv[1:] not in ([], ["--verify"]):
        print("stress_v3_invalid_arguments", file=sys.stderr)
        return 2
    try:
        execute(bool(sys.argv[1:]))
    except StressV3Error as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print("stress_v3_operation_failed_input_not_shown", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
