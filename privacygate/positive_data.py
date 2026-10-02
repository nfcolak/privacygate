"""Bounded, typed loader for synthetic POSITIVE (annotated) PII augmentation files. Never prints text or values.

Row schema (JSONL, exact keys): row_id, language, source_text, privacy_mask, template_id, split.
privacy_mask entries have exactly start/end/label (character offsets into source_text; no copied value).
Errors are ValueError(code) with a short fixed code only: no text, offsets, keys, types or labels are echoed.

Scope: synthetic research data. USERNAME, ACCOUNTNUM and PERSONALREF are initial proposed operational labels
for explicitly person-linked identifiers; they are NOT a legal classification or an exhaustive taxonomy, and no
trained support exists for them. A valid label is not evidence that a generated identifier is real.
"""
import hashlib
import json
import os
import stat

LANGS = ("en", "de", "fr", "it", "es")
SPLITS = ("train", "dev")  # no test split exists for this data
GEN_VERSION = "pos-v1"
CORE_LABELS = ("GIVENNAME", "SURNAME", "TELEPHONENUM", "IDCARDNUM", "PASSPORTNUM", "DRIVERLICENSENUM",
               "STREET", "BUILDINGNUM", "CITY", "ZIPCODE")
NEW_LABELS = ("USERNAME", "ACCOUNTNUM", "PERSONALREF")
LABELS = frozenset(CORE_LABELS + NEW_LABELS)  # allowlist; existing exact labels + 3 proposed new ones
KEYS = frozenset({"row_id", "language", "source_text", "privacy_mask", "template_id", "split"})
MASK_KEYS = frozenset({"start", "end", "label"})
MAX_ROWS, MAX_CHARS, MAX_ANNOTATIONS, MAX_ID_CHARS = 20000, 2000, 32, 200
MAX_LINE_BYTES = 32768
MAX_FILE_BYTES = 16 * 1024 * 1024


def dumps(rows):
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def content_hash(rows):
    return hashlib.sha256(dumps(rows).encode()).hexdigest()


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check_rows(rows, allowed_split="train", forbid_ids=()):
    """Fail-closed structural validation. Raises ValueError('pos_<code>') only."""
    if allowed_split not in SPLITS:
        raise ValueError("pos_bad_allowed_split")
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError("pos_row_count")
    try:
        forbid = set(forbid_ids)
    except TypeError:
        raise ValueError("pos_bad_forbid_ids") from None
    ids, texts, tmpl = set(), set(), {}
    for r in rows:
        if not isinstance(r, dict) or set(r) != KEYS:
            raise ValueError("pos_schema")
        for k in ("row_id", "language", "source_text", "template_id", "split"):
            if not isinstance(r[k], str):
                raise ValueError("pos_field_type")
        if r["split"] != allowed_split:
            raise ValueError("pos_split_mismatch")
        if r["language"] not in LANGS:
            raise ValueError("pos_language")
        text = r["source_text"]
        if not text.strip() or len(text) > MAX_CHARS:
            raise ValueError("pos_text_bounds")
        if not r["row_id"] or len(r["row_id"]) > MAX_ID_CHARS or r["row_id"] in ids or r["row_id"] in forbid:
            raise ValueError("pos_row_id")
        if not r["template_id"] or len(r["template_id"]) > MAX_ID_CHARS:
            raise ValueError("pos_template_id")
        if (r["language"], text) in texts:
            raise ValueError("pos_duplicate_text")
        mask = r["privacy_mask"]
        if not isinstance(mask, list):
            raise ValueError("pos_field_type")
        if not mask or len(mask) > MAX_ANNOTATIONS:
            raise ValueError("pos_annotation_count")
        spans = []
        for m in mask:
            if not isinstance(m, dict) or set(m) != MASK_KEYS:
                raise ValueError("pos_mask_schema")
            if not _int(m["start"]) or not _int(m["end"]) or not isinstance(m["label"], str):
                raise ValueError("pos_mask_type")
            if m["label"] not in LABELS:
                raise ValueError("pos_label")
            if not 0 <= m["start"] < m["end"] <= len(text):
                raise ValueError("pos_span_bounds")
            spans.append((m["start"], m["end"]))
        spans.sort()
        for (_, e1), (s2, _) in zip(spans, spans[1:]):
            if s2 < e1:
                raise ValueError("pos_span_overlap")
        ids.add(r["row_id"]); texts.add((r["language"], text))
        tmpl.setdefault(r["template_id"], r["language"])
        if tmpl[r["template_id"]] != r["language"]:
            raise ValueError("pos_template_language")


def _read_bounded(path):
    try:
        fd = os.open(os.fspath(path), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    except TypeError:
        raise ValueError("pos_path") from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("pos_not_regular_file")
        f = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with f:
        raw = f.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("pos_file_too_large")
    return raw


def binding_of(rows, raw, split):
    per_language = {l: 0 for l in LANGS}
    per_label = {}
    for r in rows:
        per_language[r["language"]] += 1
        for m in r["privacy_mask"]:
            per_label[m["label"]] = per_label.get(m["label"], 0) + 1
    return {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows), "per_language": per_language,
            "per_label": dict(sorted(per_label.items())), "templates": len({r["template_id"] for r in rows}),
            "split": split}


def load_positive_file(path, allowed_split="train", forbid_ids=()):
    """Return (rows, binding). Only rows whose split equals allowed_split (default 'train') are accepted;
    a dev file is rejected unless allowed_split='dev' is passed explicitly. binding is value-free."""
    if allowed_split not in SPLITS:
        raise ValueError("pos_bad_allowed_split")
    raw = _read_bounded(path)
    lines = [l for l in raw.split(b"\n") if l.strip()]
    if not lines or len(lines) > MAX_ROWS:
        raise ValueError("pos_row_count")
    if any(len(l) > MAX_LINE_BYTES for l in lines):
        raise ValueError("pos_line_too_long")
    rows = []
    for l in lines:
        try:
            rows.append(json.loads(l.decode("utf-8")))
        except (ValueError, RecursionError):
            raise ValueError("pos_unparseable") from None
    check_rows(rows, allowed_split, forbid_ids)
    return rows, binding_of(rows, raw, allowed_split)
