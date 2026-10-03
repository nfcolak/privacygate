"""Invented Spanish lexical pools: first eight train, last eight dev."""
POOL = {
    "given": ("Elviano", "Marovena", "Keloria", "Norvelo", "Talvino", "Rivela", "Selvico", "Davoria",
              "Orlina", "Vesara", "Celdrino", "Mirvana", "Avelrico", "Zorvena", "Pelvria", "Tesilo"),
    "surname": ("Velcorzo", "Norrindel", "Tesmero", "Calverosa", "Morlino", "Fenlacho", "Soravela", "Brinvalo",
                "Vellrizo", "Orrenazo", "Mistreno", "Keldrino", "Nervoldo", "Tavcresta", "Dorlano", "Wesoro"),
    "street": ("calle Velora", "avenida Nerwick", "calle Teslarco", "calle Calveno", "avenida Morrino", "calle Fenvale", "calle Sorvico", "avenida Brindelo",
               "calle Vellora", "avenida Orreno", "calle Mistreno", "avenida Keldora", "calle Nerwelo", "calle Tavlarco", "avenida Dorluna", "calle Wesora"),
    "city": ("Velmera", "Norrivale", "Tesavela", "Calveto", "Morluna", "Fenrico", "Sorvale", "Brinmera",
             "Vellavela", "Orriveto", "Mistrora", "Keldmera", "Neravela", "Tavrico", "Dorlora", "Wesmera"),
    "title": ("Dr.", "Prof.", "Sr.", "Sra."), "particle": ("de", "del", "de la", "dos"),
    "country": "España", "region": "Valmería", "cc": "ES", "dial": "34",
    "floor": "planta", "unit": "puerta", "box": "apartado postal", "extension": "extensión",
    "months": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
    "brand": ("Veltrónica", "Calveratec"), "organisation": ("Talleres Nerwick", "Sistemas Sorvale"),
    "letter_intro": (
        "Esta carta inventada trata de la inscripción personal de {name}. Su domicilio es {address}. Se puede contactar con esta persona en {email} y su número de cliente es {reference}.",
        "Escribimos sobre la solicitud personal presentada por {name}. Esta persona vive en {address}. Su correo es {email} y la referencia de su expediente personal es {reference}.",
    ),
    "letter_repeat": (
        "Para la revisión final, el nombre sigue siendo {name} y la entrega debe hacerse de nuevo en {address}. El correo sigue siendo {email} y el mismo número de cliente es {reference}.",
        "En la próxima revisión conservaremos {name} como solicitante, {address} como domicilio, {email} como correo y {reference} como número de expediente personal.",
    ),
    "letter_filler": (
        "La revisión sigue el procedimiento ya acordado. Se podrá preparar otra copia después de comprobar los documentos. No se necesita ningún pago adicional para esta fase.",
        "Conserve la explicación adjunta junto con la solicitud. La siguiente fase comenzará después de la revisión habitual y se podrá hablar de cualquier corrección antes de emitir la decisión final.",
    ),
}
