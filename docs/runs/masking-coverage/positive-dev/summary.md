Synthetic development masking diagnostic

Training: false. Test evaluated: false. Scope: development_diagnostic.
Counts are annotated synthetic coverage, not coverage of all personal information or a production privacy guarantee.
Unannotated information is outside these measurements. No complete address/person-linkage assertion.
Non-alphanumeric-only misses are not claimed to expose an identifier; Unicode alphanumeric leakage is separate.
Raw exact detections and final merged mask entities have distinct diagnostics; historical strict F1 is unchanged.
Regex supports EMAIL/checksum-valid IBAN only. No predictions were filtered by gold, no tuning or threshold selection.
Per-label row success covers that label only. Per-label excess is whole-row excess and cannot be summed across labels.
Clean completeness ratios are N/A, never a trivial 100% success.

regex
  Complete spans: 0/920; original gold chars covered: 0/7441; alnum leakage: 7182/7182.
  Positive rows completely masked: 0/280; partial/untouched spans: 0/920; excess masked chars: 0.
  Clean controls: {"completeness_ratio": null, "masked_chars": 0, "masked_rows": 0, "rows": 0, "text_chars": 0}
  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched
  ACCOUNTNUM: 0/40; 0/399; 375/375; 0/0/0/0/40
  BUILDINGNUM: 0/40; 0/111; 111/111; 0/0/0/0/40
  CITY: 0/40; 0/209; 209/209; 0/0/0/0/40
  DRIVERLICENSENUM: 0/20; 0/220; 200/200; 0/0/0/0/20
  GIVENNAME: 0/280; 0/1793; 1793/1793; 0/0/0/0/280
  IDCARDNUM: 0/20; 0/200; 200/200; 0/0/0/0/20
  PASSPORTNUM: 0/20; 0/180; 180/180; 0/0/0/0/20
  PERSONALREF: 0/40; 0/581; 554/554; 0/0/0/0/40
  STREET: 0/40; 0/551; 519/519; 0/0/0/0/40
  SURNAME: 0/260; 0/1943; 1943/1943; 0/0/0/0/260
  TELEPHONENUM: 0/40; 0/547; 423/423; 0/0/0/0/40
  USERNAME: 0/40; 0/491; 467/467; 0/0/0/0/40
  ZIPCODE: 0/40; 0/216; 208/208; 0/0/0/0/40
  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess
  de: 0/184; 0/1523; 1489/1489; 0/56; 0/184; 0
  en: 0/184; 0/1493; 1441/1441; 0/56; 0/184; 0
  es: 0/184; 0/1460; 1400/1400; 0/56; 0/184; 0
  fr: 0/184; 0/1477; 1411/1411; 0/56; 0/184; 0
  it: 0/184; 0/1488; 1441/1441; 0/56; 0/184; 0

mbert
  Complete spans: 918/920; original gold chars covered: 7430/7441; alnum leakage: 11/7182.
  Positive rows completely masked: 278/280; partial/untouched spans: 2/0; excess masked chars: 0.
  Clean controls: {"completeness_ratio": null, "masked_chars": 0, "masked_rows": 0, "rows": 0, "text_chars": 0}
  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched
  ACCOUNTNUM: 40/40; 399/399; 0/375; 0/10/30/0/0
  BUILDINGNUM: 40/40; 111/111; 0/111; 24/0/16/0/0
  CITY: 40/40; 209/209; 0/209; 40/0/0/0/0
  DRIVERLICENSENUM: 20/20; 220/220; 0/200; 0/16/4/0/0
  GIVENNAME: 280/280; 1793/1793; 0/1793; 266/11/3/0/0
  IDCARDNUM: 20/20; 200/200; 0/200; 20/0/0/0/0
  PASSPORTNUM: 20/20; 180/180; 0/180; 4/5/11/0/0
  PERSONALREF: 40/40; 581/581; 0/554; 0/15/25/0/0
  STREET: 40/40; 551/551; 0/519; 40/0/0/0/0
  SURNAME: 260/260; 1943/1943; 0/1943; 252/6/2/0/0
  TELEPHONENUM: 40/40; 547/547; 0/423; 40/0/0/0/0
  USERNAME: 38/40; 480/491; 11/467; 24/0/14/2/0
  ZIPCODE: 40/40; 216/216; 0/208; 40/0/0/0/0
  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess
  de: 184/184; 1523/1523; 0/1489; 56/56; 0/0; 0
  en: 183/184; 1488/1493; 5/1441; 55/56; 1/0; 0
  es: 183/184; 1454/1460; 6/1400; 55/56; 1/0; 0
  fr: 184/184; 1477/1477; 0/1411; 56/56; 0/0; 0
  it: 184/184; 1488/1488; 0/1441; 56/56; 0/0; 0

hybrid_union
  Complete spans: 918/920; original gold chars covered: 7430/7441; alnum leakage: 11/7182.
  Positive rows completely masked: 278/280; partial/untouched spans: 2/0; excess masked chars: 0.
  Clean controls: {"completeness_ratio": null, "masked_chars": 0, "masked_rows": 0, "rows": 0, "text_chars": 0}
  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched
  ACCOUNTNUM: 40/40; 399/399; 0/375; 0/10/30/0/0
  BUILDINGNUM: 40/40; 111/111; 0/111; 24/0/16/0/0
  CITY: 40/40; 209/209; 0/209; 40/0/0/0/0
  DRIVERLICENSENUM: 20/20; 220/220; 0/200; 0/16/4/0/0
  GIVENNAME: 280/280; 1793/1793; 0/1793; 266/11/3/0/0
  IDCARDNUM: 20/20; 200/200; 0/200; 20/0/0/0/0
  PASSPORTNUM: 20/20; 180/180; 0/180; 4/5/11/0/0
  PERSONALREF: 40/40; 581/581; 0/554; 0/15/25/0/0
  STREET: 40/40; 551/551; 0/519; 40/0/0/0/0
  SURNAME: 260/260; 1943/1943; 0/1943; 252/6/2/0/0
  TELEPHONENUM: 40/40; 547/547; 0/423; 40/0/0/0/0
  USERNAME: 38/40; 480/491; 11/467; 24/0/14/2/0
  ZIPCODE: 40/40; 216/216; 0/208; 40/0/0/0/0
  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess
  de: 184/184; 1523/1523; 0/1489; 56/56; 0/0; 0
  en: 183/184; 1488/1493; 5/1441; 55/56; 1/0; 0
  es: 183/184; 1454/1460; 6/1400; 55/56; 1/0; 0
  fr: 184/184; 1477/1477; 0/1411; 56/56; 0/0; 0
  it: 184/184; 1488/1488; 0/1441; 56/56; 0/0; 0

Full aggregate counts, classifications and clean controls: metrics.json.
Pre-scoring frozen definitions and input/checkpoint/source/tokenizer hashes: manifest.json.
Execution receipt: receipt.json.
