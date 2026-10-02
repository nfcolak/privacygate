# Stress-dev masking after mBERT sliding-window fix (development diagnostic)

Synthetic stress-dev only (110 rows, 370 gold spans). Same checkpoint (SHA256 0058a5c9...cac9) and dataset (SHA256 b901873c...bfb6cbf) as `../stress-dev/`; no training, no test set. Only `privacygate/mbert_data.py::encode` changed. Full numbers: `metrics.json`; frozen bindings: `manifest.json`, `receipt.json`.

Change: windows are built by `encode` itself (510 content tokens, step 382, last window ends at the final token). The old tokenizer-overflow path returned only 2 windows for the longest row (8752 chars, 2202 tokens) and never saw text after char 2013. The new encoder yields 6 windows for that row (token starts 0/382/764/1146/1528/1910, last window reaches char 8752).

Windows over 110 rows: old 120, new 157. All 370 gold spans lie fully inside at least one new window (0 outside).

Before (`../stress-dev/`) -> after (this dir). mBERT arm; hybrid_union is identical in every row below.

  Scope               gold  complete      partial      untouched    exposed alnum chars
  overall             370   100 -> 117    231 -> 253   39 -> 0      1609 -> 783 (of 7854)
  ADDRESS             30    0 -> 0        21 -> 30     9 -> 0       733 -> 435 (of 1464)
  TELEPHONENUM        50    3 -> 3        47 -> 47     0 -> 0       323 -> 323 (of 1080)
  long_text (family)  60    2 -> 19       19 -> 41     39 -> 0      1036 -> 210 (of 1450)
  clean controls masked     0/10 -> 0/10

Remaining misses are partial masks (253 spans), not unseen text; complete positive rows are still 0/100.

Gold spans crossing actual window cuts: 1 (partly inside a window edge, fully inside another window). Cut-crossing handling is barely tested by this set.

Scope limits: development diagnostic on synthetic data; no privacy guarantee is stated or implied.
