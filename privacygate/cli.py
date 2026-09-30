import argparse
import json
import sys

from .detect import mask


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m privacygate",
        description="Regex-only baseline: mask EMAIL and checksum-valid IBAN read from stdin. "
        "Outputs JSON (masked_text, entities with start/end offsets in the original text and label). "
        "Research prototype; NOT a privacy guarantee. Use synthetic data only.",
    )
    p.parse_args(argv)
    try:
        text = sys.stdin.read()
        json.dump(mask(text), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    except Exception:
        sys.stderr.write("privacygate: processing error (input not shown)\n")
        return 1
    return 0
