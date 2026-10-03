"""Invented Italian lexical pools: first eight train, last eight dev."""
POOL = {
    "given": ("Elviano", "Marovena", "Keloria", "Norvello", "Talvino", "Rivella", "Selvico", "Davoria",
              "Orlina", "Vessara", "Celdrino", "Mirvana", "Avelrico", "Zorvena", "Pelvria", "Tessilo"),
    "surname": ("Velcorri", "Norrindelli", "Tessmeri", "Calverosi", "Morlini", "Fenlacchi", "Soravelli", "Brinvali",
                "Vellrigi", "Orrenazzi", "Mistreni", "Keldrini", "Nervoldi", "Tavcresti", "Dorlani", "Wessori"),
    "street": ("via Velora", "via Nerwick", "viale Tesslarco", "via Calveno", "via Morrino", "viale Fenvale", "via Sorvico", "via Brindello",
               "via Vellora", "viale Orreno", "via Mistreno", "via Keldora", "viale Nerwello", "via Tavlarco", "via Dorluna", "viale Wessora"),
    "city": ("Velmera", "Norrivale", "Tessavella", "Calveto", "Morluna", "Fenrico", "Sorvale", "Brinmera",
             "Vellavella", "Orriveto", "Mistrora", "Keldmera", "Neravella", "Tavrico", "Dorlora", "Wessmera"),
    "title": ("Dott.", "Prof.", "Sig.", "Sig.ra"), "particle": ("di", "da", "del", "de"),
    "country": "Italia", "region": "Valmeria", "cc": "IT", "dial": "39",
    "floor": "piano", "unit": "interno", "box": "casella postale", "extension": "interno",
    "months": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"),
    "brand": ("Veltronica", "Calveratec"), "organisation": ("Officine Nerwick", "Sistemi Sorvale"),
    "letter_intro": (
        "Questa lettera inventata riguarda l'iscrizione personale di {name}. L'indirizzo di casa è {address}. La persona può essere contattata a {email} e il suo numero cliente è {reference}.",
        "Scriviamo in merito alla domanda personale presentata da {name}. La persona abita in {address}. La sua email è {email} e il riferimento della pratica personale è {reference}.",
    ),
    "letter_repeat": (
        "Per il controllo finale, il nome resta {name} e la consegna deve avvenire ancora a {address}. L'email rimane {email} e lo stesso numero cliente è {reference}.",
        "Nel prossimo controllo conserveremo {name} come richiedente, {address} come domicilio, {email} come recapito email e {reference} come numero della pratica personale.",
    ),
    "letter_filler": (
        "Il controllo segue la procedura già concordata. Un'altra copia potrà essere preparata dopo la verifica dei documenti. Non è richiesto un pagamento aggiuntivo per questa fase.",
        "Si prega di conservare la spiegazione allegata insieme alla domanda. La fase successiva inizierà dopo il controllo ordinario e le eventuali correzioni potranno essere discusse prima della decisione finale.",
    ),
}
