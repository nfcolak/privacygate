#!/usr/bin/env python3
"""Code-only synthetic wiring assertions. No torch, tensors, corpus, checkpoint inference or test access.

File loaders consume in-memory bytes; checkpoint guards consume in-memory metadata/file markers.
The evaluator is only a routing spy (opaque objects, no invented scores).
"""
import builtins
import contextlib
import copy
import hashlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from privacygate.data import augmentation_data as ad
from privacygate import mbert_data as md
from privacygate import negative_data as nd
from privacygate import positive_data as pd
from privacygate.model import train_guard as tg
from scripts.training import train_mbert as tm

SENTINEL = "SYNTHETIC_VALUE_NEVER_IN_ERRORS"
MICRO = {"micro-a": ("aa", [(0, 2, "GIVENNAME")], "en"),
         "micro-b": ("bb", [(0, 2, "SURNAME")], "de"),
         "micro-c": ("cc", [(0, 2, "ZIPCODE")], "fr")}
MICRO_DEV = {"micro-dev": ("dd", [(0, 2, "GIVENNAME")], "it")}
TRAIN_ENTRIES = [{"row_id": k, "language": v[2]} for k, v in MICRO.items()]
DEV_ENTRIES = [{"row_id": k, "language": v[2]} for k, v in MICRO_DEV.items()]
RAW = {}


def row(rid, label="USERNAME", split="train", text="qa", template=None):
    return {"row_id": rid, "language": "en", "source_text": text,
            "privacy_mask": [{"start": 0, "end": len(text), "label": label}],
            "template_id": template or rid + "-template", "split": split}


POS_TRAIN = [row("pos-a"), row("pos-b", "ACCOUNTNUM", text="qb"),
             row("pos-c", "PERSONALREF", text="qc")]
POS_DEV = [row("pos-dev", split="dev", text="qd")]
NEG = [{**row("negative", text="Trees grow."), "privacy_mask": []}]


def put(name, rows):
    RAW[name] = pd.dumps(rows).encode("utf-8")
    return name


def load(train=POS_TRAIN, dev=POS_DEV, neg=NEG):
    return ad.load_inputs(TRAIN_ENTRIES, DEV_ENTRIES,
                         put("positive-train", train) if train is not None else None,
                         put("positive-dev", dev) if dev is not None else None,
                         put("negative", neg) if neg is not None else None)


def refuse(code, fn):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, "wrong_refusal_code"
        assert SENTINEL not in str(exc), "value_in_error"
        assert tg.refusal_code(exc) == code, "code_not_safe"
    else:
        raise AssertionError("missing_refusal")


class CharacterTokenizer:
    def __call__(self, text, **kwargs):
        ids = [0] + [1] * len(text) + [0]
        offsets = [(0, 0)] + [(i, i + 1) for i in range(len(text))] + [(0, 0)]
        if kwargs.get("return_overflowing_tokens"):
            return {"input_ids": [ids], "offset_mapping": [offsets]}
        return {"input_ids": ids, "offset_mapping": offsets}


