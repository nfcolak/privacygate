#!/usr/bin/env python3
"""Offline train/dev alignment diagnosis; aggregates and hashed set bindings only.

No model loading, inference, training, test manifest access, or historical writes.
The candidate below is diagnostic code, not a replacement training/scoring path.
"""
import argparse
import collections
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from privacygate import mbert_data as md  # noqa: E402

OUT = ROOT / "artifacts/data-audit/micro/diagnosis"


def legacy_build_windows(tok, rows, entries, label2id, train):
    """Frozen e69fcd8 window helper, for ORIGINAL-behaviour replay only.

    Production construction has changed. Never relabel new behaviour as the
    original diagnostic or use this legacy helper for new training/evaluation.
    """
    out, excluded = [], 0
    for e in entries:
        text, spans, _ = rows[e["row_id"]]
        wins = md.encode(tok, text)
        aligned = [md.align(offs, spans) for _, offs in wins]
        if any(a[1] or a[2] for a in aligned):
            excluded += 1
            continue
        for (ids, offs), (labs, _, _) in zip(wins, aligned):
            out.append((ids, [md.IGNORE if l is None else label2id[l] for l in labs], offs, e["row_id"]))
    return out, excluded


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def binding(values):
    """No individual IDs are persisted, even though input IDs are already hashes."""
    values = sorted(set(values))
    payload = json.dumps(values, separators=(",", ":")).encode("utf-8")
    return {"count": len(values), "sha256": hashlib.sha256(payload).hexdigest()}


def safe_offsets(offsets):
    return [None if a == b == 0 else (a, b) for a, b in offsets]


def window_geometry(offsets, spans):
    real = [o for o in offsets if o is not None]
    if not real:
        return [], list(range(len(spans))), []
    lo, hi = min(o[0] for o in real), max(o[1] for o in real)
    inside, outside, crossing = [], [], []
    for j, (start, end, _) in enumerate(spans):
        if end <= lo or start >= hi:
            outside.append(j)
        elif start >= lo and end <= hi:
            inside.append(j)
        else:
            crossing.append(j)
    return inside, outside, crossing


def candidate(whole_offsets, windows, spans):
    """Whole-row gate; ignore partial spans, require full gold-span coverage.

    Outside spans are irrelevant to a window (not lost). Crossing-span tokens
    are None/-100, never O. Special tokens are None. Overlapping annotations
    and incomplete row-level coverage fail closed; no gold spans are repaired.
    """
    _, broken, lost = md.align(whole_offsets, spans)
    if broken or lost:
        return {"retained": False, "reason": "whole_row_alignment", "windows": [], "covered": set()}
    ordered = sorted(spans)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        return {"retained": False, "reason": "overlapping_gold", "windows": [], "covered": set()}
    retained, covered = [], set()
    for window_index, offsets in enumerate(windows):
        inside, outside, crossing = window_geometry(offsets, spans)
        labels, window_broken, window_lost = md.align(offsets, [spans[j] for j in inside])
        if window_broken or window_lost:
            continue
        ignored_crossing = set()
        for j in crossing:
            start, end, _ = spans[j]
            for i, o in enumerate(offsets):
                if o is not None and o[0] < end and o[1] > start:
                    labels[i] = None
                    ignored_crossing.add(i)
        # For disjoint gold spans, ignoring a crossing span cannot erase a
        # contained span. Still prove coverage from actual labels, not geometry.
        effective_inside = set()
        for j in inside:
            start, end, lab = spans[j]
            idx = [i for i, o in enumerate(offsets) if o is not None and o[0] < end and o[1] > start]
            expected = [("B-" if k == 0 else "I-") + lab for k in range(len(idx))]
            if idx and [labels[i] for i in idx] == expected:
                effective_inside.add(j)
        covered.update(effective_inside)
        retained.append({"labels": labels, "inside": effective_inside, "outside": outside,
                         "crossing": crossing, "ignored_crossing_tokens": len(ignored_crossing),
                         "source_window_index": window_index})
    if not retained or len(covered) != len(spans):
        return {"retained": False, "reason": "incomplete_gold_coverage", "windows": [], "covered": covered}
    return {"retained": True, "reason": None, "windows": retained, "covered": covered}


