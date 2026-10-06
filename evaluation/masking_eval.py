"""Aggregate-only end-to-end masking evaluation, independent of detector labels.

Reuses the interval, character and span-classification functions of
privacygate.masking_metrics. Dataset text, identifiers and offsets are held in
memory and never in reports. Retired v1-v6/dev2-dev4 loaders live in git history.
"""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any

from privacygate import masking_metrics as mm

ROOT = Path(__file__).resolve().parents[1]
SCORER_VERSION = "pipeline-masking-v1"
VERSIONS = ("v7",)
MANIFEST_PATHS = {"v7": "data/manifests/masking-stress-v7.json"}
# Receipts of every blind round stay readable so repeat arms keep being refused.
BLIND_VERSIONS = ("v4", "v5", "v6", "v7")
SPAN_KEYS = frozenset({"start", "end", "label"})
CHECK_RECEIPTS_ENV = "PRIVACYGATE_EVAL_CHECK_RECEIPTS"
MAX_BYTES = 128 * 1024 * 1024


class EvaluationError(ValueError):
    """Only fixed codes are printed at the CLI boundary."""


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise EvaluationError("eval_duplicate_json_key")
        out[key] = value
    return out


def _json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_object,
                          parse_constant=lambda _: _bad_json())
    except EvaluationError:
        raise
    except (ValueError, RecursionError, UnicodeError):
        raise EvaluationError("eval_invalid_json") from None


def _bad_json():
    raise EvaluationError("eval_invalid_json")


