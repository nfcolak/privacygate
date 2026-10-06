"""mBERT BIO region token classifier on six-field policy-v1 region JSONL.

python -m privacygate.training.train_mbert --run NAME --region-train-file P --region-dev-file P
    [--region-manifest P] [--epochs E] [--batch-size B] [--lr 3e-5] [--seed 13] [--out-dir DIR]
Dev-only selection/evaluation. Logs numbers only, never text or values.
"""
import collections
import json
import random
import sys
import time
from pathlib import Path

from privacygate import mbert_data as md
from privacygate.model import train_guard as tg


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


def evaluate_regions(model, rows, windows, device, torch, bs):
    """Original-gold strict spans and interval-union character coverage on ALL dev rows.

    Unalignable dev gold is counted, never removed from the metric denominator.
    Prediction windows have no gold-conditioned filtering or ignored offsets.
    """
    from privacygate.data import region_data as rd
    from privacygate.masking_metrics import interval_union, intersection
    model.eval()
    predictions = collections.defaultdict(set)
    with torch.no_grad():
        for batch in batches(windows, bs, False, None):
            ids, att, _ = collate(batch, torch, device)
            predicted = model(input_ids=ids, attention_mask=att).logits.argmax(-1).cpu().tolist()
            for win, labels in zip(batch, predicted):
                predictions[win[3]] |= md.decode(win[2], [rd.ID2LABEL[i] for i in labels[:len(win[0])]])
    total = [0, 0, 0]
    per_label = {label: [0, 0, 0] for label in rd.REGION_LABELS}
    per_language = collections.defaultdict(lambda: [0, 0, 0])
    gold_chars = predicted_chars = covered_chars = clean_masked_rows = 0
    for row_index, row in enumerate(rows):
        gold = {(s["start"], s["end"], s["label"]) for s in row["gold"]}
        pred = predictions[row_index]
        for span in gold | pred:
            k = 0 if span in gold and span in pred else (1 if span in pred else 2)
            for counts in (total, per_label[span[2]], per_language[row["language"]]):
                counts[k] += 1
        n = len(row["text"])
        gold_union = interval_union([(s, e) for s, e, _ in gold], n)
        pred_union = interval_union([(s, e) for s, e, _ in pred], n)
        gold_chars += sum(e - s for s, e in gold_union)
        predicted_chars += sum(e - s for s, e in pred_union)
        covered_chars += sum(e - s for s, e in intersection(gold_union, pred_union, n))
        clean_masked_rows += not gold and bool(pred_union)
    return {
        "rows_evaluated": len(rows), "windows": len(windows), "overall": prf(*total),
        "per_label": {label: prf(*counts) for label, counts in per_label.items()},
        "per_language": {lang: prf(*counts) for lang, counts in sorted(per_language.items())},
        "character": {"recall": covered_chars / gold_chars if gold_chars else 0.0,
                      "precision": covered_chars / predicted_chars if predicted_chars else 0.0,
                      "gold_chars": gold_chars, "predicted_chars": predicted_chars,
                      "covered_gold_chars": covered_chars},
        "clean_rows": sum(not row["gold"] for row in rows), "clean_masked_rows": clean_masked_rows,
    }