def synthetic_checks():
    # Hand-built character offsets; no corpus/example text or personal values.
    whole = [None, (0, 2), (2, 4), (4, 6), (6, 8), None]
    left = [None, (0, 2), (2, 4), None]
    right = [None, (4, 6), (6, 8), None]
    bridge = [None, (2, 4), (4, 6), None]
    checks = {}
    outside = candidate(whole, [left, right], [(6, 8, "X")])
    checks["outside_not_lost_or_excluded"] = outside["retained"] and outside["windows"][0]["labels"] == [None, "O", "O", None]
    checks["historical_outside_was_lost"] = md.align(left, [(6, 8, "X")])[2] == 1
    broken = candidate(whole, [left, right], [(1, 2, "X")])
    checks["genuine_whole_row_broken_excluded"] = not broken["retained"] and broken["reason"] == "whole_row_alignment"
    checks["whole_row_missing_span_excluded"] = not candidate(whole, [left, right], [(8, 10, "X")])["retained"]
    partial = candidate(whole, [left, bridge, right], [(2, 6, "X")])
    checks["crossing_segments_ignored_not_clean"] = partial["retained"] and partial["windows"][0]["labels"][2] is None and partial["windows"][2]["labels"][1] is None
    checks["covered_in_overlap_window"] = partial["retained"] and partial["covered"] == {0} and partial["windows"][1]["labels"] == [None, "B-X", "I-X", None]
    checks["historical_cut_was_broken"] = md.align(left, [(2, 6, "X")])[1] == 1
    uncovered = candidate(whole, [left, right], [(2, 6, "X")])
    checks["uncovered_crossing_row_excluded"] = not uncovered["retained"] and uncovered["reason"] == "incomplete_gold_coverage"
    huge = candidate(whole, [left, bridge, right], [(0, 8, "X")])
    checks["span_larger_than_all_windows_excluded"] = not huge["retained"] and huge["reason"] == "incomplete_gold_coverage"
    checks["touching_cut_is_outside_not_crossing"] = window_geometry(left, [(4, 6, "X")]) == ([], [0], [])
    checks["overlapping_gold_fails_closed"] = not candidate(whole, [whole], [(0, 4, "X"), (2, 6, "Y")])["retained"]
    negative = candidate(whole, [left, right], [])
    checks["empty_gold_window_remains_clean"] = negative["retained"] and all(l in (None, "O") for w in negative["windows"] for l in w["labels"])
    checks["special_tokens_ignored"] = partial["retained"] and all(w["labels"][0] is None and w["labels"][-1] is None for w in partial["windows"])
    return {"checks": checks, "passed": sum(checks.values()), "total": len(checks), "all_passed": all(checks.values())}


