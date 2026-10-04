"""Fresh synthetic lexical pools, independent of all blind-set sources."""
# Entries 0/1 are complete train/dev pools, never row-level random splits.
NAMES = {
    "en": (("Zelvara", "Lumorin", "Vesnara", "Talvian"),
           ("Quenlira", "Dovrion", "Pelvona", "Ruvlian")),
    "de": (("Nelvarda", "Torvian", "Zelmira", "Felvorn"),
           ("Quorina", "Delvian", "Pelmara", "Rolvian")),
    "fr": (("Zelviane", "Lumélie", "Vesnore", "Talvène"),
           ("Quénalie", "Dovrène", "Pelviane", "Ruvélie")),
    "it": (("Zelviana", "Lumorino", "Vesnella", "Talviero"),
           ("Quenlina", "Dovrino", "Pelvonia", "Ruvliano")),
    "es": (("Zelvaria", "Lumorino", "Vesnaria", "Talviano"),
           ("Quenliria", "Dovriona", "Pelvonia", "Ruvliana")),
}
SURNAMES = (("Velnor", "Zarvella", "Nuvranto", "Lomveri"),
            ("Qenvora", "Dorlanti", "Perluno", "Ravqueli"))
LOCATIONS = {
    "en": (("Velmora Lane", "Nuvranto Road", "Lomveri Avenue", "Zarvella Street"),
           ("Quenford", "Dorlake", "Perlvale", "Ravbridge")),
    "de": (("Velmoraweg", "Nuvrantostraße", "Lomverigasse", "Zarvellaallee"),
           ("Quenhausen", "Dorlfeld", "Perlstadt", "Ravkirch")),
    "fr": (("rue Velmora", "avenue Nuvranto", "chemin Lomveri", "allée Zarvella"),
           ("Quenville", "Dorlac", "Perlmont", "Ravbois")),
    "it": (("via Velmora", "viale Nuvranto", "corso Lomveri", "piazza Zarvella"),
           ("Quenborgo", "Dorlago", "Perlmonte", "Ravcampo")),
    "es": (("calle Velmora", "avenida Nuvranto", "camino Lomveri", "plaza Zarvella"),
           ("Quenvilla", "Dorlago", "Perlmonte", "Ravcampo")),
}
# Dev street names are entirely held out as lexical components.
DEV_STREETS = {
    "en": ("Quenvora Lane", "Dorlanti Road", "Perluno Avenue", "Ravqueli Street"),
    "de": ("Quenvoraweg", "Dorllantistraße", "Perlunogasse", "Ravqueliallee"),
    "fr": ("rue Quenvora", "avenue Dorlanti", "chemin Perluno", "allée Ravqueli"),
    "it": ("via Quenvora", "viale Dorlanti", "corso Perluno", "piazza Ravqueli"),
    "es": ("calle Quenvora", "avenida Dorlanti", "camino Perluno", "plaza Ravqueli"),
}
# Country metadata is syntax, not personal identities.
LOCALE = {
    "en": {"cc": "GB", "dial": "44", "country": "United Kingdom", "particle": "de",
           "care": "c/o", "box": "PO Box", "unit": "floor", "ext": "ext.",
           "titles": ("Dr.", "Prof.", "Dr.", "Dr."), "age": "years"},
    "de": {"cc": "DE", "dial": "49", "country": "Deutschland", "particle": "von",
           "care": "c/o", "box": "Postfach", "unit": "Etage", "ext": "Durchwahl",
           "titles": ("Dr.", "Prof.", "Dr.", "Dr."), "age": "Jahre"},
    "fr": {"cc": "FR", "dial": "33", "country": "France", "particle": "de",
           "care": "chez", "box": "BP", "unit": "étage", "ext": "poste",
           "titles": ("Dr.", "Mme.", "Dr.", "M."), "age": "ans"},
    "it": {"cc": "IT", "dial": "39", "country": "Italia", "particle": "di",
           "care": "presso", "box": "Casella postale", "unit": "piano", "ext": "interno",
           "titles": ("Dott.", "Sig.", "Prof.", "Sig.ra."), "age": "anni"},
    "es": {"cc": "ES", "dial": "34", "country": "España", "particle": "de",
           "care": "a cargo de", "box": "Apartado", "unit": "piso", "ext": "extensión",
           "titles": ("Sr.", "Sra.", "Dr.", "Sr."), "age": "años"},
}
