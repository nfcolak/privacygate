"""Locale registry; no external data or packages."""
from .pools_en import POOL as EN
from .pools_de import POOL as DE
from .pools_fr import POOL as FR
from .pools_it import POOL as IT
from .pools_es import POOL as ES

POOLS = {"en": EN, "de": DE, "fr": FR, "it": IT, "es": ES}


def word(pool, key, split, index):
    offset = 0 if split == "train" else 8
    return pool[key][offset + index % 8]
