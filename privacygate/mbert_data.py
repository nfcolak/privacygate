"""Shared data/alignment helpers for the mBERT BIO pipeline. Never prints text or values."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "google-bert/bert-base-multilingual-cased"
MODEL_REVISION = "3f076fdb1ab68d5b2880cb87a0886f315b8146f8"
MICRO_REPO = "ai4privacy/openpii-masking-micro-100k"
MICRO_REVISION = "f95b4e1539657c3d0047d9ad3f20f26675f22c7d"
RAW_DIR = Path("/Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/data/raw/openpii-masking-micro-100k")
MAX_LEN, STRIDE = 512, 128  # STRIDE = token overlap between consecutive windows
IGNORE = -100


def setup_hf_home():
    os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "hf"))


def manifest(split):
    return [json.loads(l) for l in (ROOT / "data/manifests/micro/{}.jsonl".format(split)).read_text().splitlines()]


def load_rows(entries, raw_dir=RAW_DIR):
    """Return {row_id: (text, [(start,end,label)], language)} read from raw artifacts by row ID
    (SHA256(repo:revision:path:line_index), same as audit_dataset.py)."""
    need = {e["row_id"]: e["language"] for e in entries}
    source = json.loads((ROOT / "docs/data-audit/micro/source.json").read_text())
    out = {}
    for art in source["artifacts"]:
        if "split" not in art:
            continue
        with open(raw_dir / art["path"], "rb") as handle:
            for ordinal, line in enumerate(handle):
                rid = hashlib.sha256("{}:{}:{}:{}".format(MICRO_REPO, MICRO_REVISION, art["path"], ordinal).encode()).hexdigest()
                if rid in need:
                    row = json.loads(line)
                    spans = sorted((m["start"], m["end"], m["label"]) for m in row["privacy_mask"])
                    out[rid] = (row["source_text"], spans, need[rid])
    if len(out) != len(need):
        raise ValueError("rows_missing_from_raw")
    return out


def label_list(train_rows):
    names = sorted({s[2] for _, spans, _ in train_rows.values() for s in spans})
    return ["O"] + ["{}-{}".format(p, n) for n in names for p in ("B", "I")]


def encode(tok, text):
    """Sliding windows (MAX_LEN, STRIDE overlap). Returns list of (input_ids, offsets) per window,
    special tokens carry offset (0,0) and are dropped from `offsets` as None."""
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=MAX_LEN, stride=STRIDE,
              return_overflowing_tokens=True)
    wins = []
    for ids, offs in zip(enc["input_ids"], enc["offset_mapping"]):
        offs = [None if (a == b == 0) else (a, b) for a, b in offs]
        wins.append((ids, offs))
    return wins


def align(offs, spans):
    """Char spans -> per-wordpiece BIO label names ('O','B-X','I-X', None for special tokens).
    Scheme: EVERY wordpiece overlapping a span is labelled (first = B-, rest = I-), so later subwords
    of a word carry I- (no -100). Returns (labels, broken_boundary_spans, lost_spans)."""
    labels = [None if o is None else "O" for o in offs]
    broken = lost = 0
    for start, end, lab in spans:
        idx = [i for i, o in enumerate(offs) if o is not None and o[0] < end and o[1] > start]
        if not idx:
            lost += 1
            continue
        if offs[idx[0]][0] != start or offs[idx[-1]][1] != end:
            broken += 1
        for k, i in enumerate(idx):
            labels[i] = ("B-" if k == 0 else "I-") + lab
    return labels, broken, lost


def decode(offs, pred):
    """Predicted per-wordpiece label names -> set of (start,end,label) char spans."""
    spans, cur = set(), None
    for o, p in zip(offs, pred):
        if o is None or p == "O":
            if cur:
                spans.add(tuple(cur)); cur = None
            continue
        tag, lab = p.split("-", 1)
        if tag == "B" or cur is None or cur[2] != lab:
            if cur:
                spans.add(tuple(cur))
            cur = [o[0], o[1], lab]
        else:
            cur[1] = o[1]
    if cur:
        spans.add(tuple(cur))
    return spans


def load_tokenizer():
    setup_hf_home()
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, use_fast=True)
