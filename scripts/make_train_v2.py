#!/usr/bin/env python3
"""Generate train/dev v2 or verify existing artifacts; aggregate output only."""
import argparse
import json
import re
import sys

from train_v2.io import aggregate_message, generate, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Read-only hashes, schema and full replay check")
    args = parser.parse_args()
    try:
        result = verify() if args.verify else generate()
    except json.JSONDecodeError:
        print("ERROR invalid_json", file=sys.stderr)
        return 1
    except FileExistsError:
        print("ERROR output_exists", file=sys.stderr)
        return 1
    except ValueError as error:
        code = str(error)
        if not re.fullmatch(r"[a-z_]+", code):
            code = "validation_failed"
        print(f"ERROR {code}", file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, UnicodeError):
        print("ERROR artifact_read_or_write_failed", file=sys.stderr)
        return 1
    print(aggregate_message("VERIFIED" if args.verify else "GENERATED", result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
