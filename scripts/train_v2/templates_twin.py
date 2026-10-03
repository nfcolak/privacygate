"""Matched positive constructions: exactly the same payload as clean twins."""
TWINS = {
    "en": {
        "invoice": ("Customer number {x} was recorded for the applicant.", "The patient's ledger lists personal case {x} for the applicant."),
        "order": ("Membership code {x} was assigned to the applicant.", "The individual member is tracked under personal reference {x}."),
        "sku": ("Patient identifier {x} appears on the person's letter.", "The patient's personal entry uses reference {x}."),
        "date": ("The applicant's birth date is {x}.", "The applicant was born on {x}."),
        "time": ("The applicant's birth date and time are {x}.", "The person's recorded date and time of birth are {x}."),
        "place": ("The person's private home is at {x}.", "The private delivery guide locates the applicant's home at {x}."),
        "room": ("Customer number {x} appears on the person's registration.", "The patient's letter points to personal case {x}."),
        "statistics": ("The applicant is aged {x}.", "The age of the individual applicant is {x} years."),
    },
    "de": {
        "invoice": ("Die Kundennummer {x} wurde für die antragstellende Person erfasst.", "Die Patientenakte nennt das persönliche Aktenzeichen {x} für die Person."),
        "order": ("Der Mitgliedscode {x} wurde der Person zugewiesen.", "Das einzelne Mitglied wird unter der persönlichen Referenz {x} geführt."),
        "sku": ("Die Patientenkennung {x} steht auf dem persönlichen Brief.", "Der persönliche Patienteneintrag verwendet die Referenz {x}."),
        "date": ("Das Geburtsdatum der Person ist {x}.", "Die antragstellende Person wurde am {x} geboren."),
        "time": ("Geburtsdatum und Geburtszeit der Person lauten {x}.", "Das erfasste Geburtsdatum mit Geburtszeit der Person lautet {x}."),
        "place": ("Das private Zuhause der Person liegt in {x}.", "Der private Zustellhinweis verortet das Zuhause der Person in {x}."),
        "room": ("Die Kundennummer {x} steht auf der persönlichen Anmeldung.", "Der Patientenbrief weist auf das persönliche Aktenzeichen {x} hin."),
        "statistics": ("Die antragstellende Person ist {x} Jahre alt.", "Das Alter der einzelnen antragstellenden Person beträgt {x} Jahre."),
    },
    "fr": {
        "invoice": ("Le numéro de client {x} a été enregistré pour le demandeur.", "Le dossier du patient indique la référence personnelle {x} pour cette personne."),
        "order": ("Le code d'adhésion {x} a été attribué au demandeur.", "Le membre individuel est suivi sous la référence personnelle {x}."),
        "sku": ("L'identifiant du patient {x} figure sur sa lettre personnelle.", "L'entrée personnelle du patient utilise la référence {x}."),
        "date": ("La date de naissance de la personne est {x}.", "La personne qui demande l'inscription est née le {x}."),
        "time": ("La date et l'heure de naissance de la personne sont {x}.", "La date et l'heure de naissance enregistrées pour cette personne sont {x}."),
        "place": ("Le domicile privé de la personne se trouve à {x}.", "Le guide de livraison privé situe le domicile du demandeur à {x}."),
        "room": ("Le numéro de client {x} figure sur l'inscription personnelle.", "La lettre du patient indique le dossier personnel {x}."),
        "statistics": ("La personne est âgée de {x} ans.", "L'âge de la personne qui demande l'inscription est de {x} ans."),
    },
    "it": {
        "invoice": ("Il numero cliente {x} è stato registrato per il richiedente.", "La cartella del paziente indica la pratica personale {x} per questa persona."),
        "order": ("Il codice di iscrizione {x} è stato assegnato al richiedente.", "Il singolo membro è seguito con il riferimento personale {x}."),
        "sku": ("L'identificativo del paziente {x} appare sulla sua lettera personale.", "La voce personale del paziente usa il riferimento {x}."),
        "date": ("La data di nascita della persona è {x}.", "La persona che presenta la domanda è nata il {x}."),
        "time": ("La data e l'ora di nascita della persona sono {x}.", "La data e l'ora di nascita registrate per questa persona sono {x}."),
        "place": ("La casa privata della persona si trova in {x}.", "La guida privata della consegna colloca il domicilio del richiedente in {x}."),
        "room": ("Il numero cliente {x} appare sull'iscrizione personale.", "La lettera del paziente indica la pratica personale {x}."),
        "statistics": ("La persona che presenta la domanda ha {x} anni.", "L'età del singolo richiedente è di {x} anni."),
    },
    "es": {
        "invoice": ("El número de cliente {x} se registró para el solicitante.", "El expediente del paciente indica la referencia personal {x} para esta persona."),
        "order": ("El código de afiliación {x} se asignó al solicitante.", "El miembro individual se sigue con la referencia personal {x}."),
        "sku": ("El identificador del paciente {x} aparece en su carta personal.", "La entrada personal del paciente usa la referencia {x}."),
        "date": ("La fecha de nacimiento de la persona es {x}.", "La persona que presenta la solicitud nació el {x}."),
        "time": ("La fecha y hora de nacimiento de la persona son {x}.", "La fecha y hora de nacimiento registradas para esta persona son {x}."),
        "place": ("El domicilio privado de la persona está en {x}.", "La guía privada de entrega sitúa el domicilio del solicitante en {x}."),
        "room": ("El número de cliente {x} figura en la inscripción personal.", "La carta del paciente señala el expediente personal {x}."),
        "statistics": ("La persona que presenta la solicitud tiene {x} años.", "La edad del solicitante individual es de {x} años."),
    },
}


TRANSPORT = {
    "en": {"gate": ("Membership number {x} is printed on the applicant's letter.", "The member's registration labels personal reference {x}."),
           "platform": ("Patient number {x} is printed on the person's letter.", "The patient's registration labels personal case {x}.")},
    "de": {"gate": ("Die Mitgliedsnummer {x} steht auf dem Brief der Person.", "Die Anmeldung des Mitglieds bezeichnet die persönliche Referenz {x}."),
           "platform": ("Die Patientennummer {x} steht auf dem persönlichen Brief.", "Die Anmeldung des Patienten bezeichnet das persönliche Aktenzeichen {x}.")},
    "fr": {"gate": ("Le numéro d'adhésion {x} est imprimé sur la lettre du demandeur.", "L'inscription du membre indique la référence personnelle {x}."),
           "platform": ("Le numéro de patient {x} est imprimé sur sa lettre personnelle.", "L'inscription du patient indique le dossier personnel {x}.")},
    "it": {"gate": ("Il numero di iscrizione {x} è stampato sulla lettera del richiedente.", "L'iscrizione del membro indica il riferimento personale {x}."),
           "platform": ("Il numero paziente {x} è stampato sulla lettera personale.", "L'iscrizione del paziente indica la pratica personale {x}.")},
    "es": {"gate": ("El número de afiliación {x} está impreso en la carta del solicitante.", "La inscripción del miembro indica la referencia personal {x}."),
           "platform": ("El número de paciente {x} está impreso en su carta personal.", "La inscripción del paciente indica el expediente personal {x}.")},
}
for _language, _templates in TRANSPORT.items():
    TWINS[_language].update(_templates)


def twin_template(language, split, kind):
    return TWINS[language][kind][0 if split == "train" else 1]
