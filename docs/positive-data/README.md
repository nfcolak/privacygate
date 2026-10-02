# Synthetic positive PII augmentation (pos-v1)

Status: code + generated local data only. NO training, inference or scoring was run; no test split exists for this data.
Synthetic research target, not a privacy guarantee. All-personal-information masking remains the target, not an achieved result.

Artifacts (generated JSONL is gitignored under data/augmentation/; only code and the value-free manifest are committed):
- data/augmentation/positive-train.jsonl  630 rows, 105 templates (3 per family/language, 6 variants each)
- data/augmentation/positive-dev.jsonl    280 rows,  70 templates (2 per family/language, 4 variants each); DEVELOPMENT only
- docs/positive-data/manifest.json        counts, hashes, disjointness flags, generator revision (pos-v1), template-set hash

Generate / verify:

    env -u PYTHONPATH python3 scripts/make_positives.py
    env -u PYTHONPATH python3 scripts/make_positives.py --verify

Families (EN/DE/FR/IT/ES each, present in both splits): names, phone, identity (IDCARDNUM, PASSPORTNUM, DRIVERLICENSENUM),
address (STREET, BUILDINGNUM, ZIPCODE, CITY plus the owner's name), username, account, personalref. Every name, number, address
component and code in a row is a labelled span; fixed template text contains no digits. Spans are recorded during string
assembly (no find/replace), and entries hold only start/end/label.

## Labels

Existing exact labels: GIVENNAME, SURNAME, TELEPHONENUM, IDCARDNUM, PASSPORTNUM, DRIVERLICENSENUM, STREET, BUILDINGNUM, CITY, ZIPCODE.
New, initial proposed operational labels (not a taxonomy, not a legal classification, no trained support, not exhaustive):
- USERNAME: handle/account name explicitly stated as belonging to an invented person.
- ACCOUNTNUM: non-IBAN membership/customer/loyalty/library number explicitly tied to an invented person.
- PERSONALREF: order/tracking/case reference explicitly tied to an invented person. Shapes vary; some are IBAN-shaped strings with an
  invalid checksum (23 rows) and remain positive: an invalid checksum never makes a person-linked code negative.
Generic codes without person context are NOT labelled personal here; they belong to the ambiguity pool of docs/scope/masking-policy.md.
No catch-all label is introduced for unsupported details. Health, narrative, biometric and other categories remain open.

## Split protocol

Train and dev use different template pools (template IDs and template strings disjoint) and different invented-name onsets, street stems,
cities and handle stems; code-like values already used in train are rejected in dev. The manifest records disjoint flags for template IDs,
template strings, row IDs, exact texts and the value pools. Pools are authored, not randomly split, so dev is NOT evidence of
generalisation beyond this generator: dev templates are written by the same author in the same style (semantic independence is not proven).
Do not feed dev rows to training. `load_positive_file(path, allowed_split="train")` rejects a dev file unless allowed_split="dev".

## Loader

`privacygate.positive_data.load_positive_file(path, allowed_split="train", forbid_ids=()) -> (rows, binding)`: regular file only, at most
16 MiB, 20000 lines, 32 KiB per line, 2000 chars per text, 32 annotations per row; exact six row keys and three mask keys; ints only
(bool rejected); 0 <= start < end <= len; sorted non-overlap; label allowlist; unique row IDs (and disjoint from forbid_ids); split must equal
allowed_split. Errors are fixed `pos_*` codes and never echo input. binding = sha256 of file bytes, rows, per_language, per_label, templates, split.
train_mbert.py is not wired to it yet.

## Limitations

Names are invented syllable compositions and may coincide with real people by chance; cities are real public place names used as address
components; phone numbers use reserved/fictional-style ranges where known but formats are artificial and not verified to be unassigned;
identity numbers are random strings with no checksum or real national format; no value is a verified real contact or identity. Low
lexical diversity (few templates, modest variants); a model trained on this may learn the template cues. Automated structural checks in
--verify are not human annotation review.
