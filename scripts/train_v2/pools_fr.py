"""Invented French lexical pools: first eight train, last eight dev."""
POOL = {
    "given": ("Elviane", "Marovène", "Kélorie", "Norvèle", "Talvien", "Rivelle", "Selviane", "Davorie",
              "Orline", "Vessarie", "Celdrine", "Mirvane", "Avelrie", "Zorvène", "Pelvrie", "Thessile"),
    "surname": ("Velcour", "Norrivel", "Tessmeron", "Calverose", "Morlivet", "Fenlache", "Sorhavelle", "Brinvalon",
                "Vellrieux", "Orrenelle", "Mistrenne", "Keldroux", "Nervallon", "Tavcrête", "Dorlune", "Wessorin"),
    "street": ("rue de Velora", "avenue de Nerwick", "rue Tesslark", "allée de Calven", "rue Morrin", "avenue Fenvale", "rue Sorwick", "allée Brindel",
               "rue Vellora", "avenue Orren", "rue Mistrenne", "allée Keldora", "rue Nerwell", "avenue Tavlark", "rue Dorlune", "allée Wessora"),
    "city": ("Velmère", "Norrivelle", "Tesshavelle", "Calveth", "Morlune", "Fenrique", "Sorvalle", "Brinmère",
             "Vellhavelle", "Orriveth", "Mistrora", "Keldmère", "Nerhavelle", "Tavrique", "Dorlorie", "Wessmère"),
    "title": ("Dr.", "Pr.", "M.", "Mme"), "particle": ("de", "du", "le", "la"),
    "country": "France", "region": "Valmérie", "cc": "FR", "dial": "33",
    "floor": "étage", "unit": "appartement", "box": "BP", "extension": "poste",
    "months": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"),
    "brand": ("Veltronique", "Calveratec"), "organisation": ("Ateliers Nerwick", "Systèmes Sorvalle"),
    "letter_intro": (
        "Cette lettre fictive concerne l'inscription personnelle de {name}. Son adresse privée est {address}. Cette personne est joignable à {email} et son numéro de client est {reference}.",
        "Nous écrivons au sujet de la demande personnelle de {name}. Cette personne habite à {address}. Son adresse électronique est {email} et sa référence de dossier est {reference}.",
    ),
    "letter_repeat": (
        "Pour la vérification finale, le nom reste {name} et la livraison doit toujours se faire à {address}. L'adresse électronique reste {email} et le même numéro de client est {reference}.",
        "Lors du prochain examen, nous conserverons {name} comme demandeur, {address} comme domicile, {email} comme adresse électronique et {reference} comme numéro de dossier personnel.",
    ),
    "letter_filler": (
        "La vérification suit la procédure déjà convenue. Une autre copie pourra être préparée après examen des documents. Aucun paiement supplémentaire n'est nécessaire pour cette étape.",
        "Veuillez conserver l'explication jointe avec la demande. La prochaine étape commencera après l'examen habituel et toute correction pourra être discutée avant la décision définitive.",
    ),
}
