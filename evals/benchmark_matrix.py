from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmark_repository import run


def run_matrix(roots: list[Path]) -> dict[str, Any]:
    reports = [run(root) for root in roots]
    return {
        "schema_version": 1,
        "repository_count": len(reports),
        "reports": reports,
        "limitations": [
            "Each repository is measured sequentially on the same machine; results are environment-dependent.",
            "This tool reports measurements and does not label repositories small, medium, or large automatically.",
            "Use repositories you are authorized to inspect; do not publish private source paths or source-derived secrets.",
            "The benchmark does not evaluate semantic answer quality or establish production readiness.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the same RepoPilot benchmark against multiple local repositories."
    )
    parser.add_argument("roots", nargs="+", type=Path, help="One or more local repository directories")
    parser.add_argument("--output", type=Path, default=Path("repository_benchmark_matrix.json"))
    args = parser.parse_args()
    report = run_matrix(args.roots)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