def check_inventory_and_append():
    pt, tb, dv, db, neg, nb = load()
    assert tb is not None and db is not None and nb is not None
    assert tb["sha256"] == hashlib.sha256(RAW["positive-train"]).hexdigest()
    assert db["split"] == "dev" and tb["split"] == "train" and tb["rows"] == 3 and db["rows"] == 1
    assert set(tb["per_label"]) == set(pd.NEW_LABELS) and nb["rows"] == 1
    labels = ad.training_labels(MICRO, pt)
    assert ad.training_labels(MICRO, []) == md.label_list(MICRO), "default_label_order_changed"
    assert labels == ["O"] + [p + "-" + n for n in sorted(
        {"GIVENNAME", "SURNAME", "ZIPCODE", *pd.NEW_LABELS}) for p in ("B", "I")]
    rows, entries = ad.assemble_training(MICRO, TRAIN_ENTRIES[:1], pt, neg)
    assert [e["row_id"] for e in entries] == ["micro-a", "pos-a", "pos-b", "pos-c", "negative"]
    assert "pos-dev" not in rows and "micro-dev" not in rows, "dev_in_training"
    wins, excluded = tm.build_windows(CharacterTokenizer(), rows, entries,
                                     {l: i for i, l in enumerate(labels)}, True)
    assert excluded == 0 and len(wins) == len(entries)
    for rid, label in zip(("pos-a", "pos-b", "pos-c"), pd.NEW_LABELS):
        w = next(w for w in wins if w[3] == rid)
        assert [labels[i] for i in w[1] if i != md.IGNORE] == ["B-" + label, "I-" + label]
    counts = ad.source_counts(TRAIN_ENTRIES[:1], pt, neg, [w for w in wins if w[3] != "pos-c"])
    assert counts == {"micro": {"included": 1, "retained": 1, "excluded_after_windowing": 0},
                      "positive": {"included": 3, "retained": 2, "excluded_after_windowing": 1},
                      "negative": {"included": 1, "retained": 1, "excluded_after_windowing": 0}}
    ad.check_dev_labels(labels, MICRO_DEV, ad.positive_dataset(dv)[0])
    unknown = ad.positive_dataset([row("unknown", "TELEPHONENUM", "dev", SENTINEL)])[0]
    refuse("pos_dev_label_not_in_train", lambda: ad.check_dev_labels(labels, {}, unknown))
    refuse("dev_label_not_in_train", lambda: ad.check_dev_labels(["O"], MICRO_DEV, {}))
    assert "B-TELEPHONENUM" not in labels
    assert ad.load_inputs(TRAIN_ENTRIES, DEV_ENTRIES) == ([], None, [], None, [], None)


def check_admission():
    load()
    refuse("pos_split_mismatch", lambda: pd.load_positive_file("positive-dev"))
    refuse("pos_split_mismatch", lambda: load(train=POS_DEV))
    refuse("pos_split_mismatch", lambda: load(dev=POS_TRAIN))
    for e in TRAIN_ENTRIES + DEV_ENTRIES + NEG:
        for split in ("train", "dev"):
            collided = [row(e["row_id"], split=split, text=SENTINEL)]
            refuse("pos_row_id", lambda: load(train=collided) if split == "train" else load(dev=collided))
    refuse("pos_row_id", lambda: load(dev=[row("pos-a", split="dev", text=SENTINEL)]))
    refuse("pos_row_id", lambda: load(train=[POS_TRAIN[0], POS_TRAIN[0]]))
    # Exact text overlaps are rejected even when language and template IDs differ.
    overlap = [{**POS_DEV[0], "source_text": "qa", "language": "de"}]
    refuse("pos_train_dev_text_overlap", lambda: load(dev=overlap))
    refuse("pos_train_dev_template_overlap", lambda: load(dev=[{**POS_DEV[0], "template_id": "pos-a-template"}]))
    for bad, code in (({**POS_TRAIN[0], SENTINEL: SENTINEL}, "pos_schema"),
                      ({**POS_TRAIN[0], "privacy_mask": [{"start": False, "end": 2, "label": "USERNAME"}]}, "pos_mask_type"),
                      (row("bad", SENTINEL, text=SENTINEL), "pos_label")):
        refuse(code, lambda: load(train=[bad]))
    RAW["malformed"] = ('{"' + SENTINEL).encode()
    refuse("pos_unparseable", lambda: pd.load_positive_file("malformed"))
    refuse("micro_manifest_malformed", lambda: ad.manifest_entries(RAW["malformed"]))
    assert tg.refusal_code(ValueError(SENTINEL)) == "input_unreadable_or_malformed"
    assert tg.refusal_code(OSError(SENTINEL)) == "input_unreadable_or_malformed"


def check_separate_metrics():
    first, second = object(), object()
    p_rows, p_entries = ad.positive_dataset(POS_DEV)
    with patch.object(tm, "evaluate", side_effect=[first, second]) as evaluator:
        result = tm.evaluate_development(None, None, MICRO_DEV, DEV_ENTRIES, {}, None, None, 32, p_rows, p_entries)
        assert result == {"dev": first, "positive_dev": second}, "pooled_dev"
        assert evaluator.call_args_list[0].args[2:4] == (MICRO_DEV, DEV_ENTRIES)
        assert evaluator.call_args_list[1].args[2:4] == (p_rows, p_entries)
    with patch.object(tm, "evaluate", return_value=first) as evaluator:
        assert tm.evaluate_development(None, None, MICRO_DEV, DEV_ENTRIES, {}, None, None, 32) == {"dev": first}
        assert evaluator.call_count == 1, "invented_positive_metric"


