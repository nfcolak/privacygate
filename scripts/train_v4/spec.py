"""Synthetic v4 contract: frozen recipe imports plus an independent coverage grid."""
from pathlib import Path

from train_v2.spec import LABELS, LANGUAGES

ROOT = Path(__file__).resolve().parents[2]
SEED = 2026100404
SIZES = {"train": 28000, "dev": 3500}
OUTPUTS = {s: ROOT / "data" / "augmentation" / f"{s}-v4.jsonl" for s in SIZES}
MANIFEST = ROOT / "artifacts" / "train-v4" / "manifest.json"
POLICY_PATH = ROOT / "configs" / "privacy-policy-v1.json"
AGE_POLICY = ("AGE includes the number and its directly attached age-unit word, "
              "including inflected units; preceding cues are excluded. "
              "A number with no attached age unit remains numeric-only.")
AGE_UNITS = {"en": r"years?", "de": r"Jahre[n]?", "fr": r"ans?",
             "it": r"anni|anno", "es": r"años?"}
# component -> (rank, shape cells per language, label, languages)
GRID = {
    "postal_envelopes": (1, 6, "ADDRESS", LANGUAGES),
    "postal_clean_twins": (1, 3, None, LANGUAGES),
    "whole_person_names": (2, 6, "PERSONNAME", LANGUAGES),
    "name_nonpersonal_twins": (2, 3, None, LANGUAGES),
    "age_whole_value": (3, 3, "AGE", LANGUAGES),
    "nonpersonal_duration_quantity": (3, 3, None, LANGUAGES),
    "personal_reference_formats": (4, 3, "PERSONALREF", LANGUAGES),
    "operational_reference_twins": (4, 3, None, LANGUAGES),
    "clean_operational_shape_twins": (5, 6, None, LANGUAGES),
    "person_linked_operational_shape_twins": (5, 6, "typed", LANGUAGES),
    "multiline_personal_phones": (6, 6, "TELEPHONENUM", LANGUAGES),
    "multiline_operational_phone_twins": (6, 6, None, LANGUAGES),
    "social_number_group_layouts": (7, 4, "SOCIALNUM", LANGUAGES),
    "social_number_operational_twins": (7, 4, None, LANGUAGES),
    "french_driver_serial_layouts": (7, 2, "DRIVERLICENSENUM", ("fr",)),
    "french_driver_operational_twins": (7, 2, None, ("fr",)),
}
# Four independent values x four paraphrases in train; two x two held out in dev.
GRID_AXES = {"train": (4, 4), "dev": (2, 2)}


def grid_rows(split, language, clean=False):
    values, paraphrases = GRID_AXES[split]
    return sum(cells * values * paraphrases for _, cells, label, langs in GRID.values()
               if language in langs and (not clean or label is None))
