#!/usr/bin/env python3
"""Value-free exact-hash overlap of the two second-set samples with train-v6, its dev file and EXT-DEV."""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation import evaluate_external as ee

def hashes(path):
    out, families = set(), collections.Counter()
    for line in Path(path).read_text().splitlines():
        r = json.loads(line)
        out.add(ee.text_sha(r['text']))
        families[r.get('family', '?').split('-')[0]] += 1
    return out, families

import os
# train-v6 lives only in the main checkout (git-ignored); set PG_MAIN_ROOT when run from a worktree.
art = Path(os.environ.get('PG_MAIN_ROOT', ROOT)) / 'data/local/artifacts/train-v6'
train, train_f = hashes(art / 'train-v6.jsonl')
dev, _ = hashes(art / 'dev-v6-ext.jsonl')
extdev = {r['text_sha256'] for r in ee.load_data('ext-dev')[0]}
gretel_train = {ee.text_sha(t) for lang in ee.LANGUAGES
                for t in __import__('pyarrow.parquet', fromlist=['x']).read_table(ROOT / 'data/local/external/gretel-finance-7b844d1' / (lang + '_train.parquet'), columns=['generated_text'])['generated_text'].to_pylist()}
result = {'train_v6_texts': len(train), 'dev_v6_ext_texts': len(dev), 'ext_dev_texts': len(extdev),
          'gretel_train_texts': len(gretel_train), 'train_v6_texts_equal_to_gretel_train_texts': len(train & gretel_train),
          'train_v6_family_prefix_counts': dict(train_f.most_common(12))}
for name in ('nemotron', 'ai4privacy'):
    hs = {r['text_sha256'] for r in ee.load_second(name)[0]}
    result[name] = {'sample_texts': len(hs), 'overlap_train_v6': len(hs & train), 'overlap_dev_v6_ext': len(hs & dev),
                    'overlap_ext_dev': len(hs & extdev), 'overlap_gretel_train': len(hs & gretel_train)}
Path(__file__).with_name('overlap.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
