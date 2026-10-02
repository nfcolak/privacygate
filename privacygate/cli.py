import argparse
import json
import sys

from .inference import ENGINES, POLICIES, InferenceError, run


def _conf(v):
    try:
        f = float(v)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number in [0, 1]") from None
    if not (0.0 <= f <= 1.0):
        raise argparse.ArgumentTypeError("must be a number in [0, 1]")
    return f


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m privacygate",
        description="Mask text read from stdin. Engines: regex (default; EMAIL and checksum-valid IBAN only, stdlib only), "
        "mbert (local token classifier) or hybrid (regex + mBERT). "
        "Outputs JSON (masked_text, entities with start/end offsets in the original text and label). "
        "Research prototype; NOT a privacy guarantee and does not mask all personal information. Use synthetic data only.",
    )
    p.add_argument("--engine", choices=ENGINES, default="regex", help="default: regex")
    p.add_argument("--model-dir", default=None, help="local mBERT model directory (mbert/hybrid; default: models/full-1 in the repo)")
    p.add_argument("--hybrid-policy", "--policy", dest="hybrid_policy", choices=POLICIES, default="union",
                   help="hybrid combination policy (default: union; union_refined = union + rule-based span refinement; "
                   "not a claim of calibrated superiority)")
    p.add_argument("--refine", action="store_true", help="mbert engine only: apply rule-based span refinement")
    p.add_argument("--confidence", type=_conf, default=None,
                   help="mBERT min confidence in [0,1] (default 0.0; rules_first_thr default 0.5)")
    args = p.parse_args(argv)
    try:
        text = sys.stdin.read()
        result = run(text, args.engine, args.model_dir, args.hybrid_policy, args.confidence, args.refine)
    except InferenceError as e:
        sys.stderr.write("privacygate: {} (input not shown)\n".format(e))
        return 1
    except Exception:
        sys.stderr.write("privacygate: processing error (input not shown)\n")
        return 1
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0
