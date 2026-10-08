# ext-rules dev selection (Gretel EXT-DEV + v7 dev only)

Model arm: v5 + step-1 options (name_threshold 0.1, name_propagation_ext on). Each detector is switched on alone against all-rules-off; value-free counts.
Gate: keep only if exposed letters/digits (EXT-DEV + v7 dev) go down, v7 clean rows masked <= 21/300, EXT-DEV excess rises by <= 0.3 point.

| run | exposed alnum (EXT-DEV + v7) | EXT-DEV coverage % | EXT-DEV excess % | v7 clean rows masked | decision |
|---|---:|---:|---:|---:|---|
| de_steuer_idnr | 5554 | 87.9948 | 4.8888 | 19/300 | no exposed-character reduction on dev |
| es_dni_nie | 5554 | 87.9948 | 4.8888 | 19/300 | no exposed-character reduction on dev |
| gb_nino | 5554 | 87.9948 | 4.8888 | 19/300 | no exposed-character reduction on dev |
| off | 5554 | 87.9948 | 4.8888 | 19/300 | baseline |
| us_ssn | 5554 | 87.9948 | 4.8888 | 23/300 | clean rows above 21/300 |
| ch_ahv | 5554 | 87.9948 | 4.8888 | 19/300 | no exposed-character reduction on dev |
| cued_documents | 5554 | 87.9948 | 4.8888 | 19/300 | no exposed-character reduction on dev |
| fr_nir | 5539 | 88.0293 | 4.8890 | 19/300 | kept |
| it_codice_fiscale | 5522 | 88.0684 | 4.8888 | 19/300 | kept |
| all | 5507 | 88.1028 | 4.8896 | 23/300 | all registered (reference) |
| cued_personalref | 5554 | 87.9948 | 4.8888 | 19/300 | no exposed-character reduction on dev |
| cued_social_tax | 5554 | 87.9948 | 4.8893 | 19/300 | no exposed-character reduction on dev |
| chosen | 5507 | 88.1028 | 4.8890 | 19/300 | combination of kept detectors |

Chosen: fr_nir, it_codice_fiscale.
Detectors with no dev effect are not kept (EXT-DEV has no valid-checksum ES/DE/GB/CH values and v7 has no ID exposure under the official alnum metric); they stay registered and unit-tested in check_structured.py.
