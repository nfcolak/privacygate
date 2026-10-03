# Window-cut measurement: does a sliding-window cut expose personal-information spans?

Synthetic development diagnostic; training false, test evaluated false. Annotated-span coverage only; not a privacy guarantee.
Dataset sha256 ce617dda0a15deaa99e67a9018e317f6cc87d2ebb6ad47d2d47df3e452ea36ca (80 rows, 200 gold spans): 40 cut rows whose gold spans each cross an
actual window end (verified with the real mbert_data.encode: 510 content tokens, step 382, overlap 128) and 40 matched mid_window controls with the
same values and lengths placed fully inside one window's middle (>= 60 tokens from every cut). Model checkpoint sha256 0058a5c93c2ef14c5f65daf8ae8afc061851acf8d5cf5d52ba0342f578d9cac9, confidence 0.0,
one forward sweep; scorer masking_union (unchanged). Set is synthetic and small (100 crossing spans, 100 control spans): treat differences of a few spans as noise-prone.

## Arm mbert

| family | cut complete | cut partial | cut untouched | cut exposed alnum | crossing spans fully masked | control complete | control partial | control untouched | control exposed alnum |
|---|---|---|---|---|---|---|---|---|---|
| cut_phone vs mid_window/phone | 25/25 | 0 | 0 | 0/280 | 25/25 | 25/25 | 0 | 0 | 0/280 |
| cut_address vs mid_window/address | 0/25 | 25 | 0 | 331/1213 | 0/25 | 0/25 | 25 | 0 | 333/1213 |
| cut_name vs mid_window/name | 1/25 | 24 | 0 | 0/402 | 1/25 | 0/25 | 25 | 0 | 0/402 |
| cut_identifier vs mid_window/identifier | 20/25 | 5 | 0 | 0/285 | 20/25 | 18/25 | 7 | 0 | 3/285 |
| all four pooled | 46/100 | 54 | 0 | 331/2180 | 46/100 | 43/100 | 57 | 0 | 336/2180 |

## Arm hybrid_union

| family | cut complete | cut partial | cut untouched | cut exposed alnum | crossing spans fully masked | control complete | control partial | control untouched | control exposed alnum |
|---|---|---|---|---|---|---|---|---|---|
| cut_phone vs mid_window/phone | 25/25 | 0 | 0 | 0/280 | 25/25 | 25/25 | 0 | 0 | 0/280 |
| cut_address vs mid_window/address | 0/25 | 25 | 0 | 331/1213 | 0/25 | 0/25 | 25 | 0 | 333/1213 |
| cut_name vs mid_window/name | 1/25 | 24 | 0 | 0/402 | 1/25 | 0/25 | 25 | 0 | 0/402 |
| cut_identifier vs mid_window/identifier | 20/25 | 5 | 0 | 0/285 | 20/25 | 18/25 | 7 | 0 | 3/285 |
| all four pooled | 46/100 | 54 | 0 | 331/2180 | 46/100 | 43/100 | 57 | 0 | 336/2180 |

## Arm hybrid_union_refined

| family | cut complete | cut partial | cut untouched | cut exposed alnum | crossing spans fully masked | control complete | control partial | control untouched | control exposed alnum |
|---|---|---|---|---|---|---|---|---|---|
| cut_phone vs mid_window/phone | 25/25 | 0 | 0 | 0/280 | 25/25 | 25/25 | 0 | 0 | 0/280 |
| cut_address vs mid_window/address | 23/25 | 2 | 0 | 12/1213 | 23/25 | 23/25 | 2 | 0 | 12/1213 |
| cut_name vs mid_window/name | 24/25 | 1 | 0 | 0/402 | 24/25 | 25/25 | 0 | 0 | 0/402 |
| cut_identifier vs mid_window/identifier | 21/25 | 4 | 0 | 0/285 | 21/25 | 21/25 | 4 | 0 | 0/285 |
| all four pooled | 93/100 | 7 | 0 | 12/2180 | 93/100 | 94/100 | 6 | 0 | 12/2180 |

## Conclusion

- mbert: window cut causes extra exposure: no. Exposed alnum chars cut 331 vs control 336 (cut minus control -5); complete spans cut 46/100 vs control 43/100 (cut minus control +3); crossing spans fully masked 46/100.
- hybrid_union: window cut causes extra exposure: no. Exposed alnum chars cut 331 vs control 336 (cut minus control -5); complete spans cut 46/100 vs control 43/100 (cut minus control +3); crossing spans fully masked 46/100.
- hybrid_union_refined: window cut causes extra exposure: no. Exposed alnum chars cut 12 vs control 12 (cut minus control +0); complete spans cut 93/100 vs control 94/100 (cut minus control -1); crossing spans fully masked 93/100.

Incomplete spans (e.g. names, and addresses in the non-refined arms) are incomplete equally in cut and control rows, so they reflect the checkpoint's label/format limits, not the window cut.

Caveats: controls reuse the same invented values and lengths but not identical filler wording; exposure here is annotation-relative. The set is synthetic and small (10 rows per family, 2-3 spans each, one invented value pool), so it shows whether the mechanism fails visibly, not how often it would on real text.
Details: metrics.json, manifest.json.
