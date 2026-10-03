# Refinement measurement v3

Synthetic development diagnostic; training false, test evaluated false. Annotated-span coverage only; not a privacy guarantee.
Dataset sha256 313a477b124c5c7f9e7aeaa35f777c85291833940254ff74f4e98c39a1f8dd61 (150 rows, 155 gold spans).

| arm | complete spans | partial | untouched | exposed alnum chars | fully masked positive rows | excess masked chars | clean rows masked | clean masked chars |
|---|---|---|---|---|---|---|---|---|
| mbert | 29/155 | 126 | 0 | 662/4711 | 24/110 | 756 | 40/40 | 729 |
| hybrid_union | 37/155 | 118 | 0 | 585/4711 | 24/110 | 756 | 40/40 | 729 |
| hybrid_union_refined | 95/155 | 60 | 0 | 198/4711 | 57/110 | 845 | 40/40 | 818 |
