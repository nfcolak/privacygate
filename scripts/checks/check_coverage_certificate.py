#!/usr/bin/env python3
"""Offline tokenizer-only coverage certificate; synthetic dev data, aggregate output only."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from privacygate import mbert_data as md
from privacygate.model.inference import apply_mask, merge_spans, uncovered_regions


def main():
    data = ROOT / "data/augmentation/masking-stress-dev.jsonl"
    manifest = json.loads((ROOT / "artifacts/masking-stress/manifest.json").read_text())
    payload = data.read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["dataset"]["sha256"]:
        raise ValueError("coverage fixture mismatch")
    tok = md.load_tokenizer()
    total, rows = 0, 0
    for line in payload.splitlines():
        row = json.loads(line)
        if row["split"] != "dev":
            raise ValueError("development fixture required")
        text = row["text"]
        windows = md.encode(tok, text)
        regions = uncovered_regions(text, (o for _, offs in windows for o in offs))
        total += sum(b - a for a, b in regions)
        rows += 1
    if rows != manifest["dataset"]["rows"]:
        raise ValueError("coverage fixture count mismatch")
    print("uncovered_v1_chars={}".format(total))

    # Deliberately omit the final real encoder window; overlap is still allowed.
    text = "quarnix " * 2300
    windows = md.encode(tok, text)
    tokens = tok(text, add_special_tokens=False, truncation=False, verbose=False)["input_ids"]
    if len(tokens) <= 2000 or len(windows) < 2:
        raise ValueError("forced-tail fixture too short")
    if uncovered_regions(text, (o for _, offs in windows for o in offs)):
        raise ValueError("forced-tail fixture has incomplete full coverage")
    retained = windows[:-1]
    tail_start = max(o[1] for _, offs in retained for o in offs if o is not None)
    regions = uncovered_regions(text, (o for _, offs in retained for o in offs))
    spans = [{"start": a, "end": b, "label": "UNCOVERED", "source": "coverage"}
             for a, b in regions]
    result = apply_mask(text, merge_spans(spans, len(text)))
    masked = bytearray(len(text))
    for span in result["entities"]:
        masked[span["start"]:span["end"]] = b"\x01" * (span["end"] - span["start"])
    tail_chars = [i for i in range(tail_start, len(text)) if not text[i].isspace()]
    all_masked = (bool(tail_chars) and bool(regions)
                  and "[UNCOVERED]" in result["masked_text"]
                  and all(masked[i] for i in tail_chars))
    print("forced_tail_masked={}".format("ALL" if all_masked else "PARTIAL"))
    return 0 if total == 0 and all_masked else 1


if __name__ == "__main__":
    try:
        status = main()
    except Exception:
        sys.stderr.write("coverage_certificate=FAILED (input and details not shown)\n")
        status = 1
    raise SystemExit(status)
