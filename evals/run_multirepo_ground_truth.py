"""CLI for pinned, local multi-repository source-grounded evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evals.multirepo_runtime import evaluate
except ModuleNotFoundError:
    from multirepo_runtime import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="RepoPilot checkout root")
    parser.add_argument(
        "--dataset", type=Path,
        default=Path(__file__).parent / "datasets" / "ground_truth_multirepo.json",
        help="Versioned multi-repository dataset JSON",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report destination")
    parser.add_argument(
        "--use-checkout",
        action="store_true",
        help="Explicitly evaluate the supplied worktree instead of the pinned RepoPilot revision",
    )
    args = parser.parse_args()
    report = evaluate(args.root, args.dataset, use_checkout=args.use_checkout)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
