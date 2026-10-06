#!/usr/bin/env python3
"""Build Gretel TRAIN + targeted synthetic policy-v1 JSONL; value-free replay verification."""
import argparse
import json
import re
import sys

sys.dont_write_bytecode = True
from train_v6.io import generate, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Read-only input hashes, schema and exact replay")
    args = parser.parse_args()
    try:
        manifest = verify() if args.verify else generate()
    except FileExistsError:
        print("ERROR output_exists", file=sys.stderr)
        return 1
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, IndexError, OverflowError) as error:
        code = str(error) if isinstance(error, ValueError) else "artifact_read_or_write_failed"
        if not re.fullmatch(r"[a-z_]+", code):
            code = "validation_failed"
        print("ERROR " + code, file=sys.stderr)
        return 1
    outputs = manifest["outputs"]
    print("{} train={} dev={} synthetic={} languages=5 trainer_row_limit_compatible={}".format(
        "VERIFIED" if args.verify else "GENERATED", outputs["train"]["rows"], outputs["dev"]["rows"],
        outputs["train"]["sources"]["targeted_synthetic"]["rows"],
        manifest["trainer_compatibility"]["full_train_within_row_limit"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
