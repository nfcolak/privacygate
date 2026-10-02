"""mBERT BIO token classifier on Micro train; dev-only strict span evaluation. Logs numbers only, never text.

python -m privacygate.train_mbert --run NAME [--max-train-rows N] [--max-dev-rows N] [--epochs E] [--batch-size B] [--lr 3e-5]
"""
import argparse
import collections
import json
import random
import sys
import time
from pathlib import Path

from . import mbert_data as md
from . import negative_data as nd


def build_windows(tok, rows, entries, label2id, train):
    """Windows of (ids, label_ids|None, offs, row_id). Rows with a broken span boundary are excluded."""
    out, excluded = [], 0
    for e in entries:
        text, spans, _ = rows[e["row_id"]]
        wins = md.encode(tok, text)
        aligned = [md.align(offs, spans) for _, offs in wins]
        if any(a[1] or a[2] for a in aligned):
            # boundary check is on whole-row (unwindowed) tokenization in check_alignment; windows can only
            # see a subset of spans, so any window-level break also excludes the row.
            excluded += 1
            continue
        for (ids, offs), (labs, _, _) in zip(wins, aligned):
            out.append((ids, [md.IGNORE if l is None else label2id[l] for l in labs], offs, e["row_id"]))
    return out, excluded


def batches(items, bs, shuffle, rng):
    idx = list(range(len(items)))
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        yield [items[j] for j in idx[i:i + bs]]


def collate(batch, torch, device):
    n = max(len(b[0]) for b in batch)
    n = min(md.MAX_LEN, (n + 63) // 64 * 64)  # few distinct shapes (MPS)
    ids = torch.zeros(len(batch), n, dtype=torch.long)
    att = torch.zeros(len(batch), n, dtype=torch.long)
    lab = torch.full((len(batch), n), md.IGNORE, dtype=torch.long)
    for i, b in enumerate(batch):
        ids[i, :len(b[0])] = torch.tensor(b[0]); att[i, :len(b[0])] = 1
        lab[i, :len(b[1])] = torch.tensor(b[1])
    return ids.to(device), att.to(device), lab.to(device)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0, "tp": tp, "fp": fp, "fn": fn, "support": tp + fn}


