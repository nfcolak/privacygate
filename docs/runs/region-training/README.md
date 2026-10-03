# Whole-region mBERT training

Synthetic policy-v1 six-field JSONL only; region mode never reads Micro or any test/blind split.
The fixed head is O plus B/I for all 16 canonical policy labels (33 classes), including PERSONNAME, ADDRESS and DATEOFBIRTH.
Full run after the train-v2 writer's files and this commit are integrated (not executed by this pilot):
    cd /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate
    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.cache/hf /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.venv-train/bin/python -m privacygate.train_mbert --run region-v2-2ep --region-train-file data/augmentation/train-v2.jsonl --region-dev-file data/augmentation/dev-v2.jsonl --region-manifest docs/train-v2/manifest.json --epochs 2 --batch-size 16 --out-dir models

Outputs: models/region-v2-2ep/{config.json,model.safetensors,tokenizer assets,train_info.json,metrics.json}; weights/data stay git-ignored.
Each run starts from the pinned locally cached multilingual BERT base with a fresh head; best epoch is selected by region-dev strict span F1, then character recall.
metrics.json reports strict spans per canonical label/language and class-agnostic original-character union recall/precision, including clean-row false masks.
Unalignable TRAIN rows are excluded with aggregate reasons; all original DEV gold remains in metric denominators, with unalignable counts recorded separately.
Reads are bounded (20,000 rows/file, 128 MiB/file, 128 KiB/line, 12,000 characters/row, 128 gold regions/row); errors never echo input.
Optional manifest hashes use sha256 records keyed by split/filename or carrying the matching path; exact-byte hashes, labels and mode bind run identity, refusing incompatible/Micro outputs.
Pilot: 300 TRAIN + 60 DEV rows, five languages, 40% clean; 300 train windows, zero exclusions; MPS, 19 steps, 7.1011 training seconds, 9.86 seconds total wall time.
Measured rate: 2.675657 steps/sec; pilot dev strict F1 0.11215, character recall 0.86040, character precision 1.00000; this is plumbing evidence, not a quality claim.
16,000 rows x 2 epochs at batch 16: 2,000 steps and 12.46 optimizer minutes IF each row has one window and the pilot rate holds; longer windows and dev/save overhead increase this.
For actual retained training window count W, estimate optimizer minutes as 2 * ceil(W / 16) / (60 * measured_steps_per_sec); the tiny short-window pilot is not a sustained full-corpus benchmark.
Pilot artifact: /Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate/.worktrees/pg-p2-trainer/models/region-pilot; run_pipeline(profile="full") completed with zero errors; inference already reads labels from checkpoint config.
Verified: scripts/check_pipeline.py legacy_identical=110/110; smoke.py SMOKE OK; bounded schema/hash/alignment/isolation probes pass; Micro training body remains byte-identical; no download, install or push.
