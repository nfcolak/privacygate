#!/usr/bin/env python3
"""Tokenizer alignment check (mBERT fast tokenizer) on Micro train/dev manifests. Aggregate counts only.

Label scheme: every wordpiece overlapping a span is labelled; first = B-, later = I- (no -100).
Long rows: sliding windows (max_len 512, stride 128 tokens) at train/eval time; none dropped.
Rows with a span boundary inside a wordpiece (or a span with no wordpiece) are excluded, never repaired.
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from privacygate import mbert_data as md  # noqa: E402


def row_stats(tok, text, spans):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=True, truncation=False, verbose=False)
    offs = [None if (a == b == 0) else (a, b) for a, b in enc["offset_mapping"]]
    _, broken, lost = md.align(offs, spans)
    unk = sum(1 for i in enc["input_ids"] if i == tok.unk_token_id)
    return len(enc["input_ids"]), broken, lost, unk


def main():
    md.setup_hf_home()
    tok = md.load_tokenizer()
    result = {"model": md.MODEL_ID, "model_revision": md.MODEL_REVISION, "max_len": md.MAX_LEN, "window_stride_tokens": md.STRIDE,
              "label_scheme": "all wordpieces overlapping a span labelled; first B-, later I-; specials ignored (-100)",
              "long_row_handling": "sliding window, no rows dropped", "splits": {}}
    for split in ("train", "dev"):
        entries = md.manifest(split)
        rows = md.load_rows(entries)
        c = collections.Counter()
        per_lang = collections.defaultdict(collections.Counter)
        for e in entries:
            text, spans, lang = rows[e["row_id"]]
            n, broken, lost, unk = row_stats(tok, text, spans)
            for k, v in (("rows", 1), ("spans", len(spans)), ("spans_boundary_inside_wordpiece", broken), ("spans_lost", lost),
                         ("rows_with_broken_boundary", broken > 0), ("rows_with_lost_span", lost > 0),
                         ("rows_longer_than_max_len", n > md.MAX_LEN), ("unk_wordpieces", unk), ("wordpieces", n),
                         ("rows_excluded", broken > 0 or lost > 0)):
                c[k] += int(v); per_lang[lang][k] += int(v)
        c["unk_rate"] = c["unk_wordpieces"] / max(1, c["wordpieces"])
        d = dict(c)
        d["per_language"] = {l: dict(v, unk_rate=v["unk_wordpieces"] / max(1, v["wordpieces"])) for l, v in sorted(per_lang.items())}
        result["splits"][split] = d
        print(split, {k: v for k, v in d.items() if k != "per_language"})
    out = md.ROOT / "artifacts/data-audit/micro/alignment.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    sys.exit(main())
