"""Catalog prose and product tables, with genuinely held-out dev layouts."""
CATALOG = {
    "en": (
        "Stock catalog: {product} by {brand}, article {sku}, EAN {ean}, {price}, size {size}, {stock} units, {colour}; product code {x}.",
        "Stock catalog, goods only.\nProduct | Article | EAN | Price | Size | Stock | Colour | Model\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}",
        "The inventory offers a {colour} {product} from {brand} for {price}; {stock} remain, dimensions {size}, barcode {ean}, article {sku}, model identifier {x}.",
        "Warehouse assortment without customer records.\nModel / Colour / Available / Dimensions / Cost / Barcode / Article / Item\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}",
    ),
    "de": (
        "Warenkatalog: {product} von {brand}, Artikel {sku}, EAN {ean}, {price}, Größe {size}, {stock} Stück, {colour}; Produktcode {x}.",
        "Warenkatalog, nur Produkte.\nProdukt | Artikel | EAN | Preis | Größe | Bestand | Farbe | Modell\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}",
        "Im Lager gibt es {product} von {brand} für {price} in {colour}; Bestand {stock}, Maße {size}, Strichcode {ean}, Artikel {sku}, Modellkennung {x}.",
        "Lagersortiment ohne Kundendaten.\nModell / Farbe / Vorrat / Maße / Kosten / Strichcode / Artikel / Ware\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}",
    ),
    "fr": (
        "Catalogue de stock : {product} de {brand}, article {sku}, EAN {ean}, {price}, dimensions {size}, {stock} unités, {colour} ; code produit {x}.",
        "Catalogue de stock, uniquement des produits.\nProduit | Article | EAN | Prix | Dimensions | Stock | Couleur | Modèle\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}",
        "L'inventaire propose {product} de {brand} à {price}, couleur {colour} ; il reste {stock} unités de dimensions {size}, code-barres {ean}, article {sku}, modèle {x}.",
        "Assortiment du dépôt sans dossier client.\nModèle / Couleur / Disponible / Dimensions / Coût / Code-barres / Article / Objet\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}",
    ),
    "it": (
        "Catalogo delle scorte: {product} di {brand}, articolo {sku}, EAN {ean}, {price}, dimensioni {size}, {stock} pezzi, {colour}; codice prodotto {x}.",
        "Catalogo delle scorte, solo prodotti.\nProdotto | Articolo | EAN | Prezzo | Dimensioni | Scorte | Colore | Modello\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}",
        "L'inventario propone {product} di {brand} a {price}, colore {colour}; restano {stock} pezzi di dimensioni {size}, codice a barre {ean}, articolo {sku}, modello {x}.",
        "Assortimento del deposito senza dati dei clienti.\nModello / Colore / Disponibili / Dimensioni / Costo / Codice a barre / Articolo / Oggetto\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}",
    ),
    "es": (
        "Catálogo de existencias: {product} de {brand}, artículo {sku}, EAN {ean}, {price}, dimensiones {size}, {stock} unidades, {colour}; código de producto {x}.",
        "Catálogo de existencias, solo productos.\nProducto | Artículo | EAN | Precio | Dimensiones | Existencias | Color | Modelo\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}\n{product} | {sku} | {ean} | {price} | {size} | {stock} | {colour} | {x}",
        "El inventario ofrece {product} de {brand} por {price}, color {colour}; quedan {stock} unidades de dimensiones {size}, código de barras {ean}, artículo {sku}, modelo {x}.",
        "Surtido del almacén sin datos de clientes.\nModelo / Color / Disponibles / Dimensiones / Coste / Código de barras / Artículo / Objeto\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}\n{x} / {colour} / {stock} / {size} / {price} / {ean} / {sku} / {product}",
    ),
}


def catalog_template(language, split, variant):
    return CATALOG[language][(0 if split == "train" else 2) + variant]
