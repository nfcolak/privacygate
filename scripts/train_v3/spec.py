"""V3 synthetic-only contract; frozen v2 components are imported, not changed."""
from pathlib import Path

from train_v2.spec import (FAMILY, LABELS, LANGUAGES, NEGATIVE_KINDS,
                           SLICES, TWIN_LABELS, pool_manifest)

ROOT = Path(__file__).resolve().parents[2]
SEED = 2026100313
SIZES = {"train": 24000, "dev": 3000}
POLICY_PATH = ROOT / "configs" / "privacy-policy-v1.json"
OUTPUTS = {s: ROOT / "data" / "augmentation" / f"{s}-v3.jsonl" for s in SIZES}
MANIFEST = ROOT / "artifacts" / "train-v3" / "manifest.json"
# Counts per language. Every new clean row has an identical-payload positive twin.
LEGACY_CLEAN = {"train": 720, "dev": 90}
NEW_CLEAN_PER_GROUP = {"train": 480, "dev": 60}
BOUNDARY_ROWS = {"train": 400, "dev": 50}
CATALOG_KINDS = ("serial", "ean", "name", "date", "phone", "passport", "id", "sample")
NUMERIC_KINDS = ("statistics", "percentages", "version", "measurements",
                 "timetable", "scores", "tracking", "quantity")
NEAR_KINDS = ("iban_valid", "iban_invalid", "phone", "passport", "id",
              "date", "name", "sample", "batch")
NEW_GROUPS = {"catalog": CATALOG_KINDS, "numeric": NUMERIC_KINDS,
              "near-miss": NEAR_KINDS}
SHAPE_LABELS = {"serial": "PERSONALREF", "ean": "PERSONALREF",
                "name": "PERSONNAME", "date": "DATEOFBIRTH", "phone": "TELEPHONENUM",
                "passport": "PASSPORTNUM", "id": "IDCARDNUM", "sample": "PERSONALREF",
                "batch": "PERSONALREF", "iban_valid": "IBAN", "iban_invalid": "IBAN"}
NUMERIC_LABELS = {k: "PERSONALREF" for k in NUMERIC_KINDS}
NUMERIC_LABELS["statistics"] = "AGE"
INVALID_IBAN_FAMILY = "target.person-linked.near-miss.iban_invalid"


def template_id(split, language, kind, variant=0):
    return f"{split}.{language}.{kind}.{variant}"
