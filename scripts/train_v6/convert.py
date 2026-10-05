"""Read scorer constants via AST without executing its frozen evaluation pipeline."""
import ast
from collections import Counter, defaultdict
import json


def require(condition, code):
    if not condition:
        raise ValueError(code)


def scorer_constants(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    wanted = {'MAPPING', 'OUT', 'EXPECTED_HASH'}
    result = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    result[target.id] = ast.literal_eval(node.value)
    require(result.keys() == wanted, 'scorer_constants_missing')
    return result['MAPPING'], result['OUT'], result['EXPECTED_HASH']


def merge_per_label(spans):
    grouped = defaultdict(list)
    for span in spans:
        grouped[span['label']].append((span['start'], span['end']))
    result = []
    for label, pairs in grouped.items():
        merged = []
        for a, b in sorted(pairs):
            if merged and a < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        result.extend({'start': a, 'end': b, 'label': label} for a, b in merged)
    return sorted(result, key=lambda span: (span['start'], span['end'], span['label']))


def convert(row, language, split, ordinal, mapping, outside, stats):
    text = row['generated_text']
    require(isinstance(text, str), 'source_text_type')
    require(row['language'] == language, 'source_language_mismatch')
    spans = json.loads(row['pii_spans'])
    require(isinstance(spans, list), 'source_annotation_schema')
    # All source offsets, including OUT offsets, are checked. Unknown labels fail closed.
    for span in spans:
        require(isinstance(span, dict) and set(span) >= {'start', 'end', 'label'}, 'source_annotation_schema')
        require(span['label'] in set(mapping) | outside, 'unknown_source_label')
        if (type(span['start']) is not int or type(span['end']) is not int or
                not 0 <= span['start'] < span['end'] <= len(text)):
            stats['dropped_invalid_offsets'] += 1
            return None
    source_counts = Counter(span['label'] for span in spans)
    gold_before = [dict(start=span['start'], end=span['end'], label=mapping[span['label']])
                   for span in spans if span['label'] in mapping]
    gold = merge_per_label(gold_before)
    if any(a['end'] > b['start'] for a, b in zip(gold, gold[1:])):
        stats['dropped_cross_label_overlaps'] += 1
        return None
    # OUT remains O: a mapped/OUT intersection cannot satisfy that contract, so drop it.
    if any(s['start'] < g['end'] and g['start'] < s['end']
           for s in spans if s['label'] in outside for g in gold):
        stats['dropped_mapped_out_of_scope_overlaps'] += 1
        return None
    stats['same_mapped_label_merges'] += len(gold_before) - len(gold)
    stats['source_label_counts'].update(source_counts)
    stats['out_of_scope_label_counts'].update(span['label'] for span in spans if span['label'] in outside)
    return {'case_id': 'v6-gretel-{}-{:06d}'.format(language, ordinal),
            'family': 'gretel_finance_train', 'language': language_code(language),
            'split': split, 'text': text, 'gold': gold}


def language_code(language):
    from .spec import LANGUAGES
    return LANGUAGES[language]


def conversion_stats():
    return {'dropped_invalid_offsets': 0, 'dropped_cross_label_overlaps': 0,
            'dropped_mapped_out_of_scope_overlaps': 0, 'same_mapped_label_merges': 0,
            'source_label_counts': Counter(), 'out_of_scope_label_counts': Counter()}
