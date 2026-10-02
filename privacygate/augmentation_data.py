"""Trainer augmentation wiring; standard library only, fixed value-free refusal codes.

Exact-text/template-ID checks use local file contents, not manifest disjointness claims.
They do not establish semantic independence. No corpus reads or model work here.
"""
import hashlib
import json

from . import mbert_data as md
from . import negative_data as nd
from . import positive_data as pd

POSITIVE_SCHEMA_VERSION = "positive-jsonl-v1"
POSITIVE_SOURCE_VERSION = pd.GEN_VERSION


def manifest_entries(raw):
    """Read the existing train/dev manifest shape without echoing parser errors."""
    try:
        entries = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
        if not entries or any(not isinstance(e, dict) or
                              not isinstance(e.get("row_id"), str) or not e["row_id"] or
                              not isinstance(e.get("language"), str) for e in entries):
            raise ValueError
        if len({e["row_id"] for e in entries}) != len(entries):
            raise ValueError
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError("micro_manifest_malformed") from None
    return entries


def _digest(value):
    return hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).digest()


def check_positive_disjoint(train, dev):
    # Language is deliberately not part of the key: identical text in another language also overlaps.
    if {_digest(r["source_text"]) for r in train} & {_digest(r["source_text"]) for r in dev}:
        raise ValueError("pos_train_dev_text_overlap")
    if {_digest(r["template_id"]) for r in train} & {_digest(r["template_id"]) for r in dev}:
        raise ValueError("pos_train_dev_template_overlap")


def load_inputs(train_entries, dev_entries, positive_train_file=None, positive_dev_file=None,
                negative_train_file=None):
    """Admit exact splits against ALL Micro train/dev IDs and all other admitted inputs."""
    forbid = {e["row_id"] for e in train_entries + dev_entries}
    neg, neg_binding = [], None
    pos_train, train_binding, pos_dev, dev_binding = [], None, [], None
    if negative_train_file is not None:
        neg, neg_binding = nd.load_negative_file(negative_train_file, forbid_ids=forbid)
        forbid.update(r["row_id"] for r in neg)
    if positive_train_file is not None:
        pos_train, train_binding = pd.load_positive_file(
            positive_train_file, allowed_split="train", forbid_ids=forbid)
        forbid.update(r["row_id"] for r in pos_train)
    if positive_dev_file is not None:
        pos_dev, dev_binding = pd.load_positive_file(
            positive_dev_file, allowed_split="dev", forbid_ids=forbid)
    check_positive_disjoint(pos_train, pos_dev)
    return pos_train, train_binding, pos_dev, dev_binding, neg, neg_binding


def positive_dataset(positive_rows):
    """Use the original evaluator's row/entry representation, without altering alignment."""
    rows = {r["row_id"]: (r["source_text"],
            sorted((m["start"], m["end"], m["label"]) for m in r["privacy_mask"]), r["language"])
            for r in positive_rows}
    entries = [{"row_id": r["row_id"], "language": r["language"]} for r in positive_rows]
    return rows, entries


def training_labels(micro_train_rows, positive_train_rows):
    # ALL original Micro TRAIN labels, not just the selected rows. No dev data is accepted here.
    pos_rows, _ = positive_dataset(positive_train_rows)
    return md.label_list({**micro_train_rows, **pos_rows})


def check_dev_labels(labels, micro_dev_rows, positive_dev_rows):
    inventory = set(labels)
    for rows, code in ((micro_dev_rows, "dev_label_not_in_train"),
                       (positive_dev_rows, "pos_dev_label_not_in_train")):
        if any("{}-{}".format(prefix, span[2]) not in inventory
               for _, spans, _ in rows.values() for span in spans for prefix in ("B", "I")):
            raise ValueError(code)


def assemble_training(micro_rows, selected_entries, positive_train_rows, negative_rows):
    """Append each augmentation once AFTER the Micro-only selection/cap; dev cannot enter here."""
    pos_rows, pos_entries = positive_dataset(positive_train_rows)
    neg_rows = {r["row_id"]: (r["source_text"], [], r["language"]) for r in negative_rows}
    neg_entries = [{"row_id": r["row_id"], "language": r["language"]} for r in negative_rows]
    return {**micro_rows, **pos_rows, **neg_rows}, list(selected_entries) + pos_entries + neg_entries


def source_counts(micro_entries, positive_rows, negative_rows, windows):
    """Keep admission and retained/excluded counts separate for each source."""
    kept = {w[3] for w in windows}
    counts = {}
    for source, entries in (("micro", micro_entries), ("positive", positive_rows), ("negative", negative_rows)):
        ids = {r["row_id"] for r in entries}
        retained = len(ids & kept)
        counts[source] = {"included": len(ids), "retained": retained,
                          "excluded_after_windowing": len(ids) - retained}
    return counts
