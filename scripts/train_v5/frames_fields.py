"""Field- and section-owned envelopes; no stress templates are imported."""
from .lexicon import FIELDS, ROLES

CONNECTORS = {
    "en": ("Record", "Declared field", "Section", "Entry"),
    "de": ("Datensatz", "Angegebenes Feld", "Abschnitt", "Eintrag"),
    "fr": ("Fiche", "Champ déclaré", "Rubrique", "Entrée"),
    "it": ("Scheda", "Campo dichiarato", "Sezione", "Voce"),
    "es": ("Ficha", "Campo declarado", "Sección", "Entrada"),
}
POSTAL_DEV = {
    "en": ("Deliver the personal letter to the following home destination:\n{x}\nEnd of destination.",
           "The catalogue illustrates a fictional postal layout, not a person's destination:\n{x}\nEnd of exhibit."),
    "de": ("Den persönlichen Brief an dieses Wohnziel zustellen:\n{x}\nEnde des Ziels.",
           "Der Katalog zeigt ein fiktives Postlayout, keine persönliche Zustelladresse:\n{x}\nEnde des Exponats."),
    "fr": ("Livrer la lettre personnelle à ce domicile :\n{x}\nFin de la destination.",
           "Le catalogue illustre un format postal fictif, pas une destination personnelle :\n{x}\nFin de l'exposition."),
    "it": ("Consegnare la lettera personale a questa abitazione:\n{x}\nFine della destinazione.",
           "Il catalogo illustra un formato postale fittizio, non una destinazione personale:\n{x}\nFine dell'esposizione."),
    "es": ("Entregar la carta personal en este domicilio:\n{x}\nFin del destino.",
           "El catálogo ilustra un formato postal ficticio, no un destino personal:\n{x}\nFin de la exposición."),
}
PHONE_DEV = {
    "en": ("To reach me directly, dial\n{x}\nThis is my own line.",
           "The malformed equipment serial is\n{x}\nIt has no subscriber."),
    "de": ("Um mich direkt zu erreichen, wählen Sie\n{x}\nDas ist mein eigener Anschluss.",
           "Die fehlerhafte Geräteserie lautet\n{x}\nSie hat keine teilnehmende Person."),
    "fr": ("Pour me joindre directement, composez\n{x}\nC'est ma propre ligne.",
           "La série d'équipement mal formée est\n{x}\nElle n'a aucun abonné."),
    "it": ("Per raggiungermi direttamente, componete\n{x}\nÈ la mia linea personale.",
           "La serie errata dell'apparecchio è\n{x}\nNon ha alcun abbonato."),
    "es": ("Para comunicarse directamente conmigo, marque\n{x}\nEs mi propia línea.",
           "La serie mal formada del equipo es\n{x}\nNo tiene abonado."),
}
DATE_DEV = {
    "en": ("I was born on", "The maintenance calendar lists"),
    "de": ("Ich wurde geboren am", "Der Wartungskalender nennt"),
    "fr": ("Je suis né le", "Le calendrier de maintenance indique"),
    "it": ("Sono nato il", "Il calendario di manutenzione indica"),
    "es": ("Nací el", "El calendario de mantenimiento indica"),
}
DOC_DEV = {
    "en": ("The holder confirms that this is their personal document", "No holder is assigned; this is an equipment/invoice template"),
    "de": ("Die innehabende Person bestätigt ihr persönliches Dokument", "Niemand ist zugeordnet; dies ist eine Geräte- oder Rechnungsvorlage"),
    "fr": ("La personne titulaire confirme son document personnel", "Aucun titulaire n'est attribué ; c'est un modèle d'équipement ou de facture"),
    "it": ("La persona titolare conferma il proprio documento personale", "Non è assegnato alcun titolare; è un modello di apparecchio o fattura"),
    "es": ("La persona titular confirma su documento personal", "No hay titular asignado; es una plantilla de equipo o factura"),
}


def postal_frame(language, split, layout, scope, sample, positive):
    f = FIELDS[language]
    if split == "dev":
        return POSTAL_DEV[language][0 if positive else 1]
    key = f["private" if positive else "specimen"]
    word = CONNECTORS[language][(layout + scope + sample) % 4]
    # Preserve a bounded value field despite its internal pipe/slash/newline.
    return f"{word} — {key}:\n{{x}}\n[{word}]"


def birth_frame(language, split, layout, scope, sample, positive):
    f = FIELDS[language]
    variant = (layout + scope + sample) % 4
    separator = (": ", " = ", "\n", ":\n")[variant]
    key = f["birth" if positive else "calendar"][scope]
    if split == "dev":
        if scope == 0:
            return DATE_DEV[language][0 if positive else 1] + separator + "{x}."
        # Held-out field-first structure with ownership/context after the value.
        tail = f["owner" if positive else "operational"]
        return f"({key}{separator}{{x}})\n{tail}."
    prefix = f["personal" if positive else "operational"]
    return f"{prefix}\n{key}{separator}{{x}}\n{CONNECTORS[language][variant]}"


def phone_frame(language, split, layout, scope, sample, positive):
    f = FIELDS[language]
    if split == "dev" and scope:
        return PHONE_DEV[language][0 if positive else 1]
    key = (ROLES[language]["phone"][(layout + sample) % 4] if positive else f["phone_sample"])
    if split == "dev":
        return f"({{x}}) ← {key}; {f['owner' if positive else 'operational']}."
    prefix = f["owner" if positive and scope else "personal" if positive else "operational"]
    return f"{prefix}\n{key} = {{x}}"


def document_frame(language, split, layout, scope, sample, positive):
    f = FIELDS[language]
    label, separator = divmod(layout, 3)
    key = f["documents"][label][scope] if positive else f["codes"][label]
    binding = (": ", " = ", ":\n")[separator]
    if split == "dev":
        tail = DOC_DEV[language][0 if positive else 1]
        return f"{key}{binding}{{x}}\n({tail})"
    prefix = f["personal" if positive and not scope else "owner" if positive else "operational"]
    return f"{prefix}\n{CONNECTORS[language][sample % 4]} — {key}{binding}{{x}}"


BUILDERS = {"postal_object_envelopes": postal_frame, "birth_calendar_fields": birth_frame,
            "balanced_phone_envelopes": phone_frame, "document_alias_sections": document_frame}
