"""Invented English lexical pools: first eight train, last eight dev."""
POOL = {
    "given": ("Elvian", "Maroven", "Kelora", "Norveth", "Talven", "Rivella", "Selwick", "Davora",
              "Orlith", "Vessara", "Celdren", "Mirvane", "Avelric", "Zorwen", "Pelvra", "Thessil"),
    "surname": ("Velcroft", "Norrindle", "Tessmere", "Calverose", "Morlwick", "Fenlatch", "Sorhaven", "Brinvale",
                "Vellridge", "Orrenshaw", "Mistren", "Keldrift", "Nerwold", "Tavcrest", "Dorlane", "Wessford"),
    "street": ("Velora Lane", "Nerwick Road", "Tesslark Way", "Calven Street", "Morrin Drive", "Fenvale Road", "Sorwick Lane", "Brindel Way",
               "Vellora Road", "Orren Lane", "Mistralden Way", "Keldora Street", "Nerwell Drive", "Tavlark Lane", "Dorlune Road", "Wessora Way"),
    "city": ("Velmere", "Norrivale", "Tesshaven", "Calveth", "Morlune", "Fenrick", "Sorvale", "Brinmere",
             "Vellhaven", "Orriveth", "Mistrora", "Keldmere", "Nerhaven", "Tavrick", "Dorlora", "Wessmere"),
    "title": ("Dr.", "Prof.", "Mr.", "Ms."), "particle": ("van", "de", "von", "del"),
    "country": "United Kingdom", "region": "Velshire", "cc": "GB", "dial": "44",
    "floor": "floor", "unit": "flat", "box": "PO Box", "extension": "extension",
    "months": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
    "brand": ("Veltronix", "Calveratek"), "organisation": ("Nerwick Systems", "Sorvale Works"),
    "letter_intro": (
        "This fictional letter concerns the private registration of {name}. The home delivery address is {address}. Please use {email} to contact this person and quote their customer number {reference}.",
        "We are writing about the personal application submitted by {name}. The applicant lives at {address}. Their email is {email} and the personal case reference is {reference}.",
    ),
    "letter_repeat": (
        "For the final review, the applicant is again identified as {name}; delivery must still go to {address}. The contact email remains {email}, and the same customer number is {reference}.",
        "The next review must retain {name} as the applicant, {address} as the home address, {email} as the contact email and {reference} as the applicant's case number.",
    ),
    "letter_filler": (
        "The review follows the previously agreed procedure. A further copy may be prepared once the documentation has been checked. No additional payment is needed for this step.",
        "Please keep the enclosed explanation with the application. The next stage will begin after the routine review, and any correction can be discussed before the final decision is issued.",
    ),
}
