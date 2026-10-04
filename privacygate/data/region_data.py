"""Bounded six-field policy-v1 region JSONL and whole-row BIO alignment.

Standard library only at import time. Errors contain fixed codes, never input.
Gold stays in original Python character coordinates; clean negatives are retained.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import NoReturn

from privacygate import mbert_data as md
from privacygate.data import window_alignment as wa

SCHEMA_VERSION = "policy-v1-six-field-regions-v1"
REGION_LABELS = (
    "PERSONNAME", "ADDRESS", "EMAIL", "USERNAME", "TELEPHONENUM", "IBAN",
    "ACCOUNTNUM", "CREDITCARDNUMBER", "PASSPORTNUM", "IDCARDNUM",
    "DRIVERLICENSENUM", "TAXNUM", "SOCIALNUM", "PERSONALREF", "DATEOFBIRTH", "AGE",
)
LABELS = ["O"] + [prefix + "-" + label for label in REGION_LABELS for prefix in ("B", "I")]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for label, i in LABEL2ID.items()}
LANGUAGES = frozenset(("en", "de", "fr", "it", "es"))
ROW_KEYS = frozenset(("case_id", "family", "gold", "language", "split", "text"))
GOLD_KEYS = frozenset(("start", "end", "label"))
MAX_ROWS, MAX_CHARS, MAX_GOLD, MAX_ID_CHARS = 32000, 12000, 128, 200
MAX_LINE_BYTES, MAX_FILE_BYTES = 128 * 1024, 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}")
ERROR_CODES = frozenset("region_" + code for code in (
    "split schema field_type language text_bounds identifier duplicate_id duplicate_text "
    "gold_schema gold_type label span_bounds span_order_overlap row_count path not_regular_file "
    "file_too_large line_too_long unparseable manifest_schema manifest_missing_hash "
    "manifest_ambiguous_hash manifest_hash_mismatch train_dev_overlap empty_windows mode_arguments"
).split())


def _fail(code) -> NoReturn:
    raise ValueError("region_" + code) from None


def _open_bounded(path, limit):
    """Reject directories/devices/FIFOs before reading, including a growing file."""
    try:
        fd = os.open(os.fspath(path), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        handle = os.fdopen(fd, "rb")
    except (OSError, ValueError, TypeError):
        _fail("path")
    try:
        meta = os.fstat(handle.fileno())
        if not stat.S_ISREG(meta.st_mode):
            _fail("not_regular_file")
        if meta.st_size > limit:
            _fail("file_too_large")
    except Exception:
        handle.close()
        raise
    return handle


def _parse(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        _fail("unparseable")


def _manifest_sha256(manifest_path, data_path, split):
    """Accept split/filename-keyed hash records or path-bearing artifact records.

    Records contain sha256 and optional path/file; bare hashes may be keyed by
    split or filename. Exactly one matching record is required; no silent fallback.
    """
    try:
        with _open_bounded(manifest_path, MAX_MANIFEST_BYTES) as handle:
            raw = handle.read(MAX_MANIFEST_BYTES + 1)
    except OSError:
        _fail("path")
    if len(raw) > MAX_MANIFEST_BYTES:
        _fail("file_too_large")
    manifest = _parse(raw)
    if not isinstance(manifest, dict):
        _fail("manifest_schema")
    found = []
    target = Path(data_path).name

    def visit(node, key=None, depth=0):
        if depth > 16:
            _fail("manifest_schema")
        if isinstance(node, dict):
            named = node.get("path", node.get("file", node.get("filename")))
            matches = (isinstance(named, str) and Path(named).name == target) or (
                named is None and key in (split, target))
            if matches and "sha256" in node:
                found.append(node["sha256"])
            for k, value in node.items():
                if k == "sha256" and matches:
                    continue
                visit(value, k, depth + 1)
        elif isinstance(node, list):
            for value in node:
                visit(value, None, depth + 1)
        elif key in (split, target, split + "_sha256") and isinstance(node, str):
            if SHA256.fullmatch(node):
                found.append(node)

    # Generators v3/v4/v5 bind data only under outputs; template_catalog has its
    # own split-keyed hashes, which are not hashes of the JSONL artifacts.
    if manifest.get("manifest_version") in (3, 4, 5):
        outputs = manifest.get("outputs")
        if not isinstance(outputs, dict):
            _fail("manifest_schema")
        visit(outputs)
    else:
        visit(manifest)
    if not found:
        _fail("manifest_missing_hash")
    if len(found) != 1:
        _fail("manifest_ambiguous_hash")
    if not isinstance(found[0], str) or not SHA256.fullmatch(found[0]):
        _fail("manifest_schema")
    return found[0], hashlib.sha256(raw).hexdigest()


def _check_row(row, split):
    if not isinstance(row, dict) or row.keys() != ROW_KEYS:
        _fail("schema")
    if any(not isinstance(row[k], str) for k in ROW_KEYS - {"gold"}):
        _fail("field_type")
    if row["split"] != split:
        _fail("split")
    if row["language"] not in LANGUAGES:
        _fail("language")
    if any(not row[k] or len(row[k]) > MAX_ID_CHARS for k in ("case_id", "family")):
        _fail("identifier")
    text = row["text"]
    if not text.strip() or len(text) > MAX_CHARS or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
        _fail("text_bounds")
    gold = row["gold"]
    if not isinstance(gold, list) or len(gold) > MAX_GOLD:
        _fail("gold_schema")
    end = 0
    for span in gold:
        if not isinstance(span, dict) or span.keys() != GOLD_KEYS:
            _fail("gold_schema")
        a, b, label = span["start"], span["end"], span["label"]
        if type(a) is not int or type(b) is not int or not isinstance(label, str):
            _fail("gold_type")
        if label not in REGION_LABELS:
            _fail("label")
        if not 0 <= a < b <= len(text):
            _fail("span_bounds")
        if a < end:
            _fail("span_order_overlap")
        end = b


def load_region_file(path, allowed_split="train", manifest_path=None):
    """Return validated rows and aggregate provenance, hashing the exact bytes read."""
    if allowed_split not in ("train", "dev"):
        _fail("split")
    expected, manifest_hash = (None, None) if manifest_path is None else _manifest_sha256(
        manifest_path, path, allowed_split)
    rows, ids, texts, size, digest = [], set(), {}, 0, hashlib.sha256()
    try:
        with _open_bounded(path, MAX_FILE_BYTES) as handle:
            while True:
                raw = handle.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break
                if len(raw) > MAX_LINE_BYTES:
                    _fail("line_too_long")
                size += len(raw)
                if size > MAX_FILE_BYTES:
                    _fail("file_too_large")
                if len(rows) >= MAX_ROWS:
                    _fail("row_count")
                digest.update(raw)
                row = _parse(raw)
                _check_row(row, allowed_split)
                text_hash = hashlib.sha256(row["text"].encode()).digest()
                if row["case_id"] in ids:
                    _fail("duplicate_id")
                # Finite synthetic pools can repeat a rendered example within a
                # split. Keep its sampling weight, but reject conflicting gold
                # or language; check_disjoint still rejects train/dev repeats.
                signature = (row["language"], tuple(
                    (span["start"], span["end"], span["label"]) for span in row["gold"]))
                if text_hash in texts and texts[text_hash] != signature:
                    _fail("duplicate_text")
                ids.add(row["case_id"])
                texts[text_hash] = signature
                rows.append(row)
    except OSError:
        _fail("path")
    if not rows:
        _fail("row_count")
    actual = digest.hexdigest()
    if expected is not None and actual != expected:
        _fail("manifest_hash_mismatch")
    return rows, {"sha256": actual, "bytes": size, "rows": len(rows), "split": allowed_split,
                  "clean_rows": sum(not row["gold"] for row in rows),
                  "schema": SCHEMA_VERSION, "manifest_sha256": manifest_hash}


def check_disjoint(train, dev):
    if {row["case_id"] for row in train} & {row["case_id"] for row in dev}:
        _fail("train_dev_overlap")
    hashes = lambda rows: {hashlib.sha256(row["text"].encode()).digest() for row in rows}
    if hashes(train) & hashes(dev):
        _fail("train_dev_overlap")


def build_windows(tok, rows):
    """md.encode + md.align (through wa): crossing gold ignored, whole rows gated.

    Every gold region must align exactly and be complete in a retained window.
    Returns trainer tuples plus value-free counts; no partial-row supervision.
    """
    windows, stats = [], wa.empty_stats()
    stats.update(rows_available=len(rows), rows_used=0, rows_excluded=0, clean_rows_used=0)
    for row_index, row in enumerate(rows):
        spans = [(s["start"], s["end"], s["label"]) for s in row["gold"]]
        encoded = md.encode(tok, row["text"])
        aligned = wa.align_windows(wa.whole_offsets(tok, row["text"]),
                                   [offs for _, offs in encoded], spans)
        stats["windows_discarded_alignment"] += aligned["windows_discarded_alignment"]
        if not aligned["retained"]:
            stats["rows_excluded"] += 1
            for reason in aligned["reasons"]:
                stats["rows_excluded_by_reason"][reason] += 1
            continue
        stats["rows_used"] += 1
        stats["clean_rows_used"] += not spans
        stats["gold_spans_retained"] += len(spans)
        stats["gold_spans_fully_covered"] += len(aligned["covered"])
        for win in aligned["windows"]:
            ids, offs = encoded[win["source_window_index"]]
            stats["ignored_crossing_tokens_retained"] += win["ignored_crossing_tokens"]
            windows.append((ids, [md.IGNORE if label is None else LABEL2ID[label]
                                  for label in win["labels"]], offs, row_index))
    stats["windows"] = len(windows)
    return windows, stats
