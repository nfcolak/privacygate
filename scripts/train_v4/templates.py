"""Independent monolingual paraphrases; dev constructions are held out whole."""
# Four train and two dev paragraph constructions, all newly authored.
WRAPPERS = {
    "en": {
        True: ("For this applicant, the private detail supplied is {field}.",
               "The person has confirmed the following private detail: {field}.",
               "During the individual's review we recorded {field}.",
               "The member requested that we retain this personal detail: {field}.",
               "A confidential detail was verified with the individual; it reads {field}.",
               "For the member's own record the confirmed detail appears as {field}."),
        False: ("The stock catalogue, with no person assigned, lists {field}.",
                "This technical entry describes goods only: {field}.",
                "For unassigned warehouse equipment the operational detail is {field}.",
                "No customer is linked to this product entry: {field}.",
                "An equipment-only inventory note gives the detail as {field}.",
                "This public technical description concerns stock, not a person: {field}."),
    },
    "de": {
        True: ("Für diese Person wurde die private Angabe {field} bestätigt.",
               "Das Mitglied hat diese persönliche Angabe mitgeteilt: {field}.",
               "Bei der privaten Prüfung der Person wurde {field} notiert.",
               "Die antragstellende Person nennt als eigene Angabe {field}.",
               "Eine vertrauliche Angabe wurde mit der Person geprüft; sie lautet {field}.",
               "Im persönlichen Nachweis des Mitglieds wird die Angabe als {field} geführt."),
        False: ("Im Lagerkatalog ohne Personenzuordnung steht {field}.",
                "Dieser technische Eintrag betrifft nur Waren: {field}.",
                "Für nicht zugeordnete Lagergeräte lautet die Betriebsangabe {field}.",
                "Kein Kunde ist mit diesem Produkteintrag verbunden: {field}.",
                "Eine reine Geräteinventur nennt folgende Einzelheit: {field}.",
                "Diese öffentliche technische Beschreibung betrifft Lagerware: {field}."),
    },
    "fr": {
        True: ("Pour cette personne, le détail privé communiqué est {field}.",
               "Le membre a confirmé cette donnée personnelle : {field}.",
               "Lors de l'examen privé de cette personne, nous avons noté {field}.",
               "Le demandeur souhaite conserver ce détail personnel : {field}.",
               "Une donnée confidentielle a été vérifiée avec la personne ; elle indique {field}.",
               "Dans le justificatif personnel du membre, le détail figure comme {field}."),
        False: ("Le catalogue de stock sans personne attribuée indique {field}.",
                "Cette entrée technique concerne uniquement les marchandises : {field}.",
                "Pour le matériel de réserve non attribué, le détail est {field}.",
                "Aucun client n'est lié à cette entrée de produit : {field}.",
                "Une note d'inventaire limitée au matériel donne {field}.",
                "Cette description technique publique concerne le stock : {field}."),
    },
    "it": {
        True: ("Per questa persona il dettaglio privato fornito è {field}.",
               "Il membro ha confermato il seguente dato personale: {field}.",
               "Durante la verifica privata della persona abbiamo annotato {field}.",
               "Il richiedente vuole conservare questo dettaglio personale: {field}.",
               "Un dato riservato è stato verificato con la persona; risulta {field}.",
               "Nel documento personale del membro il dettaglio compare come {field}."),
        False: ("Il catalogo di scorte senza persona assegnata elenca {field}.",
                "Questa voce tecnica riguarda soltanto merci: {field}.",
                "Per le attrezzature di riserva non assegnate il dato è {field}.",
                "Nessun cliente è collegato a questa voce di prodotto: {field}.",
                "Una nota di inventario riservata al materiale indica {field}.",
                "Questa descrizione tecnica pubblica riguarda scorte: {field}."),
    },
    "es": {
        True: ("Para esta persona el detalle privado aportado es {field}.",
               "El miembro ha confirmado el siguiente dato personal: {field}.",
               "Durante la revisión privada de la persona anotamos {field}.",
               "El solicitante desea conservar este detalle personal: {field}.",
               "Se verificó un dato confidencial con la persona; figura como {field}.",
               "En el documento personal del miembro el detalle aparece como {field}."),
        False: ("El catálogo de existencias sin persona asignada indica {field}.",
                "Esta entrada técnica describe solamente mercancías: {field}.",
                "Para el equipo de reserva sin asignar el detalle es {field}.",
                "Ningún cliente está vinculado a esta entrada de producto: {field}.",
                "Una nota de inventario limitada al material indica {field}.",
                "Esta descripción técnica pública se refiere a existencias: {field}."),
    },
}
CUES = {
    "en": {"postal": ("Address", "Private delivery", "Delivery", "Home address"),
           "name": ("Recipient", "Private contact", "Contact person", "Recipient"),
           "age": ("age is", "age", "aged", "personal age"), "ref": "Case",
           "typed": ("my account IBAN", "personal phone", "date of birth"),
           "operational": ("Product serial", "Unassigned order code", "Manufacturing date", "Public maintenance calendar"),
           "phone": "Telephone", "social": "social security number",
           "clean": ("routing instruction", "public locality index", "catalogue routing description", "brand", "street name", "department", "operational duration", "product warranty", "measurement quantity")},
    "de": {"postal": ("Adresse", "Privatanschrift", "Zustellung", "Wohnanschrift"),
           "name": ("Empfänger", "Privatkontakt", "Kontaktperson", "Empfänger"),
           "age": ("Alter beträgt", "Alter", "Alter ist", "persönliches Alter"), "ref": "Fall",
           "typed": ("meine Konto-IBAN", "persönliches Telefon", "Geburtsdatum"),
           "operational": ("Produktseriencode", "Unvergebener Bestellcode", "Herstelldatum", "Öffentlicher Wartungskalender"),
           "phone": "Telefon", "social": "Sozialversicherungsnummer",
           "clean": ("Routenanweisung", "öffentlicher Ortsindex", "Katalogroutenbeschreibung", "Marke", "Straßenname", "Abteilung", "Betriebsdauer", "Produktgarantie", "Messmenge")},
    "fr": {"postal": ("Adresse", "Livraison privée", "Livraison", "Adresse personnelle"),
           "name": ("Destinataire", "Contact privé", "Personne de contact", "Destinataire"),
           "age": ("âge est", "âge", "âge actuel", "âge personnel"), "ref": "Dossier",
           "typed": ("IBAN de mon compte", "téléphone personnel", "date de naissance"),
           "operational": ("Numéro de série produit", "Code de commande non attribué", "Date de fabrication", "Calendrier public d'entretien"),
           "phone": "Téléphone", "social": "sécurité sociale",
           "clean": ("instruction de routage", "index public des localités", "description de routage du catalogue", "marque", "nom de rue", "département", "durée de fonctionnement", "garantie du produit", "quantité mesurée")},
    "it": {"postal": ("Indirizzo", "Consegna privata", "Consegna", "Indirizzo personale"),
           "name": ("Destinatario", "Contatto privato", "Persona di contatto", "Destinatario"),
           "age": ("età è", "età", "età attuale", "età personale"), "ref": "Caso",
           "typed": ("IBAN del mio conto", "telefono personale", "data di nascita"),
           "operational": ("Seriale prodotto", "Codice ordine non assegnato", "Data di fabbricazione", "Calendario pubblico di manutenzione"),
           "phone": "Telefono", "social": "previdenza",
           "clean": ("istruzione di instradamento", "indice pubblico delle località", "descrizione del percorso di catalogo", "marchio", "nome di strada", "reparto", "durata operativa", "garanzia del prodotto", "quantità misurata")},
    "es": {"postal": ("Dirección", "Entrega privada", "Entrega", "Dirección personal"),
           "name": ("Destinatario", "Contacto privado", "Persona de contacto", "Destinatario"),
           "age": ("edad es", "edad", "edad actual", "edad personal"), "ref": "Caso",
           "typed": ("IBAN de mi cuenta", "teléfono personal", "fecha de nacimiento"),
           "operational": ("Número de serie", "Código de pedido sin asignar", "Fecha de fabricación", "Calendario público de mantenimiento"),
           "phone": "Teléfono", "social": "seguridad social",
           "clean": ("instrucción de ruta", "índice público de localidades", "descripción de ruta del catálogo", "marca", "nombre de calle", "departamento", "duración operativa", "garantía del producto", "cantidad medida")},
}


