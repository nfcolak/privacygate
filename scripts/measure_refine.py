#!/usr/bin/env python3
"""Aggregate-only measurement of rule-based span refinement (arms: mbert, hybrid_union, hybrid_union_refined).

Reuses privacygate.masking_metrics (unchanged scoring) and the exact mBERT path of scripts/measure_masking.py
(hybrid.Mbert, one forward sweep per dataset, thr=0.0). Does not modify measure_masking.py or frozen run dirs.
No text, row IDs, offsets or predicted fragments are written.

Scoring adaptation: masking_metrics only admits model labels for predictions, so the ADDRESS label produced by
refinement is mapped to STREET for scoring input only. All reported metrics are class-agnostic interval-union
coverage and are unaffected; label-dependent diagnostics (raw/final exact-label classes) are NOT used for the
refined arm.

  measure_refine.py --dataset P --version v1|v2|v3 --model-dir D --out-dir O
  measure_refine.py --summary          # write docs/runs/masking-coverage/refine-summary.md from both runs
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import measure_masking as mm  # noqa: E402  (imported only; not modified)
from privacygate import hybrid, inference, mbert_data, positive_data, refine as refine_mod  # noqa: E402
from privacygate.masking_metrics import DEFINITIONS, EngineAggregate, MaskingError, SCORER_VERSION, validate_spans  # noqa: E402

ARMS = ("mbert", "hybrid_union", "hybrid_union_refined")
RUNS = ROOT / "docs/runs/masking-coverage"
SOURCES = (
    "privacygate/masking_metrics.py", "privacygate/refine.py", "privacygate/hybrid.py", "privacygate/inference.py",
    "privacygate/detect.py", "privacygate/mbert_data.py", "scripts/measure_refine.py", "scripts/measure_masking.py",
    "scripts/make_masking_stress.py", "scripts/make_masking_stress_v2.py", "scripts/make_masking_stress_v3.py",
    "docs/masking-stress/manifest.json", "docs/masking-stress-v2/manifest.json", "docs/masking-stress-v3/manifest.json",
)
SCOPE = {"test_evaluated": False, "training": False, "scoring_scope": "development_diagnostic"}


def load_rows(path, version):
    if version == "v1":
        rows, binding = mm.load_dataset(path, "stress")  # enforces the frozen v1 sha/shape
        return rows, binding
    raw = positive_data._read_bounded(path)
    manifest_path = ROOT / ("docs/masking-stress-v3/manifest.json" if version == "v3" else "docs/masking-stress-v2/manifest.json")
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))["dataset"]["sha256"]
    if hashlib.sha256(raw).hexdigest() != expected:
        raise MaskingError("mask_stress_binding")
    try:
        data = [json.loads(line.decode("utf-8"), object_pairs_hook=mm._unique_object) for line in raw.split(b"\n") if line.strip()]
    except MaskingError:
        raise
    except (ValueError, RecursionError):
        raise MaskingError("stress_unparseable") from None
    mm.check_stress_rows(data)
    binding = {"sha256": expected, "rows": len(data), "split": "dev", "bytes": len(raw),
               "positive_rows": sum(bool(r["gold"]) for r in data), "clean_rows": sum(not r["gold"] for r in data),
               "gold_spans": sum(len(r["gold"]) for r in data)}
    return [(r["text"], r["gold"], r["language"], r["family"]) for r in data], binding


def _scorable(spans):
    # Scoring input only: ADDRESS is not a model label in masking_metrics.LABELS; coverage ignores labels.
    return [{"start": s["start"], "end": s["end"], "label": "STREET" if s["label"] == "ADDRESS" else s["label"]} for s in spans]


def score(rows, model, raws):
    aggs = {name: EngineAggregate() for name in ARMS}
    for (text, gold, language, family), raw in zip(rows, raws):
        mb = model.spans(raw, thr=0.0)
        rx = hybrid.regex(text)
        validate_spans(rx, len(text))
        validate_spans(mb, len(text))
        union = hybrid.union(rx, mb)
        refined = _scorable(refine_mod.refine(text, union))
        cand = {"mbert": mb, "hybrid_union": rx + mb, "hybrid_union_refined": refined}
        final = {
            "mbert": inference.merge_spans(mb, len(text)),
            "hybrid_union": inference.merge_spans(union, len(text)),
            "hybrid_union_refined": inference.merge_spans(refined, len(text)),
        }
        for name in ARMS:
            aggs[name].add(text, gold, language, cand[name], final[name], family=family)
    return aggs


def manifest_of(args, binding):
    frozen_refine_sha256 = "5fcfa1e688140e0ba72c3980523c5114df98a97fe8329a4dcee51abb9d6dfdaf"
    if args.version == "v3" and mm.sha256(ROOT / "privacygate/refine.py") != frozen_refine_sha256:
        raise MaskingError("mask_v3_rules_not_frozen")
    model_dir = Path(args.model_dir)
    files = {n: mm.sha256(model_dir / n) for n in ("config.json", "model.safetensors", "train_info.json")}
    if files["model.safetensors"] != mm.EXPECTED_MODEL:
        raise MaskingError("mask_model_binding")
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1" or not os.environ.get("HF_HOME"):
        raise MaskingError("mask_offline_required")
    snap = Path(os.environ["HF_HOME"]) / "hub" / "models--google-bert--bert-base-multilingual-cased" / "snapshots" / mbert_data.MODEL_REVISION
    return {
        **SCOPE, "scorer_version": SCORER_VERSION, "dataset_version": args.version, "dataset": binding,
        "model_sha256": mm.EXPECTED_MODEL, "checkpoint_file_sha256": files,
        "tokenizer": {"model_id": mbert_data.MODEL_ID, "revision": mbert_data.MODEL_REVISION,
                      "file_sha256": {n: mm.sha256(snap / n) for n in mm.TOKENIZER_FILES}},
        "source_sha256": {n: mm.sha256(ROOT / n) for n in SOURCES},
        "arms": {
            "mbert": {"confidence": 0.0, "mask_semantics": "inference.merge_spans"},
            "hybrid_union": {"confidence": 0.0, "mask_semantics": "hybrid.union then inference.merge_spans"},
            "hybrid_union_refined": {"confidence": 0.0, "mask_semantics": "refine.refine(hybrid.union) then inference.merge_spans",
                                     "scoring_label_mapping": "ADDRESS -> STREET for scoring input only; coverage metrics are label-agnostic"},
        },
        "definitions": DEFINITIONS, "model_forward_sweeps_requested": 1, "threshold_selection": False,
        "synthetic_only": True, "aggregate_only": True,
        "note": ("Blind synthetic dev v3: generated before any model or rule saw it; rules frozen at refine.py sha256 "
                 + frozen_refine_sha256 + "; one sweep; no tuning. Not a privacy guarantee."
                 if args.version == "v3" else
                 "Refinement rules were written after inspecting v1 failure shapes; v1 gains are optimistic. v2 was generated before any model output on it was seen, but one rule (street-type word before a STREET piece) was added after value-free failure shapes of both v1 and v2 were viewed; v2 is not fully blind. The later tightening of refine.py (address-part validity, phone-extension guards, dimension guard) was designed after v1 and v2 failures were seen, so neither set is blind any more."),
        "runtime": {"python_version": sys.version.split()[0]},
    }


def _row(m):
    return {"complete": m["complete_gold_spans"], "total": m["gold_spans"], "partial": m["partial_gold_spans"],
            "untouched": m["untouched_gold_spans"], "leaked_alnum": m["leaked_gold_alnum_chars"], "alnum": m["gold_alnum_chars"],
            "rows_ok": m["fully_masked_positive_rows"], "rows": m["positive_rows"], "excess": m["excess_masked_chars"]}


def summary_md(version, report, dataset):
    lines = ["# Refinement measurement " + version, "",
             "Synthetic development diagnostic; training false, test evaluated false. Annotated-span coverage only; not a privacy guarantee.",
             "Dataset sha256 " + dataset["sha256"] + " (" + str(dataset["rows"]) + " rows, " + str(dataset["gold_spans"]) + " gold spans).", "",
             "| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess masked chars | clean rows masked | clean masked chars |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name in ARMS:
        o = report["engines"][name]["overall"]
        r, c = _row(o), o["clean_controls"]
        lines.append("| {} | {}/{} | {} | {} | {}/{} | {}/{} | {} | {}/{} | {} |".format(
            name, r["complete"], r["total"], r["partial"], r["untouched"], r["leaked_alnum"], r["alnum"], r["rows_ok"], r["rows"],
            r["excess"], c["masked_rows"], c["rows"], c["masked_chars"]))
    lines.append("")
    return "\n".join(lines) + "\n"


def execute(args):
    rows, binding = load_rows(args.dataset, args.version)
    out = Path(args.out_dir)
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise MaskingError("mask_output_exists") from None
    manifest = manifest_of(args, binding)
    mm.json_write(out / "manifest.json", manifest)
    texts = [r[0] for r in rows]
    with mm.quiet_libraries():
        model = hybrid.Mbert(Path(args.model_dir), tok=mbert_data.load_tokenizer())
        raws = model.raw(texts)
    if len(raws) != len(rows):
        raise MaskingError("mask_prediction_count")
    aggs = score(rows, model, raws)
    for name in ARMS:
        if aggs[name].overall.counts["rows"] != len(rows):
            raise MaskingError("mask_count_mismatch")
    for n, d in manifest["source_sha256"].items():
        if mm.sha256(ROOT / n) != d:
            raise MaskingError("mask_source_changed")
    report = {**SCOPE, "scorer_version": SCORER_VERSION, "dataset_version": args.version, "dataset_sha256": binding["sha256"],
              "model_sha256": mm.EXPECTED_MODEL, "rows_evaluated": len(rows), "forward_sweeps": 1,
              "engines": {n: a.report() for n, a in aggs.items()}}
    mm.json_write(out / "metrics.json", report)
    (out / "summary.md").write_text(summary_md(args.version, report, binding), encoding="utf-8")
    print("refine_complete version=" + args.version + " rows=" + str(len(rows)) + " sweeps=1")
    for name in ARMS:
        o = report["engines"][name]["overall"]
        print(name + " complete={complete_gold_spans}/{gold_spans} partial={partial_gold_spans} untouched={untouched_gold_spans} leaked_alnum={leaked_gold_alnum_chars} rows_ok={fully_masked_positive_rows}/{positive_rows} excess={excess_masked_chars}".format(**o)
              + " clean_masked={}/{}".format(o["clean_controls"]["masked_rows"], o["clean_controls"]["rows"]))
    return 0


def _cell(a, b):
    return str(a) + " -> " + str(b)


# hybrid_union_refined before the tightening (committed refine-summary.md of the previous commit), for the "Tightening" section.
BEFORE = {"v1": {"excess": 148, "clean_chars": 0, "ADDRESS": (30, 30), "TELEPHONENUM": (46, 50), "complete": (201, 370)},
          "v2": {"excess": 64, "clean_chars": 64, "ADDRESS": (45, 45), "TELEPHONENUM": (25, 25), "complete": (70, 130)}}


def _tightening(reports):
    L = ["## Tightening", "",
         "refine.py was tightened after two measured problems: (a) v1 excess masked chars 0 -> 148 (ZIPCODE/BUILDINGNUM-like pieces the model finds",
         "inside non-address values, e.g. a username or phone number, were merged with the real address across a short gap); (b) v2 clean-control masked",
         "chars 56 -> 64. Diagnosis (value-free shapes) confirmed (a) but corrected (b): the added chars came from word completion extending an AGE span",
         "that sat in front of a letter+digit run (shape 9a9), not from a bare x extension rule; no TELEPHONENUM span was involved on those clean rows.",
         "Changes: address pieces overlapping/sharing an alphanumeric run with a non-address span, or not word-bounded, are not merged; a merged ADDRESS",
         "needs a STREET or CITY piece; phone extension rules need >= 6 digits and a bare x needs whitespace/span end before it and no unit or further",
         "x+digit after it (kept as guards although not the observed cause); word completion leaves digit-x-digit dimension runs alone.", "",
         "hybrid_union_refined, before -> after (hybrid_union for reference):", "",
         "| metric | v1 | v2 |", "|---|---|---|"]
    a = {v: reports[v]["engines"]["hybrid_union_refined"] for v in BEFORE}
    u = {v: reports[v]["engines"]["hybrid_union"] for v in BEFORE}
    L.append("| excess masked chars | " + " | ".join(_cell(BEFORE[v]["excess"], a[v]["overall"]["excess_masked_chars"]) + " (hybrid_union " + str(u[v]["overall"]["excess_masked_chars"]) + ")" for v in BEFORE) + " |")
    L.append("| clean-control masked chars | " + " | ".join(_cell(BEFORE[v]["clean_chars"], a[v]["overall"]["clean_controls"]["masked_chars"]) + " (hybrid_union " + str(u[v]["overall"]["clean_controls"]["masked_chars"]) + ")" for v in BEFORE) + " |")
    for k in ("ADDRESS", "TELEPHONENUM"):
        L.append("| " + k + " complete spans | " + " | ".join(_cell("{}/{}".format(*BEFORE[v][k]), "{}/{}".format(a[v]["per_gold_label"][k]["complete_gold_spans"], a[v]["per_gold_label"][k]["gold_spans"])) for v in BEFORE) + " |")
    L.append("| all complete spans | " + " | ".join(_cell("{}/{}".format(*BEFORE[v]["complete"]), "{}/{}".format(a[v]["overall"]["complete_gold_spans"], a[v]["overall"]["gold_spans"])) for v in BEFORE) + " |")
    L += ["", "Both sets are no longer blind: the tightening was designed after seeing the v1 and v2 failures (and the rules before it after seeing v1/v2 shapes), so these numbers are development evidence, not an unbiased estimate.", ""]
    return L


def write_summary():
    reports = {v: json.loads((RUNS / ("refine-" + v) / "metrics.json").read_text(encoding="utf-8")) for v in ("v1", "v2")}
    L = ["# Rule-based span refinement: hybrid_union -> hybrid_union_refined", ""] + _tightening(reports) + [
         "Synthetic development diagnostic only (training false, test evaluated false). Counts are annotated-span coverage of invented",
         "synthetic rows; unannotated information is outside them. This is not a privacy guarantee and says nothing about real data.",
         "Same mBERT checkpoint (sha256 " + mm.EXPECTED_MODEL + "), confidence 0.0, one forward sweep per dataset; scoring is the existing",
         "masking_metrics union-coverage scorer, unchanged (refined ADDRESS spans are labelled STREET for scoring input only; no metric below depends on labels).", "",
         "Caveat: the refinement rules were written after seeing the stress v1 failure shapes, so v1 gains are optimistic.",
         "Stress v2 (different formats; generated before any model output on it was seen) is the fairer check, but not fully blind: the first v2 run",
         "(rules a-c as briefed) gave ADDRESS 33/45 and 58/130 complete spans overall; value-free failure shapes (a street-type word such as 'via'/'calle'",
         "left outside the STREET piece) then led to one added rule (street-type prefix), which is what the numbers below include.",
         "Fully masked positive rows stay 0 because every row also carries an owner-name gold span (PERSONNAME) that this checkpoint has no label for;",
         "refinement does not touch names.", ""]
    for v, title in (("v1", "Stress v1"), ("v2", "Stress v2")):
        rep = reports[v]["engines"]
        b, a = rep["hybrid_union"], rep["hybrid_union_refined"]
        mb = rep["mbert"]
        L += ["## " + title + " (" + str(reports[v]["rows_evaluated"]) + " rows)", "",
              "Overall, hybrid_union -> hybrid_union_refined (mbert arm shown for reference):", "",
              "| metric | mbert | hybrid_union | hybrid_union_refined |", "|---|---|---|---|"]
        o = {n: rep[n]["overall"] for n in ARMS}
        for label, f in (
            ("complete spans / gold spans", lambda x: "{}/{}".format(x["complete_gold_spans"], x["gold_spans"])),
            ("partial spans", lambda x: x["partial_gold_spans"]),
            ("untouched spans", lambda x: x["untouched_gold_spans"]),
            ("exposed alnum chars", lambda x: "{}/{}".format(x["leaked_gold_alnum_chars"], x["gold_alnum_chars"])),
            ("fully masked positive rows", lambda x: "{}/{}".format(x["fully_masked_positive_rows"], x["positive_rows"])),
            ("clean controls with any mask", lambda x: "{}/{}".format(x["clean_controls"]["masked_rows"], x["clean_controls"]["rows"])),
            ("clean-control masked chars", lambda x: x["clean_controls"]["masked_chars"]),
            ("excess masked chars (all rows, outside gold)", lambda x: x["excess_masked_chars"]),
        ):
            L.append("| " + label + " | " + " | ".join(str(f(o[n])) for n in ARMS) + " |")
        L += ["", "Per gold label / family (hybrid_union -> hybrid_union_refined):", "",
              "| slice | complete spans | partial | untouched | exposed alnum chars | fully masked rows | row-scoped excess chars |", "|---|---|---|---|---|---|---|"]
        slices = [("ADDRESS", "per_gold_label", "ADDRESS"), ("TELEPHONENUM", "per_gold_label", "TELEPHONENUM"), ("long_text rows", "per_family", "long_text")]
        for name, grp, key in slices:
            x, y = b[grp].get(key), a[grp].get(key)
            if x is None:
                continue
            L.append("| " + name + " | " + _cell("{}/{}".format(x["complete_gold_spans"], x["gold_spans"]), "{}/{}".format(y["complete_gold_spans"], y["gold_spans"]))
                     + " | " + _cell(x["partial_gold_spans"], y["partial_gold_spans"]) + " | " + _cell(x["untouched_gold_spans"], y["untouched_gold_spans"])
                     + " | " + _cell(x["leaked_gold_alnum_chars"], y["leaked_gold_alnum_chars"])
                     + " | " + _cell("{}/{}".format(x["fully_masked_positive_rows"], x["positive_rows"]), "{}/{}".format(y["fully_masked_positive_rows"], y["positive_rows"]))
                     + " | " + _cell(x["excess_masked_chars"], y["excess_masked_chars"]) + " |")
        bo, ao = b["overall"], a["overall"]
        L += ["", "Clean controls: any mask " + _cell("{}/{}".format(bo["clean_controls"]["masked_rows"], bo["clean_controls"]["rows"]), "{}/{}".format(ao["clean_controls"]["masked_rows"], ao["clean_controls"]["rows"]))
              + "; masked chars " + _cell(bo["clean_controls"]["masked_chars"], ao["clean_controls"]["masked_chars"])
              + "; excess masked chars over all rows " + _cell(bo["excess_masked_chars"], ao["excess_masked_chars"]) + ".", ""]
    L += ["Per-slice excess is row-scoped (whole-row excess for rows containing the label) and not additive across slices.",
          "Details: refine-v1/ and refine-v2/ (metrics.json, manifest.json, summary.md)."]
    (RUNS / "refine-summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("refine_summary_written")
    return 0


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise MaskingError("mask_arguments")


def main():
    try:
        p = SafeParser(description=__doc__)
        p.add_argument("--summary", action="store_true")
        p.add_argument("--dataset")
        p.add_argument("--version", choices=("v1", "v2", "v3"))
        p.add_argument("--model-dir")
        p.add_argument("--out-dir")
        args = p.parse_args()
        if args.summary:
            return write_summary()
        if not (args.dataset and args.version and args.model_dir and args.out_dir):
            raise MaskingError("mask_arguments")
        return execute(args)
    except MaskingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except ValueError as error:
        print("refine_invalid_input" if str(error).startswith("invalid spans") else "mask_validation_failed", file=sys.stderr)
        return 1
    except Exception:
        print("refine_operation_failed_input_not_shown", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
