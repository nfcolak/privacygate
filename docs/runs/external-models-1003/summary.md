# Frozen GLiNER2-PII comparison on stress v1, v2 and blind v3

Synthetic development diagnostics only: training false, test_evaluated false. Exactly one successful GLiNER2 sweep per set, aggregates only. All sweeps completed on MPS; no CPU fallback, downloads, installs, training, test-split evaluation or tuning.

Model: fastino/gliner2-privacy-filter-PII-multi, revision 1cb4166094dc58fa8d836429f060d6c95f62b495, Apache-2.0. Model weights SHA256: 0280f6f39f6012da50b6640bad438d9b7e763a1b0102094115d1b710c4dd79b6. Runtime: GLiNER2 commit 55656fbfa01d3d4a77485e1a1eeeaf682990ccdf. Exact installed package versions are recorded in requirements-external.txt and each manifest.json.

The checksum-verified measurement script was copied unchanged; no base-compatibility fix was needed. This summary was assembled from the completed metrics.json files, rather than the copied script's legacy --summary references. The hybrid_union_refined references are the committed refine-v1-1003, refine-v2-1003 and blind-v3-1003 artifacts; those engines were not rerun here. Reference dataset hashes match the external runs.

## Stress v1

Dataset SHA256: b901873cbdd3715aaae2c78477193fecb3fd47410344fdb240ce75abdbfb6cbf; 110 rows, 100 positive and 10 clean controls. V1 is non-blind development evidence for the refined engine.

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess chars | clean rows masked | clean masked chars | seconds/row | peak host RSS (MiB) | device |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gliner2_pii | 281/370 | 73 | 16 | 550/7854 | 49/100 | 0 | 0/10 | 0 | 0.166009 | 2795.86 | mps |
| hybrid_union_refined | 369/370 | 1 | 0 | 0/7854 | 99/100 | 0 | 0/10 | 0 | not recorded | not recorded | not recorded |

GLiNER2: 208 chunks; sweep 18.261 s; model load 6.508 s; process total including load 24.772 s. Reference: docs/runs/masking-coverage/refine-v1-1003/metrics.json.

## Stress v2

Dataset SHA256: 4b52ff31718ba6dd0b7e8a9fda9637f241295f782504d456179467a6b0c2f0d2; 80 rows, 60 positive and 20 clean controls. V2 is non-blind development evidence for the refined engine.

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess chars | clean rows masked | clean masked chars | seconds/row | peak host RSS (MiB) | device |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gliner2_pii | 101/130 | 29 | 0 | 110/2827 | 32/60 | 162 | 10/20 | 162 | 0.065004 | 3119.16 | mps |
| hybrid_union_refined | 130/130 | 0 | 0 | 0/2827 | 60/60 | 46 | 5/20 | 46 | not recorded | not recorded | not recorded |

GLiNER2: 89 chunks; sweep 5.200 s; model load 5.553 s; process total including load 10.754 s. Reference: docs/runs/masking-coverage/refine-v2-1003/metrics.json.

## Blind stress v3

Dataset SHA256: 313a477b124c5c7f9e7aeaa35f777c85291833940254ff74f4e98c39a1f8dd61; 150 rows, 110 positive and 40 clean controls. Generator verification returned VERIFIED. Exactly one successful external invocation and forward sweep; no retry, row-level failure inspection or tuning.

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess chars | clean rows masked | clean masked chars | seconds/row | peak host RSS (MiB) | device |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gliner2_pii | 76/155 | 53 | 26 | 1123/4711 | 46/110 | 574 | 24/40 | 564 | 0.075632 | 3117.89 | mps |
| hybrid_union_refined | 95/155 | 60 | 0 | 198/4711 | 57/110 | 845 | 40/40 | 818 | not recorded | not recorded | not recorded |

GLiNER2: 187 chunks; sweep 11.345 s; model load 4.973 s; process total including load 16.319 s. Reference: docs/runs/masking-coverage/blind-v3-1003/metrics.json. Both arms' v3 results are frozen single-sweep aggregates.

## Fixed measurement and limits

The pinned card's full 42-label list, including aliases and its order, and default threshold 0.5 were retained. Chunking uses exact runtime encoded length including schema and terminal punctuation, capped at 512 tokens, with fixed 64-word-token overlap, batch size 1, no input truncation and asserted coverage of every original character. Only known runtime-added terminal punctuation is projected back to the original domain. Every original-character prediction is retained, mapped to STREET solely for scorer compatibility, merged with inference.merge_spans and scored by the unchanged masking_metrics.EngineAggregate. Coverage is class-agnostic; exact-label diagnostics are not comparable detection accuracy. Full character coverage does not guarantee complete entity detection across chunk boundaries.

Seconds/row covers chunk planning, extraction, merging and aggregate scoring, excluding model load, binding hashes and artifact writes. Peak RSS is process-lifetime host memory including imports and model load, not MPS device allocation. Refined-engine timings, RSS and device were not recorded in its reference metrics/manifests and are not inferred; this is not a speed comparison. Process total starts after initial binding hashes and excludes final artifact writes.

Mechanically annotated invented values, limited languages and formats, and annotation-relative excess masking limit generalization. V1/v2 refinement results are tuned development evidence, not unbiased estimates; v3 is blind for this frozen external sweep and remains aggregate-only. No real-data, production privacy or legal guarantee is established.

## Reference artifact bindings

- v1: docs/runs/masking-coverage/refine-v1-1003/metrics.json; SHA256 ba6a45b6fb697a2065fab3795a6919ebcfd24b74c9c413bef3955dfeb9583cfe.
- v2: docs/runs/masking-coverage/refine-v2-1003/metrics.json; SHA256 a2bacc64b8d9005b1846d81663a840d39f305302064dfc0186452f68d062ca82.
- v3: docs/runs/masking-coverage/blind-v3-1003/metrics.json; SHA256 921f1441b88afbf9ca13228bb6ffa91e647a80a4da249fb0f4998dbfd4aa7b23.