def train_regions(args):
    """Fresh-base, offline region recipe; never reads test data."""
    from privacygate.data import region_data as rd
    try:
        tg.check_run_name(args.run)
        tg.check_settings(args)
        if args.region_train_file is None or args.region_dev_file is None:
            raise ValueError("region_mode_arguments")
        train_rows, train_binding = rd.load_region_file(args.region_train_file, "train", args.region_manifest)
        dev_rows, dev_binding = rd.load_region_file(args.region_dev_file, "dev", args.region_manifest)
        rd.check_disjoint(train_rows, dev_rows)
        model_dir = args.out_dir / args.run
        identity = tg.build_region_identity(args, md.MODEL_ID, md.MODEL_REVISION, md.MAX_LEN, md.STRIDE,
                                            rd.LABELS, train_binding, dev_binding, model_dir)
        state = tg.check_region_existing(identity, model_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("refused: {}".format(tg.refusal_code(exc)), file=sys.stderr)
        return 2
    if state == "reuse":
        print("compatible region checkpoint found; outputs unchanged", flush=True)
        return 0

    # Set offline mode before importing the HF stack, regardless of caller environment.
    import os
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    md.setup_hf_home()
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    tok = AutoTokenizer.from_pretrained(md.MODEL_ID, revision=md.MODEL_REVISION,
                                        use_fast=True, local_files_only=True)
    train_windows, train_alignment = rd.build_windows(tok, train_rows)
    _, dev_alignment = rd.build_windows(tok, dev_rows)
    if not train_windows:
        raise ValueError("region_empty_windows")
    # Preserve every actual prediction window, including unalignable gold rows.
    dev_windows = [(ids, [md.IGNORE] * len(ids), offsets, row_index)
                   for row_index, row in enumerate(dev_rows) for ids, offsets in md.encode(tok, row["text"])]
    model = AutoModelForTokenClassification.from_pretrained(
        md.MODEL_ID, revision=md.MODEL_REVISION, local_files_only=True,
        num_labels=len(rd.LABELS), id2label=rd.ID2LABEL, label2id=rd.LABEL2ID).to(device)
    model.config.privacygate_training_mode = "region"
    model.config.privacygate_region_schema = rd.SCHEMA_VERSION
    model.config.privacygate_region_labels = list(rd.REGION_LABELS)
    # Atomically reserve a new directory: even a concurrently created Micro run
    # cannot be overwritten between preflight and the first region checkpoint save.
    try:
        model_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise ValueError("run_output_path_invalid") from None
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total = args.epochs * ((len(train_windows) + args.batch_size - 1) // args.batch_size)
    warm = max(1, total // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min((s + 1) / warm, max(0.0, (total - s) / max(1, total - warm))))
    print(json.dumps({"mode": "region", "train_rows": len(train_rows), "dev_rows": len(dev_rows),
                      "train_windows": len(train_windows), "train_rows_excluded": train_alignment["rows_excluded"],
                      "dev_rows_unalignable": dev_alignment["rows_excluded"],
                      "steps": total, "device": device.type, "num_labels": len(rd.LABELS)}), flush=True)
    step, train_time, evaluation_time, save_time = 0, 0.0, 0.0, 0.0
    best_key, selected_epoch, best_dev, history = None, None, None, []
    for epoch in range(args.epochs):
        model.train()
        if device.type == "mps":
            torch.mps.synchronize()
        start = time.perf_counter()
        for batch in batches(train_windows, args.batch_size, True, rng):
            ids, att, gold = collate(batch, torch, device)
            loss = model(input_ids=ids, attention_mask=att, labels=gold).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            step += 1
            if device.type == "mps" and step % 20 == 0:
                torch.mps.empty_cache()
            if step == 1 or step % 10 == 0 or step == total:
                print("region step {}/{} epoch {} loss {:.4f}".format(step, total, epoch + 1, loss.item()), flush=True)
        if device.type == "mps":
            torch.mps.synchronize()
        train_time += time.perf_counter() - start
        start = time.perf_counter()
        dev = evaluate_regions(model, dev_rows, dev_windows, device, torch, args.batch_size)
        evaluation_time += time.perf_counter() - start
        key = (dev["overall"]["f1"], dev["character"]["recall"])
        history.append({"epoch": epoch + 1, "overall": dev["overall"], "character": dev["character"]})
        print(json.dumps({"epoch": epoch + 1, "region_dev": history[-1]}), flush=True)
        if best_key is None or key > best_key:
            best_key, selected_epoch, best_dev = key, epoch + 1, dev
            start = time.perf_counter()
            # Only the guarded fresh region directory can be written by this recipe.
            model_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(model_dir)
            tok.save_pretrained(model_dir)
            save_time += time.perf_counter() - start
    assert best_dev is not None and selected_epoch is not None
    info = {
        "mode": "region", "model": md.MODEL_ID, "model_revision": md.MODEL_REVISION,
        "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed,
        "max_len": md.MAX_LEN, "window_stride_tokens": md.STRIDE,
        "labels": rd.LABELS, "region_labels": list(rd.REGION_LABELS), "device": device.type,
        "train_rows": len(train_rows), "dev_rows": len(dev_rows),
        "train_rows_used": train_alignment["rows_used"], "train_rows_excluded": train_alignment["rows_excluded"],
        "train_windows": len(train_windows), "dev_windows": len(dev_windows),
        "train_alignment_stats": train_alignment, "dev_alignment_stats": dev_alignment,
        "steps": step, "train_time_s": train_time, "steps_per_sec": step / train_time,
        "eval_time_s": evaluation_time, "save_time_s": save_time, "selected_epoch": selected_epoch,
        "selection": identity["selection"],
        "data_sha256s": {"train": train_binding["sha256"], "dev": dev_binding["sha256"]},
        "run_identity": identity,
        "note": "Region rows only; fresh pinned base; all dev gold scored, including unalignable rows; no test split.",
    }
    metrics = {"run": args.run, "mode": "region", "dev": best_dev, "epochs": history,
               "run_identity": identity, "selected_epoch": selected_epoch}
    (model_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    # Final-checkpoint marker: written last, only after weights/tokenizer/metrics exist.
    (model_dir / "train_info.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"steps": step, "steps_per_sec": info["steps_per_sec"],
                      "selected_epoch": selected_epoch, "dev_overall": best_dev["overall"],
                      "character": best_dev["character"]}), flush=True)
    return 0


def main():
    ap = tg.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out-dir", type=Path, default=md.ROOT / "models", help="parent dir for model checkpoints")
    ap.add_argument("--region-train-file", type=Path, required=True,
                    help="six-field policy-v1 region train JSONL")
    ap.add_argument("--region-dev-file", type=Path, required=True,
                    help="six-field region dev JSONL; region checkpoint selection only")
    ap.add_argument("--region-manifest", type=Path, default=None,
                    help="optional JSON manifest binding both region files to exact-byte sha256 hashes")
    args = ap.parse_args()
    try:
        return train_regions(args)
    except Exception as exc:
        print("region training failed: {}".format(tg.refusal_code(exc)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
