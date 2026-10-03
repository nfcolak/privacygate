# Refinement measurement v1

Synthetic development diagnostic; training false, test evaluated false. Annotated-span coverage only; not a privacy guarantee.
Dataset sha256 b901873cbdd3715aaae2c78477193fecb3fd47410344fdb240ce75abdbfb6cbf (110 rows, 370 gold spans).

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess masked chars | clean rows masked | clean masked chars |
|---|---|---|---|---|---|---|---|---|
| mbert | 117/370 | 253 | 0 | 783/7854 | 0/100 | 0 | 0/10 | 0 |
| hybrid_union | 117/370 | 253 | 0 | 783/7854 | 0/100 | 0 | 0/10 | 0 |
| hybrid_union_refined | 369/370 | 1 | 0 | 0/7854 | 99/100 | 0 | 0/10 | 0 |

