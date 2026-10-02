#!/usr/bin/env python3
"""Production window/offset checks on hand-built synthetic fixtures only.

No corpus, checkpoint, torch/transformers, model inference or saved diagnosis
writes. A deterministic stub exercises evaluator decoding, not model scoring.
"""
import contextlib
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from privacygate import mbert_data as md
from privacygate import train_guard as tg
from privacygate import train_mbert as tm
from privacygate import window_alignment as wa
from scripts import diagnose_alignment as diagnosis

WHOLE = [None, (0, 2), (2, 4), (4, 6), (6, 8), None]
LEFT = [None, (0, 2), (2, 4), None]
RIGHT = [None, (4, 6), (6, 8), None]
BRIDGE = [None, (2, 4), (4, 6), None]
LABELS = {"O": 0, "B-X": 1, "I-X": 2, "B-Y": 3, "I-Y": 4}


class OffsetTokenizer:
    def __init__(self, windows):
        self.windows = windows

    def __call__(self, text, **kwargs):
        def offsets(seq):
            return [(0, 0) if off is None else off for off in seq]
        if kwargs.get("return_overflowing_tokens"):
            return {"input_ids": [[0] * len(w) for w in self.windows],
                    "offset_mapping": [offsets(w) for w in self.windows]}
        assert kwargs["truncation"] is False
        return {"input_ids": [0] * len(WHOLE), "offset_mapping": offsets(WHOLE)}


def build(spans, windows):
    stats = {}
    wins, excluded = tm.build_windows(OffsetTokenizer(windows), {"synthetic": ("abcdefgh", spans, "en")},
                                     [{"row_id": "synthetic"}], LABELS, True, stats)
    return wins, excluded, stats


def check_construction():
    cases = [
        ("outside", [LEFT, RIGHT], [(6, 8, "X")]),
        ("broken", [LEFT, RIGHT], [(1, 2, "X")]),
        ("lost", [LEFT, RIGHT], [(8, 10, "X")]),
        ("crossing_covered", [LEFT, BRIDGE, RIGHT], [(2, 6, "X")]),
        ("crossing_uncovered", [LEFT, RIGHT], [(2, 6, "X")]),
        ("huge", [LEFT, BRIDGE, RIGHT], [(0, 8, "X")]),
        ("touching", [LEFT, RIGHT], [(4, 6, "X")]),
        ("overlap", [WHOLE], [(0, 4, "X"), (2, 6, "Y")]),
        ("negative", [LEFT, RIGHT], []),
        ("special_only_negative", [[None, None]], []),
        ("no_windows", [], []),
        ("window_failure_covered", [[None, (0, 1), (1, 3), None], WHOLE], [(0, 2, "X")]),
        ("window_failure_uncovered", [[None, (0, 1), (1, 3), None]], [(0, 2, "X")]),
    ]
    for name, windows, spans in cases:
        actual = wa.align_windows(WHOLE, windows, spans)
        original_candidate = diagnosis.candidate(WHOLE, windows, spans)
        for key in ("retained", "covered", "windows"):
            assert actual[key] == original_candidate[key], "diagnostic_candidate_mismatch"
        wins, ex, stats = build(spans, windows)
        assert bool(ex) != actual["retained"], "production_retention_mismatch"
        assert len(wins) == len(actual["windows"]), "production_window_mismatch"
        for win, aligned in zip(wins, actual["windows"]):
            assert win[1] == [md.IGNORE if l is None else LABELS[l] for l in aligned["labels"]]
            assert win[2] == windows[aligned["source_window_index"]], "gold_censored_offsets"
        assert stats["gold_spans_retained"] == stats["gold_spans_fully_covered"]
        if name == "outside":
            assert ex == 0 and wins[0][1] == [md.IGNORE, 0, 0, md.IGNORE]
            assert wins[1][1] == [md.IGNORE, 0, 1, md.IGNORE]
            assert diagnosis.legacy_build_windows(OffsetTokenizer(windows), {"synthetic": ("abcdefgh", spans, "en")},
                                                 [{"row_id": "synthetic"}], LABELS, True)[1] == 1
        if name == "crossing_covered":
            assert wins[0][1][2] == md.IGNORE and wins[2][1][1] == md.IGNORE
            assert wins[1][1] == [md.IGNORE, 1, 2, md.IGNORE]
            assert stats["ignored_crossing_tokens_retained"] == 2
        if name in ("crossing_uncovered", "huge", "no_windows", "window_failure_uncovered"):
            assert ex == 1 and stats["rows_excluded_by_reason"]["incomplete_gold_coverage"] == 1
        if name == "broken":
            assert stats["rows_excluded_by_reason"]["whole_row_broken_boundary"] == 1
        if name == "lost":
            assert stats["rows_excluded_by_reason"]["whole_row_lost_span"] == 1
        if name.startswith("window_failure"):
            assert stats["windows_discarded_alignment"] == 1
        print("CHECK production_" + name + " OK")
    # The frozen diagnostic's original 13 fixture assertions still hold; no execute/corpus call.
    assert diagnosis.synthetic_checks()["all_passed"]


