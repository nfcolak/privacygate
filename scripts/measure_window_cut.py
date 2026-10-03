#!/usr/bin/env python3
"""Aggregate-only measurement: is a span still fully masked when it crosses an actual sliding-window cut?

Dataset: data/augmentation/window-cut-dev.jsonl (git-ignored; scripts/make_window_cut_fixture.py). Cut families
(cut_phone/address/name/identifier) are scored against their matched mid_window control (same values and lengths,
spans far from every cut). Arms mbert / hybrid_union / hybrid_union_refined, one model forward sweep (thr=0.0), scored with
scripts/measure_refine.score (unchanged) and privacygate.masking_metrics (unchanged). Crossing is re-verified here with the
real mbert_data.encode. No text, row IDs, offsets or predicted fragments are written.

  measure_window_cut.py --model-dir D [--dataset P] [--out-dir O]
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import make_window_cut_fixture as fx  # noqa: E402
import measure_masking as mm  # noqa: E402  (imported only)
import measure_refine as mr  # noqa: E402  (imported only)
from privacygate import hybrid, inference, mbert_data, positive_data, refine as refine_mod  # noqa: E402
from privacygate.masking_metrics import MaskingError, SCORER_VERSION, count_chars, interval_union, intersection, validate_spans  # noqa: E402

ARMS = mr.ARMS
DATASET = fx.DATA
OUT = ROOT / "artifacts/runs/masking-coverage/window-cut"
KINDS = ("phone", "address", "name", "identifier")
EXTRA_SOURCES = ("scripts/measure_window_cut.py", "scripts/make_window_cut_fixture.py", "artifacts/window-cut/manifest.json")
NOTE = ("Synthetic and small: 40 cut rows (100 verified crossing spans) and 40 matched control rows. Controls match values, lengths and "
        "total token count, not the surrounding filler wording. Refinement rules were written before this fixture existed but after "
        "stress v1/v2 failure shapes were seen.")


def load_rows():
    raw = positive_data._read_bounded(DATASET)
    committed = json.loads((ROOT / "artifacts/window-cut/manifest.json").read_text(encoding="utf-8"))["dataset"]["sha256"]
    if hashlib.sha256(raw).hexdigest() != committed:
        raise MaskingError("mask_stress_binding")
    try:
        data = [json.loads(line.decode("utf-8"), object_pairs_hook=mm._unique_object) for line in raw.split(b"\n") if line.strip()]
    except MaskingError:
        raise
    except (ValueError, RecursionError):
        raise MaskingError("stress_unparseable") from None
    if not data or any(not isinstance(r, dict) or r.keys() != fx.KEYS or r["split"] != "dev" or r["language"] not in positive_data.LANGS for r in data):
        raise MaskingError("stress_schema")
    for r in data:
        validate_spans(r["gold"], len(r["text"]), gold=True)
        if r["family"] not in fx.CUT_FAMILIES + (fx.CONTROL,):
            raise MaskingError("stress_family")
    binding = {"sha256": committed, "rows": len(data), "split": "dev", "bytes": len(raw), "gold_spans": sum(len(r["gold"]) for r in data)}
    return data, binding


def group_of(row):
    """cut_<kind> for cut rows; mid_<kind> for controls (kind read from the fixed case_id pattern mid_window-<kind>-<lang>-<n>)."""
    if row["family"] == fx.CONTROL:
        return "mid_" + row["case_id"].split("-")[1]
    return row["family"]


def finals(text, model, raw):
    """Same per-arm final masks as measure_refine.score, kept as intervals so crossing spans can be checked."""
    mb = model.spans(raw, thr=0.0)
    rx = hybrid.regex(text)
    union = hybrid.union(rx, mb)
    refined = mr._scorable(refine_mod.refine(text, union))
    out = {}
    for name, spans in (("mbert", mb), ("hybrid_union", union), ("hybrid_union_refined", refined)):
        merged = inference.merge_spans(spans, len(text))
        out[name] = interval_union([(s["start"], s["end"]) for s in merged], len(text))
    return out


def crossing_counts(rows, model, raws, tok):
    """Per arm and group: crossing spans (re-verified with the real encode) and how many are fully masked."""
    res = {name: {} for name in ARMS}
    for row, raw in zip(rows, raws):
        text, gold = row["text"], row["gold"]
        vres, _, _ = fx.verify_row(tok, text, gold, "cut")
        fin = finals(text, model, raw)
        g = group_of(row)
        for name in ARMS:
            d = res[name].setdefault(g, {"crossing_spans": 0, "crossing_fully_masked": 0, "crossing_partial": 0, "crossing_untouched": 0})
            for sp, v in zip(gold, vres):
                if len(v["cut_windows"]) != 1:
                    continue
                cov = count_chars(intersection([(sp["start"], sp["end"])], fin[name], len(text)), len(text))
                d["crossing_spans"] += 1
                d["crossing_fully_masked"] += cov == sp["end"] - sp["start"]
                d["crossing_partial"] += 0 < cov < sp["end"] - sp["start"]
                d["crossing_untouched"] += cov == 0
    return res


def metrics_row(m):
    return {"complete": m["complete_gold_spans"], "total": m["gold_spans"], "partial": m["partial_gold_spans"],
            "untouched": m["untouched_gold_spans"], "exposed_alnum": m["leaked_gold_alnum_chars"], "alnum": m["gold_alnum_chars"],
            "rows": m["rows"], "excess_masked_chars": m["excess_masked_chars"]}


def pool(items):
    keys = ("complete", "total", "partial", "untouched", "exposed_alnum", "alnum", "rows", "excess_masked_chars")
    return {k: sum(i[k] for i in items) for k in keys}


def build_tables(report):
    """table[arm][kind] = {cut: {...}, control: {...}}, plus kind 'all' (pooled)."""
    tables = {}
    for arm in ARMS:
        t = {}
        for kind in KINDS:
            c = dict(metrics_row(report["groups"]["cut_" + kind][arm]), **report["crossing"][arm]["cut_" + kind])
            m = metrics_row(report["groups"]["mid_" + kind][arm])
            t[kind] = {"cut": c, "control": m}
        cut_all = pool([t[k]["cut"] for k in KINDS])
        cut_all.update({k: sum(t[kk]["cut"][k] for kk in KINDS) for k in ("crossing_spans", "crossing_fully_masked", "crossing_partial", "crossing_untouched")})
        t["all"] = {"cut": cut_all, "control": pool([t[k]["control"] for k in KINDS])}
        tables[arm] = t
    return tables


def summary_md(report, binding, tables):
    L = ["# Window-cut measurement: does a sliding-window cut expose personal-information spans?", "",
         "Synthetic development diagnostic; training false, test evaluated false. Annotated-span coverage only; not a privacy guarantee.",
         "Dataset sha256 " + binding["sha256"] + " (" + str(binding["rows"]) + " rows, " + str(binding["gold_spans"]) + " gold spans): 40 cut rows whose gold spans each cross an",
         "actual window end (verified with the real mbert_data.encode: 510 content tokens, step 382, overlap 128) and 40 matched mid_window controls with the",
         "same values and lengths placed fully inside one window's middle (>= " + str(fx.MID_MARGIN_TOKENS) + " tokens from every cut). Model checkpoint sha256 " + mm.EXPECTED_MODEL + ", confidence 0.0,",
         "one forward sweep; scorer masking_union (unchanged). Set is synthetic and small (100 crossing spans, 100 control spans): treat differences of a few spans as noise-prone.", ""]
    for arm in ARMS:
        L += ["## Arm " + arm, "",
              "| family | cut complete | cut partial | cut untouched | cut exposed alnum | crossing spans fully masked | control complete | control partial | control untouched | control exposed alnum |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for kind in KINDS + ("all",):
            c, m = tables[arm][kind]["cut"], tables[arm][kind]["control"]
            name = ("cut_" + kind + " vs mid_window/" + kind) if kind != "all" else "all four pooled"
            L.append("| {} | {}/{} | {} | {} | {}/{} | {}/{} | {}/{} | {} | {} | {}/{} |".format(
                name, c["complete"], c["total"], c["partial"], c["untouched"], c["exposed_alnum"], c["alnum"],
                c["crossing_fully_masked"], c["crossing_spans"], m["complete"], m["total"], m["partial"], m["untouched"], m["exposed_alnum"], m["alnum"]))
        L.append("")
    L += ["## Conclusion", ""]
    for arm in ARMS:
        a = tables[arm]["all"]
        dc, dx = a["cut"]["complete"] - a["control"]["complete"], a["cut"]["exposed_alnum"] - a["control"]["exposed_alnum"]
        verdict = "yes" if dx > 0 else "no"
        L.append("- {}: window cut causes extra exposure: {}. Exposed alnum chars cut {} vs control {} (cut minus control {:+d}); complete spans cut {}/{} vs control {}/{} (cut minus control {:+d}); crossing spans fully masked {}/{}.".format(
            arm, verdict, a["cut"]["exposed_alnum"], a["control"]["exposed_alnum"], dx, a["cut"]["complete"], a["cut"]["total"],
            a["control"]["complete"], a["control"]["total"], dc, a["cut"]["crossing_fully_masked"], a["cut"]["crossing_spans"]))
    L += ["", "Incomplete spans (e.g. names, and addresses in the non-refined arms) are incomplete equally in cut and control rows, so they reflect the checkpoint's label/format limits, not the window cut.",
          "", "Caveats: controls reuse the same invented values and lengths but not identical filler wording; exposure here is annotation-relative. "
          "The set is synthetic and small (10 rows per family, 2-3 spans each, one invented value pool), so it shows whether the mechanism fails visibly, not how often it would on real text.",
          "Details: metrics.json, manifest.json."]
    return "\n".join(L) + "\n"


def execute(args):
    rows, binding = load_rows()
    out = Path(args.out_dir)
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise MaskingError("mask_output_exists") from None
    ns = SimpleNamespace(model_dir=args.model_dir, version="window-cut")
    manifest = mr.manifest_of(ns, binding)
    manifest["dataset_version"] = fx.VERSION
    manifest["note"] = NOTE
    for n in EXTRA_SOURCES:
        manifest["source_sha256"][n] = mm.sha256(ROOT / n)
    wm = json.loads((ROOT / "artifacts/window-cut/manifest.json").read_text(encoding="utf-8"))
    manifest["fixture"] = {"verified_cut_crossing_spans_total": wm["verified_cut_crossing_spans_total"], "windowing": wm["windowing"]}
    mm.json_write(out / "manifest.json", manifest)
    texts = [r["text"] for r in rows]
    tok = mbert_data.load_tokenizer()
    with mm.quiet_libraries():
        model = hybrid.Mbert(Path(args.model_dir), tok=tok)
        raws = model.raw(texts)
    if len(raws) != len(rows):
        raise MaskingError("mask_prediction_count")
    group_idx = {}
    for i, r in enumerate(rows):
        group_idx.setdefault(group_of(r), []).append(i)
    groups = {g: {} for g in sorted(group_idx)}
    for g, idx in sorted(group_idx.items()):
        # family=None: masking_metrics only admits its frozen stress family names; per-group slicing is done here instead.
        sub = [(rows[i]["text"], rows[i]["gold"], rows[i]["language"], None) for i in idx]
        aggs = mr.score(sub, model, [raws[i] for i in idx])
        for name in ARMS:
            groups[g][name] = aggs[name].overall.report()
    total = mr.score([(r["text"], r["gold"], r["language"], None) for r in rows], model, raws)
    crossing = crossing_counts(rows, model, raws, tok)
    for arm in ARMS:
        for g in groups:
            if g.startswith("cut_") and crossing[arm][g]["crossing_spans"] != groups[g][arm]["gold_spans"]:
                raise MaskingError("mask_count_mismatch")
            if g.startswith("cut_") and crossing[arm][g]["crossing_fully_masked"] != groups[g][arm]["complete_gold_spans"]:
                raise MaskingError("mask_count_mismatch")
        if total[arm].overall.counts["rows"] != len(rows):
            raise MaskingError("mask_count_mismatch")
    for n, d in manifest["source_sha256"].items():
        if mm.sha256(mm.source_path(n)) != d:
            raise MaskingError("mask_source_changed")
    report = {**mr.SCOPE, "scorer_version": SCORER_VERSION, "dataset_version": fx.VERSION, "dataset_sha256": binding["sha256"],
              "model_sha256": mm.EXPECTED_MODEL, "rows_evaluated": len(rows), "forward_sweeps": 1,
              "overall": {n: a.overall.report() for n, a in total.items()}, "groups": groups, "crossing": crossing}
    tables = build_tables(report)
    report["tables"] = tables
    mm.json_write(out / "metrics.json", report)
    print("window_cut_complete rows=" + str(len(rows)) + " sweeps=1")
    for arm in ARMS:
        a = tables[arm]["all"]
        print("{} cut complete={}/{} exposed_alnum={} crossing_masked={}/{} | control complete={}/{} exposed_alnum={}".format(
            arm, a["cut"]["complete"], a["cut"]["total"], a["cut"]["exposed_alnum"], a["cut"]["crossing_fully_masked"], a["cut"]["crossing_spans"],
            a["control"]["complete"], a["control"]["total"], a["control"]["exposed_alnum"]))
    return 0


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise MaskingError("mask_arguments")


def main():
    try:
        p = SafeParser(description=__doc__)
        p.add_argument("--model-dir", required=True)
        p.add_argument("--out-dir", default=str(OUT))
        return execute(p.parse_args())
    except MaskingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except ValueError as error:
        print("window_cut_invalid_input" if str(error).startswith("invalid spans") else "mask_validation_failed", file=sys.stderr)
        return 1
    except Exception:
        print("window_cut_operation_failed_input_not_shown", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
