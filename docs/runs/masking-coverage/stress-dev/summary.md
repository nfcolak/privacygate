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
  Complete spans: 10/370; original gold chars covered: 350/9130; alnum leakage: 7534/7854.
  Positive rows completely masked: 0/100; partial/untouched spans: 0/360; excess masked chars: 0.
  Clean controls: {"completeness_ratio": null, "masked_chars": 0, "masked_rows": 0, "rows": 10, "text_chars": 3233}
  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched
  ACCOUNTNUM: 0/10; 0/110; 90/90; 0/0/0/0/10
  ADDRESS: 0/30; 0/1785; 1464/1464; 0/0/0/0/30
  DRIVERLICENSENUM: 0/10; 0/110; 90/90; 0/0/0/0/10
  EMAIL: 10/10; 350/350; 0/320; 10/0/0/0/0
  IDCARDNUM: 0/20; 0/200; 160/160; 0/0/0/0/20
  PASSPORTNUM: 0/10; 0/110; 90/90; 0/0/0/0/10
  PERSONALREF: 0/30; 0/585; 480/480; 0/0/0/0/30
  PERSONNAME: 0/150; 0/3640; 3330/3330; 0/0/0/0/150
  TELEPHONENUM: 0/50; 0/1415; 1080/1080; 0/0/0/0/50
  USERNAME: 0/50; 0/825; 750/750; 0/0/0/0/50
  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess
  de: 2/74; 70/1836; 1526/1590; 0/20; 0/72; 0
  en: 2/74; 70/1822; 1490/1554; 0/20; 0/72; 0
  es: 2/74; 70/1854; 1538/1602; 0/20; 0/72; 0
  fr: 2/74; 70/1820; 1498/1562; 0/20; 0/72; 0
  it: 2/74; 70/1798; 1482/1546; 0/20; 0/72; 0
  Family: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess; clean masked/total
  account: 0/20; 0/348; 308/308; 0/10; 0/20; 0; 0/0
  clean: 0/0; 0/0; 0/0; 0/0; 0/0; 0; 0/10
  full_address: 0/20; 0/833; 706/706; 0/10; 0/20; 0; 0/0
  identity: 0/40; 0/558; 478/478; 0/10; 0/40; 0; 0/0
  long_text: 0/60; 0/1714; 1450/1450; 0/10; 0/60; 0; 0/0
  multiple_entities: 10/70; 350/1926; 1312/1632; 0/10; 0/60; 0; 0/0
  names: 0/30; 0/784; 714/714; 0/10; 0/30; 0; 0/0
  personalref: 0/20; 0/433; 378/378; 0/10; 0/20; 0; 0/0
  phone: 0/20; 0/521; 434/434; 0/10; 0/20; 0; 0/0
  repeated_values: 0/70; 0/1610; 1386/1386; 0/10; 0/70; 0; 0/0
  username: 0/20; 0/403; 368/368; 0/10; 0/20; 0; 0/0

mbert
  Complete spans: 100/370; original gold chars covered: 6898/9130; alnum leakage: 1609/7854.
  Positive rows completely masked: 0/100; partial/untouched spans: 231/39; excess masked chars: 0.
  Clean controls: {"completeness_ratio": null, "masked_chars": 0, "masked_rows": 0, "rows": 10, "text_chars": 3233}
  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched
  ACCOUNTNUM: 10/10; 110/110; 0/90; 0/5/5/0/0
  ADDRESS: 0/30; 752/1785; 733/1464; 0/0/0/21/9
  DRIVERLICENSENUM: 10/10; 110/110; 0/90; 9/0/1/0/0
  EMAIL: 10/10; 350/350; 0/320; 7/0/3/0/0
  IDCARDNUM: 20/20; 200/200; 0/160; 0/3/17/0/0
  PASSPORTNUM: 0/10; 100/110; 0/90; 0/0/0/10/0
  PERSONALREF: 17/30; 383/585; 166/480; 0/9/8/3/10
  PERSONNAME: 0/150; 3262/3640; 218/3330; 0/0/0/140/10
  TELEPHONENUM: 3/50; 997/1415; 323/1080; 3/0/0/47/0
  USERNAME: 30/50; 634/825; 169/750; 0/12/18/10/10
  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess
  de: 19/74; 1338/1836; 377/1590; 0/20; 47/8; 0
  en: 19/74; 1432/1822; 262/1554; 0/20; 48/7; 0
  es: 19/74; 1390/1854; 341/1602; 0/20; 47/8; 0
  fr: 22/74; 1371/1820; 322/1562; 0/20; 44/8; 0
  it: 21/74; 1367/1798; 307/1546; 0/20; 45/8; 0
  Family: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess; clean masked/total
  account: 10/20; 338/348; 0/308; 0/10; 10/0; 0; 0/0
  clean: 0/0; 0/0; 0/0; 0/0; 0/0; 0; 0/10
  full_address: 0/20; 570/833; 157/706; 0/10; 20/0; 0; 0/0
  identity: 20/40; 538/558; 0/478; 0/10; 20/0; 0; 0/0
  long_text: 2/60; 476/1714; 1036/1450; 0/10; 19/39; 0; 0/0
  multiple_entities: 33/70; 1596/1926; 197/1632; 0/10; 37/0; 0; 0/0
  names: 0/30; 754/784; 0/714; 0/10; 30/0; 0; 0/0
  personalref: 10/20; 423/433; 0/378; 0/10; 10/0; 0; 0/0
  phone: 1/20; 432/521; 64/434; 0/10; 19/0; 0; 0/0
  repeated_values: 14/70; 1378/1610; 155/1386; 0/10; 56/0; 0; 0/0
  username: 10/20; 393/403; 0/368; 0/10; 10/0; 0; 0/0