def diagnose_split(tok, split, history):
    entries = md.manifest(split)  # split is restricted to train/dev by argparse
    ids = [e["row_id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_manifest_ids")
    rows = md.load_rows(entries, raw_dir=md.RAW_DIR)
    sets = {k: set() for k in (
        "requested", "whole_broken", "whole_lost", "whole_excluded", "long",
        "original_excluded", "original_retained", "outside_any_window", "crossing_window_extent_any",
        "original_window_broken", "original_window_lost", "candidate_retained",
        "candidate_excluded", "candidate_incomplete_coverage", "candidate_overlapping_gold",
        "candidate_window_alignment_failure", "original_extra_excluded", "original_missing_excluded",
        "extra_excluded_with_outside", "extra_excluded_with_crossing", "extra_excluded_outside_only",
        "extra_excluded_crossing_only", "unexplained_window_error", "unexplained_extra", "unexplained_missing",
    )}
    counts = collections.Counter({k: 0 for k in (
        "rows", "spans", "wordpieces_including_specials", "unk_wordpieces", "whole_broken_spans", "whole_lost_spans",
        "original_windows_total", "original_windows_retained", "original_window_broken_span_events",
        "original_window_lost_span_events", "outside_window_span_events", "window_extent_crossing_span_events",
        "candidate_windows_retained", "candidate_windows_discarded", "candidate_ignored_crossing_tokens",
        "candidate_gold_spans_retained", "candidate_gold_spans_fully_covered", "candidate_gold_spans_excluded",
        "candidate_uncovered_gold_spans_before_row_rejection", "original_gold_spans_retained",
        "original_gold_spans_fully_covered", "original_gold_support_deduplicated",
        "candidate_crossing_span_events_retained", "candidate_outside_span_events_retained",
        "candidate_crossing_tokens_incorrectly_clean", "whole_broken_rows_retained_by_candidate",
    )})
    for entry in entries:
        rid = entry["row_id"]
        text, spans, _ = rows[rid]
        sets["requested"].add(rid)
        enc = tok(text, return_offsets_mapping=True, add_special_tokens=True, truncation=False, verbose=False)
        whole = safe_offsets(enc["offset_mapping"])
        _, broken, lost = md.align(whole, spans)
        counts.update(rows=1, spans=len(spans), wordpieces_including_specials=len(enc["input_ids"]),
                      unk_wordpieces=sum(i == tok.unk_token_id for i in enc["input_ids"]),
                      whole_broken_spans=broken, whole_lost_spans=lost)
        if broken:
            sets["whole_broken"].add(rid)
        if lost:
            sets["whole_lost"].add(rid)
        if broken or lost:
            sets["whole_excluded"].add(rid)
        if len(enc["input_ids"]) > md.MAX_LEN:
            sets["long"].add(rid)
        wins = md.encode(tok, text)
        offsets = [o for _, o in wins]
        counts["original_windows_total"] += len(wins)
        original_covered = set()
        for o in offsets:
            inside, outside, crossing = window_geometry(o, spans)
            _, wb, wl = md.align(o, spans)
            counts.update(original_window_broken_span_events=wb, original_window_lost_span_events=wl,
                          outside_window_span_events=len(outside), window_extent_crossing_span_events=len(crossing))
            original_covered.update(inside)
            if not (broken or lost):
                crossing_with_tokens = sum(any(off is not None and off[0] < spans[j][1] and off[1] > spans[j][0] for off in o) for j in crossing)
                expected_broken = crossing_with_tokens
                expected_lost = len(outside) + len(crossing) - crossing_with_tokens
                if wb != expected_broken or wl != expected_lost:
                    sets["unexplained_window_error"].add(rid)
                _, contained_broken, contained_lost = md.align(o, [spans[j] for j in inside])
                if contained_broken or contained_lost:
                    sets["candidate_window_alignment_failure"].add(rid)
            for key, value in (("outside_any_window", outside), ("crossing_window_extent_any", crossing),
                               ("original_window_broken", wb), ("original_window_lost", wl)):
                if value:
                    sets[key].add(rid)
        label2id = {name: i for i, name in enumerate(["O"] + sorted({p + lab for _, _, lab in spans for p in ("B-", "I-")}))}
        # Replay the explicitly frozen original helper, not new production semantics.
        # This is label construction, not model evaluation.
        old_windows, old_excluded = legacy_build_windows(tok, {rid: rows[rid]}, [entry], label2id, split == "train")
        derived_excluded = rid in sets["original_window_broken"] or rid in sets["original_window_lost"]
        if bool(old_excluded) != derived_excluded:
            raise ValueError("production_exclusion_replay_mismatch")
        sets["original_excluded" if old_excluded else "original_retained"].add(rid)
        if not old_excluded:
            counts.update(original_windows_retained=len(old_windows), original_gold_spans_retained=len(spans),
                          original_gold_spans_fully_covered=len(original_covered),
                          original_gold_support_deduplicated=len(set(spans)))
        new = candidate(whole, offsets, spans)
        if new["retained"]:
            sets["candidate_retained"].add(rid)
            counts.update(candidate_windows_retained=len(new["windows"]),
                          candidate_windows_discarded=len(wins) - len(new["windows"]),
                          candidate_gold_spans_retained=len(spans), candidate_gold_spans_fully_covered=len(new["covered"]),
                          whole_broken_rows_retained_by_candidate=int(bool(broken)))
            for w in new["windows"]:
                o = offsets[w["source_window_index"]]
                counts.update(candidate_ignored_crossing_tokens=w["ignored_crossing_tokens"],
                              candidate_crossing_span_events_retained=len(w["crossing"]),
                              candidate_outside_span_events_retained=len(w["outside"]))
                for j in w["crossing"]:
                    start, end, _ = spans[j]
                    for i, off in enumerate(o):
                        if off is not None and off[0] < end and off[1] > start and w["labels"][i] is not None:
                            counts["candidate_crossing_tokens_incorrectly_clean"] += 1
        else:
            sets["candidate_excluded"].add(rid)
            counts["candidate_gold_spans_excluded"] += len(spans)
            if new["reason"] == "incomplete_gold_coverage":
                sets["candidate_incomplete_coverage"].add(rid)
                counts["candidate_uncovered_gold_spans_before_row_rejection"] += len(spans) - len(new["covered"])
            elif new["reason"] == "overlapping_gold":
                sets["candidate_overlapping_gold"].add(rid)

    extra = sets["original_excluded"] - sets["whole_excluded"]
    missing = sets["whole_excluded"] - sets["original_excluded"]
    sets["original_extra_excluded"] = extra
    sets["original_missing_excluded"] = missing
    sets["extra_excluded_with_outside"] = extra & sets["outside_any_window"]
    sets["extra_excluded_with_crossing"] = extra & sets["crossing_window_extent_any"]
    sets["extra_excluded_outside_only"] = extra & sets["outside_any_window"] - sets["crossing_window_extent_any"]
    sets["extra_excluded_crossing_only"] = extra & sets["crossing_window_extent_any"] - sets["outside_any_window"]
    sets["unexplained_extra"] = (extra - (sets["outside_any_window"] | sets["crossing_window_extent_any"])) | (extra & sets["unexplained_window_error"])
    sets["unexplained_missing"] = missing
    count_keys = {"rows": "rows", "spans": "spans", "spans_boundary_inside_wordpiece": "whole_broken_spans",
                  "spans_lost": "whole_lost_spans", "wordpieces": "wordpieces_including_specials", "unk_wordpieces": "unk_wordpieces"}
    observed = {h: counts[k] for h, k in count_keys.items()}
    observed.update(rows_excluded=len(sets["whole_excluded"]), rows_with_broken_boundary=len(sets["whole_broken"]),
                    rows_with_lost_span=len(sets["whole_lost"]), rows_longer_than_max_len=len(sets["long"]))
    historical_alignment = history["alignment"]["splits"][split]
    audit_deltas = {k: observed[k] - historical_alignment[k] for k in observed}
    expected_excluded = history["full"]["train"]["train_rows_excluded_broken"] if split == "train" else history["full"]["dev"]["rows_excluded_broken_boundary"]
    expected_retained = history["full"]["train"]["train_rows_used"] if split == "train" else history["full"]["dev"]["rows_evaluated"]
    replay_deltas = {"excluded_rows": len(sets["original_excluded"]) - expected_excluded,
                     "retained_rows": len(sets["original_retained"]) - expected_retained}
    if split == "train":
        replay_deltas["retained_windows"] = counts["original_windows_retained"] - history["full"]["train"]["train_windows"]
    else:
        replay_deltas.update(compare_excluded_rows=len(sets["original_excluded"]) - history["compare"]["micro_rows_excluded_broken_boundary"],
                             compare_retained_rows=len(sets["original_retained"]) - history["compare"]["micro_rows_evaluated"],
                             gold_support=counts["original_gold_support_deduplicated"] - history["full"]["dev"]["overall"]["support"])
    reproduced = not any(audit_deltas.values()) and not any(replay_deltas.values())
    explained = not sets["unexplained_extra"] and not sets["unexplained_missing"]
    candidate_invariants = {"broken_rows_not_retained": not (sets["whole_broken"] & sets["candidate_retained"]),
                            "whole_excluded_rows_not_retained": not (sets["whole_excluded"] & sets["candidate_retained"]),
                            "all_retained_gold_fully_covered": counts["candidate_gold_spans_retained"] == counts["candidate_gold_spans_fully_covered"],
                            "crossing_tokens_never_clean": counts["candidate_crossing_tokens_incorrectly_clean"] == 0}
    return {"counts": dict(sorted(counts.items())), "row_sets": {k: binding(v) for k, v in sorted(sets.items())},
            "historical_reconciliation": {"status": "reproduced_and_explained" if reproduced and explained else "unresolved",
                                          "alignment_count_deltas": audit_deltas, "full_and_compare_count_deltas": replay_deltas,
                                          "original_minus_whole_excluded": len(extra), "whole_minus_original_excluded": len(missing)},
            "candidate_invariants": candidate_invariants}


def execute(splits):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    main = md.RAW_DIR.parents[2]
    hf_home = Path(os.environ.get("HF_HOME", str(main / ".cache/hf")))
    os.environ["HF_HOME"] = str(hf_home)
    snapshot = hf_home / "hub" / ("models--" + md.MODEL_ID.replace("/", "--")) / "snapshots" / md.MODEL_REVISION
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(snapshot, use_fast=True, local_files_only=True, trust_remote_code=False)
    if not tok.is_fast:
        raise ValueError("fast_tokenizer_required")
    paths = {
        "alignment": ROOT / "artifacts/data-audit/micro/alignment.json",
        "full": ROOT / "artifacts/runs/full-1/metrics.json",
        "compare": ROOT / "artifacts/runs/compare-dev/metrics.json",
        "config": ROOT / "artifacts/runs/full-1/config.json",
        "source": ROOT / "artifacts/data-audit/micro/source.json",
    }
    history = {k: json.loads(p.read_text()) for k, p in paths.items()}
    config = history["config"]
    for settings in (history["alignment"], config):
        if (settings["model"], settings["model_revision"], settings["max_len"], settings["window_stride_tokens"]) != (md.MODEL_ID, md.MODEL_REVISION, md.MAX_LEN, md.STRIDE):
            raise ValueError("historical_settings_mismatch")
    source = history["source"]
    if (source["repo_id"], source["revision"]) != (md.MICRO_REPO, md.MICRO_REVISION):
        raise ValueError("raw_source_pin_mismatch")
    raw_files = {art["path"]: md.RAW_DIR / art["path"] for art in source["artifacts"] if "split" in art}
    raw_hashes = {k: file_hash(p) for k, p in raw_files.items()}
    if any(raw_hashes[art["path"]] != art["sha256"] or raw_files[art["path"]].stat().st_size != art["bytes"] for art in source["artifacts"] if "split" in art):
        raise ValueError("raw_source_integrity_mismatch")
    protected = dict(paths)
    protected.update({"manifest_" + split: ROOT / ("data/manifests/micro/" + split + ".jsonl") for split in splits})
    protected.update({"script_" + name: ROOT / name for name in ("scripts/check_alignment.py", "privacygate/train_mbert.py", "privacygate/mbert_data.py", "scripts/compare.py")})
    protected_hashes = {k: file_hash(p) for k, p in protected.items()}
    assets = {name: snapshot / name for name in ("tokenizer_config.json", "tokenizer.json", "vocab.txt", "config.json") if (snapshot / name).is_file()}
    asset_hashes = {k: file_hash(p) for k, p in assets.items()}
    fixtures = synthetic_checks()
    if not fixtures["all_passed"]:
        raise ValueError("synthetic_checks_failed")
    results = {split: diagnose_split(tok, split, history) for split in splits}
    unchanged = (all(file_hash(p) == protected_hashes[k] for k, p in protected.items())
                 and all(file_hash(p) == asset_hashes[k] for k, p in assets.items())
                 and all(file_hash(p) == raw_hashes[k] for k, p in raw_files.items()))
    if not unchanged:
        raise ValueError("read_only_inputs_changed")
    result = {
        "schema_version": 1,
        "scope": {"splits": splits, "test_manifest_loaded": False, "model_loaded": False,
                  "model_evaluated": False, "training_performed": False, "network_used": False,
                  "annotation_review": "automated structural checks only; no human semantic review"},
        "settings": {"model": md.MODEL_ID, "model_revision": md.MODEL_REVISION,
                     "dataset": md.MICRO_REPO, "dataset_revision": md.MICRO_REVISION,
                     "max_len": md.MAX_LEN, "window_overlap_tokens": md.STRIDE,
                     "tokenizer": type(tok).__name__, "cached_snapshot_local_only": True,
                     "whole_row_special_tokens": True, "original_helper_replayed": "diagnose_alignment.legacy_build_windows (frozen e69fcd8)"},
        "bindings": {"protected_files_sha256": protected_hashes, "raw_artifacts_sha256": raw_hashes,
                     "tokenizer_assets_sha256": asset_hashes,
                     "set_hash_scheme": "sha256(UTF-8 compact JSON array of sorted unique manifest row IDs); individual IDs never persisted"},
        "synthetic_window_fixtures": fixtures, "splits": results,
        "read_only_inputs_unchanged": unchanged,
        "limitations": ["No human annotation review or semantic correctness conclusion.",
                        "Split/provenance and complete personal-information coverage gates remain open.",
                        "Candidate is label/coverage diagnosis only, not a trained model or a new scorer.",
                        "Changed row selection invalidates direct comparison against historical F1; future scoring must use identical retained dev IDs and one new scorer for both models."],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "aggregate.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return {"status": "completed", "synthetic_window_fixtures": fixtures,
            "splits": {split: {"reconciliation": r["historical_reconciliation"],
                               "row_set_counts": {k: v["count"] for k, v in r["row_sets"].items()},
                               "candidate_invariants": r["candidate_invariants"]} for split, r in results.items()},
            "read_only_inputs_unchanged": unchanged}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "dev"), action="append", help="requested manifest; default both train and dev")
    args = parser.parse_args()
    # Suppress ALL dependency stdout/stderr and exception strings: offsets,
    # corpus fragments, paths containing values, and IDs must never leak.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = execute(sorted(set(args.split or ("train", "dev"))))
    except Exception:
        print(json.dumps({"status": "failed", "error": "offline_alignment_diagnosis_failed"}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
