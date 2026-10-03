# Evaluation protocol v1

Scope: synthetic, annotation-relative masking research under privacy-policy-v1.
No training, test-split evaluation, raw-row reports, network calls, privacy/legal
certification or threshold selection. Existing v1/v2 and consumed v3 are exposed
research evidence. Do not read or rescore v3; it is not a tuning population.

## Frozen inputs and the real entry point

`evaluate_pipeline.py --dataset P --version v1|v2|v4|dev2 --profile NAME
--model-dir D --out-dir O` calls `privacygate.pipeline.run_pipeline` per row,
exactly the public pipeline entry point used by the CLI. All six-field rows must
have split=dev and ordered, nonoverlapping original Unicode code-point gold spans.
Any nonempty gold/prediction label is admitted; labels never gate mask coverage.
Missing pipeline/config/model assets fail with fixed, value-free errors.

Dataset bytes must match the selected runtime manifest:

- v1: docs/masking-stress/manifest.json, plus the historical SHA/count rules.
- v2: docs/masking-stress-v2/manifest.json.
- v4: docs/masking-stress-v4/manifest.json.
- dev2: docs/train-v2/manifest.json, selecting its dev dataset record, normally
  data/augmentation/dev-v2.jsonl, not its training hash.

Manifests may use `dataset: {path, sha256, rows, bytes}` or a nested `datasets`
mapping with a separate dev record. Selection requires an exact dataset basename
(or an explicit dev key for dev2); missing/ambiguous hashes fail closed. Supplied
row/byte counts are checked. Model weights and local checkpoint files, tokenizer
assets, privacygate/*.py, evaluator source, configuration and available policy
are hashed before inference and checked afterwards, together with input bindings.
Reports record versions, wall time, training=false and test_evaluated=false.

`--predictions-from inference` selects only legacy_union_refined and invokes
`inference.run(engine="hybrid", policy="union_refined")`. Its real loaded model is
reused across rows; no predictions are fabricated/cached and coverage/refinement
are not reconstructed by the scorer. The explicit legacy call arguments provide
its config hash; it does not depend on configs/pipeline-v1.json. The frozen v1
comparison must produce 369/370 complete spans, matching refine-v1-1003. Other
metrics can differ from historical score-only artifacts because this is the
actual end-to-end coverage path.

## Blind-v4 custody

Predeclare and freeze these four profiles before any v4 outcome is inspected:
legacy_union_refined, structured, structured_address_names, full. Missing modules
are unavailable arms, never silently skipped stages. Choose a research candidate
on development/calibration evidence first; blind ablations are explanatory, not
permission to pick an independently validated winner after seeing their scores.

Each (profile, model.safetensors SHA256) is allowed once. An exclusive lock guards
docs/runs/blind-v4/RECEIPTS.jsonl. A durable sibling .STARTED reservation is written
immediately before inference; a crash, scoring failure or interrupted run consumes
that arm. On success exactly one final receipt is appended, containing profile,
model hash, dataset hash, UTC time and metrics hash. Existing final/started keys
refuse before scoring. There is no --allow-repeat. New config/source hashes do not
reopen the same key; a new independent blind round is required after results guide
changes. Do not delete/redirect custody logs to repeat an arm. The receipts-env
fixture override is enabled only by the Python check's private check parameter;
normal CLI invocations reject it. A busy lock fails instead of queuing a repeat.

Runtime manifests and reports reveal only aggregates, approved group metadata and
artifact hashes. Never emit dataset text, values, case ids or offsets, including
exceptions. Each output directory must be new; historical artifacts stay intact.

## Scores and milestone gates

Reuse unchanged masking_metrics interval_union/intersection/count_chars/count_alnum
and span_class. The new aggregate adapter validates arbitrary labels independently;
there is no ADDRESS-to-STREET alias, mutable allowlist or raw-vs-final-union
assumption. Count whole-value complete, partial and untouched spans; all-character
and alphanumeric exposure; fully masked positive rows; annotation-relative excess;
clean rows/characters masked; blocked and execution-uncovered counts. Report every
gold label, language and family, including small strata. Per-label completeness
refers to that label's spans; row-scoped excess repeats across labels, not an
additive decomposition. Blocked rows have no released output or mask entities and
count as positive-row failures; report clean blocking separately to avoid claiming
abstention is clean preservation.

Phase-1 acceptance gates, frozen before blind measurement:

- Clean rows with any mask <=5% of clean rows; clean original characters masked
  <=1% of all clean original characters. Report both denominators and blocked rows.
- Zero newly exposed gold alphanumeric characters versus the parent profile.
  Check paired original positions in evaluator memory, not only net aggregate
  leakage (a gain elsewhere cannot excuse a new leak). Parent sequence:
  legacy_union_refined -> structured -> structured_address_names -> full.
  This evaluator reports each arm independently; a paired noninferiority decision
  needs a separately frozen paired comparison, not a pass inferred from totals.
- Report per-family complete-span rates and positive-row success rates, with
  denominators. Target >=98% overall complete spans and >=95% per-positive-family
  fully masked rows; high-risk phone/ID/banking/email/handle families target zero
  exposed alphanumeric characters and >=99% complete spans. Failed family floors
  cannot be hidden by a favorable overall average.
- Require >=95% OK/released rows and >=95% unconditional fully masked positive
  rows; blocked rows count as failures. These are finite-suite research gates,
  not a production claim. Human annotation/semantic QA remains a separate gate.

Wilson two-sided 95% intervals accompany every row-level rate, including each
label/language/family; zero denominators have null rates/bounds. They are descriptive
IID illustrations, not valid guarantees under shared synthetic grammar dependence.
Do not treat characters or within-row spans as independent Bernoulli trials.
Tiny/zero-event strata remain visible but cannot establish universal protection;
paired superiority/noninferiority needs a preregistered cluster-aware comparison.
No human review, paired cluster inference or semantic-safety claim is fabricated.
