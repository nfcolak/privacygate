# Privacy policy v1

Research prototype; synthetic data only. This is an operational masking and gold-annotation policy, not a privacy or legal guarantee. An `ok` receipt means the declared pipeline completed, not that every personal fact was recognized.

## Shared policy (verbatim)

Mask: natural-person names (with attached titles Dr./Prof./Herr/Mme/Sig.ra/Sr., initials, particles van/von/de/di/da/del/du/le/la/dos, compound/hyphenated and reversed "Surname, Given" forms; the salutation word itself such as Dear/Sehr geehrte/Bonjour is NOT masked); emails; usernames/handles incl. the @; phone numbers incl. country code, trunk "(0)", groups and the whole extension phrase; a person's postal address as ONE region incl. c/o + recipient, street, number, floor/unit, PO box, postcode, city, region, country; passport, ID card, driving licence, tax, social security numbers incl. separators; IBAN, account and card numbers incl. separators; personal reference numbers (customer/patient/case/membership no. tied to a person); a person's birth date and age.
Do not mask: generic calendar dates/times, dimensions and quantities, product/order/invoice/SKU codes with no person link, brands and organizations, public places mentioned in general, room numbers with no person link.
Ambiguous = mask (recall first). Gold spans cover the whole value incl. internal separators, never surrounding prose or sentence punctuation.
Canonical gold labels for new data: PERSONNAME, ADDRESS, EMAIL, USERNAME, TELEPHONENUM, IBAN, ACCOUNTNUM, CREDITCARDNUMBER, PASSPORTNUM, IDCARDNUM, DRIVERLICENSENUM, TAXNUM, SOCIALNUM, PERSONALREF, DATEOFBIRTH, AGE. Row schema = v3 six fields: {"case_id","family","gold":[{"start","end","label"}],"language","split","text"} (one JSON object per line, gold ordered and non-overlapping).
Format families RESERVED for blind v4 only (the training generator must NOT produce them): (1) form-style key/value records, (2) chat/messaging lines, (3) email signature blocks, (4) mixed-language documents (text in one language, value formats of another country), (5) OCR-like noise (line breaks or missing spaces inside values).

## Gold boundary rules

- All offsets are half-open Python `str` indices on the original, unnormalized text: `0 <= start < end <= len(text)`. They are not UTF-8 byte or UTF-16 offsets.
- Annotate the entire value, including internal spaces, separators, initials, particles, attached titles, handle sigils and phone extension phrases. Do not annotate surrounding introductory prose, salutations or sentence punctuation.
- Annotate a person's complete postal routing address as one ADDRESS region, including its c/o recipient, street, number, floor/unit, PO box, postcode, city, region and country when present.
- Keep gold ordered and non-overlapping; repeated mentions have separate gold occurrences. Labels describe whole-value regions, not an arbitrary detector's token fragments.
- Uncertain person linkage is masked; failed checksum, low confidence or another detector's disagreement does not by itself declassify a value.

## Execution contract

`configs/pipeline-v1.json` declares the four profiles. The new profiles keep candidates separate through structural validation, optional context, address/name assembly and name propagation. The shared candidate dict has exactly `start`, `end`, `label`, `source`, `score`, `validation`, `context`, `protected`, `stage`. Labels and sources are extensible strings; validation/context/stage have the shared fixed enum values. Scores are finite floats or null. Candidates never carry original text or values.

Required modules are imported lazily and checked before inference. Missing stages produce `status=blocked`, empty `masked_text`/`entities`, and the fixed value-free error `pipeline_stage_unavailable:<stage>`. Other failures also block rather than returning unprocessed input. Diagnostics contain aggregate integer counts only. Completion reports the per-call number of non-whitespace characters omitted from actual predicted token offsets; such regions are protected and added after semantic refinement in new profiles. This count is processing coverage, not semantic recall.

Only an unprotected candidate can be rejected by the context stage. Assembly and propagation are additive. The existing refiner is a legacy four-field adapter: the pipeline retains the candidate ledger separately and makes new-profile refinement additive, so every accepted or unresolved proposal, protected anchor and whole ADDRESS/PERSONNAME region remains masked. Global class-agnostic union is the final new-profile operation before rendering; display labels never shorten the union.

`legacy_union_refined` deliberately uses the existing inference implementation, including its historical merge, labels and coverage/refinement order. Its `masked_text` and `entities` are unchanged. `inference.run` and the default CLI retain their original two-field output; the pipeline API adds status, per-call completion and aggregate diagnostics, and the opt-in CLI exposes this result. `LAST_UNCOVERED_CHARS` remains available only for backward compatibility.

## Evaluation discipline

v1/v2 are exposed development material. v3 has been consumed: no v3 tuning or row inspection in this phase. Independent blind v4 keeps the reserved format families above and is generated separately from detector/training code. Evaluation must call the same `run_pipeline` entry point as the opt-in CLI. No model download, training, test-split use, raw-value logging, or production guarantee is authorized by this policy.
