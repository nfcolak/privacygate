# Training/dev generator v2

Synthetic development material under the frozen `privacy-policy-v1` policy.
No external packages, network access, real-person lists, Faker or training.

## Run

From the repository root:

    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 scripts/make_train_v2.py
    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 scripts/make_train_v2.py --verify
    env -u PYTHONPATH python3 smoke.py

Generation refuses if either JSONL or the manifest already exists. Verification
is read-only. Both modes log aggregates or value-free error codes only.
The JSONLs remain git-ignored; commit the generator and documentation, not data.
The manifest is compact JSON to keep this artifact below 200 lines.

## Dataset

| Split | Rows | Clean rows | Per language | Matched pairs | Long letters |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 16,000 | 6,400 (40%) | 3,200 | 4,000 | 465 |
| dev | 2,000 | 800 (40%) | 400 | 500 | 55 |

Languages are EN/DE/FR/IT/ES. Each split uses 295 template IDs. Of the 80
language-specific negative templates in each split, 50 have positive twins.
Every occurrence of these templates produces both rows with the identical
payload and an explicit change from non-person context to person linkage.

Clean constructions cover invoice/order/SKU codes, software versions, prices,
dimensions, generic dates and timetables, invented brands and organisations,
public venues, rooms/gates/platforms, equipment age statistics and quantities.
Positive constructions cover all 16 canonical labels. Letters repeat each
personal value three times and reach up to 2,450 characters. Other rows are
short prose. All names, streets, cities and organisational names are invented;
emails use reserved `.invalid` domains. Financial values are mathematical
fixtures: MOD97-valid IBANs and Luhn-valid cards, not issued credentials.

## Gold and split isolation

Gold is assembled from explicitly typed placeholders, not substring searches.
Each Python-string span covers the whole value, including internal separators,
attached titles, phone extension phrases and complete postal routing regions.
Salutations, surrounding prose and sentence punctuation stay outside gold.
Leading `@` on handles and `+` on phones are part of the value. Multiline postal
addresses use deliberate routing lines, never OCR corruption inside components.

Train/dev select different prose constructions before generating rows. The
family-grouped numeric pool slices are `[0,512)` and `[512,640)`; invented
lexical components use separate halves of each pool. Age ranges and birth years
are disjoint too, so dev intentionally has a different age distribution.
The manifest records all template IDs, pool slices, seed, policy hash, both
JSONL hashes, generator hashes and label/language/family/split counts.

`--verify` checks those hashes and aggregates, exact six-field schema, integer
half-open offsets, ordered non-overlapping whole-value boundaries, checksums,
clean share, language balance, pair payload identity, full catalog coverage and
train/dev value/template isolation. Exact deterministic replay additionally
checks every row and every gold boundary against its originating construction.

Reserved blind families are never generated: key/value forms, chat lines,
email signatures, mixed-language documents or OCR-like value noise. No blind
v3/v4 data or stress-generator code is read or imported.
