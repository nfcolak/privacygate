"""mBERT BIO token classifier; Micro mode unchanged, opt-in policy-v1 region mode.

python -m privacygate.train_mbert --run NAME [--max-train-rows N] [--max-dev-rows N] [--epochs E] [--batch-size B] [--lr 3e-5]
Region mode: --region-train-file P --region-dev-file P [--region-manifest P].
Dev-only selection/evaluation. Logs numbers only, never text or values.
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
from . import window_alignment as wa


def build_windows(tok, rows, entries, label2id, train, alignment_stats=None):
    """Windows of (ids, label_ids, offs, row_id), with whole-row/full-coverage gates.

    The compatible excluded count includes ALL exclusion reasons, not only broken
    boundaries. Optional aggregate stats distinguish them. Offsets remain intact
    even where gold labels are IGNORE: predictions must never use gold censorship.
    """
    out, excluded = [], 0
    stats = wa.empty_stats()
    for e in entries:
        text, spans, _ = rows[e["row_id"]]
        whole = wa.whole_offsets(tok, text)
        wins = md.encode(tok, text)
        aligned = wa.align_windows(whole, [offs for _, offs in wins], spans)
        stats["windows_discarded_alignment"] += aligned["windows_discarded_alignment"]
        if not aligned["retained"]:
            excluded += 1
            for reason in aligned["reasons"]:
                stats["rows_excluded_by_reason"][reason] += 1
            continue
        stats["gold_spans_retained"] += len(spans)
        stats["gold_spans_fully_covered"] += len(aligned["covered"])
        for window in aligned["windows"]:
            ids, offs = wins[window["source_window_index"]]
            stats["ignored_crossing_tokens_retained"] += window["ignored_crossing_tokens"]
            out.append((ids, [md.IGNORE if l is None else label2id[l] for l in window["labels"]],
                        offs, e["row_id"]))
    if alignment_stats is not None:
        alignment_stats.update(stats)
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
    alignment_stats = {}
    wins, excluded = build_windows(tok, rows, entries, {v: k for k, v in id2label.items()}, False,
                                   alignment_stats=alignment_stats)
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
    return {"rows_evaluated": evaluated, "rows_excluded_broken_boundary": excluded,
            "rows_excluded_by_reason": alignment_stats["rows_excluded_by_reason"],
            "alignment_stats": alignment_stats, "overall": prf(*tot),
            "per_label": {k: prf(*v) for k, v in sorted(per_label.items())},
            "per_language": {k: prf(*v) for k, v in sorted(per_lang.items())}}


def evaluate_development(model, tok, micro_rows, micro_entries, id2label, device, torch, bs,
                         positive_rows=None, positive_entries=None):
    """Two distinct evaluator calls, never pooled. Absent positive dev produces no synthetic result."""
    metrics = {"dev": evaluate(model, tok, micro_rows, micro_entries, id2label, device, torch, bs)}
    if positive_entries is not None:
        metrics["positive_dev"] = evaluate(model, tok, positive_rows, positive_entries, id2label, device, torch, bs)
    return metrics


def evaluate_regions(model, rows, windows, device, torch, bs):
    """Original-gold strict spans and interval-union character coverage on ALL dev rows.

    Unalignable dev gold is counted, never removed from the metric denominator.
    Prediction windows have no gold-conditioned filtering or ignored offsets.
    """
    from . import region_data as rd
    from .masking_metrics import interval_union, intersection
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
    """Separate fresh-base, offline region recipe; never reads Micro or test data."""
    from . import region_data as rd
    try:
        tg.check_run_name(args.run)
        tg.check_settings(args)
        if (args.region_train_file is None or args.region_dev_file is None or
                any(p is not None for p in (args.positive_train_file, args.positive_dev_file,
                                           args.negative_train_file, args.max_train_rows, args.max_dev_rows))):
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
    ap.add_argument("--region-train-file", type=Path, default=None,
                    help="six-field policy-v1 region train JSONL; exclusive of Micro/augmentation mode")
    ap.add_argument("--region-dev-file", type=Path, default=None,
                    help="six-field region dev JSONL; region checkpoint selection only")
    ap.add_argument("--region-manifest", type=Path, default=None,
                    help="optional JSON manifest binding both region files to exact-byte sha256 hashes")
    args = ap.parse_args()
    if any(p is not None for p in (args.region_train_file, args.region_dev_file, args.region_manifest)):
        try:
            return train_regions(args)
        except Exception as exc:
            print("region training failed: {}".format(tg.refusal_code(exc)), file=sys.stderr)
            return 2

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
              "alignment_policy": wa.ALIGNMENT_POLICY, "alignment_source_version": wa.ALIGNMENT_SOURCE_VERSION,
              "exclusion_count_note": "compatible broken-boundary count fields count all excluded rows; reason counts may overlap",
              "prediction_decoding": "strict window-decoded span union; no gold-ignore censorship; partial/duplicate span errors possible",
              "run_identity": identity}
    t0 = time.time()
    if state == "reuse":
        info = tg._read_json(final)
        print("final checkpoint found; skipping training; only missing outputs may be written", flush=True)
        model = AutoModelForTokenClassification.from_pretrained(model_dir).to(device)
    else:
        train_alignment_stats = {}
        train_wins, ex = build_windows(tok, train_rows, train_entries, label2id, True,
                                       alignment_stats=train_alignment_stats)
        config["train_rows_used"] = len({w[3] for w in train_wins}); config["train_rows_excluded_broken"] = ex
        config["train_rows_excluded_by_reason"] = train_alignment_stats["rows_excluded_by_reason"]
        config["train_alignment_stats"] = train_alignment_stats
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
                "train_rows_excluded_by_reason": train_alignment_stats["rows_excluded_by_reason"],
                "train_alignment_stats": train_alignment_stats,
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
                   "train_windows": info.get("train_windows"), "train_row_counts": info.get("train_row_counts"),
                   "train_rows_excluded_by_reason": info.get("train_rows_excluded_by_reason"),
                   "train_alignment_stats": info.get("train_alignment_stats")})
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
