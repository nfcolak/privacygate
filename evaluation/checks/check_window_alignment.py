#!/usr/bin/env python3
"""Production region window/offset checks on hand-built synthetic fixtures only.

No corpus, checkpoint, torch/transformers or model inference. A deterministic
stub exercises the region evaluator's decoding, not model scoring.
"""
import contextlib
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from privacygate import mbert_data as md
from privacygate.data import region_data as rd
from privacygate.data import window_alignment as wa
from privacygate.model import train_guard as tg
from privacygate.training import train_mbert as tm

WHOLE = [None, (0, 2), (2, 4), (4, 6), (6, 8), None]
LEFT = [None, (0, 2), (2, 4), None]
RIGHT = [None, (4, 6), (6, 8), None]
BRIDGE = [None, (2, 4), (4, 6), None]
X, Y = "PERSONNAME", "ADDRESS"
LABELS = rd.LABEL2ID


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


_real_encode = md.encode


def _fixture_encode(tok, text):
    # encode now builds windows itself from content tokens; the hand-built fixtures here
    # specify exact window shapes, so the fixture tokenizer supplies them directly.
    if isinstance(tok, OffsetTokenizer):
        return [([0] * len(w), [off for off in w]) for w in tok.windows]
    return _real_encode(tok, text)


md.encode = _fixture_encode


def build(spans, windows):
    rows = [{"text": "abcdefgh", "gold": [{"start": a, "end": b, "label": l} for a, b, l in spans]}]
    wins, stats = rd.build_windows(OffsetTokenizer(windows), rows)
    return wins, stats["rows_excluded"], stats


def check_construction():
    cases = [
        ("outside", [LEFT, RIGHT], [(6, 8, X)]),
        ("broken", [LEFT, RIGHT], [(1, 2, X)]),
        ("lost", [LEFT, RIGHT], [(8, 10, X)]),
        ("crossing_covered", [LEFT, BRIDGE, RIGHT], [(2, 6, X)]),
        ("crossing_uncovered", [LEFT, RIGHT], [(2, 6, X)]),
        ("huge", [LEFT, BRIDGE, RIGHT], [(0, 8, X)]),
        ("touching", [LEFT, RIGHT], [(4, 6, X)]),
        ("overlap", [WHOLE], [(0, 4, X), (2, 6, Y)]),
        ("negative", [LEFT, RIGHT], []),
        ("special_only_negative", [[None, None]], []),
        ("no_windows", [], []),
        ("window_failure_covered", [[None, (0, 1), (1, 3), None], WHOLE], [(0, 2, X)]),
        ("window_failure_uncovered", [[None, (0, 1), (1, 3), None]], [(0, 2, X)]),
    ]
    for name, windows, spans in cases:
        actual = wa.align_windows(WHOLE, windows, spans)
        wins, ex, stats = build(spans, windows)
        assert bool(ex) != actual["retained"], "production_retention_mismatch"
        assert len(wins) == len(actual["windows"]), "production_window_mismatch"
        for win, aligned in zip(wins, actual["windows"]):
            assert win[1] == [md.IGNORE if l is None else LABELS[l] for l in aligned["labels"]]
            assert win[2] == windows[aligned["source_window_index"]], "gold_censored_offsets"
        assert stats["gold_spans_retained"] == stats["gold_spans_fully_covered"]
        b, i = LABELS["B-" + X], LABELS["I-" + X]
        if name == "outside":
            assert ex == 0 and wins[0][1] == [md.IGNORE, 0, 0, md.IGNORE]
            assert wins[1][1] == [md.IGNORE, 0, b, md.IGNORE]
        if name == "crossing_covered":
            assert wins[0][1][2] == md.IGNORE and wins[2][1][1] == md.IGNORE
            assert wins[1][1] == [md.IGNORE, b, i, md.IGNORE]
            assert stats["ignored_crossing_tokens_retained"] == 2
        if name in ("crossing_uncovered", "huge", "no_windows", "window_failure_uncovered"):
            assert ex == 1 and stats["rows_excluded_by_reason"]["incomplete_gold_coverage"] == 1
        if name == "broken":
            assert stats["rows_excluded_by_reason"]["whole_row_broken_boundary"] == 1
        if name.startswith("window_failure"):
            assert stats["windows_discarded_alignment"] == 1
        if name == "lost":
            assert stats["rows_excluded_by_reason"]["whole_row_lost_span"] == 1
        if name == "overlap":
            assert stats["rows_excluded_by_reason"]["overlapping_gold"] == 1
        print("CHECK production_" + name + " OK")


def check_prediction_independence():
    b = LABELS["B-" + X]
    predictions = [[0, 0, b, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
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
    rows = [{"text": "abcdefgh", "language": "en", "gold": [{"start": 2, "end": 6, "label": X}]}]
    # Same prediction windows as the trainer: every window, gold-independent IGNORE labels.
    windows = [(ids, [md.IGNORE] * len(ids), offsets, 0)
               for ids, offsets in md.encode(OffsetTokenizer([LEFT, BRIDGE, RIGHT]), "abcdefgh")]
    with patch.object(tm, "collate", return_value=(object(), object(), object())), \
            patch.object(md, "decode", wraps=md.decode) as decoder:
        result = tm.evaluate_regions(Stub(), rows, windows, None,
                                     SimpleNamespace(no_grad=contextlib.nullcontext), 32)
    assert decoder.call_args_list[0].args == (LEFT, ["O", "O", "B-" + X, "O"])
    assert md.decode(*decoder.call_args_list[0].args) == {(2, 4, X)}
    assert result["overall"]["fp"] == 1 and result["overall"]["fn"] == 1, "prediction_gold_censorship"
    assert result["windows"] == 3 and result["character"]["covered_gold_chars"] == 2
    print("CHECK evaluator_predictions_not_censored_by_gold OK")


def check_identity():
    args = SimpleNamespace(run="synthetic", epochs=1, batch_size=2, lr=3e-5, seed=13)
    binding = {"sha256": "0" * 64, "split": "train"}
    identity = tg.build_region_identity(args, md.MODEL_ID, md.MODEL_REVISION, md.MAX_LEN, md.STRIDE,
                                        rd.LABELS, binding, dict(binding, split="dev"), Path('/synthetic/model'))
    assert identity["version"] == "region-run-identity-v1"
    assert identity["alignment_policy"] == wa.ALIGNMENT_POLICY
    assert identity["alignment_source_version"] == wa.ALIGNMENT_SOURCE_VERSION
    tg._check_identity(copy.deepcopy(identity), identity, "run_identity_mismatch")
    for field, value in (("version", "run-identity-v3"), ("encoder_version", "legacy"),
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
