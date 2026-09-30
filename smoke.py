"""Deterministic smoke test: python smoke.py"""
import json, os, subprocess, sys

env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
def run(*a, inp=""):
    return subprocess.run([sys.executable, "-m", "privacygate", *a], input=inp,
                          capture_output=True, text=True, env=env, cwd=os.path.dirname(os.path.abspath(__file__)))

EMAIL, IBAN = "anna.test@example.org", "DE89370400440532013000"
text = f"Mail {EMAIL} und {IBAN}, ok."
r = run(inp=text); assert r.returncode == 0, r.stderr
out = json.loads(r.stdout)
assert out["masked_text"] == "Mail [EMAIL] und [IBAN], ok.", out
ents = out["entities"]
assert [(e["start"], e["end"], e["label"]) for e in ents] == [
    (5, 5 + len(EMAIL), "EMAIL"),
    (text.index(IBAN), text.index(IBAN) + len(IBAN), "IBAN")], ents
assert all(set(e) == {"start", "end", "label"} for e in ents)
assert EMAIL not in r.stdout and IBAN not in r.stdout
bad = run(inp="DE89370400440532013001 x"); assert json.loads(bad.stdout)["entities"] == []
clean = json.loads(run(inp="Nothing here.").stdout)
assert clean == {"masked_text": "Nothing here.", "entities": []}, clean
h = run("--help"); assert h.returncode == 0 and "usage" in h.stdout.lower()
print("SMOKE OK")
