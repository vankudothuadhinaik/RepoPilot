"""Run reproducible top-k spot checks against real local repositories."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from repopilot.indexer import index_repository
from repopilot.store import Store


def parse_repo(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name or not raw_path:
        raise argparse.ArgumentTypeError("repositories must use NAME=PATH")
    return name, Path(raw_path).expanduser().resolve()


def parse_case(value: str) -> tuple[str, str, str]:
    name, separator, remainder = value.partition("|")
    query, separator_two, expected_path = remainder.rpartition("|")
    if not separator or not separator_two or not name or not query or not expected_path:
        raise argparse.ArgumentTypeError("cases must use NAME|QUERY|EXPECTED_PATH")
    return name, query, expected_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", type=parse_repo, required=True)
    parser.add_argument("--case", action="append", type=parse_case, required=True)
    args = parser.parse_args()
    repositories = dict(args.repo)
    cases = args.case
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "benchmark.sqlite3")
        ids: dict[str, str] = {}
        report: list[dict[str, Any]] = []
        for name, root in repositories.items():
            indexed = index_repository(root)
            stored = store.index(indexed)
            ids[name] = stored["id"]
            report.append({
                "name": name,
                "root": str(root),
                "commit": indexed["commit"],
                "files_indexed": stored["file_count"],
                "symbols": stored["symbol_count"],
                "errors": len(indexed["errors"]),
            })
        checks = []
        for name, query, expected_path in cases:
            if name not in ids:
                parser.error(f"case references unknown repository: {name}")
            results = store.search(ids[name], query, limit=5)
            rank = next(
                (index for index, result in enumerate(results, 1) if result["path"] == expected_path),
                None,
            )
            checks.append({"name": name, "query": query, "expected_path": expected_path,
                           "rank_at_5": rank})
        print(json.dumps({"repositories": report, "checks": checks}, indent=2, sort_keys=True))
        if any(check["rank_at_5"] is None for check in checks):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