def check_prediction_independence():
    predictions = [[0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    class Logits:
        def argmax(self, axis):
            return self
        def cpu(self):
            return self
        def tolist(self):
            return predictions
    class Stub:
        def eval(self):
            pass
        def __call__(self, **kwargs):
            return SimpleNamespace(logits=Logits())
    rows = {"synthetic": ("abcdefgh", [(2, 6, "X")], "en")}
    with patch.object(tm, "collate", return_value=(object(), object(), object())), \
            patch.object(md, "decode", wraps=md.decode) as decoder:
        result = tm.evaluate(Stub(), OffsetTokenizer([LEFT, BRIDGE, RIGHT]), rows,
                             [{"row_id": "synthetic"}], {v: k for k, v in LABELS.items()},
                             None, SimpleNamespace(no_grad=contextlib.nullcontext), 32)
    assert decoder.call_args_list[0].args == (LEFT, ["O", "O", "B-X", "O"])
    assert md.decode(*decoder.call_args_list[0].args) == {(2, 4, "X")}
    assert result["overall"]["fp"] == 1 and result["overall"]["fn"] == 1, "prediction_gold_censorship"
    assert result["alignment_stats"]["ignored_crossing_tokens_retained"] == 2
    print("CHECK evaluator_predictions_not_censored_by_gold OK")


def check_identity():
    args = SimpleNamespace(run="synthetic", epochs=1, batch_size=2, lr=3e-5, seed=13,
                           max_train_rows=1, max_dev_rows=1)
    identity = tg.build_identity(args, md.MODEL_ID, md.MODEL_REVISION, md.MAX_LEN, md.STRIDE,
                                 "synthetic-manifest-binding", None, Path('/synthetic/model'), labels=list(LABELS))
    assert identity["version"] == "run-identity-v3"
    assert identity["alignment_policy"] == wa.ALIGNMENT_POLICY
    assert identity["alignment_source_version"] == wa.ALIGNMENT_SOURCE_VERSION
    for field, value in (("version", "run-identity-v1"), ("version", "run-identity-v2"),
                         ("alignment_policy", "legacy"), ("alignment_source_version", "legacy")):
        recorded = copy.deepcopy(identity)
        recorded[field] = value
        try:
            tg._check_identity(recorded, identity, "run_identity_mismatch")
        except ValueError as exc:
            assert str(exc) == "run_identity_mismatch"
        else:
            raise AssertionError("old_alignment_identity_admitted")
    print("CHECK alignment_identity_old_versions_refused OK")


if __name__ == '__main__':
    try:
        check_construction()
        check_prediction_independence()
        check_identity()
        assert 'torch' not in sys.modules and 'transformers' not in sys.modules
        print('WINDOW ALIGNMENT OK (synthetic only; no trained model scoring)')
    except Exception:
        print('WINDOW ALIGNMENT FAILED', file=sys.stderr)
        sys.exit(1)
