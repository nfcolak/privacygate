# Dataset provenance and license check (stage 1)

Candidate: `ai4privacy/openpii-masking-mini-10k` at revision `ad851605dfd3c1a3fefe51c8d8f1cc0e4a6853d0` (S1, S3).
Retrieved: 2026-09-30. Source IDs [S#] refer to `provenance-sources.json`, which holds URLs, revisions and evidence paraphrases.
Scope: provenance and license only. No dataset rows were read for this document; the numerical row audit and split design belong to the sibling work. This is not legal advice.

## Decision: CONDITIONAL GO for local, controlled research

Use the pinned subset locally for research experiments, treating the data as synthetic-declared but unverified. This is not a legal clearance, not a finding that the data is synthetic, and not approval for production or any privacy/compliance claim. The dataset is neither replaced nor banned on this evidence.

## What the sources say (publisher claims, not established facts)

- The pinned subset card declares CC BY 4.0, names `ai4privacy/pii-masking-openpii-1m` as its source, carries a `synthetic` tag, and says 9,000 train / 1,000 validation, 23 languages, 19 labels [S1, S3]. It contains no "synthetic PII only" statement, no attribution instruction and no copyright line [S1].
- The upstream card calls the data "1,428,143 synthetic text examples" and states twice that it "contains synthetic PII only - no real personal data is included" [S2]. It gives CC-BY-4.0, copyright Ai Suisse SA, and an attribution instruction [S2].
- Platform metadata agrees on the license (`cc-by-4.0`) and on the `synthetic` tag [S3, S4]. Nothing in these sources describes how the data was generated, and no generation code or dataset-specific provenance document was found on the publisher's GitHub organisation or website [S14, S15].

## The "real PII" wording conflict

- The pinned subset's schema table describes `source_text` as "Original text with real PII" [S1]. The upstream says synthetic only [S2].
- Card history shows the subset's first cards (be19414, f7b4c91) carried the synthetic-only declaration, and the commit that added "real PII" (f5db59e, 2026-04-03) and the pinned head do not [S7, S8, S9]. The sources give no reason for the change. Whether it is a template/wording slip or something else is unresolved.
- Facts established: the two cards disagree textually, and the subset card does not itself repeat the synthetic-only declaration. Not established: that any row belongs to a real person, or that every row is synthetic. A publisher's synthetic claim does not prove every row is synthetic, and structural checks on rows (offsets, duplicates, label counts) cannot establish provenance either way.
- Consequence: handle the data as if it could contain real personal data until clarified. That means local-only storage, no row text in logs or reports, no sending rows to external services, no redistribution of rows. The CC deed itself warns that privacy rights may limit use of licensed material [S13].
- No clarification was sought from the authors (out of scope). Open question to the user: whether to ask the publisher later.

## License obligations as stated by the sources

- Subset: CC BY 4.0 "same as source dataset" [S1]. Upstream: CC-BY-4.0, copyright 2026 Ai Suisse SA; research, commercial use, redistribution and modification permitted subject to attribution; credit "Ai4Privacy / Ai Suisse SA" and link to the upstream repository [S2].
- CC BY 4.0 deed: give appropriate credit, link to the license, indicate if changes were made, no additional restrictions, no warranties [S13]. The deed is a summary; the full legal code was not read.
- Upstream disclaimer: provided "as is", no warranty or liability, users responsible for legal compliance [S2].
- For this project: reports or artifacts derived from the data should carry the attribution above, name the pinned revision, and state modifications (language filtering, splits, relabeling). Project-owned tooling, reports and aggregate numbers are not described by any source as restricted; whether derived model weights carry obligations is not addressed by any source and is not resolved here.
- History: upstream was "All Rights Reserved" on 2026-03-27 and changed to CC-BY-4.0 on 2026-03-31 [S6, S10, S11]. The subset was created on 2026-04-03, after the change [S7]. Retain the retrieval date and pinned revision as evidence of the license state seen. Metadata inconsistency is minor: upstream uses `license: other` + `license_name: cc-by-4.0`, the subset uses `cc-by-4.0` [S3, S4]. No LICENSE file exists in either repository [S3, S4, S5].

## Permissible claimed scope

Allowed wording: "a controlled benchmark on a pinned public subset declared by its publisher to be synthetic, CC BY 4.0; languages EN/DE/FR/IT/ES selected from its 23; results do not represent production or real private data."
Do not claim: that the data is verified synthetic or real-PII-free; legal, GDPR or license clearance; production safety; geographic coverage beyond language. The card counts for the five target languages (EN 1256, FR 918, DE 841, ES 632, IT 625; 4,272 total) are publisher claims to be checked by the row audit [S1].

## EMAIL / IBAN taxonomy implications (pinned metadata only)

- EMAIL is in the subset's 19 labels [S1] and the upstream taxonomy [S2, S12]; it is usable as a shared label with the regex baseline, subject to the row audit.
- IBAN is absent from the subset card and the upstream card and distribution file [S1, S2, S12]; the upstream says extended financial taxonomies are offered separately, not in this dataset [S2]. The closest labels are CREDITCARDNUMBER and TAXNUM; neither is IBAN. So an IBAN claim cannot be evaluated on this data. It needs a separately created, clearly labeled synthetic stratum, and a learned IBAN arm only if that class is added to training. This document does not check the rows for IBAN-shaped text.

## Unresolved conditions (must hold or be resolved before relying on the data)

1. "Real PII" wording vs synthetic-only declaration: unresolved; the publisher has not been asked. Keep the local-only handling above until clarified.
2. Generation method: undocumented in every reachable primary source [S14, S15]. No independent provenance evidence exists.
3. Sibling row audit: counts, languages, labels, offsets, duplicates/leakage must confirm the card claims; any contradiction (e.g. a card figure that does not match) downgrades this decision.
4. Data files at the pinned revision: file hashes are recorded [S5]; whether the data files changed after 2026-04-03 was not diffed [S7]. The pin makes this reproducible but does not prove it is what the card describes.
5. Attribution and change notice included in any artifact that uses or derives from the data.
6. Full CC BY 4.0 legal code not reviewed; any need for legal review of redistribution or model release is not answered here.
7. Unreachable or missing sources: no dataset paper, no GitHub dataset repository, and no full legal code were reached; see `unreachable_or_not_available` in the ledger.
