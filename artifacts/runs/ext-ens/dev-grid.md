# v5v6 ensemble_pair dev grid

Selection data: Gretel EXT-DEV (1,000 rows) and v7 dev (not blind). No TEST, Nemotron or ai4privacy rows used; no training.
Rule: fewest exposed letters/digits (EXT-DEV + v7 dev) with v7 clean rows masked <= 21/300 and EXT-DEV excess <= 5.8888 (v5 + step-1 EXT-DEV excess 4.8888 + 1.0); ties lower EXT-DEV excess.

| mode | name threshold | propagation ext | EXT-DEV coverage % | EXT-DEV excess % | EXT-DEV rows exposed | EXT-DEV exposed | v7 clean masked | v7 exposed | total exposed | eligible |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| mean | None | False | 90.1336 | 1.3643 | 154 | 4290 | 19/300 | 2313 | 6603 | True |
| mean | None | True | 90.2233 | 1.3793 | 150 | 4251 | 19/300 | 2313 | 6564 | True |
| mean | 0.3 | False | 93.0314 | 1.8622 | 117 | 3030 | 19/300 | 2298 | 5328 | True |
| mean | 0.3 | True | 93.1280 | 1.9196 | 116 | 2988 | 19/300 | 2298 | 5286 | True |
| mean | 0.1 | False | 94.2504 | 2.3778 | 105 | 2500 | 19/300 | 2284 | 4784 | True |
| mean | 0.1 | True | 94.3815 | 2.4554 | 105 | 2443 | 19/300 | 2284 | 4727 | True |
| union | None | False | 96.2926 | 4.6060 | 64 | 1612 | 19/300 | 306 | 1918 | True |
| union | None | True | 96.3179 | 4.6661 | 63 | 1601 | 19/300 | 306 | 1907 | True |
| union | 0.3 | False | 96.8676 | 4.7552 | 57 | 1362 | 19/300 | 306 | 1668 | True |
| union | 0.3 | True | 96.9136 | 4.8180 | 57 | 1342 | 19/300 | 306 | 1648 | True |
| union | 0.1 | False | 97.5990 | 5.1976 | 46 | 1044 | 19/300 | 306 | 1350 | True |
| union | 0.1 | True | 97.5990 | 5.2711 | 46 | 1044 | 19/300 | 306 | 1350 | True |

Chosen: v5v6 {"ensemble": false, "ensemble_pair": "union", "name_propagation_ext": false, "name_threshold": 0.1}
