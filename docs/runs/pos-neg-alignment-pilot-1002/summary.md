pos-neg-alignment-pilot-1002

DONE: exactly one specified trainer process completed, no repeat or resume.
MPS; wall 171.878921s; optimizer-loop wall 159.802330s; 226 steps; 1.414247216 steps/s.
Optimizer-loop time includes forward/backward, update/scheduler, collation and periodic cache clearing; it is not isolated optimizer-kernel time.
Trainer eval_time_s=6.960953s is a residual including window construction, base loading, checkpoint writing and both dev calls, not isolated eval time.
Wall minus optimizer=12.076591s is a startup/evaluation/filesystem proxy, not profiling.

Frozen: 2000 selected Micro TRAIN + all 630 positive TRAIN + all 1000 negative TRAIN; one epoch, batch16, lr3e-5, seed13.
Fresh pinned multilingual BERT BASE, unchanged tokenizer/discovery/preprocessing/scorer. TRAIN-only 45-class BIO head.
USERNAME B/I=41/42; ACCOUNTNUM B/I=1/2; PERSONALREF B/I=25/26. Verified in actual safetensors classifier [45,768], bias [45], saved maps and v3 identity.
Source/input/cache byte hashes verified before/after; byte-integrity proxies do not prove semantic correctness or privacy.

Training admission / retained / excluded after windowing:
  micro: 2000 / 1979 / 21
  positive: 630 / 630 / 0
  negative: 1000 / 1000 / 0
Total retained rows/windows: 3609/3609.
All 21 excluded TRAIN rows are Micro whole-row broken boundaries; other reason counts zero. Positive/negative exclusions zero.

Separate development results (strict exact character span + label, never pooled):
  dev: selected/admitted 500; evaluated 495; exclusions 5; support 3532; precision 0.698207; recall 0.793884; F1 0.742978; TP/FP/FN 2804/1212/728.
  Exclusion reasons: {"incomplete_gold_coverage": 0, "overlapping_gold": 0, "whole_row_broken_boundary": 5, "whole_row_lost_span": 0}
  positive_dev: selected/admitted 280; evaluated 280; exclusions 0; support 920; precision 0.702247; recall 0.815217; F1 0.754527; TP/FP/FN 750/318/170.
  Exclusion reasons: {"incomplete_gold_coverage": 0, "overlapping_gold": 0, "whole_row_broken_boundary": 0, "whole_row_lost_span": 0}

Per-label support / recall / F1 from saved artifacts only; absent zero-support Micro labels are N/A, not evaluated successes:
Label              Micro support recall F1        Positive-dev support recall F1
GIVENNAME           438 0.739726 0.703583        280 0.950000 0.972578
SURNAME             378 0.764550 0.703163        260 0.969231 0.978641
TELEPHONENUM        175 0.960000 0.933333         40 1.000000 0.909091
IDCARDNUM           107 0.757009 0.465517         20 1.000000 0.344828
PASSPORTNUM          59 0.203390 0.167832         20 0.200000 0.135593
DRIVERLICENSENUM     83 0.168675 0.177215         20 0.000000 0.000000
STREET              168 0.797619 0.765714         40 1.000000 0.963855
BUILDINGNUM         162 0.666667 0.654545         40 0.600000 0.551724
ZIPCODE             158 0.930380 0.859649         40 1.000000 0.898876
CITY                265 0.924528 0.887681         40 1.000000 0.792079
USERNAME              0 N/A      N/A         40 0.600000 0.600000
ACCOUNTNUM            0 N/A      N/A         40 0.000000 0.000000
PERSONALREF           0 N/A      N/A         40 0.000000 0.000000

Checkpoint wiring is verified, not universal learning: positive-dev ACCOUNTNUM and PERSONALREF exact recall/F1 are 0 with support40 each; USERNAME recall/F1=.6 with support40.
High component scores do not establish whole-address reconstruction, person linkage or complete masking. Positive dev probes authored generator templates only, not real-world/final-test generalisation.
Original full-1 and earlier negative pilot are UNMATCHED; no win/loss, rescoring or historical quality comparison.
test_evaluated=false; no test manifest opened; no full run, seed sweep, install, download, push or source edit.

PROVISIONAL future compute only; NO full run starts:
All current provisional TRAIN means 30404 manifest rows, not the entire publisher corpus. Existing diagnostic corrected-policy count proxy: 30033 Micro retained rows / 30037 windows; input-manifest/tokenizer hashes match, but current production full pass not performed.
Expanded: 30037+630+1000=31667 windows; ceil(windows/16)=1980 steps for one epoch.
Fresh Micro-only control: 30037 windows, 1878 steps; matched control+candidate total 3858 steps.
At this pilot measured 1.414247216 steps/s: expanded optimizer 1400.038s (23.334min); expanded wall proxy 1441.764s (24.029min).
Matched study optimizer 2727.953s (45.466min); wall proxy 2808.890s (46.815min).
Historical old-alignment 0.749387508 steps/s is ONLY a sensitivity anchor: expanded optimizer 2642.158s; expanded wall proxy 2683.883s (44.731min); study wall proxy 5229.141s (87.152min). NOT a confidence interval or measured new full rate.
Augmentation window fraction drops from 45.164866% in this pilot to 5.147314% in the expanded count proxy.
Short augmentation fraction changes batch maxima; padding rounds to 64-token buckets; attention depends on padded lengths. Pilot batch lengths uninstrumented. Whole-row mean, long windows and sustained battery/thermal/MPS conditions do not fix full-run rate. Control 39-class head differs naturally from candidate45 via TRAIN-only discovery.
Matched study would freshly train both arms under corrected protocol and compare identical retained Micro dev IDs with the identical scorer/preprocessing. Control has no new TRAIN labels, so unchanged trainer cannot admit new-label positive dev for control; candidate positive dev stays separate, not a cross-arm comparison.
Wall budgets add a row-scaled trainer eval residual plus a separate startup/filesystem residual proxy; these are not isolated evaluation estimates or reserved maxima. See compute-estimate.json for formulas, bindings and assumptions.

Existing smoke.py once: SMOKE OK. All documentation/report computations derived programmatically; trainer config/metrics bytes remain untouched.

Artifact source paths:
  Docs: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-expanded-pilot-1002/docs/runs/pos-neg-alignment-pilot-1002
  Checkpoint: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-expanded-pilot-1002/models/pos-neg-alignment-pilot-1002
  Results: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-expanded-pilot-1002/results/pos-neg-alignment-pilot-1002
  Launcher: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/_runs/pg-expanded-pilot-1002
  Exact file inventories and SHA256/size bindings: run-manifest.json; final doc hashes: launcher artifact-verification.json.