def read_bounded(path, limit=MAX_BYTES):
    try:
        with open(path, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise EvaluationError("eval_not_regular_file")
            raw = handle.read(limit + 1)
    except (OSError, TypeError):
        raise EvaluationError("eval_file_unavailable") from None
    if len(raw) > limit:
        raise EvaluationError("eval_file_bounds")
    return raw


def json_write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_spans(spans, n, gold=False):
    """Any nonempty label is admitted; values/offsets are never echoed."""
    if not isinstance(spans, list) or len(spans) > 4096:
        raise EvaluationError("eval_span_schema")
    pairs = []
    for span in spans:
        if not isinstance(span, dict) or not SPAN_KEYS <= span.keys():
            raise EvaluationError("eval_span_schema")
        if gold and span.keys() != SPAN_KEYS:
            raise EvaluationError("eval_gold_schema")
        if not isinstance(span["label"], str) or not span["label"]:
            raise EvaluationError("eval_label")
        pairs.append((span["start"], span["end"]))
    try:
        mm.interval_union(pairs, n)
    except mm.MaskingError:
        raise EvaluationError("eval_span_offsets") from None
    if gold and (pairs != sorted(pairs) or any(b > c for (_, b), (c, _) in zip(pairs, pairs[1:]))):
        raise EvaluationError("eval_gold_order_overlap")


def wilson(successes, total):
    if type(successes) is not int or type(total) is not int or not 0 <= successes <= total:
        raise EvaluationError("eval_interval_counts")
    if not total:
        return {"successes": successes, "total": total, "rate": None, "low": None, "high": None}
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return {"successes": successes, "total": total, "rate": rate,
            "low": max(0.0, center - half), "high": min(1.0, center + half)}


class Aggregate:
    def __init__(self):
        self.counts = Counter()
        self.clean = Counter()
        self.classes = Counter({key: 0 for key in mm.CLASSES})

    def add(self, text, gold, final, status="ok", uncovered_chars=0, all_gold=None):
        n = len(text)
        validate_spans(gold, n, gold=True)
        validate_spans(final, n)
        all_gold = gold if all_gold is None else all_gold
        validate_spans(all_gold, n, gold=True)
        if status not in ("ok", "blocked") or type(uncovered_chars) is not int or not 0 <= uncovered_chars <= n:
            raise EvaluationError("eval_completion_schema")
        if status == "blocked" and final:
            raise EvaluationError("eval_blocked_has_entities")
        mask = mm.interval_union([(p["start"], p["end"]) for p in final], n)
        gold_union = mm.interval_union([(g["start"], g["end"]) for g in all_gold], n)
        c = self.counts
        masked = mm.count_chars(mask, n)
        excess = masked - mm.count_chars(mm.intersection(mask, gold_union, n), n)
        c.update({"rows": 1, "text_chars": n, "masked_chars": masked,
                  "excess_masked_chars": excess, "final_mask_entities": len(final),
                  "ok_rows": int(status == "ok"), "blocked_rows": int(status == "blocked"),
                  "uncovered_chars": uncovered_chars, "rows_with_uncovered_chars": int(uncovered_chars > 0)})
        if not gold:
            self.clean.update({"rows": 1, "masked_rows": int(masked > 0), "masked_chars": masked,
                               "text_chars": n, "ok_rows": int(status == "ok"),
                               "blocked_rows": int(status == "blocked")})
            return
        c["positive_rows"] += 1
        c["positive_nongold_chars"] += n - mm.count_chars(gold_union, n)
        c["positive_excess_masked_chars"] += excess
        complete = 0
        for g in gold:
            a, b = g["start"], g["end"]
            hits = mm.intersection([(a, b)], mask, n)
            covered = mm.count_chars(hits, n)
            alnum = mm.count_alnum(text, [(a, b)])
            covered_alnum = mm.count_alnum(text, hits)
            self.classes[mm.span_class(g, final, covered)] += 1
            c.update({"gold_spans": 1, "gold_chars": b - a, "covered_gold_chars": covered,
                      "uncovered_gold_chars": b - a - covered, "gold_alnum_chars": alnum,
                      "covered_gold_alnum_chars": covered_alnum,
                      "leaked_gold_alnum_chars": alnum - covered_alnum})
            if covered == b - a:
                c["complete_gold_spans"] += 1
                complete += 1
            else:
                c["partial_gold_spans" if covered else "untouched_gold_spans"] += 1
        c["fully_masked_positive_rows"] += int(complete == len(gold) and status == "ok")
        c["released_positive_rows"] += int(status == "ok")

    def report(self):
        keys = ("rows", "positive_rows", "fully_masked_positive_rows", "released_positive_rows",
                "gold_spans", "complete_gold_spans", "partial_gold_spans", "untouched_gold_spans",
                "gold_chars", "covered_gold_chars", "uncovered_gold_chars", "gold_alnum_chars",
                "covered_gold_alnum_chars", "leaked_gold_alnum_chars", "text_chars", "masked_chars",
                "excess_masked_chars", "positive_excess_masked_chars", "positive_nongold_chars",
                "final_mask_entities", "ok_rows", "blocked_rows", "uncovered_chars", "rows_with_uncovered_chars")
        out: dict[str, Any] = {key: self.counts[key] for key in keys}
        clean: dict[str, Any] = {key: self.clean[key] for key in ("rows", "masked_rows", "masked_chars", "text_chars", "ok_rows", "blocked_rows")}
        ratio = lambda a, b: a / b if b else None
        out["ratios"] = {
            "complete_gold_spans": ratio(out["complete_gold_spans"], out["gold_spans"]),
            "fully_masked_positive_rows": ratio(out["fully_masked_positive_rows"], out["positive_rows"]),
            "released_fully_masked_positive_rows": ratio(out["fully_masked_positive_rows"], out["released_positive_rows"]),
            "leaked_gold_alnum_chars": ratio(out["leaked_gold_alnum_chars"], out["gold_alnum_chars"]),
            "positive_excess_chars": ratio(out["positive_excess_masked_chars"], out["positive_nongold_chars"]),
        }
        clean["masked_row_rate"] = ratio(clean["masked_rows"], clean["rows"])
        clean["masked_char_rate"] = ratio(clean["masked_chars"], clean["text_chars"])
        out["clean_controls"] = clean
        out["final_mask_classification"] = dict(self.classes)
        out["row_rate_wilson_95"] = {
            "fully_masked_positive_rows": wilson(out["fully_masked_positive_rows"], out["positive_rows"]),
            "released_fully_masked_positive_rows": wilson(out["fully_masked_positive_rows"], out["released_positive_rows"]),
            "clean_masked_rows": wilson(clean["masked_rows"], clean["rows"]),
            "clean_ok_rows": wilson(clean["ok_rows"], clean["rows"]),
            "ok_rows": wilson(out["ok_rows"], out["rows"]),
            "blocked_rows": wilson(out["blocked_rows"], out["rows"]),
            "rows_with_uncovered_chars": wilson(out["rows_with_uncovered_chars"], out["rows"]),
        }
        if sum(self.classes.values()) != out["gold_spans"] or sum(out[k] for k in ("complete_gold_spans", "partial_gold_spans", "untouched_gold_spans")) != out["gold_spans"]:
            raise EvaluationError("eval_count_mismatch")
        return out


class EvaluationAggregate:
    def __init__(self):
        self.overall = Aggregate()
        self.languages, self.labels, self.families = {}, {}, {}

    def add(self, row, result):
        if not isinstance(result, dict) or result.get("status") not in ("ok", "blocked"):
            raise EvaluationError("eval_pipeline_result")
        final = result.get("entities")
        completion = result.get("completion")
        if not isinstance(completion, dict) or "uncovered_chars" not in completion:
            raise EvaluationError("eval_completion_schema")
        if not isinstance(result.get("masked_text"), str):
            raise EvaluationError("eval_pipeline_result")
        if result["status"] == "blocked" and result["masked_text"]:
            raise EvaluationError("eval_blocked_has_output")
        args = (row["text"], row["gold"], final, result["status"], completion["uncovered_chars"])
        self.overall.add(*args)
        self.languages.setdefault(row["language"], Aggregate()).add(*args)
        self.families.setdefault(row["family"], Aggregate()).add(*args)
        for label in sorted({g["label"] for g in row["gold"]}):
            selected = [g for g in row["gold"] if g["label"] == label]
            self.labels.setdefault(label, Aggregate()).add(row["text"], selected, final,
                                                         result["status"], completion["uncovered_chars"],
                                                         all_gold=row["gold"])

    def report(self):
        return {"overall": self.overall.report(),
                "per_language": {k: v.report() for k, v in sorted(self.languages.items())},
                "per_gold_label": {k: v.report() for k, v in sorted(self.labels.items())},
                "per_family": {k: v.report() for k, v in sorted(self.families.items())}}


class BlindCustody:
    """Exclusive run lock plus durable started reservations: failure consumes an arm.

    A successful run appends exactly one final RECEIPTS line. STARTED is separate
    so interruption cannot reopen the same blind arm. The check's override cannot
    be used by the CLI to redirect production custody.
    """
    def __init__(self, root, profile, model_sha256, dataset_sha256, check=False, version="v7"):
        if version not in BLIND_VERSIONS:
            raise EvaluationError("eval_dataset_version")
        if not isinstance(profile, str) or not _digest(model_sha256) or not _digest(dataset_sha256):
            raise EvaluationError("eval_blind_custody_binding")
        if CHECK_RECEIPTS_ENV in os.environ and not check:
            raise EvaluationError("eval_check_override_forbidden")
        self.path = Path(os.environ[CHECK_RECEIPTS_ENV]) if check else Path(root) / f"artifacts/runs/blind-{version}/RECEIPTS.jsonl"
        self.started = self.path.with_name(self.path.name + ".STARTED")
        self.profile, self.model = profile, model_sha256
        self.dataset = dataset_sha256
        self.lock = None
        self.finished = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = open(self.path.with_name(self.path.name + ".lock"), "a", encoding="utf-8")
        try:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise EvaluationError("eval_blind_busy") from None
        try:
            for path in (self.path, self.started):
                if path.exists():
                    for line in read_bounded(path, 8 * 1024 * 1024).splitlines():
                        if not line.strip():
                            continue
                        entry = _json(line)
                        if not isinstance(entry, dict) or not isinstance(entry.get("profile"), str) or not _digest(entry.get("model_sha256")):
                            raise EvaluationError("eval_blind_receipt_schema")
                        if (entry["profile"], entry["model_sha256"]) == (self.profile, self.model):
                            raise EvaluationError("eval_blind_repeat_forbidden")
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def _append(self, path, entry):
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def reserve(self):
        self._append(self.started, {"profile": self.profile, "model_sha256": self.model,
                                   "dataset_sha256": self.dataset, "time": utc_now()})

    def finish(self, metrics_sha256):
        if self.finished or not _digest(metrics_sha256):
            raise EvaluationError("eval_blind_receipt_state")
        self._append(self.path, {"profile": self.profile, "model_sha256": self.model,
                                "dataset_sha256": self.dataset, "time": utc_now(),
                                "metrics_sha256": metrics_sha256})
        self.finished = True

    def __exit__(self, *_):
        if self.lock is not None and not self.lock.closed:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_UN)
            self.lock.close()


@contextmanager
def quiet_libraries():
    """Suppress native/Python diagnostics that might contain input fragments."""
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(fd) for fd in (1, 2)]
    try:
        with open(os.devnull, "w") as sink:
            for fd in (1, 2):
                os.dup2(sink.fileno(), fd)
            yield
            sys.stdout.flush()
            sys.stderr.flush()
    finally:
        for fd, original in zip((1, 2), saved):
            os.dup2(original, fd)
            os.close(original)
