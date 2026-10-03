"""Explicit placeholder assembly: repeated values retain independent spans."""
import re

from .pools import POOLS
from .spec import FAMILY
from .values import value

PLACEHOLDER = re.compile(r"\{([a-z]+)\}")


def render(template, bindings):
    text, gold, cursor = [], [], 0
    length = 0
    for match in PLACEHOLDER.finditer(template):
        prefix = template[cursor:match.start()]
        text.append(prefix)
        length += len(prefix)
        token, label = bindings[match.group(1)]
        text.append(token)
        if label is not None:
            gold.append({"start": length, "end": length + len(token), "label": label})
        length += len(token)
        cursor = match.end()
    text.append(template[cursor:])
    return "".join(text), gold


def letter(language, split, sequence, pick_index):
    pool = POOLS[language]
    variant = 0 if split == "train" else 1
    labels = {"name": "PERSONNAME", "address": "ADDRESS",
              "email": "EMAIL", "reference": "PERSONALREF"}
    bindings = {
        key: (value(label, language, split,
                    pick_index(split, language, FAMILY[label], sequence)), label)
        for key, label in labels.items()
    }
    parts = [pool["letter_intro"][variant], pool["letter_repeat"][variant],
             pool["letter_repeat"][variant]]
    template = "\n\n".join(parts)
    while True:
        candidate = template + "\n\n" + pool["letter_filler"][variant]
        text, _ = render(candidate, bindings)
        if len(text) > 2450:
            break
        template = candidate
    return render(template, bindings)
