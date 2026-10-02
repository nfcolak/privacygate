Actual masking finding — annotated synthetic positive dev only

Complete masking was NOT achieved: mbert(confidence=0) and hybrid_union(confidence=0) each completely masked 918/920 annotated spans and 278/280 positive rows. They covered 7430/7441 original gold characters. The 11 uncovered characters are all Unicode alphanumeric, not merely spaces: two partially masked USERNAME spans, with 5 characters in English and 6 in Spanish. No gold span was entirely untouched. Excess masked characters relative to annotations: 0. Both arms reused one model forward sweep; the regex arm added no detected intervals on this dataset.

ACCOUNTNUM and PERSONALREF historical strict misses are not evidence of literal exposure here:

  ACCOUNTNUM: 40/40 complete; 399/399 original characters; 0/375 alphanumeric characters exposed.
    0 exact correct-label detections; 10 exact different-label detections; 30 fully covered by nonexact/combined intervals; 0 partial; 0 untouched.
    Of the 30 nonexact fully covered spans, 24 had some overlapping correct-label raw detection and 6 had only different-label raw detections.

  PERSONALREF: 40/40 complete; 581/581 original characters; 0/554 alphanumeric characters exposed.
    0 exact correct-label detections; 15 exact different-label detections; 25 fully covered by nonexact/combined intervals; 0 partial; 0 untouched.
    Of the 25 nonexact fully covered spans, 10 had some overlapping correct-label raw detection and 15 had only different-label raw detections.

The nonexact category is larger/combined final interval-union coverage, not an assertion that every such detection expanded its boundary. Adjacent fragments may jointly mask an entire annotated span even if no individual raw/final entity matches its boundaries. Correct-label overlap is a separate diagnostic and does not establish exact classification.

Additional complete-span evidence (mbert and hybrid_union are identical on these aggregates):

  GIVENNAME 280/280; SURNAME 260/260; TELEPHONENUM 40/40.
  IDCARDNUM 20/20; PASSPORTNUM 20/20; DRIVERLICENSENUM 20/20.
  STREET 40/40; BUILDINGNUM 40/40; CITY 40/40; ZIPCODE 40/40.
  USERNAME 38/40: 24 exact correct-label, 14 fully covered nonexact, 2 partial, 0 untouched.

These component counts do not establish complete addresses or person/address linkage. Names and identity numbers can be completely masked despite incorrect predicted categories; those classification errors remain in metrics.json.

Overall mutually exclusive raw-detection classification: 750 exact correct-label, 63 exact different-label, 105 fully covered nonexact, 2 partially covered, 0 untouched. Final merged-entity classification has the same aggregate counts in this run, but its semantics remain separately reported. Historical strict positive-dev scoring (750 exact span-and-label true positives out of 920) remains unchanged; numeric agreement does not assert scorer equivalence. No historical F1 artifacts were rewritten.

Regex supports only EMAIL and checksum-valid IBAN. It masked 0/920 gold spans here; none of the annotated gold categories are in that narrow scope. This dataset contains 280 positive rows and 0 empty-gold controls, so it cannot measure clean-row false positives. Clean completeness is N/A, not 100%; zero annotation-relative excess is not a real-world false-positive guarantee.

Limitations: measurements apply only to annotated synthetic development data. Unannotated personal information is not evaluated. There was no training, threshold/model selection, held-out test evaluation, Micro corpus loading, real/company data access or production/privacy guarantee. Original-substring disappearance was not used as a masking proof.

Model SHA256: 0058a5c93c2ef14c5f65daf8ae8afc061851acf8d5cf5d52ba0342f578d9cac9
Dataset SHA256: 7cc5c56f555021d135118e9e6b772e5fe8271cf887ddba3aa38530f3ac777a42
Scoring scope: development_diagnostic; training=false; test_evaluated=false.
Frozen scorer/source/tokenizer/checkpoint bindings and definitions: manifest.json.
Aggregate metrics: metrics.json. Actual execution and artifact hashes: receipt.json.