def evaluate(model, tok, rows, entries, id2label, device, torch, bs):
    model.eval()
    wins, excluded = build_windows(tok, rows, entries, {v: k for k, v in id2label.items()}, False)
    pred_spans = collections.defaultdict(set)
    with torch.no_grad():
        for batch in batches(wins, bs, False, None):
            ids, att, _ = collate(batch, torch, device)
            pred = model(input_ids=ids, attention_mask=att).logits.argmax(-1).cpu().tolist()
            for b, p in zip(batch, pred):
                names = [id2label[x] for x in p[:len(b[0])]]
                pred_spans[b[3]] |= md.decode(b[2], names)
    tot, per_label, per_lang = [0, 0, 0], collections.defaultdict(lambda: [0, 0, 0]), collections.defaultdict(lambda: [0, 0, 0])
    evaluated = 0
    kept = {w[3] for w in wins}
    for e in entries:
        if e["row_id"] not in kept:
            continue
        evaluated += 1
        text, spans, lang = rows[e["row_id"]]
        gold, pred = set(spans), pred_spans[e["row_id"]]
        for s in gold | pred:
            k = 0 if s in gold and s in pred else (1 if s in pred else 2)
            for t in (tot, per_label[s[2]], per_lang[lang]):
                t[k] += 1
    return {"rows_evaluated": evaluated, "rows_excluded_broken_boundary": excluded, "overall": prf(*tot),
            "per_label": {k: prf(*v) for k, v in sorted(per_label.items())},
            "per_language": {k: prf(*v) for k, v in sorted(per_lang.items())}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--max-train-rows", type=int, default=None)
    ap.add_argument("--max-dev-rows", type=int, default=None)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--negative-train-file", type=Path, default=None,
                    help="optional synthetic clean-negative JSONL (split=train, empty annotations); appended after positive selection")
    ap.add_argument("--out-dir", type=Path, default=md.ROOT / "models", help="parent dir for model checkpoints")
    args = ap.parse_args()

    md.setup_hf_home()
    import torch
    from transformers import AutoModelForTokenClassification

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)
    tok = md.load_tokenizer()
    train_entries = md.manifest("train")
    dev_entries = md.manifest("dev")
    train_rows = md.load_rows(train_entries)
    labels = md.label_list(train_rows)  # from ALL Micro train rows, independent of --max-train-rows
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    rng.shuffle(train_entries)
    rng.shuffle(dev_entries)
    if args.max_train_rows:
        train_entries = train_entries[:args.max_train_rows]
    if args.max_dev_rows:
        dev_entries = dev_entries[:args.max_dev_rows]
    dev_rows = md.load_rows(dev_entries)
    neg_binding = None
    if args.negative_train_file:
        try:
            neg_rows, neg_binding = nd.load_negative_file(args.negative_train_file, forbid_ids=set(train_rows) | set(dev_rows))
        except (ValueError, OSError) as exc:
            print("negative file rejected: {}".format(exc if isinstance(exc, ValueError) else "unreadable"), file=sys.stderr)
            return 2
        for r in neg_rows:  # appended after positive selection; labels stay those of the original Micro train
            train_rows[r["row_id"]] = (r["source_text"], [], r["language"])
            train_entries.append({"row_id": r["row_id"], "language": r["language"]})

    model_dir = args.out_dir / args.run
    final = model_dir / "train_info.json"
    config = {"run": args.run, "model": md.MODEL_ID, "model_revision": md.MODEL_REVISION, "epochs": args.epochs,
              "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed, "max_len": md.MAX_LEN,
              "window_stride_tokens": md.STRIDE, "max_train_rows": args.max_train_rows, "max_dev_rows": args.max_dev_rows,
              "label_scheme": "first wordpiece of span B-, later wordpieces I-; specials -100",
              "rows_with_broken_boundary_excluded": True, "labels": labels, "data": "Micro provisional train/dev manifests",
              "optimizer": "AdamW wd=0.01, linear schedule 10% warmup", "device": device.type,
              "negative_train": neg_binding}
    prior_cfg = md.ROOT / "docs" / "runs" / args.run / "config.json"
    if prior_cfg.is_file() or final.is_file():
        prior = json.loads(prior_cfg.read_text()).get("negative_train") if prior_cfg.is_file() else None
        if prior != neg_binding:
            print("refusing: existing run is bound to a different negative-train configuration", file=sys.stderr)
            return 2
    t0 = time.time()
    if final.is_file():
        info = json.loads(final.read_text())
        print("final checkpoint found; skipping training", flush=True)
        model = AutoModelForTokenClassification.from_pretrained(model_dir).to(device)
    else:
        train_wins, ex = build_windows(tok, train_rows, train_entries, label2id, True)
        config["train_rows_used"] = len({w[3] for w in train_wins}); config["train_rows_excluded_broken"] = ex
        config["train_windows"] = len(train_wins)
        print(json.dumps({k: v for k, v in config.items() if k != "labels"}), flush=True)
        model = AutoModelForTokenClassification.from_pretrained(
            md.MODEL_ID, revision=md.MODEL_REVISION, num_labels=len(labels), id2label=id2label, label2id=label2id).to(device)
        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
        total = args.epochs * ((len(train_wins) + args.batch_size - 1) // args.batch_size)
        warm = max(1, total // 10)
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min((s + 1) / warm, max(0.0, (total - s) / max(1, total - warm))))
        model.train()
        step, t_train = 0, time.time()
        for epoch in range(args.epochs):
            for batch in batches(train_wins, args.batch_size, True, rng):
                ids, att, lab = collate(batch, torch, device)
                loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step(); sched.step(); opt.zero_grad()
                step += 1
                if device.type == "mps" and step % 20 == 0:
                    torch.mps.empty_cache()
                if step == 1 or step % 10 == 0:
                    print("step {}/{} epoch {} loss {:.4f} elapsed_s {:.0f}".format(step, total, epoch + 1, loss.item(), time.time() - t_train), flush=True)
        train_time = time.time() - t_train
        info = {"train_time_s": train_time, "steps": step, "steps_per_sec": step / train_time, "device": device.type,
                "train_windows": len(train_wins), "train_rows_used": config["train_rows_used"],
                "train_rows_excluded_broken": ex}
        model_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(model_dir)
        final.write_text(json.dumps(info, indent=2))  # written last = final-checkpoint marker
    dev = evaluate(model, tok, dev_rows, dev_entries, id2label, device, torch, 32)
    metrics = {"run": args.run, "dev": dev, "train": info, "device": device.type, "eval_time_s": time.time() - t0 - info["train_time_s"] if "train_time_s" in info else None,
               "note": "dev only; strict exact char span + label; test split untouched"}
    config.update({"train_rows_used": info.get("train_rows_used"), "train_rows_excluded_broken": info.get("train_rows_excluded_broken"),
                   "train_windows": info.get("train_windows")})
    for base in (md.ROOT / "results" / args.run, md.ROOT / "docs" / "runs" / args.run):
        base.mkdir(parents=True, exist_ok=True)
        (base / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    (md.ROOT / "docs" / "runs" / args.run / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"dev_overall": dev["overall"], "rows_evaluated": dev["rows_evaluated"]}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
