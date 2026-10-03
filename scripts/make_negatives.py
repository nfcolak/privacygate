"""Deterministic TRAIN-ONLY clean negatives (EN, DE, FR, IT, ES). Standard library only.

python3 scripts/make_negatives.py            # write data/augmentation/negatives-train.jsonl + docs/augmentation/manifest.json
python3 scripts/make_negatives.py --verify   # regenerate in memory; compare with manifest and file on disk
Prints counts and hashes only; generated text is gitignored.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from privacygate import negative_data as nd

OUT = ROOT / "data/augmentation/negatives-train.jsonl"
MANIFEST = ROOT / "docs/augmentation/manifest.json"


def manifest_of(rows):
    tmpl = {}
    for r in rows:
        tmpl[r["template_id"]] = tmpl.get(r["template_id"], 0) + 1
    return {"generator_version": nd.GEN_VERSION, "seed": nd.SEED, "split": "train", "rows": len(rows),
            "per_language": nd.counts(rows), "templates": dict(sorted(tmpl.items())),
            "sha256": nd.content_hash(rows), "file": "data/augmentation/negatives-train.jsonl",
            "note": "synthetic; text not committed; generic impersonal statements, no digits; no semantic-independence claim"}


def main():
    rows = nd.generate()
    man = manifest_of(rows)
    if "--verify" in sys.argv:
        if not OUT.is_file() or not MANIFEST.is_file():
            print("VERIFY FAIL: missing output or manifest"); return 1
        if json.loads(MANIFEST.read_text()) != man:
            print("VERIFY FAIL: manifest differs from regeneration"); return 1
        _, binding = nd.load_negative_file(OUT)
        if binding["sha256"] != man["sha256"]:
            print("VERIFY FAIL: file hash differs"); return 1
        print("VERIFY OK rows={} sha256={}".format(len(rows), man["sha256"])); return 0
    OUT.parent.mkdir(parents=True, exist_ok=True); MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(nd.dumps(rows))
    MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
    print("WROTE rows={} per_language={} sha256={}".format(len(rows), man["per_language"], man["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
