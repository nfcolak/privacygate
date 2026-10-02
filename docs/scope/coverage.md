# Personal-information coverage (aggregate-only)

Mask ALL personal information, including but not limited to names, phones, identity numbers and a person's address.

This is a target, not achieved coverage. Synthetic research only; no privacy guarantee.

## Reconciled inventory

Checkpoint: 39 BIO labels (including O), 19 entity labels; 2 rule labels. Full-1 historical label order and both checkpoint maps reconcile.
Mini taxonomy matches. Micro also contains 12 hashed out-of-taxonomy bins / 1144 spans; these do not add checkpoint coverage.

## Supported labels and historical recall

Counts are full-population audit span counts, not evaluation. R is historical strict span recall on Micro dev, not person/category recall or current CLI recall.

| Label | Mini spans | Micro spans | mBERT R | rules_first_thr R |
|---|---:|---:|---:|---:|
| AGE | 3969 | 35574 | 0.972572 | 0.972572 |
| BUILDINGNUM | 3650 | 33474 | 0.979250 | 0.978452 |
| CITY | 5476 | 50105 | 0.985959 | 0.984919 |
| CREDITCARDNUMBER | 2551 | 22804 | 1.000000 | 1.000000 |
| DATE | 9662 | 85671 | 0.998487 | 0.998487 |
| DRIVERLICENSENUM | 2376 | 19787 | 0.907258 | 0.904570 |
| EMAIL | 5973 | 54015 | 0.999482 | 0.968427 |
| GENDER | 2399 | 19414 | 0.951657 | 0.948895 |
| GIVENNAME | 9579 | 85017 | 0.863914 | 0.863609 |
| IDCARDNUM | 2491 | 23622 | 0.932636 | 0.926829 |
| PASSPORTNUM | 1749 | 14529 | 0.926733 | 0.918812 |
| SEX | 2148 | 17710 | 0.976351 | 0.976351 |
| SOCIALNUM | 2153 | 17139 | 0.951258 | 0.948113 |
| STREET | 3736 | 34061 | 0.979719 | 0.979719 |
| SURNAME | 8318 | 73012 | 0.856534 | 0.852273 |
| TAXNUM | 2185 | 18728 | 0.970149 | 0.970149 |
| TELEPHONENUM | 4626 | 40440 | 0.995668 | 0.995668 |
| TITLE | 5009 | 47173 | 0.995501 | 0.995501 |
| ZIPCODE | 3421 | 30808 | 0.995008 | 0.995008 |

Exact unrounded values, support and source/key are in `coverage.json`: every numeric evidence object has `source` + JSON Pointer `key`; `sources` resolves paths and SHA256.
Counts: `mini#/overall/entity_counts/<LABEL>` and `micro#/overall_all_languages/entity_counts/<LABEL>`.
R: `metrics#/arms/<ARM>/micro_dev/per_label/<LABEL>/recall` (support at sibling `/support`).

## Requirement map (non-exhaustive)

| Category | Actual labels / rules | Status |
|---|---|---|
| names | GIVENNAME, SURNAME | partial |
| phones | TELEPHONENUM | label_supported |
| identity_numbers | IDCARDNUM, PASSPORTNUM, DRIVERLICENSENUM, SOCIALNUM, TAXNUM | partial |
| person_address | STREET, BUILDINGNUM, CITY, ZIPCODE | partial |
| email | EMAIL, rule:EMAIL | label_and_rule_supported |
| payment_cards | CREDITCARDNUMBER | partial |
| bank_iban | rule:IBAN | rule_only |
| age | AGE | label_supported |
| personal_dates | DATE | partial |
| sex_gender | SEX, GENDER | label_supported |
| personal_titles | TITLE | partial |
| person_linked_order_tracking_serial_reference | none dedicated | absent_dedicated_support |
| usernames_handles_customer_membership_accounts | none dedicated | absent_dedicated_support |
| ip_mac_device_cookie_online_identifiers | none dedicated | absent_dedicated_support |
| precise_location_and_movements | none dedicated | absent_dedicated_support |
| health_disability_genetic_biometric | none dedicated | absent_dedicated_support |
| religion_politics_ethnicity_sexuality | none dedicated | absent_dedicated_support |
| employment_education_financial_history | none dedicated | absent_dedicated_support |
| relationships_behavior_personal_narratives | none dedicated | absent_dedicated_support |
| credentials_and_person_linked_secrets | none dedicated | absent_dedicated_support |

Detailed gaps and measurement status are in `coverage.json#/categories`; component recall never proves whole-address or person-link recall.

## Limits and gates

- Label supported is not successful detection, semantic completeness or a privacy guarantee; no finite taxonomy proves all personal information covered.
- Recall values are unchanged historical strict start/end/label dev aggregates, not new evaluation, category-level recall or current CLI recall.
- Historical taxonomy equality does not verify checkpoint weights or bind historical scores to a new inference implementation.
- Threshold was tuned on dev; single seed/model and synthetic templates; no test inspection or scoring performed.
- Decoy FP is a benchmark-convention result, not a proven masking error under the all-personal-information policy.
- Regex negatives were selected by absence of regex detections; zero FP is by construction, not robustness evidence.
- Alignment metadata excludes 38 dev rows, comparison metadata excludes 39; their row sets cannot be reconciled from aggregates alone.
- Micro extra labels are hashed out-of-taxonomy audit bins, not checkpoint support; semantic label names cannot be recovered from hashes alone.
- Full person-address, person linkage, unannotated information and combinations of indirect identifiers remain unmeasured.

Negative policy: `masking-policy.md`. Unresolved evidence and next bounded preflight/full-run boundary: `gates.md`.

Reproduce without corpus access or model loading:

    env -u PYTHONPATH HF_HUB_OFFLINE=1 python3 scripts/audit_coverage.py --model-config /absolute/path/to/models/full-1/config.json