hybrid_union
  Complete spans: 100/370; original gold chars covered: 6898/9130; alnum leakage: 1609/7854.
  Positive rows completely masked: 0/100; partial/untouched spans: 231/39; excess masked chars: 0.
  Clean controls: {"completeness_ratio": null, "masked_chars": 0, "masked_rows": 0, "rows": 10, "text_chars": 3233}
  Gold label: complete/total; chars covered/total; alnum leaked/total; exact-correct/exact-different/full-nonexact/partial/untouched
  ACCOUNTNUM: 10/10; 110/110; 0/90; 0/5/5/0/0
  ADDRESS: 0/30; 752/1785; 733/1464; 0/0/0/21/9
  DRIVERLICENSENUM: 10/10; 110/110; 0/90; 9/0/1/0/0
  EMAIL: 10/10; 350/350; 0/320; 10/0/0/0/0
  IDCARDNUM: 20/20; 200/200; 0/160; 0/3/17/0/0
  PASSPORTNUM: 0/10; 100/110; 0/90; 0/0/0/10/0
  PERSONALREF: 17/30; 383/585; 166/480; 0/9/8/3/10
  PERSONNAME: 0/150; 3262/3640; 218/3330; 0/0/0/140/10
  TELEPHONENUM: 3/50; 997/1415; 323/1080; 3/0/0/47/0
  USERNAME: 30/50; 634/825; 169/750; 0/12/18/10/10
  Language: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess
  de: 19/74; 1338/1836; 377/1590; 0/20; 47/8; 0
  en: 19/74; 1432/1822; 262/1554; 0/20; 48/7; 0
  es: 19/74; 1390/1854; 341/1602; 0/20; 47/8; 0
  fr: 22/74; 1371/1820; 322/1562; 0/20; 44/8; 0
  it: 21/74; 1367/1798; 307/1546; 0/20; 45/8; 0
  Family: complete/total; chars covered/total; alnum leaked/total; positive rows fully masked/total; partial/untouched; excess; clean masked/total
  account: 10/20; 338/348; 0/308; 0/10; 10/0; 0; 0/0
  clean: 0/0; 0/0; 0/0; 0/0; 0/0; 0; 0/10
  full_address: 0/20; 570/833; 157/706; 0/10; 20/0; 0; 0/0
  identity: 20/40; 538/558; 0/478; 0/10; 20/0; 0; 0/0
  long_text: 2/60; 476/1714; 1036/1450; 0/10; 19/39; 0; 0/0
  multiple_entities: 33/70; 1596/1926; 197/1632; 0/10; 37/0; 0; 0/0
  names: 0/30; 754/784; 0/714; 0/10; 30/0; 0; 0/0
  personalref: 10/20; 423/433; 0/378; 0/10; 10/0; 0; 0/0
  phone: 1/20; 432/521; 64/434; 0/10; 19/0; 0; 0/0
  repeated_values: 14/70; 1378/1610; 155/1386; 0/10; 56/0; 0; 0/0
  username: 10/20; 393/403; 0/368; 0/10; 10/0; 0; 0/0

Full aggregate counts, classifications and clean controls: metrics.json.
Pre-scoring frozen definitions and input/checkpoint/source/tokenizer hashes: manifest.json.
Execution receipt: receipt.json.