def check_run_binding():
    pt, tb, dv, db, neg, nb = load()
    labels = ad.training_labels(MICRO, pt)
    model, docs, results = (Path("/synthetic") / n for n in ("model", "docs", "results"))
    args = SimpleNamespace(run="synthetic", epochs=1, batch_size=2, lr=3e-5, seed=13,
                           max_train_rows=1, max_dev_rows=1)
    identity = tg.build_identity(args, md.MODEL_ID, md.MODEL_REVISION, md.MAX_LEN, md.STRIDE,
                                 "manifest-digest", nb, model, tb, db, labels)
    assert identity["positive_source_version"] == pd.GEN_VERSION and identity["positive_schema_version"]
    files = {model / "config.json": {"id2label": {str(i): l for i, l in enumerate(labels)},
                                     "label2id": {l: i for i, l in enumerate(labels)}},
             model / "model.safetensors": None,  # existence marker ONLY, no tensor/file/model
             model / "train_info.json": {"run_identity": identity},
             docs / "config.json": {"run_identity": identity, "labels": labels},
             docs / "metrics.json": {"run_identity": identity}, results / "metrics.json": {"run_identity": identity}}
    dirs = {model, docs, results}
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(Path, "is_symlink", return_value=False))
        stack.enter_context(patch.object(Path, "is_dir", lambda p: p in dirs))
        stack.enter_context(patch.object(Path, "is_file", lambda p: p in files))
        stack.enter_context(patch.object(Path, "exists", lambda p: p in files or p in dirs))
        stack.enter_context(patch.object(tg, "_nonempty", lambda p: p in dirs))
        stack.enter_context(patch.object(tg, "_read_json", lambda p: copy.deepcopy(files[p])))
        before = copy.deepcopy(files)
        assert tg.check_existing(identity, model, docs, results) == "reuse"
        deferred = {**identity, "labels": None}
        assert tg.check_existing(deferred, model, docs, results) == "reuse"
        for binding in ("positive_train", "positive_dev", "negative_train"):
            changed = copy.deepcopy(identity)
            changed[binding]["sha256"] = "changed-digest"
            refuse("run_identity_mismatch", lambda: tg.check_existing(changed, model, docs, results))
        for key, value in (("labels", list(reversed(labels))), ("positive_train", None),
                           ("positive_dev", None), ("positive_source_version", "changed"),
                           ("positive_schema_version", "changed"), ("output_dir", "/other")):
            refuse("run_identity_mismatch", lambda: tg.check_existing({**identity, key: value}, model, docs, results))
        assert files == before, "guard_modified_metadata"
        files[model / "train_info.json"] = {}
        refuse("run_without_provenance", lambda: tg.check_existing(identity, model, docs, results))
        files[model / "train_info.json"] = {"run_identity": {k: v for k, v in identity.items() if k != "labels"}}
        refuse("run_label_inventory_missing", lambda: tg.check_existing(deferred, model, docs, results))
        files[model / "train_info.json"] = {"run_identity": {**identity, "version": "run-identity-v1"}}
        refuse("run_identity_mismatch", lambda: tg.check_existing(deferred, model, docs, results))
        files.update(before)
        files[docs / "metrics.json"] = {}
        refuse("run_without_provenance", lambda: tg.check_existing(identity, model, docs, results))
        files.update(before)
        files[model / "config.json"]["label2id"] = {}
        refuse("run_classifier_labels_mismatch", lambda: tg.check_existing(identity, model, docs, results))


class ModelBoundary(RuntimeError):
    pass


