"""Non-person numeric prose; each dev construction is held out in full."""
NUMERIC = {
    "en": {
        "statistics": ("The oldest test machine is {x} years old.", "The equipment survey reports an average machine age of {x} years."),
        "percentages": ("The production yield increased by {x}%.", "The chart shows {x}% of the manufactured parts passed inspection."),
        "version": ("The firmware version is {x}.", "The released software build carries version {x}."),
        "measurements": ("The steel panel measures {x} cm.", "The engineering drawing gives the crate dimensions as {x} cm."),
        "timetable": ("The public train timetable lists departure at {x}.", "The station's published service begins at {x}."),
        "scores": ("The game ended with a team score of {x}.", "The tournament scoreboard shows the result {x}."),
        "tracking": ("The unassigned stock parcel has tracking number {x}; no recipient is recorded.", "Shipment {x} contains spare parts for warehouse stock, without a personal recipient."),
        "quantity": ("The warehouse stores {x} bolts.", "The inventory count is {x} components."),
    },
    "de": {
        "statistics": ("Die älteste Testmaschine ist {x} Jahre alt.", "Die Geräteübersicht nennt ein durchschnittliches Maschinenalter von {x} Jahren."),
        "percentages": ("Die Produktionsausbeute stieg um {x}%.", "Laut Diagramm bestanden {x}% der gefertigten Teile die Prüfung."),
        "version": ("Die Firmwareversion lautet {x}.", "Die veröffentlichte Softwareausgabe trägt die Version {x}."),
        "measurements": ("Die Stahlplatte misst {x} cm.", "Die technische Zeichnung gibt die Kistenmaße mit {x} cm an."),
        "timetable": ("Der öffentliche Fahrplan nennt die Abfahrt um {x}.", "Der veröffentlichte Bahnhofsbetrieb beginnt um {x}."),
        "scores": ("Das Spiel endete mit dem Mannschaftsergebnis {x}.", "Die Turnieranzeige zeigt den Spielstand {x}."),
        "tracking": ("Das nicht zugeordnete Lagerpaket hat die Sendungsnummer {x}; es ist kein Empfänger erfasst.", "Die Sendung {x} enthält Ersatzteile für das Lager, ohne persönlichen Empfänger."),
        "quantity": ("Im Lager liegen {x} Schrauben.", "Die Inventur zählt {x} Bauteile."),
    },
    "fr": {
        "statistics": ("La plus ancienne machine d'essai a {x} ans.", "L'enquête sur le matériel indique un âge moyen des machines de {x} ans."),
        "percentages": ("Le rendement de production a augmenté de {x}%.", "Le graphique montre que {x}% des pièces fabriquées ont réussi le contrôle."),
        "version": ("La version du micrologiciel est {x}.", "Le logiciel distribué a été compilé dans l'édition {x}."),
        "measurements": ("Le panneau en acier mesure {x} cm.", "Le dessin technique donne les dimensions de la caisse : {x} cm."),
        "timetable": ("L'horaire public des trains indique un départ à {x}.", "Le service publié de la gare commence à {x}."),
        "scores": ("Le match s'est terminé sur un score d'équipe de {x}.", "Le tableau du tournoi affiche le résultat {x}."),
        "tracking": ("Le colis de stock non attribué porte le numéro de suivi {x}, sans destinataire enregistré.", "L'envoi {x} contient des pièces pour le dépôt, sans destinataire personnel."),
        "quantity": ("L'entrepôt stocke {x} boulons.", "L'inventaire compte {x} composants."),
    },
    "it": {
        "statistics": ("La macchina di prova più vecchia ha {x} anni.", "L'indagine sulle attrezzature indica un'età media delle macchine di {x} anni."),
        "percentages": ("La resa produttiva è aumentata del {x}%.", "Il grafico mostra che il {x}% dei pezzi fabbricati ha superato il controllo."),
        "version": ("La versione del firmware è {x}.", "Il software pubblicato porta la versione {x}."),
        "measurements": ("Il pannello d'acciaio misura {x} cm.", "Il disegno tecnico indica le dimensioni della cassa come {x} cm."),
        "timetable": ("L'orario ferroviario pubblico indica la partenza alle {x}.", "Il servizio pubblicato della stazione comincia alle {x}."),
        "scores": ("La partita è finita con il punteggio di squadra {x}.", "Il tabellone del torneo mostra il risultato {x}."),
        "tracking": ("Il pacco di scorte non assegnato ha il numero di tracciamento {x}, senza destinatario registrato.", "La spedizione {x} contiene ricambi per il deposito, senza destinatario personale."),
        "quantity": ("Il magazzino conserva {x} bulloni.", "L'inventario conta {x} componenti."),
    },
    "es": {
        "statistics": ("La máquina de ensayo más antigua tiene {x} años.", "El estudio del equipo indica una edad media de las máquinas de {x} años."),
        "percentages": ("El rendimiento de producción aumentó un {x}%.", "El gráfico muestra que el {x}% de las piezas fabricadas superó la inspección."),
        "version": ("La versión del firmware es {x}.", "El software publicado lleva la versión {x}."),
        "measurements": ("El panel de acero mide {x} cm.", "El plano técnico indica las dimensiones de la caja como {x} cm."),
        "timetable": ("El horario ferroviario público indica la salida a las {x}.", "El servicio publicado de la estación comienza a las {x}."),
        "scores": ("El partido terminó con un resultado de equipo de {x}.", "El marcador del torneo muestra el resultado {x}."),
        "tracking": ("El paquete de existencias sin asignar tiene el número de seguimiento {x}, sin destinatario registrado.", "El envío {x} contiene repuestos para el almacén, sin destinatario personal."),
        "quantity": ("El almacén guarda {x} tornillos.", "El inventario cuenta {x} componentes."),
    },
}
# References identify a person's sample or case, NOT their generic measurement.
PATIENT_REFERENCE = {
    "en": ("The patient's sample identifier is {x}.", "The specimen assigned to this patient is registered under identifier {x}."),
    "de": ("Die Probenkennung des Patienten lautet {x}.", "Die dieser Person zugeordnete Probe ist unter der Kennung {x} registriert."),
    "fr": ("L'identifiant de l'échantillon du patient est {x}.", "Le prélèvement attribué à cette personne est enregistré sous l'identifiant {x}."),
    "it": ("L'identificativo del campione del paziente è {x}.", "Il campione assegnato a questa persona è registrato con l'identificativo {x}."),
    "es": ("El identificador de la muestra del paciente es {x}.", "La muestra asignada a esta persona está registrada con el identificador {x}."),
}


def numeric_template(language, split, kind):
    return NUMERIC[language][kind][0 if split == "train" else 1]


def patient_template(language, split):
    return PATIENT_REFERENCE[language][0 if split == "train" else 1]
