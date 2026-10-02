# Refinement measurement v2

Synthetic development diagnostic; training false, test evaluated false. Annotated-span coverage only; not a privacy guarantee.
Dataset sha256 4b52ff31718ba6dd0b7e8a9fda9637f241295f782504d456179467a6b0c2f0d2 (80 rows, 130 gold spans).

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess masked chars | clean rows masked | clean masked chars |
|---|---|---|---|---|---|---|---|---|
| mbert | 19/130 | 111 | 0 | 119/2827 | 0/60 | 56 | 9/20 | 56 |
| hybrid_union | 19/130 | 111 | 0 | 119/2827 | 0/60 | 56 | 9/20 | 56 |
| hybrid_union_refined | 70/130 | 60 | 0 | 0/2827 | 0/60 | 56 | 9/20 | 56 |

