"""Value-free validation and aggregate accounting."""
from collections import Counter, defaultdict
import re

from .numbers import luhn_total, mod97
from .pools import POOLS
from .spec import LABELS, LANGUAGES, SIZES

FIELDS = {"case_id", "family", "gold", "language", "split", "text"}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def validate_row(row, split):
    require(isinstance(row, dict) and set(row) == FIELDS, "row_schema")
    for field in ("case_id", "family", "language", "split", "text"):
        require(isinstance(row[field], str) and bool(row[field]), "row_string_field")
    require(row["split"] == split and row["language"] in LANGUAGES, "row_split_language")
    require(isinstance(row["gold"], list), "gold_schema")
    require(1 <= len(row["text"]) <= 2500, "text_length")
    previous = 0
    for span in row["gold"]:
        require(isinstance(span, dict) and set(span) == {"start", "end", "label"}, "span_schema")
        start, end, label = span["start"], span["end"], span["label"]
        require(type(start) is int and type(end) is int, "offset_type")
        require(isinstance(label, str) and label in LABELS, "span_label")
        require(previous <= start < end <= len(row["text"]), "span_order_overlap")
        previous = end
        token = row["text"][start:end]
        require(token == token.strip(), "span_boundary_space")
        leading_sigil = {"USERNAME": "@", "TELEPHONENUM": "+"}.get(label)
        require(token[0].isalnum() or token[0] == leading_sigil, "span_leading_punctuation")
        require(token[-1].isalnum(), "span_trailing_punctuation")
        if label == "IBAN":
            compact = re.sub(r"[ -]", "", token)
            expected = {"GB": 22, "DE": 22, "FR": 27, "IT": 27, "ES": 24}
            country = POOLS[row["language"]]["cc"]
            require(compact.startswith(country) and len(compact) == expected[country], "iban_locale")
            require(mod97(token) == 1, "iban_mod97")
        if label == "CREDITCARDNUMBER":
            digits = re.sub(r"[ -]", "", token)
            require(digits.isdigit() and len(digits) == 16 and luhn_total(digits) % 10 == 0,
                    "card_luhn")
        if label == "TELEPHONENUM":
            require(token.startswith("+" + POOLS[row["language"]]["dial"]), "phone_locale")


def summarize(records, split):
    languages, families, labels, label_rows = Counter(), Counter(), Counter(), Counter()
    templates, ids, pairs = set(), set(), defaultdict(list)
    values = {label: set() for label in LABELS}
    clean, long_letters, max_length = 0, 0, 0
    for row, metadata in records:
        validate_row(row, split)
        require(row["case_id"] not in ids, "duplicate_case_id")
        ids.add(row["case_id"])
        require(row["case_id"].endswith("--" + metadata["template_id"]), "case_template_id")
        require(metadata["template_id"].startswith(split + "." + row["language"] + "."),
                "template_split")
        templates.add(metadata["template_id"])
        languages[row["language"]] += 1
        families[row["family"]] += 1
        clean += not row["gold"]
        max_length = max(max_length, len(row["text"]))
        long_letters += row["family"] == "letter.repeated-values"
        for span in row["gold"]:
            labels[span["label"]] += 1
            values[span["label"]].add(row["text"][span["start"]:span["end"]])
        label_rows.update({span["label"] for span in row["gold"]})
        if metadata["pair_id"] is not None:
            pairs[metadata["pair_id"]].append(row)
    require(len(records) == SIZES[split], "row_count")
    require(0.38 <= clean / len(records) <= 0.42, "clean_share")
    ideal = len(records) / len(LANGUAGES)
    require(set(languages) == set(LANGUAGES), "language_coverage")
    require(all(abs(count - ideal) <= ideal * 0.05 for count in languages.values()), "language_balance")
    require(set(labels) == set(LABELS), "label_coverage")
    for rows in pairs.values():
        require(len(rows) == 2, "twin_pair_count")
        negatives = [row for row in rows if not row["gold"]]
        positives = [row for row in rows if row["gold"]]
        require(len(negatives) == len(positives) == 1, "twin_pair_classes")
        positive = positives[0]
        require(len(positive["gold"]) == 1, "twin_whole_payload")
        span = positive["gold"][0]
        require(positive["text"][span["start"]:span["end"]] in negatives[0]["text"],
                "twin_identical_payload")
    summary = {
        "rows": len(records), "clean_rows": clean, "clean_share": clean / len(records),
        "counts": {"label": dict(sorted(labels.items())), "language": dict(sorted(languages.items())),
                   "family": dict(sorted(families.items()))},
        "label_rows": dict(sorted(label_rows.items())), "matched_pairs": len(pairs),
        "long_letter_rows": long_letters, "max_text_chars": max_length,
    }
    return summary, templates, values


def check_split_isolation(observed):
    require(not observed["train"][1] & observed["dev"][1], "template_leakage")
    for label in LABELS:
        require(not observed["train"][2][label] & observed["dev"][2][label], "value_pool_leakage")