def template(language, split, component, cell, paraphrase, personal):
    cues = CUES[language]
    if component.startswith("postal"):
        cue = cues["postal"][paraphrase] if personal else cues["clean"][cell]
    elif component == "whole_person_names":
        cue = cues["name"][paraphrase]
    elif component == "name_nonpersonal_twins":
        cue = cues["clean"][3 + cell]
    elif component == "age_whole_value":
        cue = cues["age"][paraphrase]
    elif component == "nonpersonal_duration_quantity":
        cue = cues["clean"][6 + cell]
    elif "reference" in component:
        patient_cue = {"en": "Patient reference", "de": "Patientenreferenz", "fr": "Référence patient",
                       "it": "Riferimento paziente", "es": "Referencia del paciente"}[language]
        cue = (patient_cue if paraphrase == 1 else cues["ref"]) if personal else {
            "en": ("Order code", "Invoice reference", "Product serial"),
            "de": ("Bestellcode", "Rechnungsreferenz", "Produktseriencode"),
            "fr": ("Code de commande", "Référence de facture", "Numéro de série produit"),
            "it": ("Codice ordine", "Riferimento fattura", "Seriale prodotto"),
            "es": ("Código de pedido", "Referencia de factura", "Número de serie"),
        }[language][cell]
    elif "operational_shape" in component:
        shape, regime = divmod(cell, 2)
        cue = cues["typed"][shape] if personal else cues["operational"][shape + (shape == 2 and regime)]
    elif "multiline" in component:
        cue = cues["phone"] if personal else cues["operational"][1]
    elif component.startswith("social_number"):
        cue = cues["social"] if personal else cues["operational"][1]
    else:
        cue = ("permis", "permis de conduire")[paraphrase % 2] if personal else cues["operational"][0]
    separator = ":\n" if component == "age_whole_value" and cell == 2 else ": "
    if component == "age_whole_value" and cell == 1:
        separator = " "
    field = cue + separator + "{x}"
    offset = 0 if split == "train" else 4
    return WRAPPERS[language][personal][offset + paraphrase].replace("{field}", field)
