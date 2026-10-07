# EXT-DEV inference-only grid

Selection only: 200 text-hash-sorted, TEST-deduplicated train rows per language; no training.
Same-model excess budget = baseline + 1.0 percentage point. Ensemble baseline averages v4/v5; name options off.

| model | name threshold | propagation ext | coverage % | excess % | rows exposed | excess cap % | eligible |
|---|---|---|---:|---:|---:|---:|---|
| v6 | None | False | 94.8276 | 1.1800 | 97 | 2.1800 | True |
| v6 | None | True | 94.9242 | 1.2487 | 95 | 2.1800 | True |
| v6 | 0.4 | False | 95.2025 | 1.2106 | 88 | 2.1800 | True |
| v6 | 0.4 | True | 95.2416 | 1.2887 | 87 | 2.1800 | True |
| v6 | 0.3 | False | 95.5268 | 1.2507 | 86 | 2.1800 | True |
| v6 | 0.3 | True | 95.5475 | 1.3259 | 85 | 2.1800 | True |
| v6 | 0.2 | False | 96.0534 | 1.3093 | 81 | 2.1800 | True |
| v6 | 0.2 | True | 96.1086 | 1.3962 | 80 | 2.1800 | True |
| v6 | 0.1 | False | 96.5249 | 1.4739 | 73 | 2.1800 | True |
| v6 | 0.1 | True | 96.5249 | 1.5517 | 73 | 2.1800 | True |

For comparison: v5 rows repeated from the step-1 grid (artifacts/runs/ext-step1/ext-dev-grid.json), same EXT-DEV rows.

| model | name threshold | propagation ext | coverage % | excess % | rows exposed |
|---|---|---|---:|---:|---:|
| v5 | None | False | 86.5964 | 4.4641 | 198 |
| v5 | None | True | 86.6861 | 4.4891 | 196 |
| v5 | 0.4 | False | 86.8310 | 4.5008 | 197 |
| v5 | 0.4 | True | 86.9575 | 4.5251 | 195 |
| v5 | 0.3 | False | 87.1875 | 4.5684 | 197 |
| v5 | 0.3 | True | 87.3209 | 4.5924 | 195 |
| v5 | 0.2 | False | 87.3071 | 4.6816 | 196 |
| v5 | 0.2 | True | 87.4405 | 4.7074 | 194 |
| v5 | 0.1 | False | 87.8752 | 4.8591 | 191 |
| v5 | 0.1 | True | 87.9948 | 4.8888 | 190 |

Chosen: v6 {"ensemble": false, "name_propagation_ext": false, "name_threshold": 0.1}
TEST is not used for selection; its text hashes are used only to exclude duplicates.
