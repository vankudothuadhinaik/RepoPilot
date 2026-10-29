from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .benchmark_repository import run
except ImportError:  # Support direct script execution from the evals directory.
    from benchmark_repository import run


def run_matrix(roots: list[Path], *, redact_paths: bool = False) -> dict[str, Any]:
    """Benchmark distinct repository roots and optionally remove absolute paths."""
    resolved_roots = [root.expanduser().resolve(strict=True) for root in roots]
    if not resolved_roots:
        raise ValueError("at least one repository root is required")
    if len(set(resolved_roots)) != len(resolved_roots):
        raise ValueError("repository roots must be distinct")

    reports = [run(root) for root in resolved_roots]
    if redact_paths:
        for report in reports:
            report["root"] = "<redacted>"
    return {
        "schema_version": 2,
        "repository_count": len(reports),
        "path_redaction": "enabled" if redact_paths else "disabled",
        "reports": reports,
        "limitations": [
            "Each repository is measured sequentially on the same machine; results are environment-dependent.",
            "This tool reports measurements and does not label repositories small, medium, or large automatically.",
            "Use repositories you are authorized to inspect; do not publish private source paths or source-derived secrets.",
            "Path redaction removes the absolute root field but does not sanitize repository names or source-derived values.",
            "The benchmark does not evaluate semantic answer quality or establish production readiness.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the same RepoPilot benchmark against multiple local repositories."
    )
    parser.add_argument("roots", nargs="+", type=Path, help="One or more local repository directories")
    parser.add_argument("--output", type=Path, default=Path("repository_benchmark_matrix.json"))
    parser.add_argument(
        "--redact-paths",
        action="store_true",
        help="Replace absolute repository root paths in the report before sharing it",
    )
    args = parser.parse_args()
    report = run_matrix(args.roots, redact_paths=args.redact_paths)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
