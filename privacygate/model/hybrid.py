"""Regex, mBERT and hybrid span detectors returning char spans [{start,end,label,source}].

Never prints or logs text. mBERT needs torch/transformers (training venv); regex/policies are stdlib.
"""
from privacygate.detect import detect as _regex_detect
from privacygate import mbert_data as md

DEFAULT_MODEL_DIR = md.ROOT / "models" / "full-1"
RULE_LABELS = ("EMAIL", "IBAN")


def regex(text):
    return [dict(s, source="regex") for s in _regex_detect(text)]


class Mbert:
    """Loads model+tokenizer once. raw(texts) -> per text a list of windows (offsets, label names, confidences);
    spans(raw_text, thr) decodes to char spans; tokens with max-softmax < thr become 'O'."""

    def __init__(self, model_dir=DEFAULT_MODEL_DIR, tok=None, device=None):
        import torch
        from transformers import AutoModelForTokenClassification
        self.torch = torch
        self.device = device or torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.tok = tok or md.load_tokenizer()
        self.model = AutoModelForTokenClassification.from_pretrained(model_dir).to(self.device).eval()
        self.id2label = {int(k): v for k, v in self.model.config.id2label.items()}

    def raw(self, texts, bs=32):
        torch = self.torch
        items = []  # (text_index, ids, offs)
        for ti, t in enumerate(texts):
            for ids, offs in md.encode(self.tok, t):
                items.append((ti, ids, offs))
        order = sorted(range(len(items)), key=lambda i: len(items[i][1]))  # similar lengths per batch
        out = [[] for _ in texts]
        with torch.no_grad():
            for b in range(0, len(order), bs):
                batch = [items[i] for i in order[b:b + bs]]
                n = max(len(x[1]) for x in batch)
                ids = torch.zeros(len(batch), n, dtype=torch.long)
                att = torch.zeros(len(batch), n, dtype=torch.long)
                for i, x in enumerate(batch):
                    ids[i, :len(x[1])] = torch.tensor(x[1]); att[i, :len(x[1])] = 1
                prob = self.model(input_ids=ids.to(self.device), attention_mask=att.to(self.device)).logits.float().softmax(-1)
                conf, arg = prob.max(-1)
                conf, arg = conf.cpu().tolist(), arg.cpu().tolist()
                for i, x in enumerate(batch):
                    L = len(x[1])
                    out[x[0]].append((x[2], [self.id2label[a] for a in arg[i][:L]], conf[i][:L]))
        return out

    def raw_probabilities(self, texts, bs=8):
        """Opt-in full softmax windows, in memory only; legacy raw is unchanged."""
        import numpy as np
        torch = self.torch
        items = [(ti, ids, offs) for ti, text in enumerate(texts)
                 for ids, offs in md.encode(self.tok, text)]
        order = sorted(range(len(items)), key=lambda i: len(items[i][1]))
        out = [[] for _ in texts]
        with torch.no_grad():
            for b in range(0, len(order), bs):
                batch = [items[i] for i in order[b:b + bs]]
                n = max(len(x[1]) for x in batch)
                ids = torch.zeros(len(batch), n, dtype=torch.long)
                att = torch.zeros(len(batch), n, dtype=torch.long)
                for i, x in enumerate(batch):
                    ids[i, :len(x[1])] = torch.tensor(x[1])
                    att[i, :len(x[1])] = 1
                prob = self.model(input_ids=ids.to(self.device),
                                  attention_mask=att.to(self.device)).logits.float().softmax(-1)
                prob = prob.cpu().numpy()
                for i, (ti, token_ids, offs) in enumerate(batch):
                    out[ti].append((offs, np.array(prob[i, :len(token_ids)], copy=True)))
        return out

    @staticmethod
    def decode_probabilities(windows, id2label, name_threshold=None):
        """Convert probabilities to the legacy window contract before BIO decode.

        Override ANY argmax winner when the summed B/I PERSONNAME mass meets
        the threshold; choose its more probable BIO tag. Other tokens retain
        their original winner and confidence. No additional confidence filter.
        """
        import numpy as np
        labels = [id2label[i] for i in range(len(id2label))]
        bi = [labels.index(tag + "-PERSONNAME") for tag in ("B", "I")]
        raw = []
        for offs, probabilities in windows:
            prob = np.asarray(probabilities)
            arg = prob.argmax(axis=-1)
            conf = prob[np.arange(len(arg)), arg].copy()
            if name_threshold is not None:
                mass = prob[:, bi].sum(axis=-1)
                override = mass >= name_threshold
                arg[override] = np.asarray(bi)[prob[override][:, bi].argmax(axis=-1)]
                conf[override] = mass[override]
            raw.append((offs, [labels[int(a)] for a in arg], conf.tolist()))
        return raw

    @staticmethod
    def average_probabilities(first, second):
        """Aligned tokenizer windows only; refuse mismatched offsets/shapes."""
        if len(first) != len(second):
            raise ValueError("ensemble_windows_mismatch") from None
        averaged = []
        for (offs, p), (other_offs, q) in zip(first, second):
            if offs != other_offs or p.shape != q.shape:
                raise ValueError("ensemble_windows_mismatch") from None
            averaged.append((offs, (p + q) * 0.5))
        return averaged

    @staticmethod
    def spans(raw_text, thr=0.0):
        found = set()
        for offs, names, conf in raw_text:
            names = [n if c >= thr else "O" for n, c in zip(names, conf)]
            found |= md.decode(offs, names)
        return [{"start": s, "end": e, "label": l, "source": "mbert"} for s, e, l in sorted(found)]

    @staticmethod
    def spans_with_scores(raw_text, thr=0.0):
        """The same decoded spans, with minimum contributing token confidence.

        Duplicate spans from overlapping windows retain the minimum window score.
        Scores are in-memory evidence, not calibrated privacy probabilities. The
        original spans()/detect() output and threshold behavior remain unchanged.
        """
        found = {}
        for offs, names, conf in raw_text:
            names = [n if c >= thr else "O" for n, c in zip(names, conf)]
            for start, end, label in md.decode(offs, names):
                scores = [float(c) for o, n, c in zip(offs, names, conf)
                          if o is not None and o[0] < end and start < o[1]
                          and n != "O" and n.split("-", 1)[1] == label]
                score = min(scores) if scores else None
                key = (start, end, label)
                if key not in found or found[key] is None:
                    found[key] = score
                elif score is not None:
                    found[key] = min(found[key], score)
        return [{"start": s, "end": e, "label": l, "source": "mbert", "score": found[(s, e, l)]}
                for s, e, l in sorted(found)]

    def detect(self, text, thr=0.0):
        return self.spans(self.raw([text])[0], thr)

    def detect_with_scores(self, text, thr=0.0):
        return self.spans_with_scores(self.raw([text])[0], thr)


