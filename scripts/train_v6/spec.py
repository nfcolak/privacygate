"""Frozen paths, input hashes and shared reservation (TEST is text-hashing only)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path('/Users/necatifurkancolak/AI-Workplace/Projects/current/privacygate')
DATA = MAIN / '.cache/external/gretel-finance-7b844d1'
ARTIFACTS = Path('/Users/necatifurkancolak/AI-Workplace/Artifacts/PrivacyGate')
V5 = ARTIFACTS / 'train-v5/train-v5.jsonl'
SCORER = ARTIFACTS / 'external/gretel-results/evaluate_external.py'
POLICY = ROOT / 'configs/privacy-policy-v1.json'
MANIFEST = ROOT / 'artifacts/train-v6/manifest.json'
OUTPUTS = {'train': ROOT / 'data/augmentation/train-v6.jsonl',
           'dev': ROOT / 'data/augmentation/dev-v6-ext.jsonl'}
LANGUAGES = {'English': 'en', 'France': 'fr', 'German': 'de', 'Italian': 'it', 'Spanish': 'es'}
SEED = 2026100506
REVISION = '7b844d16738527a04264f50214cb426a4cea0897'
EXT_DEV_PER_LANGUAGE = 200
ENGLISH_CAP = 8000
V5_ROWS = 16000
SYNTHETIC_ROWS = 8000
TRAIN_HASHES = {
    'English': '2858af81ec59d8528f81059facb099ac33e6b47caf2501da3eac113bccfee9c7',
    'France': 'a8303598dce1a6af58840d6e69ca31667f85da2abcad06b38c0cc8e296802825',
    'German': 'e7534ae69a3f2009bfa0e56af5f0d14d4a59e7138d5cf400e56ea81a7862a404',
    'Italian': 'd24d97511a933269e36ea36e591415f319cb61201838b586cf6e760cd5584082',
    'Spanish': '39954d0931f3d3771af1200f0255016bbe29905dcd0fec539864d3b01ea63b7b',
}
V5_HASH = '93d52f8965004c02b372467b6e5f2f977293ae507b5fb77b48a96810b6a11f20'
