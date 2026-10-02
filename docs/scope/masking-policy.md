# All-personal-information masking policy

Accepted target: mask ALL personal information, including names, telephone numbers, identity numbers and addresses belonging to a person. These examples are non-exhaustive. Direct identifiers, person-linked attributes, sensitive information, indirect identifiers and identifying combinations remain in scope regardless of whether a current label exists. This is a synthetic research target, not an achieved privacy guarantee.

## Negative-label policy

Keep three separate pools; do not collapse uncertainty into the outside (`O`) label:

| Pool | Admission rule | Training/measurement treatment |
|---|---|---|
| Clearly clean negative | Constructed synthetic non-personal context with no personal attributes, person-linked identifiers, identifying combinations or unresolved references; record construction intent and provenance. | May be all-`O` only after this policy check. Regex silence alone is insufficient. |
| Ambiguous reference | Order, tracking, serial, ticket, license, account or reference code whose person linkage cannot be established or ruled out. | Exclude from clean-negative augmentation; retain a separately identified ambiguity pool, without claiming false positives under the new policy. |
| Positive personal identifier/information | Synthetic context explicitly links an identifier or attribute to a person, including a person's order/tracking/reference code. | Mask regardless of checksum or shape. If no suitable label exists, record a coverage/schema gap; do not silently force `O` or invent a supported label. |

Order/tracking/serial/reference codes are context-dependent, NOT automatically safe negatives. A valid or invalid IBAN checksum, an unusual prefix, a short number, a price-like shape or a version-like shape cannot settle person linkage. Public-looking information is not automatically non-personal. Clean negatives must be clean for the all-personal-information target, not merely EMAIL-free, IBAN-free or free of the current annotation taxonomy. A row with no annotations is not independently certified non-personal.

Unknown linkage requires abstention or exclusion from the clean-negative pool, not an assumption that information is safe to expose. This policy records the research target; it does not claim the current CLI can detect or enforce every case. Genuine non-personal quantities, specifications and generic operational facts may be used only in contexts constructed to have no personal linkage or personal narrative. Do not put concrete personal values in tools, logs, examples or reports.

## Historical benchmark interpretation (unchanged)

`scripts/make_challenge.py`: `T['iban_decoy']`, `make_decoy`, and the `generate` branch guarded by `if not detect(text)` define the frozen decoy convention. Codes are placed in order/tracking/reference/serial contexts; absence of a regex detection was used to select negatives. That convention does not establish absence of personal linkage.

`docs/runs/compare-dev/metrics.json#/arms/<ARM>/challenge_dev/decoy_fp_rate` and `.../overmasked_char_rate_clean_decoy` measure disagreement with those historical labels. They are benchmark-convention results, NOT proven masking errors under the accepted policy. `clean_fp_rate` is likewise scoped to the historical synthetic clean stratum, not a guarantee on arbitrary clean text. Regex zero FP on constructed regex negatives is not robustness evidence.

Keep all frozen challenge, Micro split and historical result files byte-unchanged. Do not relabel historical dev/test, regenerate their files or rescore them in this preparation. Any future policy-aligned benchmark needs a separately versioned protocol and explicit approval; it must not silently replace the existing benchmark or access the final test.

## Claim boundary

Current checkpoint/rule support and historical label recall are inventoried separately in `coverage.json` and `coverage.md`. Missing categories, contextual linkage and whole-person-address recall remain unknown. No finite taxonomy proves that all personal information is covered; a missed category is a coverage gap, not an exemption from the target. Synthetic-only local research; no production, compliance or privacy guarantee.
