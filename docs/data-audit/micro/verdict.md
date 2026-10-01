# Stage 2 verdict: openpii-masking-micro-100k (EN/DE/FR/IT/ES)

**Verdict: AUDITED, NOT TRAINING-READY.** Provisional structural manifests only. Selection (ADR-003) does not authorize training. No model/tokenizer was downloaded; no training or evaluation was run.

## Pinned source
- `ai4privacy/openpii-masking-micro-100k`, revision `f95b4e1539657c3d0047d9ad3f20f26675f22c7d` (HF API `sha`, last modified 2026-06-03; `x-repo-commit` header confirmed on every download). Not gated.
- Artifacts (size, SHA256), see `source.json`:
  - `README.md` 3,213 B `287e7363...612fc`
  - `data/train.jsonl` 292,509,371 B `6863d8df...cafa74` (90,000 rows)
  - `data/validation.jsonl` 32,576,568 B `c2175f31...627e5b` (10,000 rows)
- Raw files are gitignored. Outputs: `audit.json`, `output-hashes.json` here; `data/manifests/micro/{selected,excluded,train,dev,test}.jsonl`, `split-policy.json`.

## Measured
- 100,000 rows; schema = Mini 10K fields + `source_dataset` (`base` 87,282 / `asia-pacific` 12,718); 30 languages (card: 30). Embedded split field matches physical files. 724,227 spans (card claims 723,083: differs by 1,144, which are the out-of-taxonomy labels below).
- EN/DE/FR/IT/ES selected: **38,835** = EN 12,503, DE 7,341, FR 8,025, IT 5,453, ES 5,513.
- All annotated character offsets in bounds, no value mismatches, no span overlaps, no masked-text reconstruction mismatch among rows checked (all offsets Python code points).
- **Quarantined (target languages, not repaired): 442 rows**; reason events: inferred_bio_entity_boundary_mismatch 407, inferred_token_crosses_span_boundary 16, bio_class_invalid 34, bio_entity_count_mismatch 34, span_label_invalid 34, inferred_token_span_label_mismatch 3, empty_text 1, token_list_invalid 1 (a row can have several reasons).
- Out-of-taxonomy labels (not among the card's 19): `TIME` (all languages incl. 116 EN spans in 34 target rows, plus a few ORGANISATION/URL/AMOUNT-type labels in non-target languages). These rows are quarantined, so card label list and data disagree.
- `[UNK]` tokens appear in 38,974 rows (mostly non-target scripts); token positions cannot be fully verified without a tokenizer. Unverified, not repaired.
- Duplicates inside Micro (all languages): exact source 1 group / 1 extra row; normalized masked template 14 groups / 30 extra rows (2 groups cross official train/validation); near-template (Jaccard >= 85/100 on 5-grams, same method as Stage 1) 22 matching template pairs. No duplicate uid groups. All duplicates are merged into the same group before splitting.
- **Overlap with Mini 10K (4,272 selected rows, recomputed and cross-checked against the Stage 1 manifests): 317 Micro EN/DE/FR/IT/ES rows** overlap (313 exact; 3 template-only; 1 near-only; 316 by template). They touch Mini train 239, dev 34, test 40, quarantined 4. Handling: **every overlapping Micro row is excluded from all Micro splits** (reasons `mini_overlap_exact/template/near`), so zero overlap with Mini dev/test (checked, 0 in Micro train/dev/test). Note: Micro overlapping Mini *train* is also excluded (conservative).
- Splits (seed `privacygate-stage2-micro-20261001`, same SHA256 group-bucket method 80/10/10 as Stage 1, group-disjoint over exact/template/near): excluded 755 (442 quarantine + 313 overlap, some rows both) -> **train 30,404 / dev 3,835 / test 3,841** = 38,080.
  - train: de 5,766, en 9,765, es 4,261, fr 6,310, it 4,302
  - dev: de 751, en 1,196, es 549, fr 827, it 512
  - test: de 703, en 1,295, es 565, fr 758, it 520
- Cross-split disjointness checked for row_id, exact hash, template hash, group_id: all 0. All 19 labels present in every language/split.

## Provenance (publisher claims, not verified)
- Pinned card (https://huggingface.co/datasets/ai4privacy/openpii-masking-micro-100k/raw/f95b4e1539657c3d0047d9ad3f20f26675f22c7d/README.md): front matter `license: other`, `license_name: cc-by-4.0`; tag `synthetic`; License section: "CC-BY-4.0. Copyright (c) 2026 Ai Suisse SA. Contains **synthetic PII only**, no real personal data." Describes itself as a stratified sample of OpenPII 1.5M (https://huggingface.co/datasets/ai4privacy/pii-masking-openpii-1.5m, whose card also states synthetic PII only).
- Unlike Mini 10K, this card has **no internal real-vs-synthetic conflict** (no "real PII" schema wording). It is a claim only; we cannot prove absence of real PII from the data. The card's "19 labels / 723,083 annotations" and data (TIME and others, 724,227 spans) differ.
- Mini 10K's card cites the 1M dataset; Micro cites 1.5M. Lineage/shared generator between them is unverified; the observed 317 overlaps show they are not independent.
- "license: other" with name cc-by-4.0 is non-standard metadata; attribution to Ai Suisse SA would be needed. Not legal advice.

## Limitations
Structural checks only; no semantic annotation quality review; lexical (not semantic/translation) independence; token alignment unverifiable without a tokenizer (UNK); label taxonomy drift; manifests are provisional.

## Remaining gates before training
1. Explicit user approval for training. 2. Semantic annotation-quality review (sampled, human). 3. Decision on tokenizer-based alignment (needs authorized tokenizer download). 4. Confirm the provenance/attribution position and the label-taxonomy discrepancy with the publisher. 5. Final freeze of splits (currently provisional).

Reproduce: `env -u PYTHONPATH .venv/bin/python scripts/audit_micro.py [--offline] | --verify`.

## Stage 3: mBERT tokenizer alignment (added 2026-10-01)
Tokenizer `google-bert/bert-base-multilingual-cased` @ `3f076fdb1ab68d5b2880cb87a0886f315b8146f8` (fast, offset mapping), run over the provisional Micro train/dev manifests by `scripts/check_alignment.py`; aggregates in `alignment.json`. Scheme: every wordpiece overlapping a span is labelled, first = `B-`, later = `I-`; special tokens ignored. Rows longer than 512 wordpieces use sliding windows (stride 128), none dropped.
- train (30,404 rows, 219,446 spans): 364 spans with a boundary inside a wordpiece in 362 rows; 0 spans lost; 13 rows > 512 wordpieces; [UNK] rate 1.03% (31,795 / 3,097,209).
- dev (3,835 rows, 27,546 spans): 39 broken-boundary spans in 38 rows; 0 spans lost; 1 row > 512; [UNK] rate 1.03% (3,953 / 385,632).
- Rows with a broken boundary are excluded from training and dev evaluation (not repaired): 362 train, 38 dev. This does not change the provisional manifests.
