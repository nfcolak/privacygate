#!/usr/bin/env python3
"""Value-free miss/excess shape counts for the v6-chosen arm, from the saved entity receipts.

Output is counts of character-class shapes per label; no text or span values are printed or stored.
Usage: shapes.py <gretel|nemotron|ai4privacy> <receipts.jsonl> <out.json>
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation import evaluate_external as ee
from privacygate.masking_metrics import interval_union, intersection

CURRENCY = set('$€£¥') | {'CHF'}


def shape(text, a, b):
    s = text[a:b].strip()
    if not s:
        return 'blank'
    before = text[max(0, a - 4):a]
    cur = any(c in before + s for c in '$€£¥') or bool(re.search(r'\b(USD|EUR|CHF|GBP)\b', text[max(0, a - 6):b + 6]))
    if '@' in s:
        return 'email-like'
    if re.search(r'(https?://|www\.|\.(com|org|net|io|de|fr|it|es|ch)\b)', s, re.I):
        return 'url-like'
    if re.fullmatch(r'[\d\s.,:/\-+()%]+', s):
        d = sum(c.isdigit() for c in s)
        kind = 'digits' + ('<=4' if d <= 4 else '5-9' if d <= 9 else '10+')
        return kind + ('+currency' if cur else '') + ('+decimal' if re.search(r'\d[.,]\d{2}\b', s) else '')
    words = s.split()
    if all(w[:1].isupper() and w[1:].islower() for w in words if w.isalpha()) and all(w.isalpha() for w in words):
        return 'capitalised-words(n={})'.format(min(len(words), 4))
    if s.isupper():
        return 'upper'
    if s.islower():
        return 'lower'
    if any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
        return 'mixed-alnum'
    return 'other'


def pieces(interval, cut, n):
    """interval minus cut (both interval lists), as interval list."""
    inside = intersection(interval, cut, n)
    result, pos = [], 0
    for a, b in interval:
        cur = a
        for x, y in inside:
            if y <= cur or x >= b:
                continue
            if x > cur:
                result.append((cur, x))
            cur = max(cur, y)
        if cur < b:
            result.append((cur, b))
    return result


def main():
    name, receipts, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    rows = ee.load_data('test')[0] if name == 'gretel' else ee.load_second(name)[0]
    saved = [json.loads(line) for line in receipts.read_text().splitlines()]
    assert len(saved) == len(rows)
    excess, miss = defaultdict(Counter), defaultdict(Counter)
    excess_chars, miss_chars = defaultdict(Counter), defaultdict(Counter)
    for row, res in zip(rows, saved):
        text, n = row['text'], len(row['text'])
        ann = interval_union([(s['start'], s['end']) for s in row['all_annotations']], n)
        for ent in res['entities']:
            for a, b in pieces(interval_union([(ent['start'], ent['end'])], n), ann, n):
                k = shape(text, a, b)
                excess[ent['label']][k] += 1
                excess_chars[ent['label']][k] += sum(c.isalnum() for c in text[a:b])
        mask = interval_union([(s['start'], s['end']) for s in res['entities']], n)
        for g in row['gold']:
            for a, b in pieces([(g['start'], g['end'])], mask, n):
                k = shape(text, a, b)
                miss[g['label']][k] += 1
                miss_chars[g['label']][k] += sum(c.isalnum() for c in text[a:b])

    def top(counts, chars, limit):
        flat = [(label, k, c, chars[label][k]) for label, ks in counts.items() for k, c in ks.items()]
        flat.sort(key=lambda t: -t[3])
        return [dict(label=l, shape=k, pieces=c, alnum_chars=ch) for l, k, c, ch in flat[:limit]]
    result = {'set': name, 'receipts': receipts.name, 'arm': 'v6-chosen',
              'top_miss_shapes': top(miss, miss_chars, 12), 'top_excess_shapes': top(excess, excess_chars, 12),
              'miss_alnum_by_label': {k: sum(v.values()) for k, v in miss_chars.items()},
              'excess_alnum_by_entity_label': {k: sum(v.values()) for k, v in excess_chars.items()}}
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'set': name, 'miss_top': result['top_miss_shapes'][:5], 'excess_top': result['top_excess_shapes'][:5]}))


if __name__ == '__main__':
    main()
