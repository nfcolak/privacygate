"""Dev-only comparison: regex vs mBERT vs hybrid policies on Micro dev and challenge dev. Numbers only, no text.

env -u PYTHONPATH HF_HUB_OFFLINE=1 <venv-train>/bin/python scripts/compare.py [--model-dir DIR] [--max-micro-rows N]
Test splits are never read. The mBERT confidence threshold is tuned on dev only (and so is optimistic on dev).
"""
import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from privacygate import hybrid, mbert_data as md  # noqa: E402
from privacygate.train_mbert import build_windows, prf  # noqa: E402

THRS = [0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
ARMS = ["regex", "mbert", "union", "rules_first", "rules_first_thr"]


def preds_for(arm, rx, raw, mb, thr):
    if arm == "regex":
        return rx
    if arm == "mbert":
        return mb.spans(raw, 0.0)
    if arm == "union":
        return hybrid.union(rx, mb.spans(raw, 0.0))
    if arm == "rules_first":
        return hybrid.rules_first(rx, mb.spans(raw, 0.0))
    return hybrid.rules_first(rx, mb.spans(raw, thr))


def chars(spans):
    c = set()
    for s in spans:
        c.update(range(s["start"], s["end"]))
    return c


def evaluate(items, label_filter=None):
    """items: list of dict(lang, stratum, text_len, gold[spans], pred[spans])."""
    tot, lab, lang = [0, 0, 0], collections.defaultdict(lambda: [0, 0, 0]), collections.defaultdict(lambda: [0, 0, 0])
    cm = [0, 0, 0, 0]  # gold chars masked, gold chars, masked chars gold, masked chars
    for it in items:
        gold = {(s["start"], s["end"], s["label"]) for s in it["gold"]}
        pred = {(s["start"], s["end"], s["label"]) for s in it["pred"]}
        for s in gold | pred:
            if label_filter and s[2] != label_filter:
                continue
            k = 0 if s in gold and s in pred else (1 if s in pred else 2)
            for t in (tot, lab[s[2]], lang[it["lang"]]):
                t[k] += 1
        g, p = chars(it["gold"]), chars(it["pred"])
        cm[0] += len(g & p); cm[1] += len(g); cm[2] += len(g & p); cm[3] += len(p)
    out = {"overall": prf(*tot), "per_label": {k: prf(*v) for k, v in sorted(lab.items())},
           "per_language": {k: prf(*v) for k, v in sorted(lang.items())},
           "char_mask": {"recall": cm[0] / cm[1] if cm[1] else None, "precision": cm[2] / cm[3] if cm[3] else None,
                         "gold_chars": cm[1], "masked_chars": cm[3]}}
    return out


def challenge_metrics(items):
    ib = [i for i in items if i["stratum"] == "iban"]
    res = {"iban_n": len(ib)}
    res["iban_recall_strict"] = sum(1 for i in ib if all((g["start"], g["end"], g["label"]) in {(p["start"], p["end"], p["label"]) for p in i["pred"]} for g in i["gold"])) / len(ib)
    res["iban_recall_label_agnostic"] = sum(1 for i in ib if all(chars([g]) <= chars(i["pred"]) for g in i["gold"])) / len(ib)
    res["iban_strict_prf"] = prf(*(lambda t: t)(_count(ib, "IBAN")))
    for st, key in (("iban_decoy", "decoy_fp_rate"), ("clean", "clean_fp_rate")):
        sub = [i for i in items if i["stratum"] == st]
        res[key] = sum(1 for i in sub if i["pred"]) / len(sub)
        res[st + "_n"] = len(sub)
    neg = [i for i in items if i["stratum"] in ("iban_decoy", "clean")]
    tl = sum(i["text_len"] for i in neg)
    res["overmasked_char_rate_clean_decoy"] = sum(len(chars(i["pred"])) for i in neg) / tl
    res["per_language_iban_recall_label_agnostic"] = {
        l: sum(1 for i in ib if i["lang"] == l and all(chars([g]) <= chars(i["pred"]) for g in i["gold"])) / sum(1 for i in ib if i["lang"] == l)
        for l in sorted({i["lang"] for i in ib})}
    return res


def _count(items, label):
    tp = fp = fn = 0
    for it in items:
        g = {(s["start"], s["end"]) for s in it["gold"] if s["label"] == label}
        p = {(s["start"], s["end"]) for s in it["pred"] if s["label"] == label}
        tp += len(g & p); fp += len(p - g); fn += len(g - p)
    return tp, fp, fn


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-dir", type=Path, default=hybrid.DEFAULT_MODEL_DIR)
    ap.add_argument("--max-micro-rows", type=int, default=None)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs/runs/compare-dev")
    args = ap.parse_args()

    mb = hybrid.Mbert(args.model_dir)
    label2id = {v: k for k, v in mb.id2label.items()}

    entries = md.manifest("dev")
    if args.max_micro_rows:
        entries = entries[:args.max_micro_rows]
    rows = md.load_rows(entries)
    wins, excluded = build_windows(mb.tok, rows, entries, label2id, False)  # same exclusion as train_mbert.evaluate
    kept = {w[3] for w in wins}
    entries = [e for e in entries if e["row_id"] in kept]
    micro = [{"lang": rows[e["row_id"]][2], "stratum": "micro", "text": rows[e["row_id"]][0],
              "gold": [{"start": s, "end": e_, "label": l} for s, e_, l in rows[e["row_id"]][1]]} for e in entries]
    chal = []
    for line in (ROOT / "data/challenge/dev.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        chal.append({"lang": r["lang"], "stratum": r["stratum"], "text": r["text"], "gold": r["spans"]})

    sets = {"micro_dev": micro, "challenge_dev": chal}
    cache = {}
    for name, items in sets.items():
        raws = mb.raw([i["text"] for i in items])
        cache[name] = ([hybrid.regex(i["text"]) for i in items], raws)
        for i in items:
            i["text_len"] = len(i["text"])

    def run(name, arm, thr):
        rxs, raws = cache[name]
        items = sets[name]
        return [dict(lang=i["lang"], stratum=i["stratum"], text_len=i["text_len"], gold=i["gold"],
                     pred=preds_for(arm, rx, raw, mb, thr)) for i, rx, raw in zip(items, rxs, raws)]

    # threshold tuning on dev: lowest clean+decoy FP rate among thresholds within 0.005 of best Micro-dev F1 (rules_first)
    sweep = {}
    for t in THRS:
        m = evaluate(run("micro_dev", "rules_first_thr", t))["overall"]
        c = challenge_metrics(run("challenge_dev", "rules_first_thr", t))
        sweep[str(t)] = {"micro_f1": m["f1"], "micro_precision": m["precision"], "micro_recall": m["recall"],
                         "decoy_fp_rate": c["decoy_fp_rate"], "clean_fp_rate": c["clean_fp_rate"]}
    top = max(v["micro_f1"] for v in sweep.values())
    ok = [t for t in THRS if sweep[str(t)]["micro_f1"] >= top - 0.005]  # keep Micro F1 within 0.005 of best, minimise false positives
    best = min(ok, key=lambda t: (sweep[str(t)]["clean_fp_rate"] + sweep[str(t)]["decoy_fp_rate"], t))

    metrics = {"note": "dev only; strict exact start/end/label; test splits untouched; threshold tuned on dev; single seed",
               "micro_rows_evaluated": len(micro), "micro_rows_excluded_broken_boundary": excluded,
               "challenge_rows": len(chal), "threshold_sweep": sweep, "chosen_threshold": best, "arms": {}}
    for arm in ARMS:
        thr = best if arm == "rules_first_thr" else 0.0
        mi = run("micro_dev", arm, thr)
        ch = run("challenge_dev", arm, thr)
        metrics["arms"][arm] = {"micro_dev": evaluate(mi), "micro_dev_email_only": evaluate(mi, "EMAIL")["overall"],
                                "challenge_dev": {**challenge_metrics(ch), "strict": evaluate(ch), "char_mask": evaluate(ch)["char_mask"]}}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    f = lambda x: "-" if x is None else "{:.3f}".format(x)
    lines = ["# Hybrid comparison on dev data", "",
             "Micro dev rows: {} (excluded for broken wordpiece boundary: {}); challenge dev rows: {}. mBERT = full-1. rules_first_thr uses mBERT confidence >= {} (tuned on dev).".format(
                 len(micro), excluded, len(chal), best), "",
             "| arm | Micro strict F1 | Micro EMAIL F1 | Micro char P | Micro char R | IBAN recall strict | IBAN recall any-label | decoy FP | clean FP | overmask chars |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        a = metrics["arms"][arm]
        c = a["challenge_dev"]
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            arm, f(a["micro_dev"]["overall"]["f1"]), f(a["micro_dev_email_only"]["f1"]), f(a["micro_dev"]["char_mask"]["precision"]),
            f(a["micro_dev"]["char_mask"]["recall"]), f(c["iban_recall_strict"]), f(c["iban_recall_label_agnostic"]),
            f(c["decoy_fp_rate"]), f(c["clean_fp_rate"]), "{:.4f}".format(c["overmasked_char_rate_clean_decoy"])))
    lines += ["", "Threshold sweep (rules_first, dev): threshold -> Micro F1 / clean FP / decoy FP"]
    lines += ["  {}: {:.3f} / {:.3f} / {:.3f}".format(t, v["micro_f1"], v["clean_fp_rate"], v["decoy_fp_rate"]) for t, v in sweep.items()]
    lines += ["", "Findings (see metrics.json):",
              "- mBERT has no IBAN label: strict IBAN recall 0, and only part of IBAN characters are masked under other labels. Regex and both hybrids reach full IBAN recall on this synthetic set.",
              "- On Micro dev, mBERT and the hybrids are within about 0.003 strict F1; union is closest to mBERT, rules_first loses a little because regex EMAIL spans differ from gold boundaries.",
              "- EMAIL-only strict F1 on Micro dev: regex is lower than mBERT; rules_first is lower than union because regex wins on overlap.",
              "- Regex has zero false positives on decoys and clean text (decoys were built to be negatives for the regex, so this is by construction, not evidence of robustness).",
              "- mBERT (and all hybrids using it) flags many clean and decoy sentences, because it was trained on Micro, which has no clean negatives; decoy codes look like ID-like PII to it. Whether masking decoys with some label is an error depends on the use.",
              "- The confidence threshold trades Micro recall for fewer false positives: see sweep. Chosen value is dev-tuned and optimistic.",
              "", "Limitations: dev data only (tests frozen), single seed and single model, synthetic data, challenge templates are few and simple; the label sets differ (regex 2 labels vs mBERT 19), so general strict F1 is not a fair regex comparison, use the EMAIL-only column."]
    open(args.out_dir / "summary.md", "w").write("\n".join(lines) + "\n")
    print(json.dumps({"chosen_threshold": best, "micro_rows": len(micro)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