def check_main_preflight():
    original_import = builtins.__import__
    def block_model(name, *args, **kwargs):
        if name in ("torch", "transformers"):
            raise ModelBoundary
        return original_import(name, *args, **kwargs)

    def manifest_bytes(path):
        assert path.name in ("train.jsonl", "dev.jsonl"), "unexpected_file_read"
        entries = TRAIN_ENTRIES if path.name == "train.jsonl" else DEV_ENTRIES
        return "\n".join(json.dumps(e) for e in entries).encode()

    for dev, expected in ((POS_DEV, None), ([row("unknown", "TELEPHONENUM", "dev", SENTINEL)],
                                          "pos_dev_label_not_in_train")):
        load(dev=dev)
        argv = ["train_mbert", "--run", "synthetic", "--max-train-rows", "1", "--max-dev-rows", "1",
                "--positive-train-file", "positive-train", "--positive-dev-file", "positive-dev",
                "--negative-train-file", "negative", "--out-dir", "/synthetic/models"]
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", argv))
            stack.enter_context(patch.object(Path, "read_bytes", manifest_bytes))
            stack.enter_context(patch.object(md, "load_rows", lambda entries: {
                e["row_id"]: {**MICRO, **MICRO_DEV}[e["row_id"]] for e in entries}))
            guard = stack.enter_context(patch.object(tg, "check_existing", return_value="fresh"))
            assembly = stack.enter_context(patch.object(ad, "assemble_training", wraps=ad.assemble_training))
            stack.enter_context(patch.object(builtins, "__import__", block_model))
            writer = stack.enter_context(patch.object(Path, "write_text", side_effect=AssertionError("unexpected_write")))
            stack.enter_context(contextlib.redirect_stdout(output))
            stack.enter_context(contextlib.redirect_stderr(errors))
            if expected:
                assert tm.main() == 2 and errors.getvalue() == "refused: " + expected + "\n"
                assert not assembly.called, "unknown_dev_admitted"
            else:
                try:
                    tm.main()
                except ModelBoundary:
                    pass
                else:
                    raise AssertionError("missing_model_boundary")
                assert guard.call_count == 2 and assembly.call_count == 1
                assert guard.call_args.args[0]["labels"] == ad.training_labels(MICRO, POS_TRAIN)
                selected = assembly.call_args.args[1]
                assert len(selected) == 1 and assembly.call_args.args[2:] == (POS_TRAIN, NEG)
                assert not errors.getvalue()
            assert not writer.called and SENTINEL not in output.getvalue() + errors.getvalue()
    # CLI help and invalid arguments remain dependency-free and value-free.
    for argv, code in ((["train_mbert", "--help"], 0),
                       (["train_mbert", "--run", "synthetic", "--epochs", SENTINEL], 2)):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", argv), patch.object(builtins, "__import__", block_model), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                tm.main()
            except SystemExit as exc:
                assert exc.code == code
            else:
                raise AssertionError("missing_cli_exit")
        assert SENTINEL not in output.getvalue() + errors.getvalue()
        if code == 0:
            assert "--positive-train-file" in output.getvalue() and "--positive-dev-file" in output.getvalue()
            assert "--test" not in output.getvalue()
        else:
            assert errors.getvalue() == "refused: cli_invalid_arguments\n"


def main():
    assert "torch" not in sys.modules and "transformers" not in sys.modules
    with patch.object(pd, "_read_bounded", lambda path: RAW[str(path)]), \
            patch.object(nd, "_read_bounded", lambda path: RAW[str(path)]):
        for name, check in (("train_inventory_append_bio_counts", check_inventory_and_append),
                            ("split_overlap_ids_value_free_errors", check_admission),
                            ("separate_dev_routing_no_invented_results", check_separate_metrics),
                            ("checkpoint_identity_and_metadata", check_run_binding),
                            ("trainer_preflight_and_cli", check_main_preflight)):
            check()
            print("CHECK " + name + " OK")
    assert "torch" not in sys.modules and "transformers" not in sys.modules
    print("POSITIVE TRAINING WIRING OK (synthetic only; no training/evaluation)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never emit fixture values or exception tracebacks, even if an assertion fails.
        print("POSITIVE TRAINING WIRING FAILED", file=sys.stderr)
        sys.exit(1)
