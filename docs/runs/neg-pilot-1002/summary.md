Negative-augmentation bounded pilot: DONE

Purpose: actual existing-pipeline wiring and timing, not model-quality improvement or production privacy evidence.
All-personal-information masking is the target, not an achieved guarantee. Test was not evaluated. Full training remains unapproved.

Execution
  Process exit 0; 155.975 s total (<360 s); MPS; seed 13; 1 epoch; batch 16; lr 3e-5.
  Requested: 2000 Micro train + 1000 neg-v2; 500 dev. Included: 1979 Micro + 1000 negative rows, 2979 windows.
  Excluded by unchanged boundary policy: 21 Micro train, 0 negatives; dev 495 included / 5 excluded.
  Real optimizer steps: 187; training 145.106 s; 1.288715 steps/s; final checkpoint verified loadable (representative tensors, no new inference).

Timing distinction
  Runner eval_time_s = 6.410 s, but source subtracts only train time: this includes windowing, model load, save and dev evaluation.
  Dev evaluation plus metrics-write filesystem interval proxy: 5.000 s (not an independently instrumented pure evaluate() timer).
  Total non-training process overhead: 10.870 s. Model load plus optimizer/scheduler setup approximate interval: 0.401–1.401 s from rounded first-step logs; not an exact timer.

Dev strict exact-span + label metrics (existing output; 19 labels)
  Rows 495; gold span support 3532; TP 2747; FP 1377; FN 785.
  All-class micro precision 0.666101; recall 0.777746; F1 0.717607.
  Unweighted 19-label mean precision 0.602190; recall 0.666168; F1 0.624074 (derived from existing per-label metrics).
  Label                Support  Precision  Recall     F1
  AGE                     166  0.876404   0.939759   0.906977
  BUILDINGNUM             162  0.564103   0.679012   0.616246
  CITY                    265  0.829268   0.898113   0.862319
  CREDITCARDNUMBER        107  0.857143   0.953271   0.902655
  DATE                    432  0.988532   0.997685   0.993088
  DRIVERLICENSENUM         83  0.100000   0.108434   0.104046
  EMAIL                   261  0.988593   0.996169   0.992366
  GENDER                   90  0.608696   0.777778   0.682927
  GIVENNAME               438  0.612840   0.719178   0.661765
  IDCARDNUM               107  0.221014   0.570093   0.318538
  PASSPORTNUM              59  0.027027   0.050847   0.035294
  SEX                      69  0.842105   0.463768   0.598131
  SOCIALNUM                73  0.120000   0.123288   0.121622
  STREET                  168  0.709497   0.755952   0.731988
  SURNAME                 378  0.637363   0.767196   0.696279
  TAXNUM                   82  0.125000   0.182927   0.148515
  TELEPHONENUM            175  0.730769   0.977143   0.836186
  TITLE                   259  0.762082   0.791506   0.776515
  ZIPCODE                 158  0.841176   0.905063   0.871951

Provisional full-run compute only; no run launched
  Budget assumption: historical full-1 count (30029 Micro windows, 375 excluded rows), 2 epochs, batch 16; candidate adds 1000 negative windows.
  One candidate: 3880 steps / 1.288715 = 3010.8 s = 50.18 min.
  Matched control + candidate: 3754 + 3880 steps = 98.73 min compute (48.55 + 50.18).
  Historical throughput sensitivity only (0.749388 steps/s): candidate 86.29 min; pair 169.78 min.
  This is not a confidence interval or completion ETA. The pilot has more short negative text per batch than a full run; pilot-rate extrapolation may be optimistic.
  Full-dev same-row-distribution evaluation proxy: 38.34 s per run; model load/save and full window-construction overhead remain separately unmeasured.
  Positive-category expansion and alignment changes are NOT in this pilot or estimate.

Checks and restrictions
  Single existing check: smoke.py, exit 0, exact aggregate SMOKE OK captured without fixture output.
  Identity/settings/source/input SHA checks, original labels, 1000 all-O negative windows, checkpoint structure/finite representative tensors and aggregate metric arithmetic verified.
  Main checkout and shared cache/raw/model/venv metadata unchanged; no cache copy, download, install, baseline rerun, push, or held-out test inspection/scoring.
  Initial nested sandbox launch failed before executing Python (exit 71). Its aggregate capture was preserved outside the train guard namespace; only ONE actual trainer invocation occurred.
  Successful invocation used offline HF settings and disabled telemetry. Extra OS network isolation could not be nested in the agent sandbox; it is not claimed.
  Artifact verification emitted a tokenizer regex warning from the installed Transformers package. No tokenizer flag or source was changed; the pinned existing pipeline was preserved. The warning is an unresolved implementation caveat, not a new measurement.
  No source code edited. Structural checks are NOT human annotation review and do not settle synthetic provenance, taxonomy completeness, split independence or semantic negative safety.

Artifacts retained in this worktree (logical bytes, not disk allocation)
  model: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-neg-pilot-1002/models/neg-pilot-1002 — 709198460 bytes across 3 files.
  results: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-neg-pilot-1002/results/neg-pilot-1002 — 16287 bytes across 3 files.

Evidence locations
  Training: models/neg-pilot-1002/train_info.json; settings: config.json; all-class/per-label/per-language: metrics.json.
  Binding, hashes, settings, gates, artifact hashes/sizes: run-manifest.json; budget assumptions/formulas: compute-estimate.json; checks: acceptance.json; exact command: command.txt.
  Aggregate-only training log: results/neg-pilot-1002/run.jsonl; process/timing record: results/neg-pilot-1002/execution.json.
  Full training, matched control, expanded taxonomy/alignment experiments and held-out test remain pending separate approval.
