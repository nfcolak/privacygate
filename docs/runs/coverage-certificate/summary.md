# Coverage certificate
Runtime coverage uses offsets returned by actual mBERT prediction windows, not a second tokenization.
Special tokens cover nothing; maximal unseen non-whitespace runs become UNCOVERED spans with source coverage.
Coverage bypasses confidence and hybrid rule precedence and is added before refinement and final masking merge.
Callers can read inference.LAST_UNCOVERED_CHARS; it resets per run, is not thread-local, and does not alter CLI JSON.
Tokenizer-only offline check verifies the frozen synthetic v1 hash and all 110 development rows: uncovered_v1_chars=0.
An invented text exceeding 2000 tokens, with its last encoder window removed, yields forced_tail_masked=ALL.
Real checkpoint hybrid/union CLI output is byte-identical to base; SHA256 0923b214332b9e4b25637f31cc59dd6569679097d7514d7fdaf4eff548deebae.
Existing smoke.py passes: SMOKE OK; encoder, scorer, model weights and committed manifests remain unchanged.
Limits: whitespace is exempt, offsets must be truthful, and coverage does not certify detection/privacy; tokenizer emitted a regex-pattern warning.
