"""Semantic age and correspondence scopes with held-out dev grammars."""
AGES = {
    "en": (("My age is {x}.", "The applicant states their age: {x}."),
           ("I am {x} old.", "The recipient is {x} old."),
           ("I was born in the spring; today I have reached [{x}].", "The applicant celebrates another birthday [{x}].")),
    "de": (("Mein Alter ist {x}.", "Die antragstellende Person nennt ihr Alter: {x}."),
           ("Ich bin {x} alt.", "Die empfangende Person ist {x} alt."),
           ("Ich wurde im Frühling geboren; heute bin ich [{x}].", "Die antragstellende Person feiert Geburtstag [{x}].")),
    "fr": (("Mon âge est {x}.", "La personne candidate indique son âge : {x}."),
           ("J'ai {x}.", "La personne destinataire a {x}."),
           ("Je suis né au printemps ; j'ai maintenant [{x}].", "La personne candidate fête son anniversaire [{x}].")),
    "it": (("La mia età è {x}.", "La persona candidata dichiara la sua età: {x}."),
           ("Ho {x}.", "La persona destinataria ha {x}."),
           ("Sono nato in primavera; ora ho [{x}].", "La persona candidata festeggia il compleanno [{x}].")),
    "es": (("Mi edad es {x}.", "La persona solicitante declara su edad: {x}."),
           ("Tengo {x}.", "La persona destinataria tiene {x}."),
           ("Nací en primavera; ahora tengo [{x}].", "La persona solicitante celebra su cumpleaños [{x}].")),
}
DEV_AGES = {
    "en": (("How old are you? I answer: {x}.", "Age reported by the resident — {x}."),
           ("Having turned {x}, I may sign.", "Aged {x}, the applicant may enter."),
           ("At my birthday dinner I wrote [{x}] beside my portrait.", "The resident's birthday candle total is [{x}].")),
    "de": (("Wie alt bist du? Meine Antwort: {x}.", "Von der bewohnenden Person angegebenes Alter — {x}."),
           ("Mit meinen {x} darf ich unterschreiben.", "Im Alter von {x} darf die antragstellende Person eintreten."),
           ("Zum Geburtstag schrieb ich [{x}] neben mein Porträt.", "Die Zahl der Geburtstagskerzen der bewohnenden Person ist [{x}].")),
    "fr": (("Quel âge avez-vous ? Je réponds : {x}.", "Âge communiqué par la personne résidente — {x}."),
           ("Ayant atteint {x}, je peux signer.", "À l'âge de {x}, la personne candidate peut entrer."),
           ("À mon anniversaire, j'ai écrit [{x}] à côté de mon portrait.", "Le nombre de bougies d'anniversaire de la personne résidente est [{x}].")),
    "it": (("Quanti anni hai? Rispondo: {x}.", "Età comunicata dalla persona residente — {x}."),
           ("Avendo compiuto {x}, posso firmare.", "All'età di {x}, la persona candidata può entrare."),
           ("Al mio compleanno ho scritto [{x}] accanto al mio ritratto.", "Il numero di candeline di compleanno della persona residente è [{x}].")),
    "es": (("¿Cuántos años tienes? Respondo: {x}.", "Edad comunicada por la persona residente — {x}."),
           ("Al cumplir {x}, puedo firmar.", "A la edad de {x}, la persona solicitante puede entrar."),
           ("En mi cumpleaños escribí [{x}] junto a mi retrato.", "El número de velas de cumpleaños de la persona residente es [{x}].")),
}
CLEAN_AGES = {
    "en": ("The projected service lifetime is {x}.", "The nonpersonal storage duration is {x}.", "The product tray quantity is [{x}]."),
    "de": ("Die vorgesehene Nutzungsdauer beträgt {x}.", "Die sachliche Lagerdauer beträgt {x}.", "Die Menge im Produktbehälter ist [{x}]."),
    "fr": ("La durée de vie prévue est {x}.", "La durée de stockage non personnelle est {x}.", "La quantité du plateau de produits est [{x}]."),
    "it": ("La durata di servizio prevista è {x}.", "La durata di conservazione non personale è {x}.", "La quantità nel vassoio del prodotto è [{x}]."),
    "es": ("La vida útil prevista es {x}.", "La duración de almacenamiento no personal es {x}.", "La cantidad de la bandeja del producto es [{x}]."),
}
DEV_CLEAN_AGES = {
    "en": ("For how many cycles? The machine specification answers {x}.", "After {x}, replace the unassigned test fixture.", "Catalogue prose uses the word [{x}] for the count of parts."),
    "de": ("Für wie viele Zyklen? Die Maschinenspezifikation antwortet {x}.", "Nach {x} das nicht zugeordnete Testgerät ersetzen.", "Der Katalogtext verwendet das Wort [{x}] für die Teilezahl."),
    "fr": ("Pour combien de cycles ? La fiche de machine répond {x}.", "Après {x}, remplacer le dispositif d'essai non attribué.", "Le texte du catalogue utilise le mot [{x}] pour compter les pièces."),
    "it": ("Per quanti cicli? La scheda della macchina risponde {x}.", "Dopo {x}, sostituire il dispositivo di prova non assegnato.", "Il testo del catalogo usa la parola [{x}] per contare i pezzi."),
    "es": ("¿Para cuántos ciclos? La ficha de la máquina responde {x}.", "Después de {x}, sustituir el dispositivo de prueba sin asignar.", "El texto del catálogo usa la palabra [{x}] para contar piezas."),
}
NAMES = {
    "en": ("Thank you for your reply.\nWarm regards,\n{x}", "I approve this request.\nSigned personally: {x}", "Dear {x},\nPlease confirm your visit."),
    "de": ("Vielen Dank für Ihre Antwort.\nMit herzlichen Grüßen\n{x}", "Ich genehmige diesen Antrag.\nPersönlich unterzeichnet: {x}", "Liebe Person {x},\nBitte bestätigen Sie Ihren Besuch."),
    "fr": ("Merci pour votre réponse.\nBien cordialement,\n{x}", "J'approuve cette demande.\nSigné personnellement : {x}", "Bonjour {x},\nMerci de confirmer votre visite."),
    "it": ("Grazie per la risposta.\nCordiali saluti,\n{x}", "Approvo questa richiesta.\nFirmato personalmente: {x}", "Gentile {x},\nConfermi la sua visita."),
    "es": ("Gracias por su respuesta.\nUn saludo cordial,\n{x}", "Apruebo esta solicitud.\nFirmado personalmente: {x}", "Estimada persona {x},\nConfirme su visita."),
}
DEV_NAMES = {
    "en": ("Until our next meeting,\n{x}\nYour correspondent", "{x}\nHandwritten signature of the applicant", "To {x}: welcome, and take a seat."),
    "de": ("Bis zu unserem nächsten Treffen\n{x}\nIhre korrespondierende Person", "{x}\nHandschriftliche Unterschrift der antragstellenden Person", "An {x}: willkommen, bitte nehmen Sie Platz."),
    "fr": ("À notre prochaine rencontre,\n{x}\nVotre correspondant", "{x}\nSignature manuscrite de la personne candidate", "À {x} : bienvenue, prenez place."),
    "it": ("Al nostro prossimo incontro,\n{x}\nLa persona che vi scrive", "{x}\nFirma manoscritta della persona candidata", "A {x}: benvenuti, accomodatevi."),
    "es": ("Hasta nuestro próximo encuentro,\n{x}\nLa persona que le escribe", "{x}\nFirma manuscrita de la persona solicitante", "Para {x}: bienvenida, tome asiento."),
}
CLEAN_NAMES = {
    "en": ("Catalogue footer — team brand, not a signer:\n{x}", "Unsigned product sheet.\nDisplay title: {x}", "Organisation banner text: {x}; no personal addressee."),
    "de": ("Katalogfußzeile — Teammarke, keine Unterschrift:\n{x}", "Nicht unterzeichnetes Produktblatt.\nAnzeigetitel: {x}", "Text des Organisationsbanners: {x}; keine persönliche Anrede."),
    "fr": ("Pied du catalogue — marque d'équipe, pas de signature :\n{x}", "Fiche de produit non signée.\nTitre affiché : {x}", "Texte de la bannière de l'organisation : {x} ; aucun destinataire personnel."),
    "it": ("Piè di catalogo — marchio della squadra, non una firma:\n{x}", "Scheda di prodotto non firmata.\nTitolo esposto: {x}", "Testo del banner dell'organizzazione: {x}; nessun destinatario personale."),
    "es": ("Pie del catálogo — marca del equipo, no firma:\n{x}", "Ficha de producto sin firmar.\nTítulo expuesto: {x}", "Texto del banner de la organización: {x}; ningún destinatario personal."),
}
DEV_CLEAN_NAMES = {
    "en": ("{x}\nThis closing mark identifies a workshop team, not an author.", "The unassigned model is sold under the stock label [{x}].", "A quoted organisation title, «{x}», appears in the exhibit index."),
    "de": ("{x}\nDieses Schlusszeichen bezeichnet ein Werkstattteam, keine schreibende Person.", "Das nicht zugeordnete Modell wird unter der Lagerbezeichnung [{x}] verkauft.", "Der zitierte Organisationstitel «{x}» steht im Ausstellungsverzeichnis."),
    "fr": ("{x}\nCette marque finale désigne une équipe d'atelier, pas un auteur.", "Le modèle non attribué est vendu sous l'étiquette de stock [{x}].", "Un titre d'organisation cité, «{x}», figure dans l'index de l'exposition."),
    "it": ("{x}\nQuesto marchio finale indica una squadra di officina, non un autore.", "Il modello non assegnato è venduto con l'etichetta di magazzino [{x}].", "Un titolo di organizzazione citato, «{x}», compare nell'indice della mostra."),
    "es": ("{x}\nEsta marca final identifica un equipo de taller, no un autor.", "El modelo sin asignar se vende con la etiqueta de almacén [{x}].", "Un título de organización citado, «{x}», aparece en el índice de la exposición."),
}


def frame(component, language, split, layout, scope, positive):
    if component == "semantic_ages":
        if positive:
            return (DEV_AGES if split == "dev" else AGES)[language][layout][scope]
        phrase = (DEV_CLEAN_AGES if split == "dev" else CLEAN_AGES)[language][layout]
        # Scope two is a separate specification field rather than a duplicate.
        return phrase if not scope else "[" + phrase + "]"
    pool = ((DEV_NAMES if split == "dev" else NAMES) if positive else
            (DEV_CLEAN_NAMES if split == "dev" else CLEAN_NAMES))
    return pool[language][scope]
