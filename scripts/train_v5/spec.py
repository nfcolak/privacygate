"""Independent v5 seed, output contract and diagnosis coverage axes."""
from pathlib import Path

from train_v2.spec import LABELS, LANGUAGES

ROOT = Path(__file__).resolve().parents[2]
SEED = 2026100405
SIZES = {"train": 32000, "dev": 4000}
OUTPUTS = {s: ROOT / "data" / "augmentation" / f"{s}-v5.jsonl" for s in SIZES}
MANIFEST = ROOT / "artifacts" / "train-v5" / "manifest.json"
POLICY_PATH = ROOT / "configs" / "privacy-policy-v1.json"
AGE_POLICY = ("AGE includes the complete numeric or lexical cardinal and its attached "
              "age unit, when present; preceding cues and enclosing brackets are excluded.")
# Layout x scope/pattern x independently generated variants, per language and side.
GRID: dict[str, tuple[int, str, tuple[int, int, int], tuple[int, int, int]]] = {
    "semantic_ages": (1, "AGE", (3, 2, 8), (3, 2, 2)),
    "signature_greeting_names": (2, "PERSONNAME", (4, 3, 6), (4, 3, 2)),
    "contact_stock_records": (3, "TELEPHONENUM", (4, 3, 4), (4, 3, 1)),
    "postal_object_envelopes": (4, "ADDRESS", (3, 2, 4), (3, 2, 1)),
    "birth_calendar_fields": (5, "DATEOFBIRTH", (3, 2, 4), (3, 2, 1)),
    "balanced_phone_envelopes": (6, "TELEPHONENUM", (3, 2, 4), (3, 2, 1)),
    "document_alias_sections": (7, "typed", (12, 2, 4), (12, 2, 1)),
}
DOCUMENT_LABELS = ("DRIVERLICENSENUM", "TAXNUM", "PERSONALREF", "SOCIALNUM")
AXIS_MEANINGS = {
    "semantic_ages": ["lexical/word-unit/birth-parenthetical", "personal cue scope", "cardinal"],
    "signature_greeting_names": ["ordinary/initial/compound/inverted", "closing/signature/greeting", "name"],
    "contact_stock_records": ["four record grammars", "numeric grouping", "header/cue variant"],
    "postal_object_envelopes": ["pipe/slash/newline", "postal order", "road grammar"],
    "birth_calendar_fields": ["slash/middle-dot/named-month", "full/section alias", "field/context variant"],
    "balanced_phone_envelopes": ["dotted/line-break/trunk", "field/ownership", "number variant"],
    "document_alias_sections": ["four labels x space/slash/newline", "document/ownership", "serial variant"],
}


def axes(component, split):
    return GRID[component][2 if split == "train" else 3]


def grid_rows(split, language=None, clean=False):
    multiplier = 1 if language else len(LANGUAGES)
    return multiplier * (1 if clean else 2) * sum(
        a * b * c for component in GRID for a, b, c in (axes(component, split),))
