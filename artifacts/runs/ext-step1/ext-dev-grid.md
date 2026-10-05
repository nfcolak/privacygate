# EXT-DEV inference-only grid

Selection only: 200 text-hash-sorted, TEST-deduplicated train rows per language; no training.
Same-model excess budget = baseline + 1.0 percentage point. Ensemble baseline averages v4/v5; name options off.

| model | name threshold | propagation ext | coverage % | excess % | rows exposed | excess cap % | eligible |
|---|---|---|---:|---:|---:|---:|---|
| v4 | None | False | 84.0988 | 3.9890 | 259 | 4.9890 | True |
| v4 | None | True | 84.3403 | 4.0145 | 256 | 4.9890 | True |
| v4 | 0.4 | False | 84.2667 | 4.0014 | 257 | 4.9890 | True |
| v4 | 0.4 | True | 84.4967 | 4.0257 | 253 | 4.9890 | True |
| v4 | 0.3 | False | 84.3541 | 4.0296 | 254 | 4.9890 | True |
| v4 | 0.3 | True | 84.5726 | 4.0583 | 250 | 4.9890 | True |
| v4 | 0.2 | False | 84.5151 | 4.0589 | 249 | 4.9890 | True |
| v4 | 0.2 | True | 84.7520 | 4.0918 | 246 | 4.9890 | True |
| v4 | 0.1 | False | 84.6761 | 4.1151 | 248 | 4.9890 | True |
| v4 | 0.1 | True | 84.9428 | 4.1484 | 243 | 4.9890 | True |
| v5 | None | False | 86.5964 | 4.4641 | 198 | 5.4641 | True |
| v5 | None | True | 86.6861 | 4.4891 | 196 | 5.4641 | True |
| v5 | 0.4 | False | 86.8310 | 4.5008 | 197 | 5.4641 | True |
| v5 | 0.4 | True | 86.9575 | 4.5251 | 195 | 5.4641 | True |
| v5 | 0.3 | False | 87.1875 | 4.5684 | 197 | 5.4641 | True |
| v5 | 0.3 | True | 87.3209 | 4.5924 | 195 | 5.4641 | True |
| v5 | 0.2 | False | 87.3071 | 4.6816 | 196 | 5.4641 | True |
| v5 | 0.2 | True | 87.4405 | 4.7074 | 194 | 5.4641 | True |
| v5 | 0.1 | False | 87.8752 | 4.8591 | 191 | 5.4641 | True |
| v5 | 0.1 | True | 87.9948 | 4.8888 | 190 | 5.4641 | True |
| ensemble | None | False | 85.1544 | 3.7458 | 230 | 4.7458 | True |
| ensemble | None | True | 85.5086 | 3.7719 | 226 | 4.7458 | True |
| ensemble | 0.4 | False | 86.2308 | 3.9083 | 218 | 4.7458 | True |
| ensemble | 0.4 | True | 86.3849 | 3.9263 | 215 | 4.7458 | True |
| ensemble | 0.3 | False | 86.6355 | 4.0113 | 208 | 4.7458 | True |
| ensemble | 0.3 | True | 86.7413 | 4.0367 | 206 | 4.7458 | True |
| ensemble | 0.2 | False | 87.1599 | 4.1789 | 205 | 4.7458 | True |
| ensemble | 0.2 | True | 87.3002 | 4.2101 | 203 | 4.7458 | True |
| ensemble | 0.1 | False | 87.6176 | 4.4023 | 203 | 4.7458 | True |
| ensemble | 0.1 | True | 87.7510 | 4.4321 | 201 | 4.7458 | True |

Chosen: v5 {"ensemble": false, "name_propagation_ext": true, "name_threshold": 0.1}
TEST is not used for selection; its text hashes are used only to exclude duplicates.
