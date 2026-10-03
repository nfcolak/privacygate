"""Lookalikes explicitly linked to goods, brands, batches or non-human samples."""
NEAR = {
    "en": {
        "iban": ("The lamp's serial code is {x}; it identifies a product, not a bank account.", "The spare-part batch carries {x} as a product serial, with no account holder."),
        "phone": ("The engine model number is {x}, not a contact telephone.", "The device catalog uses {x} as a hardware serial without a subscriber."),
        "passport": ("The valve product serial is {x}; this is not a travel document.", "The manufactured part bears batch number {x}, unrelated to any passport holder."),
        "id": ("The panel's model number is {x}; it does not identify a person.", "The catalog lists item serial {x}, with no identity-card owner."),
        "date": ("The batch production date is {x}.", "The release date printed on the product is {x}, not a person's birthday."),
        "name": ("The invented product brand is {x}, not the name of a person.", "The catalog uses {x} as a fictional model brand rather than an individual."),
        "sample": ("The mineral specimen from the quarry has lab sample ID {x}, with no human donor.", "The soil sample is registered as {x}; it is not linked to a patient."),
        "batch": ("The batch number of the metal stock is {x}.", "The factory assigns {x} to this production lot, with no customer association."),
    },
    "de": {
        "iban": ("Der Seriencode der Lampe lautet {x}; er bezeichnet ein Produkt, kein Bankkonto.", "Die Ersatzteilcharge trägt {x} als Produktserie, ohne Kontoinhaber."),
        "phone": ("Die Motormodellnummer lautet {x}, nicht eine Kontakttelefonnummer.", "Der Gerätekatalog nutzt {x} als Hardwareserie ohne Telefonteilnehmer."),
        "passport": ("Die Produktserie des Ventils lautet {x}; dies ist kein Reisedokument.", "Das gefertigte Teil trägt die Charge {x}, ohne Bezug zu einem Passinhaber."),
        "id": ("Die Modellnummer der Platte lautet {x}; sie bezeichnet keine Person.", "Der Katalog nennt die Artikelserie {x}, ohne Ausweisinhaber."),
        "date": ("Das Produktionsdatum der Charge ist {x}.", "Das aufgedruckte Erscheinungsdatum des Produkts ist {x}, nicht der Geburtstag einer Person."),
        "name": ("Die erfundene Produktmarke heißt {x}, nicht eine Person.", "Der Katalog verwendet {x} als fiktive Modellmarke statt als Personenname."),
        "sample": ("Die Mineralprobe aus dem Steinbruch hat die Laborprobenkennung {x}, ohne menschlichen Spender.", "Die Bodenprobe ist als {x} registriert; sie ist keinem Patienten zugeordnet."),
        "batch": ("Die Chargennummer des Metallvorrats lautet {x}.", "Die Fabrik ordnet {x} diesem Produktionslos zu, ohne Kundenbezug."),
    },
    "fr": {
        "iban": ("Le code de série de la lampe est {x} ; il désigne un produit, pas un compte bancaire.", "Le lot de pièces porte {x} comme série de produit, sans titulaire de compte."),
        "phone": ("Le numéro de modèle du moteur est {x}, pas un téléphone de contact.", "Le catalogue utilise {x} comme série du matériel sans abonné téléphonique."),
        "passport": ("La série du produit vanne est {x} ; ce n'est pas un document de voyage.", "La pièce fabriquée porte le lot {x}, sans rapport avec un titulaire de passeport."),
        "id": ("Le numéro de modèle du panneau est {x} ; il n'identifie aucune personne.", "Le catalogue indique la série d'article {x}, sans propriétaire de carte d'identité."),
        "date": ("La date de production du lot est {x}.", "La date de sortie imprimée sur le produit est {x}, pas l'anniversaire d'une personne."),
        "name": ("La marque de produit inventée est {x}, pas le nom d'une personne.", "Le catalogue emploie {x} comme marque fictive du modèle plutôt que comme individu."),
        "sample": ("Le spécimen minéral de la carrière porte l'identifiant de laboratoire {x}, sans donneur humain.", "L'échantillon de sol est enregistré sous {x} ; il n'est lié à aucun patient."),
        "batch": ("Le numéro du lot de métal en stock est {x}.", "L'usine attribue {x} à ce lot de production, sans lien avec un client."),
    },
    "it": {
        "iban": ("Il codice di serie della lampada è {x}; identifica un prodotto, non un conto bancario.", "Il lotto di ricambi porta {x} come serie del prodotto, senza titolare di conto."),
        "phone": ("Il numero di modello del motore è {x}, non un telefono di contatto.", "Il catalogo usa {x} come serie dell'hardware senza abbonato telefonico."),
        "passport": ("La serie del prodotto valvola è {x}; non è un documento di viaggio.", "Il pezzo fabbricato porta il lotto {x}, senza rapporto con un titolare di passaporto."),
        "id": ("Il numero di modello del pannello è {x}; non identifica una persona.", "Il catalogo indica la serie dell'articolo {x}, senza proprietario di carta d'identità."),
        "date": ("La data di produzione del lotto è {x}.", "La data di uscita stampata sul prodotto è {x}, non il compleanno di una persona."),
        "name": ("Il marchio di prodotto inventato è {x}, non il nome di una persona.", "Il catalogo usa {x} come marchio fittizio del modello invece di un individuo."),
        "sample": ("Il campione minerale della cava ha l'identificativo di laboratorio {x}, senza donatore umano.", "Il campione di terreno è registrato come {x}; non è collegato a un paziente."),
        "batch": ("Il numero di lotto del metallo in magazzino è {x}.", "La fabbrica assegna {x} a questo lotto produttivo, senza legame con un cliente."),
    },
    "es": {
        "iban": ("El código de serie de la lámpara es {x}; identifica un producto, no una cuenta bancaria.", "El lote de repuestos lleva {x} como serie del producto, sin titular de cuenta."),
        "phone": ("El número de modelo del motor es {x}, no un teléfono de contacto.", "El catálogo usa {x} como serie del equipo sin abonado telefónico."),
        "passport": ("La serie del producto válvula es {x}; no es un documento de viaje.", "La pieza fabricada lleva el lote {x}, sin relación con un titular de pasaporte."),
        "id": ("El número de modelo del panel es {x}; no identifica a una persona.", "El catálogo indica la serie de artículo {x}, sin dueño de tarjeta de identidad."),
        "date": ("La fecha de producción del lote es {x}.", "La fecha de lanzamiento impresa en el producto es {x}, no el cumpleaños de una persona."),
        "name": ("La marca de producto inventada es {x}, no el nombre de una persona.", "El catálogo usa {x} como marca ficticia del modelo en lugar de un individuo."),
        "sample": ("La muestra mineral de la cantera tiene el identificador de laboratorio {x}, sin donante humano.", "La muestra de suelo se registra como {x}; no está vinculada a un paciente."),
        "batch": ("El número de lote del metal almacenado es {x}.", "La fábrica asigna {x} a este lote de producción, sin asociación con un cliente."),
    },
}
BOUNDARY = {
    "en": ("The customer {name}, living at {address}, can be called on {phone}.", "For the resident {name}, the home address is {address}, and their phone number is {phone}."),
    "de": ("Die Person {name}, wohnhaft in {address}, ist unter {phone} telefonisch erreichbar.", "Für das Mitglied {name} gilt die Wohnanschrift {address}, und seine Telefonnummer lautet {phone}."),
    "fr": ("La personne {name}, domiciliée à {address}, est joignable au {phone}.", "Pour le membre {name}, l'adresse du domicile est {address}, et son numéro de téléphone est {phone}."),
    "it": ("La persona {name}, residente in {address}, è raggiungibile al {phone}.", "Per il membro {name}, l'indirizzo di casa è {address}, e il suo numero di telefono è {phone}."),
    "es": ("La persona {name}, que vive en {address}, está disponible por teléfono en {phone}.", "Para el miembro {name}, la dirección de casa es {address}, y su número de teléfono es {phone}."),
}


def near_template(language, split, kind):
    if kind.startswith("iban_"):
        kind = "iban"
    return NEAR[language][kind][0 if split == "train" else 1]


def boundary_template(language, split):
    return BOUNDARY[language][0 if split == "train" else 1]
