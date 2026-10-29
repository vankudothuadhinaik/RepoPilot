from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

try:
    from .benchmark_repository import run
except ImportError:  # Support direct script execution from the evals directory.
    from benchmark_repository import run


def parse_source_revision(value: str) -> tuple[str, str]:
    """Parse a pinned upstream source revision as NAME=SHA."""
    name, separator, revision = value.partition("=")
    if not separator or not name.strip() or not revision.strip():
        raise argparse.ArgumentTypeError("source revisions must use NAME=SHA")
    return name.strip(), revision.strip()


def _materialize_snapshot(root: Path, destination: Path) -> Path:
    """Expand a pinned JSON source bundle into a temporary repository tree."""
    snapshot_path = root / "snapshot.json"
    if not snapshot_path.is_file():
        return root
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot.get("files"), dict):
        raise ValueError(f"snapshot bundle has no files mapping: {root.name}")
    destination.mkdir(parents=True, exist_ok=False)
    for raw_path, source_text in snapshot["files"].items():
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in raw_path:
            raise ValueError(f"unsafe snapshot path in {root.name}")
        if not isinstance(source_text, str):
            raise ValueError(f"snapshot content must be text in {root.name}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source_text, encoding="utf-8")
    return destination


def run_matrix(
    roots: list[Path],
    *,
    redact_paths: bool = False,
    source_revisions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Benchmark distinct repository roots and optionally remove absolute paths."""
    resolved_roots = [root.expanduser().resolve(strict=True) for root in roots]
    if not resolved_roots:
        raise ValueError("at least one repository root is required")
    if len(set(resolved_roots)) != len(resolved_roots):
        raise ValueError("repository roots must be distinct")

    with tempfile.TemporaryDirectory(prefix="repopilot-benchmark-matrix-") as temporary:
        temporary_root = Path(temporary)
        reports = []
        for root in resolved_roots:
            materialized = _materialize_snapshot(
                root, temporary_root / root.name
            )
            report = run(materialized)
            report["repository"] = root.name
            if source_revisions and root.name in source_revisions:
                report["source_commit"] = source_revisions[root.name]
            if redact_paths:
                report["root"] = "<redacted>"
            reports.append(report)
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
    parser.add_argument(
        "--source-revision",
        action="append",
        type=parse_source_revision,
        default=[],
        metavar="NAME=SHA",
        help="Record a pinned upstream revision for a snapshot without its own .git metadata",
    )
    args = parser.parse_args()
    revisions = dict(args.source_revision)
    if len(revisions) != len(args.source_revision):
        parser.error("--source-revision names must be unique")
    report = run_matrix(
        args.roots, redact_paths=args.redact_paths, source_revisions=revisions
    )
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
