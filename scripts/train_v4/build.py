"""Build every diagnosis grid cell, then blend the regenerated v3 recipe."""
import random

from train_v2.render import render

from .legacy import build_recipe
from .pools import DEV_STREETS, LOCALE, LOCATIONS
from .spec import GRID, GRID_AXES, SEED
from .templates import template
from .values import (index, multiline_phone, name_parts, operational, postal,
                     reference, serial, whole_name)


def grid_value(component, language, split, cell, sample):
    base = index(split, language, component, cell, 0)
    # Rotate a seeded block of four: each cell has four distinct lexical/numeric
    # choices, not four random draws that can collapse to repeated values.
    n = base - base % 4 + (base % 4 + sample) % 4
    evidence = {}
    label = GRID[component][2]
    if component == "postal_envelopes":
        token = postal(language, split, n, cell, sample)
    elif component == "postal_clean_twins":
        city = (LOCATIONS[language][1] if split == "dev" else
                ("Velmorana", "Nuvrantia", "Lomverana", "Zarvellia"))[n % 4]
        if cell == 0:
            token = {"en": ("via stock depot", "through the reserve warehouse"),
                     "de": ("über das Lagerdepot", "durch das Reservelager"),
                     "fr": ("via le dépôt", "par l'entrepôt de réserve"),
                     "it": ("tramite il deposito", "attraverso il magazzino di riserva"),
                     "es": ("por el depósito", "a través del almacén de reserva")}[language][split == "dev"]
            token += " / " + {"en": "routing gate", "de": "Routentor", "fr": "porte de routage",
                              "it": "varco di instradamento", "es": "puerta de ruta"}[language] + f" {1 + n % 4}"
        elif cell == 1:
            token = f"{(70000 if split == 'train' else 80000) + n % 9999} {city}"
        else:
            street = (DEV_STREETS[language] if split == "dev" else LOCATIONS[language][0])[n % 4]
            token = f"{street} {1 + n % 200}"
    elif component == "whole_person_names":
        token = whole_name(language, split, n, cell)
    elif component == "name_nonpersonal_twins":
        given, _, surname = name_parts(language, split, n)
        if cell == 0:
            token = f"{LOCALE[language]['titles'][n % 4]}{surname}-{given}"
        elif cell == 1:
            road = {"en": "Lane", "de": "Straße", "fr": "rue", "it": "via", "es": "calle"}[language]
            token = f"{road} {given} {LOCALE[language]['particle']} {surname}"
        else:
            token = {"en": ("Private contact department", "Recipient liaison office"),
                     "de": ("Abteilung Privatkontakt", "Referat Empfängerkontakt"),
                     "fr": ("Département des contacts privés", "Bureau de liaison des destinataires"),
                     "it": ("Reparto contatti privati", "Ufficio rapporti destinatari"),
                     "es": ("Departamento de contactos privados", "Oficina de enlace destinatarios")}[language][split == "dev"]
            role = {"en": ("routing", "dispatch", "stock", "packing"),
                    "de": ("Routen", "Versand", "Lager", "Verpackung"),
                    "fr": ("routage", "expédition", "stock", "emballage"),
                    "it": ("instradamento", "spedizione", "scorte", "imballaggio"),
                    "es": ("rutas", "expedición", "existencias", "embalaje")}[language][n % 4]
            token += " / " + role
    elif component in ("age_whole_value", "nonpersonal_duration_quantity"):
        number = (18 if split == "train" else 60) + n % 40
        unit = LOCALE[language]["age"]
        token = f"{number} {unit if component == 'age_whole_value' or cell < 2 else 'kg'}"
    elif "reference" in component:
        token = reference(split, n, cell)
    elif "operational_shape" in component:
        token, typed_label, evidence = operational(language, split, n, cell)
        label = typed_label if label else None
    elif "multiline" in component:
        token = multiline_phone(language, split, n, cell)
    elif component.startswith("social_number"):
        token = serial(split, n, cell)
    else:
        token = serial(split, n, cell, driver=True)
    return token, label, evidence


def build_grid(split):
    records = []
    values, paraphrases = GRID_AXES[split]
    for component, (rank, cells, label, languages) in GRID.items():
        for language in languages:
            for cell in range(cells):
                for sample in range(values):
                    token, actual_label, evidence = grid_value(component, language, split, cell, sample)
                    for paraphrase in range(paraphrases):
                        phrase = template(language, split, component, cell, paraphrase, label is not None)
                        tid = f"{split}.{language}.grid.{component}.{cell}.{paraphrase}"
                        text, gold = render(phrase, {"x": (token, actual_label)})
                        row = {"case_id": f"{split}-v4-grid-{language}-{component}-{cell}-{sample}--{tid}",
                               "family": "grid." + component, "language": language,
                               "split": split, "text": text, "gold": gold}
                        metadata = {"template_id": tid, "template": phrase, "pair_id": None,
                                    "source": "diagnosis-grid", "component": component,
                                    "rank": rank, "cell": cell, "sample": sample,
                                    "paraphrase": paraphrase, "evidence": evidence}
                        records.append((row, metadata))
    return records


def build_split(split):
    records = build_recipe(split) + build_grid(split)
    random.Random(f"{SEED}:{split}:v4-order").shuffle(records)
    return records
