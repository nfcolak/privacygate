"""Frozen generation contract; only synthetic, single-language prose."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261003
POLICY = "privacy-policy-v1"
LANGUAGES = ("en", "de", "fr", "it", "es")
SIZES = {"train": 16000, "dev": 2000}
SLICES = {"train": (0, 512), "dev": (512, 640)}
POLICY_PATH = ROOT / "configs" / f"{POLICY}.json"
POLICY_CONFIG = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
LABELS = tuple(POLICY_CONFIG["labels"])
GROUPS = {
    "identity": ("PERSONNAME",), "postal": ("ADDRESS",),
    "contact": ("EMAIL", "USERNAME", "TELEPHONENUM"),
    "financial": ("IBAN", "ACCOUNTNUM", "CREDITCARDNUMBER"),
    "official": ("PASSPORTNUM", "IDCARDNUM", "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM"),
    "reference": ("PERSONALREF",), "birth": ("DATEOFBIRTH",), "age": ("AGE",),
}
FAMILY = {label: group for group, labels in GROUPS.items() for label in labels}
NEGATIVE_KINDS = (
    "invoice", "order", "sku", "version", "price", "dimensions", "date",
    "time", "brand", "organisation", "place", "room", "gate", "platform", "statistics", "quantity",
)
TWIN_LABELS = {
    "invoice": "PERSONALREF", "order": "PERSONALREF", "sku": "PERSONALREF",
    "date": "DATEOFBIRTH", "time": "DATEOFBIRTH", "place": "ADDRESS",
    "room": "PERSONALREF", "gate": "PERSONALREF", "platform": "PERSONALREF", "statistics": "AGE",
}
OUTPUTS = {s: ROOT / "data" / "augmentation" / f"{s}-v2.jsonl" for s in SIZES}
MANIFEST = ROOT / "artifacts" / "train-v2" / "manifest.json"


def template_id(split, language, kind, variant=0):
    return f"{split}.{language}.{kind}.{variant}"


def pool_manifest():
    return {
        split: {family: {"start": lo, "stop": hi, "labels": list(labels)}
                for family, labels in GROUPS.items()}
        for split, (lo, hi) in SLICES.items()
    }