def _overlap(a, b):
    return a["start"] < b["end"] and b["start"] < a["end"]


def union(rx, mb):
    """All spans; overlapping spans merge into their union. Label from regex if regex took part, else mBERT."""
    items = sorted([dict(s, source="regex") for s in rx] + [dict(s, source="mbert") for s in mb], key=lambda s: (s["start"], -s["end"]))
    out, group = [], []

    def flush():
        if not group:
            return
        srcs = {g["source"] for g in group}
        pick = next((g for g in group if g["source"] == "regex"), group[0])
        out.append({"start": min(g["start"] for g in group), "end": max(g["end"] for g in group), "label": pick["label"],
                    "source": "both" if len(srcs) > 1 else srcs.pop()})

    end = -1
    for s in items:
        if group and s["start"] >= end:
            flush(); group = []
        end = max(end, s["end"]) if group else s["end"]
        group.append(s)
    flush()
    return out


def rules_first(rx, mb):
    """Regex EMAIL/IBAN spans win; mBERT spans overlapping them are dropped; other mBERT spans are kept.
    Non-rule regex labels do not exist in detect(), so all regex spans count as rules."""
    rules = [dict(s, source="regex") for s in rx if s["label"] in RULE_LABELS]
    keep = [dict(s, source="mbert") for s in mb if not any(_overlap(s, r) for r in rules)]
    return sorted(rules + keep, key=lambda s: (s["start"], s["end"]))
