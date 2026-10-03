#!/usr/bin/env python3
"""Independent synthetic blind v5; no detector imports, evaluation, or network."""
import argparse
import collections
import hashlib
import json
import random
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/augmentation/masking-stress-v5.jsonl"
MANIFEST = ROOT / "artifacts/masking-stress-v5/manifest.json"
POLICY = ROOT / "configs/privacy-policy-v1.json"
SEED = 202610035173
LANGUAGES = ("EN", "DE", "FR", "IT", "ES")
LABELS = "PERSONNAME ADDRESS EMAIL USERNAME TELEPHONENUM IBAN ACCOUNTNUM CREDITCARDNUMBER PASSPORTNUM IDCARDNUM DRIVERLICENSENUM TAXNUM SOCIALNUM PERSONALREF DATEOFBIRTH AGE".split()
RESERVED = ("form_records", "chat_lines", "signature_blocks", "mixed_language", "ocr_noise")
STANDARD = ("names", "whole_addresses", "phones", "financial", "official_ids", "personal_refs", "digital", "birth_age")
QUOTAS = (4, 4, 4, 4, 4, 3, 3, 2)
RULE = "measure once per profile+model; never tune on v5"
LOCALES = {
    "EN": {
        "names": "Dr. Elowen-Mae Quillmere|Prof. Rowan de Lorn|Brindle, Amara|M. Q. Fenwick|Tessa van Alderbrook|Mr. Ivo J. Thornwick".split("|"),
        "address": "{n} Lanternfold Lane, flat {u}, c/o Tamsin Quillmere, QW{p} 7ZX, Nerowick, Westmere, United Kingdom",
        "positive": ["The interviewee is {PERSONNAME}; the session is confidential.", "Send her private correspondence to {ADDRESS}.", "His callback number is {TELEPHONENUM}.", "Her payment record: IBAN {IBAN}; account {ACCOUNTNUM}; card {CREDITCARDNUMBER}.", "His documents: passport {PASSPORTNUM}; identity card {IDCARDNUM}; driving licence {DRIVERLICENSENUM}; tax number {TAXNUM}; social security {SOCIALNUM}.", "The patient's individual case reference is {PERSONALREF}.", "Reach this person at {EMAIL}, with private handle {USERNAME}.", "Her date of birth is {DATEOFBIRTH}; her age is {AGE}."],
        "reserved": ["SEALED intake\nApplicant: {PERSONNAME}\nPrivate delivery: {ADDRESS}\nCallback: {TELEPHONENUM}\nCase: {PERSONALREF}", "[direct message] {PERSONNAME}: my private callback is {TELEPHONENUM}; my patient reference is {PERSONALREF}.", "Personal signature follows\n{PERSONNAME}\n{ADDRESS}\nPhone {TELEPHONENUM}\n{EMAIL} | {USERNAME}", "Cross-border private note: {PERSONNAME} uses the foreign-format address {ADDRESS} and callback {TELEPHONENUM}.", "Scanned private dispatch slip\nRecipient {PERSONNAME}\nDelivery {ADDRESS}\nTelephone {TELEPHONENUM}"],
        "boundary": "Private contact: {PERSONNAME}, {ADDRESS}, tel. {TELEPHONENUM}.",
        "catalog": "Unassigned product catalogue: {brand}; SKU {sample}; price {price} EUR; size {measure} cm; stock {count} units.", "header": "Product | Article | Price EUR | Size cm | Stock (catalogue only, no customers)",
        "numeric": ["Anonymous statistics: {count} observations; completion {pct}%; no individual records.", "Firmware versions {version} and 7.14.3; build {sample}; no user identifier.", "Calibration dimensions {measure} mm by 36 mm; tolerance {pct}%; anonymous apparatus.", "Public timetable: departure {time1}, arrival {time2}; platform 12; no passenger data.", "Instrument counter: {digits} pulses; {count} samples; not an account or card.", "Aggregate report: {pct}% of {count} components passed; ratio 3:7; no participants."],
        "near": ["Product serial {serial} is a printed test-fixture code, not a bank account; no owner exists.", "Unassigned order code {phonecode} is not a telephone or hotline; no buyer or person is linked.", "Laboratory sample ID {sample} identifies only an inert ceramic specimen, not a person or document.", "Manufacture date {date} belongs to this unassigned component, not anyone's birth date.", "The brand {brand} names a fictional product range, not an individual; no person is referenced."],
        "other": ["Public maintenance calendar: {date} at {time1}; generic schedule, no birthdays.", "Fictional organisation {org} operates a public exhibition; no staff or customers are named.", "Public place {place} is an open park; no street, address, resident or delivery is given.", "Public venue wayfinding: room {count}, gate {gate}, hall 8; no assigned occupants."],
        "body": "This letter describes a confidential administrative review rather than a public listing. The enclosed checklist explains how the supplied details should be handled. Please keep the correspondence separate from product inventory and aggregate statistics. The receiving desk should acknowledge the envelope without copying its contents into a public announcement. The next review will consider the completeness of the materials, not the applicant's eligibility. Questions about the procedure can be resolved through the private contact details below. No other individual is identified in this paragraph.",
        "letter": "Dear applicant,\nPrivate file for {PERSONNAME}.\n{body}\nRouting address: {ADDRESS}. Telephone: {TELEPHONENUM}. Email: {EMAIL}. Handle: {USERNAME}.\n{body}\nPayment: {IBAN}; account: {ACCOUNTNUM}; card: {CREDITCARDNUMBER}.\n{body}\nPassport: {PASSPORTNUM}; identity card: {IDCARDNUM}; licence: {DRIVERLICENSENUM}; tax: {TAXNUM}; social security: {SOCIALNUM}.\n{body}\nPersonal case: {PERSONALREF}; date of birth: {DATEOFBIRTH}; age: {AGE}.\nEnd of confidential letter.",
    },
    "DE": {
        "names": "Dr. Jonna-Fee von Kreiden|Herr Ivo J. Wetterlin|Eschenbrück, Tilda|Prof. Oda van Falkenried|R. A. Drosselwin|Mara-Liv de Steinau".split("|"),
        "address": "c/o Tilda Eschenbrück, Falterbogenstr. {n}, {u}. OG, Whg. 7, {p}731 Feldhagen, Niederwald, Deutschland",
        "positive": ["Die befragte Person heißt {PERSONNAME}; das Gespräch ist vertraulich.", "Ihre persönliche Postanschrift lautet {ADDRESS}.", "Seine private Rückrufnummer lautet {TELEPHONENUM}.", "Ihre Zahlungsdaten: IBAN {IBAN}; Kontonummer {ACCOUNTNUM}; Kreditkarte {CREDITCARDNUMBER}.", "Seine Dokumente: Reisepass {PASSPORTNUM}; Personalausweis {IDCARDNUM}; Führerschein {DRIVERLICENSENUM}; Steuernummer {TAXNUM}; Sozialversicherungsnummer {SOCIALNUM}.", "Die individuelle Patientenreferenz lautet {PERSONALREF}.", "Die Person nutzt {EMAIL} und den privaten Nutzernamen {USERNAME}.", "Ihr Geburtsdatum ist {DATEOFBIRTH}; ihr Alter beträgt {AGE}."],
        "reserved": ["VERSIEGELTE Aufnahme\nPerson: {PERSONNAME}\nPrivatanschrift: {ADDRESS}\nRückruf: {TELEPHONENUM}\nFall: {PERSONALREF}", "[Direktnachricht] {PERSONNAME}: Meine private Nummer ist {TELEPHONENUM}; meine Patientenkennung ist {PERSONALREF}.", "Persönliche Signatur\n{PERSONNAME}\n{ADDRESS}\nTelefon {TELEPHONENUM}\n{EMAIL} | {USERNAME}", "Grenzüberschreitende Privatnotiz: {PERSONNAME} verwendet die ausländische Anschrift {ADDRESS} und die Rückrufnummer {TELEPHONENUM}.", "Gescannter Privatbeleg\nEmpfänger {PERSONNAME}\nZustellung {ADDRESS}\nTelefon {TELEPHONENUM}"],
        "boundary": "Privatkontakt: {PERSONNAME}, {ADDRESS}, Tel. {TELEPHONENUM}.",
        "catalog": "Produktkatalog ohne Kundenzuordnung: {brand}; Artikel {sample}; Preis {price} EUR; Größe {measure} cm; Bestand {count} Stück.", "header": "Produkt | Artikel | Preis EUR | Größe cm | Bestand (nur Katalog, keine Kunden)",
        "numeric": ["Anonyme Statistik: {count} Beobachtungen; Abschluss {pct}%; keine Einzelpersonen.", "Firmwareversionen {version} und 7.14.3; Build {sample}; keine Nutzerkennung.", "Kalibriermaße {measure} mm mal 36 mm; Toleranz {pct}%; anonymes Gerät.", "Öffentlicher Fahrplan: Abfahrt {time1}, Ankunft {time2}; Gleis 12; keine Reisenden.", "Gerätezähler: {digits} Impulse; {count} Proben; weder Konto noch Karte.", "Aggregatbericht: {pct}% von {count} Bauteilen bestanden; Verhältnis 3:7; keine Teilnehmenden."],
        "near": ["Produktseriencode {serial} ist ein Prüfmittelcode, kein Bankkonto; ohne Besitzer.", "Unvergebener Bestellcode {phonecode} ist weder Telefonnummer noch Hotline; ohne Käuferbezug.", "Laborprobenkennung {sample} bezeichnet nur eine Keramikprobe, keine Person und kein Ausweisdokument.", "Herstelldatum {date} gehört zu diesem unvergebenen Bauteil, nicht zu einem Geburtstag.", "Die Marke {brand} bezeichnet eine erfundene Produktserie, keinen Menschen; ohne Personenbezug."],
        "other": ["Öffentlicher Wartungskalender: {date} um {time1}; allgemeiner Termin, kein Geburtstag.", "Die erfundene Organisation {org} betreibt eine öffentliche Ausstellung; ohne benannte Beschäftigte.", "Der öffentliche Ort {place} ist ein offener Park; ohne Straße, Wohnanschrift oder Empfänger.", "Öffentliche Wegweisung: Raum {count}, Tor {gate}, Halle 8; ohne zugeordnete Personen."],
        "body": "Dieses Schreiben beschreibt eine vertrauliche Verwaltungsprüfung und kein öffentliches Verzeichnis. Die beigefügte Liste erklärt den Umgang mit den übermittelten Angaben. Bitte bewahren Sie die Korrespondenz getrennt von Warenbeständen und zusammengefassten Statistiken auf. Die Empfangsstelle bestätigt den Umschlag, ohne seinen Inhalt öffentlich bekannt zu machen. Bei der nächsten Prüfung geht es um die Vollständigkeit der Unterlagen, nicht um eine Entscheidung über die Person. Verfahrensfragen können über die unten angegebenen privaten Kontaktdaten geklärt werden. In diesem Absatz wird keine weitere Person genannt.",
        "letter": "Sehr geehrte Person,\nPrivate Akte für {PERSONNAME}.\n{body}\nAnschrift: {ADDRESS}. Telefon: {TELEPHONENUM}. E-Mail: {EMAIL}. Nutzername: {USERNAME}.\n{body}\nIBAN: {IBAN}; Konto: {ACCOUNTNUM}; Karte: {CREDITCARDNUMBER}.\n{body}\nPass: {PASSPORTNUM}; Ausweis: {IDCARDNUM}; Führerschein: {DRIVERLICENSENUM}; Steuer: {TAXNUM}; Sozialversicherung: {SOCIALNUM}.\n{body}\nPersönlicher Fall: {PERSONALREF}; Geburtsdatum: {DATEOFBIRTH}; Alter: {AGE}.\nEnde des vertraulichen Schreibens.",
    },
    "FR": {
        "names": "Dr. Maëlle-Anne du Veyrac|Mme Oriane de Fernel|Brumelac, Éloi|Prof. Léonie van Arbel|C. J. Rivelune|M. Noé di Valerne".split("|"),
        "address": "chez Oriane Fernel, {n} rue des Lanternelles, bâtiment C, étage {u}, appartement 7, {p}840 Clairvaux-les-Brumes, France",
        "positive": ["La personne interrogée est {PERSONNAME}; cet entretien est confidentiel.", "Son adresse postale personnelle est {ADDRESS}.", "Son numéro de rappel privé est {TELEPHONENUM}.", "Ses données bancaires: IBAN {IBAN}; compte {ACCOUNTNUM}; carte {CREDITCARDNUMBER}.", "Ses documents: passeport {PASSPORTNUM}; carte d'identité {IDCARDNUM}; permis {DRIVERLICENSENUM}; numéro fiscal {TAXNUM}; sécurité sociale {SOCIALNUM}.", "La référence individuelle du patient est {PERSONALREF}.", "Cette personne utilise {EMAIL} et le pseudonyme privé {USERNAME}.", "Sa date de naissance est {DATEOFBIRTH}; son âge est {AGE}."],
        "reserved": ["Fiche d'accueil SCELLÉE\nPersonne: {PERSONNAME}\nAdresse privée: {ADDRESS}\nRappel: {TELEPHONENUM}\nDossier: {PERSONALREF}", "[message privé] {PERSONNAME}: mon numéro privé est {TELEPHONENUM}; ma référence patient est {PERSONALREF}.", "Signature personnelle\n{PERSONNAME}\n{ADDRESS}\nTéléphone {TELEPHONENUM}\n{EMAIL} | {USERNAME}", "Note privée transfrontalière: {PERSONNAME} utilise l'adresse au format étranger {ADDRESS} et le numéro {TELEPHONENUM}.", "Bordereau privé numérisé\nDestinataire {PERSONNAME}\nLivraison {ADDRESS}\nTéléphone {TELEPHONENUM}"],
        "boundary": "Contact privé: {PERSONNAME}, {ADDRESS}, tél. {TELEPHONENUM}.",
        "catalog": "Catalogue sans clientèle: {brand}; article {sample}; prix {price} EUR; taille {measure} cm; stock {count} pièces.", "header": "Produit | Article | Prix EUR | Taille cm | Stock (catalogue seul, aucun client)",
        "numeric": ["Statistiques anonymes: {count} observations; achèvement {pct}%; aucune fiche individuelle.", "Versions du micrologiciel {version} et 7.14.3; build {sample}; aucun identifiant personnel.", "Dimensions d'étalonnage {measure} mm sur 36 mm; tolérance {pct}%; appareil anonyme.", "Horaire public: départ {time1}, arrivée {time2}; quai 12; aucun voyageur identifié.", "Compteur instrumental: {digits} impulsions; {count} échantillons; ni compte ni carte.", "Rapport agrégé: {pct}% de {count} composants conformes; rapport 3:7; aucun participant."],
        "near": ["Le numéro de série produit {serial} est un code de banc d'essai, pas un compte bancaire; sans propriétaire.", "Le code de commande non attribué {phonecode} n'est ni téléphone ni ligne d'assistance; sans acheteur.", "L'identifiant de laboratoire {sample} désigne uniquement une éprouvette en céramique, ni personne ni document d'identité.", "La date de fabrication {date} concerne ce composant non attribué, pas une naissance.", "La marque {brand} nomme une gamme fictive, pas une personne; sans lien individuel."],
        "other": ["Calendrier public d'entretien: {date} à {time1}; planning général, aucune naissance.", "L'organisation fictive {org} gère une exposition publique; aucun membre n'est nommé.", "Le lieu public {place} est un parc ouvert; aucune rue, adresse résidentielle ou livraison.", "Orientation publique: salle {count}, porte {gate}, hall 8; aucun occupant attribué."],
        "body": "Cette lettre décrit un examen administratif confidentiel plutôt qu'un registre public. La liste jointe explique le traitement des informations reçues. Veuillez conserver cette correspondance séparément des stocks de produits et des statistiques agrégées. Le bureau destinataire accuse réception de l'enveloppe sans publier son contenu. Le prochain examen portera sur la complétude des pièces et non sur une décision concernant la personne. Les questions de procédure peuvent être résolues grâce aux coordonnées privées indiquées ci-dessous. Aucune autre personne n'est identifiée dans ce paragraphe.",
        "letter": "Bonjour,\nDossier privé de {PERSONNAME}.\n{body}\nAdresse: {ADDRESS}. Téléphone: {TELEPHONENUM}. Courriel: {EMAIL}. Pseudonyme: {USERNAME}.\n{body}\nIBAN: {IBAN}; compte: {ACCOUNTNUM}; carte: {CREDITCARDNUMBER}.\n{body}\nPasseport: {PASSPORTNUM}; identité: {IDCARDNUM}; permis: {DRIVERLICENSENUM}; fiscal: {TAXNUM}; sécurité sociale: {SOCIALNUM}.\n{body}\nDossier personnel: {PERSONALREF}; naissance: {DATEOFBIRTH}; âge: {AGE}.\nFin de la lettre confidentielle.",
    },
    "IT": {
        "names": "Dott. Nereo-Luca di Valmoro|Sig.ra Elvira del Rosceto|Fioralba, Terenzio|Prof. Irma da Selvento|G. P. Vellorani|Sig. Lidia-Mara De Orlina".split("|"),
        "address": "presso Elvira Rosceto, via delle Lucernole {n}, scala B, piano {u}, interno 7, {p}620 Borgo Velario, provincia di Selvento, Italia",
        "positive": ["La persona intervistata è {PERSONNAME}; il colloquio è riservato.", "Il suo indirizzo postale personale è {ADDRESS}.", "Il suo recapito telefonico privato è {TELEPHONENUM}.", "I suoi dati bancari: IBAN {IBAN}; conto {ACCOUNTNUM}; carta {CREDITCARDNUMBER}.", "I suoi documenti: passaporto {PASSPORTNUM}; carta d'identità {IDCARDNUM}; patente {DRIVERLICENSENUM}; codice fiscale {TAXNUM}; previdenza {SOCIALNUM}.", "Il riferimento individuale del paziente è {PERSONALREF}.", "Questa persona usa {EMAIL} e il nome utente privato {USERNAME}.", "La sua data di nascita è {DATEOFBIRTH}; la sua età è {AGE}."],
        "reserved": ["Scheda riservata SIGILLATA\nPersona: {PERSONNAME}\nIndirizzo privato: {ADDRESS}\nTelefono: {TELEPHONENUM}\nCaso: {PERSONALREF}", "[messaggio diretto] {PERSONNAME}: il mio recapito privato è {TELEPHONENUM}; il mio riferimento paziente è {PERSONALREF}.", "Firma personale\n{PERSONNAME}\n{ADDRESS}\nTelefono {TELEPHONENUM}\n{EMAIL} | {USERNAME}", "Nota privata transfrontaliera: {PERSONNAME} usa l'indirizzo in formato estero {ADDRESS} e il recapito {TELEPHONENUM}.", "Documento privato scansionato\nDestinatario {PERSONNAME}\nConsegna {ADDRESS}\nTelefono {TELEPHONENUM}"],
        "boundary": "Contatto privato: {PERSONNAME}, {ADDRESS}, tel. {TELEPHONENUM}.",
        "catalog": "Catalogo senza clienti: {brand}; articolo {sample}; prezzo {price} EUR; misura {measure} cm; scorte {count} pezzi.", "header": "Prodotto | Articolo | Prezzo EUR | Misura cm | Scorte (solo catalogo, nessun cliente)",
        "numeric": ["Statistiche anonime: {count} osservazioni; completamento {pct}%; nessuna scheda personale.", "Versioni firmware {version} e 7.14.3; build {sample}; nessun identificativo utente.", "Dimensioni di calibrazione {measure} mm per 36 mm; tolleranza {pct}%; apparecchio anonimo.", "Orario pubblico: partenza {time1}, arrivo {time2}; binario 12; nessun passeggero identificato.", "Contatore strumentale: {digits} impulsi; {count} campioni; né conto né carta.", "Rapporto aggregato: {pct}% di {count} componenti conformi; rapporto 3:7; nessun partecipante."],
        "near": ["Il seriale prodotto {serial} è un codice di banco prova, non un conto bancario; senza proprietario.", "Il codice ordine non assegnato {phonecode} non è telefono né numero di assistenza; senza acquirente.", "L'ID campione {sample} indica solo un provino ceramico, non una persona o un documento.", "La data di fabbricazione {date} riguarda questo componente non assegnato, non una nascita.", "Il marchio {brand} indica una gamma inventata, non un individuo; nessun legame personale."],
        "other": ["Calendario pubblico di manutenzione: {date} alle {time1}; data generica, nessuna nascita.", "L'organizzazione inventata {org} gestisce una mostra pubblica; nessun membro è nominato.", "Il luogo pubblico {place} è un parco aperto; nessuna via, residenza o consegna.", "Segnaletica pubblica: sala {count}, porta {gate}, padiglione 8; nessun occupante assegnato."],
        "body": "Questa lettera descrive una verifica amministrativa riservata e non un elenco pubblico. La lista allegata spiega come trattare le informazioni ricevute. Conservare la corrispondenza separata dalle scorte di prodotti e dalle statistiche aggregate. L'ufficio destinatario conferma la ricezione della busta senza pubblicarne il contenuto. La prossima verifica riguarda la completezza dei materiali e non una decisione sulla persona. Le domande sulla procedura possono essere risolte attraverso i recapiti privati riportati sotto. Nessun altro individuo viene identificato in questo paragrafo.",
        "letter": "Gentile persona,\nFascicolo privato di {PERSONNAME}.\n{body}\nIndirizzo: {ADDRESS}. Telefono: {TELEPHONENUM}. Email: {EMAIL}. Nome utente: {USERNAME}.\n{body}\nIBAN: {IBAN}; conto: {ACCOUNTNUM}; carta: {CREDITCARDNUMBER}.\n{body}\nPassaporto: {PASSPORTNUM}; identità: {IDCARDNUM}; patente: {DRIVERLICENSENUM}; fisco: {TAXNUM}; previdenza: {SOCIALNUM}.\n{body}\nCaso personale: {PERSONALREF}; nascita: {DATEOFBIRTH}; età: {AGE}.\nFine della lettera riservata.",
    },
    "ES": {
        "names": "Dra. Iria-Mar de Valdebruma|Sr. Nilo J. Ceromonte|Lumbrera, Elodia|Prof. Amaro del Vental|R. C. Miralumbre|Sra. Talia-Maia dos Arvelos".split("|"),
        "address": "a cargo de Elodia Lumbrera, calle de las Lucernillas {n}, escalera D, piso {u}, puerta 7, {p}530 Villabrisa, provincia de Ceromonte, España",
        "positive": ["La persona entrevistada es {PERSONNAME}; la conversación es confidencial.", "Su dirección postal personal es {ADDRESS}.", "Su número de devolución de llamada privado es {TELEPHONENUM}.", "Sus datos bancarios: IBAN {IBAN}; cuenta {ACCOUNTNUM}; tarjeta {CREDITCARDNUMBER}.", "Sus documentos: pasaporte {PASSPORTNUM}; identidad {IDCARDNUM}; permiso de conducir {DRIVERLICENSENUM}; número fiscal {TAXNUM}; seguridad social {SOCIALNUM}.", "La referencia individual del paciente es {PERSONALREF}.", "Esta persona utiliza {EMAIL} y el usuario privado {USERNAME}.", "Su fecha de nacimiento es {DATEOFBIRTH}; su edad es {AGE}."],
        "reserved": ["Ficha de admisión SELLADA\nPersona: {PERSONNAME}\nDirección privada: {ADDRESS}\nTeléfono: {TELEPHONENUM}\nCaso: {PERSONALREF}", "[mensaje directo] {PERSONNAME}: mi teléfono privado es {TELEPHONENUM}; mi referencia de paciente es {PERSONALREF}.", "Firma personal\n{PERSONNAME}\n{ADDRESS}\nTeléfono {TELEPHONENUM}\n{EMAIL} | {USERNAME}", "Nota privada transfronteriza: {PERSONNAME} usa la dirección de formato extranjero {ADDRESS} y el teléfono {TELEPHONENUM}.", "Documento privado escaneado\nDestinatario {PERSONNAME}\nEntrega {ADDRESS}\nTeléfono {TELEPHONENUM}"],
        "boundary": "Contacto privado: {PERSONNAME}, {ADDRESS}, tel. {TELEPHONENUM}.",
        "catalog": "Catálogo sin clientes: {brand}; artículo {sample}; precio {price} EUR; tamaño {measure} cm; existencias {count} unidades.", "header": "Producto | Artículo | Precio EUR | Tamaño cm | Existencias (solo catálogo, sin clientes)",
        "numeric": ["Estadísticas anónimas: {count} observaciones; finalización {pct}%; sin fichas individuales.", "Versiones de firmware {version} y 7.14.3; compilación {sample}; sin usuario identificado.", "Medidas de calibración {measure} mm por 36 mm; tolerancia {pct}%; aparato anónimo.", "Horario público: salida {time1}, llegada {time2}; andén 12; sin viajeros identificados.", "Contador instrumental: {digits} pulsos; {count} muestras; ni cuenta ni tarjeta.", "Informe agregado: {pct}% de {count} componentes conformes; proporción 3:7; sin participantes."],
        "near": ["El número de serie {serial} es un código de banco de pruebas, no una cuenta bancaria; sin propietario.", "El código de pedido sin asignar {phonecode} no es teléfono ni línea de ayuda; sin comprador.", "El identificador de laboratorio {sample} designa solo una muestra cerámica, no una persona ni documento.", "La fecha de fabricación {date} pertenece a este componente sin asignar, no a un nacimiento.", "La marca {brand} nombra una gama ficticia, no una persona; sin vínculo individual."],
        "other": ["Calendario público de mantenimiento: {date} a las {time1}; fecha genérica, no nacimiento.", "La organización ficticia {org} gestiona una exposición pública; sin miembros nombrados.", "El lugar público {place} es un parque abierto; sin calle, domicilio ni destinatario.", "Orientación pública: sala {count}, puerta {gate}, pabellón 8; sin ocupantes asignados."],
        "body": "Esta carta describe una revisión administrativa confidencial y no un listado público. La lista adjunta explica el tratamiento de la información recibida. Conserve la correspondencia separada del inventario de productos y las estadísticas agregadas. La oficina receptora confirma la llegada del sobre sin publicar su contenido. La próxima revisión comprobará la integridad de los materiales y no una decisión sobre la persona. Las preguntas del procedimiento pueden resolverse mediante los contactos privados indicados abajo. Ningún otro individuo aparece identificado en este párrafo.",
        "letter": "Estimado destinatario,\nExpediente privado de {PERSONNAME}.\n{body}\nDirección: {ADDRESS}. Teléfono: {TELEPHONENUM}. Correo: {EMAIL}. Usuario: {USERNAME}.\n{body}\nIBAN: {IBAN}; cuenta: {ACCOUNTNUM}; tarjeta: {CREDITCARDNUMBER}.\n{body}\nPasaporte: {PASSPORTNUM}; identidad: {IDCARDNUM}; permiso: {DRIVERLICENSENUM}; fiscal: {TAXNUM}; seguridad social: {SOCIALNUM}.\n{body}\nCaso personal: {PERSONALREF}; nacimiento: {DATEOFBIRTH}; edad: {AGE}.\nFin de la carta confidencial.",
    },
}
PLAIN_NAMES = ("Elowen Quillmere", "Jonna Wetterlin", "Oriane Brumelac", "Elvira Fioralba", "Elodia Ceromonte")
SHORT_ADDRESS = ("{n} Lanternfold Lane, QW{p} 7ZX Nerowick", "Falterbogenstr. {n}, {p}731 Feldhagen", "{n} rue des Lanternelles, {p}840 Clairvaux-les-Brumes", "via delle Lucernole {n}, {p}620 Borgo Velario", "calle de las Lucernillas {n}, {p}530 Villabrisa")
LETTER_DETAIL = (
    ("The documents should be checked in their original order. If a page is missing, return a procedural query through the private channel rather than distributing a copy to unrelated desks. Each enclosure should remain with its cover sheet so that the receiving team can distinguish a payment instruction from a delivery instruction. This is a handling request, not an instruction to publish a directory.", "The payment section is supplied only for this private file. Keep it apart from the inventory figures that appear in ordinary purchasing reports. The values are not examples of product serials and should not be transferred into catalogue descriptions. No payment is authorised by this letter; the receiving team must follow its usual review procedure before acting on a request.", "The identity section explains which personal documents accompany the application. Copies may be incomplete, so request clarification privately if the cover sheet does not match the enclosed material. Do not replace uncertain details with guesses from another file. After acknowledgement, retain only the material needed for the review and keep all correspondence in the same confidential channel."),
    ("Prüfen Sie die Unterlagen in ihrer ursprünglichen Reihenfolge. Wenn eine Seite fehlt, stellen Sie eine Rückfrage über den privaten Kanal, statt Kopien an unbeteiligte Stellen zu verteilen. Jede Anlage bleibt bei ihrem Deckblatt, damit das Empfangsteam Zahlungsanweisungen von Zustellanweisungen unterscheiden kann. Dies ist eine Bitte zum Umgang mit Unterlagen, keine Veröffentlichung eines Verzeichnisses.", "Der Zahlungsabschnitt gehört ausschließlich zu dieser privaten Akte. Bewahren Sie ihn getrennt von Bestandszahlen gewöhnlicher Einkaufsberichte auf. Die Angaben sind keine Produktseriencodes und dürfen nicht in Katalogbeschreibungen übertragen werden. Dieses Schreiben genehmigt keine Zahlung. Vor jeder Bearbeitung gilt das übliche Prüfverfahren der Empfangsstelle.", "Der Identitätsabschnitt erläutert die persönlichen Dokumente des Antrags. Kopien können unvollständig sein; bei Abweichungen zwischen Deckblatt und Anlage ist vertraulich nachzufragen. Ersetzen Sie unsichere Angaben nicht durch Vermutungen aus einer anderen Akte. Nach der Bestätigung bleibt nur das für die Prüfung erforderliche Material im selben vertraulichen Vorgang."),
    ("Vérifiez les pièces dans leur ordre initial. Si une page manque, demandez une précision par le canal privé au lieu de distribuer des copies à des services étrangers au dossier. Chaque annexe reste avec sa couverture afin que le bureau distingue une instruction de paiement d'une instruction de livraison. Cette demande concerne le traitement des pièces et non la publication d'un annuaire.", "La section bancaire est fournie uniquement pour ce dossier privé. Conservez-la séparément des chiffres d'inventaire des rapports d'achat ordinaires. Ces valeurs ne sont pas des numéros de série et ne doivent pas figurer dans un catalogue. Cette lettre n'autorise aucun paiement. Le bureau destinataire doit appliquer son contrôle habituel avant de traiter une demande.", "La section d'identité décrit les documents personnels joints à la demande. Les copies peuvent être incomplètes; demandez une précision en privé si la couverture ne correspond pas aux annexes. Ne remplacez pas une information incertaine par une supposition tirée d'un autre dossier. Après confirmation, ne conservez que les pièces nécessaires à l'examen dans le même canal confidentiel."),
    ("Controllare i documenti nel loro ordine originale. Se manca una pagina, chiedere chiarimenti nel canale privato invece di distribuire copie a uffici estranei. Ogni allegato resta con la sua copertina affinché chi riceve distingua le istruzioni di pagamento da quelle di consegna. La richiesta riguarda la gestione dei documenti, non la pubblicazione di un elenco.", "La sezione bancaria viene fornita solo per questo fascicolo privato. Tenerla separata dai dati di magazzino dei normali rapporti di acquisto. I valori non sono numeri di serie e non devono entrare nelle descrizioni di catalogo. Questa lettera non autorizza alcun pagamento. L'ufficio destinatario deve seguire la normale verifica prima di elaborare qualsiasi richiesta.", "La sezione di identità descrive i documenti personali allegati alla domanda. Le copie possono essere incomplete: chiedere chiarimenti in privato se la copertina non coincide con il materiale ricevuto. Non sostituire dati incerti con ipotesi tratte da un altro fascicolo. Dopo la conferma, conservare solo il materiale necessario alla verifica nel medesimo canale riservato."),
    ("Revise los documentos en su orden original. Si falta una página, solicite aclaraciones por el canal privado en lugar de distribuir copias a oficinas ajenas. Cada anexo debe permanecer con su portada para distinguir instrucciones de pago e instrucciones de entrega. La petición trata de la gestión de documentos y no de la publicación de un directorio.", "La sección bancaria se proporciona solo para este expediente privado. Guárdela separada de las cifras de inventario de los informes de compra habituales. Los valores no son números de serie y no deben aparecer en descripciones de catálogo. Esta carta no autoriza ningún pago. La oficina receptora debe seguir su revisión ordinaria antes de tramitar cualquier petición.", "La sección de identidad describe los documentos personales de la solicitud. Las copias pueden estar incompletas: pida aclaraciones en privado si la portada no coincide con los anexos. No sustituya datos inciertos por suposiciones de otro expediente. Tras confirmar la recepción, conserve solo lo necesario para la revisión en el mismo canal confidencial."),
)
for lang, plain, details in zip(LANGUAGES, PLAIN_NAMES, LETTER_DETAIL):
    LOCALES[lang]["names"].append(plain)
    for j, body in enumerate((LOCALES[lang]["body"],) + details): LOCALES[lang]["letter"] = LOCALES[lang]["letter"].replace("{body}", body, 1)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def values(lang, i, rng):
    loc = LOCALES[lang]; digits = lambda n: "".join(str(rng.randrange(10)) for _ in range(n))
    n, u, p = rng.randrange(3, 198), rng.randrange(1, 9), rng.randrange(10, 90)
    year = rng.randrange(1980, 2002); date = f"{rng.randrange(1, 29):02d}.{rng.randrange(1, 10):02d}.{year}"
    country, bban = {"EN": ("GB", "QVLL" + digits(14)), "DE": ("DE", digits(18)), "FR": ("FR", digits(23)), "IT": ("IT", "K" + digits(22)), "ES": ("ES", digits(20))}[lang]
    numeric = "".join(c if c.isdigit() else str(ord(c) - 55) for c in bban + country + "00")
    iban = f"{country}{98 - int(numeric) % 97:02d}{bban}"; iban = " ".join(iban[k:k + 4] for k in range(0, len(iban), 4))
    phone = {"EN": "+44 (0)20", "DE": "+49 (0)30", "FR": "+33 (0)1", "IT": "+39 06", "ES": "+34 91"}[lang] + " " + digits(3) + " " + digits(4)
    if i % 3: phone += (" ext. ", " Durchwahl ", " poste ", " interno ", " extensión ")[LANGUAGES.index(lang)] + str(300 + i)
    address = loc["address"].format(n=n, u=u, p=p)
    if i % 4 == 0: address = ("PO Box {n}, QW{p} 7ZX, Nerowick, United Kingdom", "Postfach {n}, {p}731 Feldhagen, Deutschland", "boîte postale {n}, {p}840 Clairvaux-les-Brumes, France", "casella postale {n}, {p}620 Borgo Velario, Italia", "apartado postal {n}, {p}530 Villabrisa, España")[LANGUAGES.index(lang)].format(n=n, p=p)
    vals = [loc["names"][i % len(loc["names"])], address, f"courier{i}@quillpost.example", f"@quillpost_{i}", phone, iban, " / ".join(digits(4) for _ in range(3)), "-".join(digits(4) for _ in range(4)), "QN " + digits(7), "WX-" + digits(8), "VL / " + digits(9), "/".join(digits(3) for _ in range(3)), " ".join(digits(3) for _ in range(4)), f"PAT / {lang} / {i:07d}", date, str(2026 - year) + (" years", " Jahre", " ans", " anni", " años")[LANGUAGES.index(lang)]]
    return dict(zip(LABELS, vals), body=loc["body"], brand=("Elara Voss", "Jonna Vale", "Oriane Brume", "Nereo Alba", "Iria Monte")[(i + i // 5) % 5], sample=f"QN{i:07d}", serial=iban, phonecode=phone.split(" ext.")[0].split(" Durchwahl")[0].split(" poste")[0].split(" interno")[0].split(" extensión")[0], date=date, org=f"Quillarium-{i} Foundation", place=f"Lucernelle-{i} Park", gate=f"B{i % 40}", price=f"{rng.randrange(10, 500)}.{rng.randrange(10, 99)}", count=str(rng.randrange(80, 6000)), pct=f"{rng.randrange(1, 99)}.{rng.randrange(1, 10)}", version=f"{i % 9 + 1}.{i % 23}.{i % 17}", measure=f"{rng.randrange(2, 120)}.{rng.randrange(1, 10)}", time1=f"{i % 12 + 6:02d}:{i % 6 * 10:02d}", time2=f"{i % 12 + 7:02d}:{i % 6 * 10:02d}", digits=digits(16))


def render(template, vals):
    text = ""; gold = []
    for literal, key, spec, conv in string.Formatter().parse(template):
        text += literal
        if key is not None:
            require(not spec and conv is None and key in vals, "template rule failed")
            value = vals[key]; start = len(text); text += value
            if key in LABELS: gold.append({"start": start, "end": len(text), "label": key})
    return text, gold


def generate():
    rng = random.Random(SEED); rows = []
    def add(lang, family, template, vals):
        text, gold = render(template, vals); rows.append(dict(case_id=f"v5-{lang}-{len(rows) + 1:04d}", family=family, gold=gold, language=lang, split="blind", text=text))
    for l, lang in enumerate(LANGUAGES):
        loc = LOCALES[lang]
        for f, family in enumerate(RESERVED):
            for j in range(4 if f == l else 5):
                v = values(lang, len(rows) + 1, rng)
                if family == "mixed_language": v.update(values(LANGUAGES[(l + 2) % 5], len(rows) + 1, rng))
                if family == "ocr_noise":
                    for key in ("PERSONNAME", "ADDRESS", "TELEPHONENUM"): v[key] = v[key].replace(" ", "\n", 1) if j % 2 == 0 else v[key].replace(" ", "", 1)
                add(lang, family, loc["reserved"][f], v)
        for f, quota in enumerate(QUOTAS):
            for j in range(quota): add(lang, STANDARD[f], loc["positive"][f], values(lang, len(rows) + 1, rng))
        for j in range(2): add(lang, "long_letters", loc["letter"], values(lang, len(rows) + 1, rng))
        for j in range(6):
            v = values(lang, len(rows) + 1, rng)
            if j % 2 == 0: v["ADDRESS"] = SHORT_ADDRESS[l].format(n=21 + j, p=43 + j)
            add(lang, "adjacent_contact", loc["boundary"], v)
        for family, quota, templates in (("clean_catalog", 12, [loc["catalog"], loc["header"] + "\n{brand} | {sample} | {price} | {measure} | {count}"]), ("clean_numeric", 12, loc["numeric"]), ("clean_near_miss", 20, loc["near"]), ("clean_other", 16, loc["other"])):
            for j in range(quota): add(lang, family, templates[j % len(templates)], values(lang, len(rows) + 1, rng))
    rng.shuffle(rows)
    return rows


def encode(obj, pretty=False):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2 if pretty else None, separators=None if pretty else (",", ":")) + "\n").encode("utf-8")


def validate(rows, policy) -> dict:
    require(policy["labels"] == LABELS and policy["synthetic_only"], "policy mismatch")
    require(len(rows) == 600 and len({r["case_id"] for r in rows}) == 600 and len({r["text"] for r in rows}) == 600, "row count or uniqueness failed")
    for r in rows:
        require(set(r) == set(policy["row_schema"]) and all(type(r[k]) is str and r[k] for k in ("case_id", "family", "language", "split", "text")), "row schema failed")
        require(r["language"] in LANGUAGES and r["split"] == "blind" and type(r["gold"]) is list and bool(r["gold"]) != r["family"].startswith("clean_"), "row rules failed")
        end = 0
        for s in r["gold"]:
            require(set(s) == set(policy["gold_span_schema"]) and type(s["start"]) is int and type(s["end"]) is int and s["label"] in LABELS, "gold schema failed")
            require(end <= s["start"] < s["end"] <= len(r["text"]), "gold ordering or bounds failed")
            v = r["text"][s["start"]:s["end"]]; require(v == v.strip() and v[-1] not in ".,;:!?" and any(c.isalnum() for c in v), "whole-value rule failed"); end = s["end"]
        if r["family"] == "adjacent_contact": require([s["label"] for s in r["gold"]] == ["PERSONNAME", "ADDRESS", "TELEPHONENUM"] and "\n" not in r["text"], "adjacent boundaries failed")
        if r["family"] == "long_letters": require(len(r["text"]) >= 1800 and len(r["gold"]) == 16, "long letter rule failed")
    families = dict(collections.Counter(r["family"] for r in rows)); labels = dict(collections.Counter(s["label"] for r in rows for s in r["gold"]))
    expected = dict(zip(STANDARD, (q * 5 for q in QUOTAS)), **dict.fromkeys(RESERVED, 24), long_letters=10, adjacent_contact=30, clean_catalog=60, clean_numeric=60, clean_near_miss=100, clean_other=80)
    positive = {lang: sum(bool(r["gold"]) for r in rows if r["language"] == lang) for lang in LANGUAGES}; languages = dict(collections.Counter(r["language"] for r in rows))
    require(families == expected and set(labels) == set(LABELS) and all(languages[lang] == 120 and positive[lang] == 60 for lang in LANGUAGES), "stratification failed")
    require(all({s["label"] for r in rows if r["language"] == lang for s in r["gold"]} == set(LABELS) for lang in LANGUAGES), "language label coverage failed")
    return dict(rows=600, positive_rows=300, clean_rows=300, per_language=languages, positive_per_language=positive, clean_per_language={lang: 60 for lang in LANGUAGES}, per_family=families, per_label=labels, gold_spans=sum(labels.values()), gold_original_characters=sum(s["end"] - s["start"] for r in rows for s in r["gold"]), gold_unicode_alphanumeric_characters=sum(c.isalnum() for r in rows for s in r["gold"] for c in r["text"][s["start"]:s["end"]]), reserved_positive_rows=120, reserved_positive_fraction=0.4, long_letters=10, adjacent_contact_rows=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--verify", action="store_true"); args = parser.parse_args()
    if not args.verify: require(not DATA.exists() and not MANIFEST.exists(), "refusing to overwrite data or manifest")
    policy_bytes = POLICY.read_bytes(); policy = json.loads(policy_bytes); rows = generate(); counts = validate(rows, policy)
    payload = b"".join(encode(r) for r in rows); sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = dict(version=5, seed=SEED, split="blind", synthetic_only=True, blind_status="frozen_unmeasured", measurement_rule=RULE, counts=counts, dataset=dict(path=str(DATA.relative_to(ROOT)), sha256=sha(payload), bytes=len(payload)), generator=dict(path=str(Path(__file__).resolve().relative_to(ROOT)), sha256=sha(Path(__file__).read_bytes())), policy=dict(path=str(POLICY.relative_to(ROOT)), sha256=sha(policy_bytes), version=policy["policy_version"]), schema=policy["row_schema"], gold_span_schema=policy["gold_span_schema"], reserved_families=dict(zip(policy["reserved_v4_families"], RESERVED)), independence=dict(construction="new seed, independently authored templates and fictional value pools", v4_manifest_access="family and format names only", detector_sources_read=False, training_sources_or_rows_read=False, model_outputs_or_run_metrics_read=False, exact_cross_dataset_literal_disjointness_proven=False), validation=dict(bytes="deterministic regeneration plus sha256", gold="whole inserted values; Python str offsets; ordered, non-overlapping; no surrounding prose or punctuation", counts="exact quotas and all 16 labels in every language"), limitations=["Synthetic challenge set; no production privacy or legal guarantee.", "Semantic and literal disjointness from unread datasets is not proven."])
    frozen_manifest = encode(manifest, pretty=True)
    if args.verify:
        actual = DATA.read_bytes(); require(actual == payload, "dataset bytes mismatch")
        require(validate([json.loads(line) for line in actual.splitlines()], policy) == counts, "dataset schema or counts mismatch")
        require(MANIFEST.read_bytes() == frozen_manifest, "manifest bytes, hashes or counts mismatch")
    else:
        DATA.parent.mkdir(parents=True, exist_ok=True); MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with DATA.open("xb") as data_file, MANIFEST.open("xb") as manifest_file: data_file.write(payload); manifest_file.write(frozen_manifest)
    print(json.dumps(dict(status="VERIFIED" if args.verify else "FROZEN", rows=600, positive=300, clean=300, per_language=counts["per_language"], labels=len(counts["per_label"]), reserved_positive=120, long_letters=10, adjacent_contact=30, dataset_sha256=sha(payload)), sort_keys=True))


if __name__ == "__main__":
    try: main()
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        print("FAILED: freeze or verification rejected; no row content emitted", file=sys.stderr); sys.exit(1)
