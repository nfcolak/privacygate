"""Conservative regex detectors: EMAIL and checksum-valid IBAN."""
import re

EMAIL_RE = re.compile(r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
IBAN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]{1,4}){2,8}(?![A-Za-z0-9])")


def iban_valid(s):
    s = s.replace(" ", "")
    if not (15 <= len(s) <= 34) or not s.isalnum():
        return False
    r = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1


def detect(text):
    """Return sorted, non-overlapping spans [{start,end,label}].

    Overlaps: earlier start wins, then longer span, then label name.
    """
    cands = [(m.start(), m.end(), "EMAIL") for m in EMAIL_RE.finditer(text)]
    for m in IBAN_RE.finditer(text):
        if iban_valid(m.group()):
            cands.append((m.start(), m.end(), "IBAN"))
    cands.sort(key=lambda c: (c[0], -(c[1] - c[0]), c[2]))
    out, last = [], 0
    for s, e, l in cands:
        if s >= last:
            out.append({"start": s, "end": e, "label": l})
            last = e
    return out


def mask(text):
    spans = detect(text)
    parts, pos = [], 0
    for sp in spans:
        parts.append(text[pos:sp["start"]])
        parts.append("[" + sp["label"] + "]")
        pos = sp["end"]
    parts.append(text[pos:])
    return {"masked_text": "".join(parts), "entities": spans}
