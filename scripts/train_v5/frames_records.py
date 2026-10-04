"""Column ownership and record layout contrasts, held out by grammar."""
from .lexicon import ROLES


def record_frame(language, split, layout, pattern, sample, positive):
    roles = ROLES[language]
    variant = (layout + pattern + sample) % 4
    key = roles["phone" if positive else "stock"][variant]
    scope = roles["contact" if positive else "objects"]
    quantity, cost = roles["qty"], roles["price"]
    route, status = roles["note"], roles["status"]
    # Quantities/prices are typed neighbouring cells, never inside the gold phone.
    # The clean side exposes alphanumeric prefixes/suffixes of an object serial.
    value = "{x}" if positive or pattern == 1 else "RV-{x}-K"
    if split == "train":
        return (
            f"{scope}\n{key} | {quantity} | {cost}\n{value} | 8 | 14.75",
            f"{scope}\n{quantity}\t{key}\t{cost}\n6\t{value}\t23.40",
            f"{scope}\n{key}={value}; {quantity}=12; {cost}=7.85; {route}=C",
            f"{scope}\n{quantity}: 3\n{cost}: 18.60\n{key}: {value}\n{status}: B",
        )[layout]
    # Transposed records, row keys and nested fields are absent from train.
    return (
        f"{scope}\n[{key}]\n{value}\n[{cost}]\n16.30\n[{quantity}]\n7",
        f"{scope}\n{status}\tB\n{cost}\t11.90\n{key}\t{value}\n{quantity}\t9",
        f"{scope} → ({quantity}:5) / ({key}:{value}) / ({cost}:21.55)",
        f"{scope}\n{status}=C\n  {key}\n    {value}\n  {quantity}\n    4\n  {cost}\n    9.25",
    )[layout]
