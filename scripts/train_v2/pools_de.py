"""Invented German lexical pools: first eight train, last eight dev."""
POOL = {
    "given": ("Elvian", "Marwena", "Kelora", "Norbertin", "Talwin", "Rivella", "Selwina", "Davorin",
              "Orlinde", "Vessara", "Celwin", "Mirwane", "Avelrich", "Zorwina", "Pelwina", "Thessil"),
    "surname": ("Velbrück", "Norrental", "Tesshagen", "Kalveroth", "Morlfeld", "Fenlacher", "Sorwinkel", "Brintal",
                "Vellhagen", "Orrenfels", "Mistrenkamp", "Keldbach", "Nerwold", "Tavforst", "Dorlheim", "Wessfurt"),
    "street": ("Velorenweg", "Nerwicker Straße", "Tesslarkweg", "Kalvenstraße", "Morrinweg", "Fenvaler Straße", "Sorwickweg", "Brindelstraße",
               "Vellorenweg", "Orrenstraße", "Mistrenweg", "Keldorastraße", "Nerwellweg", "Tavlarkstraße", "Dorlunenweg", "Wessorastraße"),
    "city": ("Velmeringen", "Norrival", "Tesshafen", "Kalveth", "Morlunen", "Fenrick", "Sorval", "Brinmeren",
             "Vellhafen", "Orriveth", "Mistrora", "Keldmeren", "Nerhafen", "Tavrick", "Dorlora", "Wessmeren"),
    "title": ("Dr.", "Prof.", "Herr", "Frau"), "particle": ("von", "van", "de", "zu"),
    "country": "Deutschland", "region": "Velmark", "cc": "DE", "dial": "49",
    "floor": "Etage", "unit": "Wohnung", "box": "Postfach", "extension": "Durchwahl",
    "months": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"),
    "brand": ("Veltronik", "Kalveratech"), "organisation": ("Nerwick Werke", "Sorval Systeme"),
    "letter_intro": (
        "Dieser erfundene Brief betrifft die persönliche Anmeldung von {name}. Die Wohnanschrift lautet {address}. Die Person ist unter {email} erreichbar und führt die Kundennummer {reference}.",
        "Wir schreiben zum persönlichen Antrag von {name}. Die antragstellende Person wohnt in {address}. Ihre E-Mail-Adresse ist {email} und ihr Aktenzeichen lautet {reference}.",
    ),
    "letter_repeat": (
        "Für die abschließende Prüfung wird nochmals {name} genannt; die Zustellung erfolgt weiterhin an {address}. Die E-Mail-Adresse bleibt {email} und dieselbe Kundennummer lautet {reference}.",
        "Bei der nächsten Prüfung bleiben {name} als antragstellende Person, {address} als Wohnanschrift, {email} als E-Mail-Adresse und {reference} als persönliches Aktenzeichen erhalten.",
    ),
    "letter_filler": (
        "Die Prüfung folgt dem bereits vereinbarten Verfahren. Eine weitere Kopie kann nach der Durchsicht der Unterlagen erstellt werden. Für diesen Schritt ist keine zusätzliche Zahlung erforderlich.",
        "Bitte bewahren Sie die beigefügte Erläuterung zusammen mit dem Antrag auf. Der nächste Schritt beginnt nach der üblichen Prüfung; mögliche Berichtigungen können vor der Entscheidung besprochen werden.",
    ),
}
