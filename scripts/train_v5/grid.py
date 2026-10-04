"""Full seven-component coverage grid with one clean twin per positive."""
from train_v2.render import render

from .frames_fields import BUILDERS
from .frames_records import record_frame
from .frames_semantic import frame as semantic_frame
from .spec import GRID, LANGUAGES, axes
from .values import payload


def template(component, language, split, layout, scope, sample, positive):
    if component in ("semantic_ages", "signature_greeting_names"):
        return semantic_frame(component, language, split, layout, scope, positive)
    if component == "contact_stock_records":
        return record_frame(language, split, layout, scope, sample, positive)
    return BUILDERS[component](language, split, layout, scope, sample, positive)


def build_grid(split):
    records = []
    for component, (rank, _, _, _) in GRID.items():
        layouts, scopes, samples = axes(component, split)
        for language in LANGUAGES:
            for layout in range(layouts):
                for scope in range(scopes):
                    for sample in range(samples):
                        token, label = payload(component, language, split, layout, scope, sample)
                        pair = f"{split}.{language}.new.{component}.{layout}.{scope}.{sample}"
                        for positive in (True, False):
                            phrase = template(component, language, split, layout, scope, sample, positive)
                            value = token
                            malformed = (component == "balanced_phone_envelopes" and not positive
                                         and (layout + scope + sample) % 2 == 1)
                            if malformed:
                                value = token.replace("(+", "[+", 1)
                            text, gold = render(phrase, {"x": (value, label if positive else None)})
                            side = "positive" if positive else "clean"
                            tid = f"{split}.{language}.v5grid.{component}.{layout}.{scope}.{sample}.{side}"
                            row = {"case_id": f"{split}-v5-new-{rank}-{language}-{layout}-{scope}-{sample}-{side}--{tid}",
                                   "family": f"grid-v5.{component}.{side}", "language": language,
                                   "split": split, "text": text, "gold": gold}
                            metadata = {"template_id": tid, "template": phrase, "pair_id": pair,
                                        "source": "diagnosis-v6-grid", "component": component,
                                        "rank": rank, "layout": layout, "scope": scope, "sample": sample,
                                        "payload": value, "personal_payload": token, "label": label,
                                        "malformed_serial": malformed}
                            records.append((row, metadata))
    return records
