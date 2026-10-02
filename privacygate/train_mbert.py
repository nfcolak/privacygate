"""mBERT BIO token classifier on Micro train; dev-only strict span evaluation. Logs numbers only, never text.

python -m privacygate.train_mbert --run NAME [--max-train-rows N] [--max-dev-rows N] [--epochs E] [--batch-size B] [--lr 3e-5]
"""
import collections
import hashlib
import json
import random
import sys
import time
from pathlib import Path

from . import mbert_data as md
from . import augmentation_data as ad
from . import train_guard as tg


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


def evaluate_development(model, tok, micro_rows, micro_entries, id2label, device, torch, bs,
                         positive_rows=None, positive_entries=None):
    """Two distinct evaluator calls, never pooled. Absent positive dev produces no synthetic result."""
    metrics = {"dev": evaluate(model, tok, micro_rows, micro_entries, id2label, device, torch, bs)}
    if positive_entries is not None:
        metrics["positive_dev"] = evaluate(model, tok, positive_rows, positive_entries, id2label, device, torch, bs)
    return metrics


def main():
    ap = tg.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--max-train-rows", type=int, default=None)
    ap.add_argument("--max-dev-rows", type=int, default=None)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--negative-train-file", type=Path, default=None,
                    help="optional synthetic clean-negative JSONL (split=train); appended after Micro selection")
    ap.add_argument("--positive-train-file", type=Path, default=None,
                    help="optional annotated positive JSONL (exact split=train); adds TRAIN labels/rows after Micro selection")
    ap.add_argument("--positive-dev-file", type=Path, default=None,
                    help="optional annotated positive JSONL (exact split=dev); separate metric only, never training/label discovery")
    ap.add_argument("--out-dir", type=Path, default=md.ROOT / "models", help="parent dir for model checkpoints")
    args = ap.parse_args()

    # Cheap read-only guards BEFORE torch/transformers/corpus/tokenizer/model work.
    try:
        tg.check_run_name(args.run)
        tg.check_settings(args)
        man_bytes = {sp: (md.ROOT / "data/manifests/micro/{}.jsonl".format(sp)).read_bytes() for sp in ("train", "dev")}
        train_entries = ad.manifest_entries(man_bytes["train"])
        dev_entries = ad.manifest_entries(man_bytes["dev"])
        pos_train, pos_train_binding, pos_dev, pos_dev_binding, neg_rows, neg_binding = ad.load_inputs(
            train_entries, dev_entries, args.positive_train_file, args.positive_dev_file, args.negative_train_file)
        model_dir = args.out_dir / args.run
        docs_run_dir, results_run_dir = md.ROOT / "docs" / "runs" / args.run, md.ROOT / "results" / args.run
        identity = tg.build_identity(
            args, md.MODEL_ID, md.MODEL_REVISION, md.MAX_LEN, md.STRIDE,
            hashlib.sha256(man_bytes["train"] + b"\0" + man_bytes["dev"]).hexdigest(), neg_binding, model_dir,
            positive_train=pos_train_binding, positive_dev=pos_dev_binding)
        tg.check_existing(identity, model_dir, docs_run_dir, results_run_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("refused: {}".format(tg.refusal_code(exc)), file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    # Final TRAIN-only inventory check, BEFORE heavy imports, fitting or output writes.
    try:
        train_rows = md.load_rows(train_entries)
        micro_rows_available = len(train_rows)
        labels = ad.training_labels(train_rows, pos_train)
        identity["labels"] = labels
        rng.shuffle(train_entries)
        rng.shuffle(dev_entries)
        if args.max_train_rows:
            train_entries = train_entries[:args.max_train_rows]
        if args.max_dev_rows:
            dev_entries = dev_entries[:args.max_dev_rows]
        micro_train_entries = list(train_entries)
        dev_rows = md.load_rows(dev_entries)
        pos_dev_rows, pos_dev_entries = ad.positive_dataset(pos_dev)
        ad.check_dev_labels(labels, dev_rows, pos_dev_rows)
        state = tg.check_existing(identity, model_dir, docs_run_dir, results_run_dir)
        train_rows, train_entries = ad.assemble_training(train_rows, micro_train_entries, pos_train, neg_rows)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("refused: {}".format(tg.refusal_code(exc)), file=sys.stderr)
        return 2

    if state == "reuse" and all(p.is_file() for p in (
            docs_run_dir / "config.json", docs_run_dir / "metrics.json", results_run_dir / "metrics.json")):
        print("compatible checkpoint and metrics found; skipping training/evaluation; outputs unchanged", flush=True)
        return 0

    import torch
    from transformers import AutoModelForTokenClassification

    md.setup_hf_home()
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    torch.manual_seed(args.seed)
    tok = md.load_tokenizer()
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}

    final = model_dir / "train_info.json"
    config = {"run": args.run, "model": md.MODEL_ID, "model_revision": md.MODEL_REVISION, "epochs": args.epochs,
              "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed, "max_len": md.MAX_LEN,
              "window_stride_tokens": md.STRIDE, "max_train_rows": args.max_train_rows, "max_dev_rows": args.max_dev_rows,
              "label_scheme": "first wordpiece of span B-, later wordpieces I-; specials -100",
              "rows_with_broken_boundary_excluded": True, "labels": labels, "data": "Micro provisional train/dev manifests",
              "optimizer": "AdamW wd=0.01, linear schedule 10% warmup", "device": device.type,
              "micro_train_rows_available": micro_rows_available, "micro_train_rows_selected": len(micro_train_entries),
              "positive_train_rows_included": len(pos_train), "negative_train_rows_included": len(neg_rows),
              "negative_train": neg_binding, "positive_train": pos_train_binding, "positive_dev": pos_dev_binding,
              "positive_schema_version": ad.POSITIVE_SCHEMA_VERSION, "positive_source_version": ad.POSITIVE_SOURCE_VERSION,
              "run_identity": identity}
    t0 = time.time()
    if state == "reuse":
        info = tg._read_json(final)
        print("final checkpoint found; skipping training; only missing outputs may be written", flush=True)
        model = AutoModelForTokenClassification.from_pretrained(model_dir).to(device)
    else:
        train_wins, ex = build_windows(tok, train_rows, train_entries, label2id, True)
        config["train_rows_used"] = len({w[3] for w in train_wins}); config["train_rows_excluded_broken"] = ex
        config["train_row_counts"] = ad.source_counts(micro_train_entries, pos_train, neg_rows, train_wins)
        config["train_windows"] = len(train_wins)
        print(json.dumps({k: v for k, v in config.items() if k != "labels"}), flush=True)
        # Fresh classifier on the pinned BASE model, never retrofitted onto full-1.
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
                "train_rows_excluded_broken": ex, "train_row_counts": config["train_row_counts"],
                "micro_train_rows_available": micro_rows_available, "micro_train_rows_selected": len(micro_train_entries),
                "positive_train_rows_included": len(pos_train), "negative_train_rows_included": len(neg_rows),
                "run_identity": identity}
        model_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(model_dir)
        final.write_text(json.dumps(info, indent=2))  # written last = final-checkpoint marker
    dev_metrics = evaluate_development(
        model, tok, dev_rows, dev_entries, id2label, device, torch, 32,
        pos_dev_rows if args.positive_dev_file is not None else None,
        pos_dev_entries if args.positive_dev_file is not None else None)
    dev = dev_metrics["dev"]
    metrics = {"run": args.run, **dev_metrics, "train": info, "device": device.type, "eval_time_s": time.time() - t0 - info["train_time_s"] if "train_time_s" in info else None,
               "positive_train": pos_train_binding, "positive_dev_input": pos_dev_binding, "run_identity": identity,
               "note": "dev only; strict exact char span + label; test split untouched; positive dev separate, never pooled"}
    config.update({"train_rows_used": info.get("train_rows_used"), "train_rows_excluded_broken": info.get("train_rows_excluded_broken"),
                   "train_windows": info.get("train_windows"), "train_row_counts": info.get("train_row_counts")})
    for base in (results_run_dir, docs_run_dir):
        base.mkdir(parents=True, exist_ok=True)
        path = base / "metrics.json"
        if not path.exists():  # Compatible historical files are immutable too.
            path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    config_path = docs_run_dir / "config.json"
    if not config_path.exists():
        config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    summary = {"dev_overall": dev["overall"], "rows_evaluated": dev["rows_evaluated"]}
    if "positive_dev" in metrics:
        summary["positive_dev"] = metrics["positive_dev"]
    print(json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
