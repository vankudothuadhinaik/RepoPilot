from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

from repopilot.indexer import PARSER_VERSION, index_repository
from repopilot.store import Store


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def run(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="repopilot-benchmark-") as temporary:
        database = Path(temporary) / "benchmark.sqlite3"
        store = Store(database)
        tracemalloc.start()
        started = time.perf_counter()
        first = index_repository(root)
        first_scan_seconds = time.perf_counter() - started
        started = time.perf_counter()
        first_persisted = store.index(first)
        first_index_seconds = time.perf_counter() - started

        hashes = store.file_hashes(root)
        parser_version = store.parser_version_for_root(root)
        started = time.perf_counter()
        second = index_repository(root, known_hashes=hashes, known_parser_version=parser_version)
        incremental_scan_seconds = time.perf_counter() - started
        started = time.perf_counter()
        second_persisted = store.index(second)
        incremental_persist_seconds = time.perf_counter() - started

        search_times: list[float] = []
        for _ in range(30):
            started = time.perf_counter()
            store.search(first_persisted["id"], "import", limit=10)
            search_times.append(time.perf_counter() - started)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        file_bytes = sum(item["size_bytes"] for item in second["files"])
        return {
            "schema_version": 1,
            "repository": root.name,
            "root": str(root),
            "parser_version": PARSER_VERSION,
            "file_count": len(second["files"]),
            "file_bytes_indexed": file_bytes,
            "symbol_count": second_persisted["symbol_count"],
            "scan_errors": len(second["errors"]),
            "first_scan_seconds": round(first_scan_seconds, 6),
            "first_persist_seconds": round(first_index_seconds, 6),
            "incremental_scan_seconds": round(incremental_scan_seconds, 6),
            "incremental_persist_seconds": round(incremental_persist_seconds, 6),
            "incremental_changed_files": second_persisted["index_delta"]["added"] + second_persisted["index_delta"]["updated"],
            "incremental_unchanged_files": second_persisted["index_delta"]["unchanged"],
            "search_latency_ms": {
                "median": round(statistics.median(search_times) * 1000, 3),
                "p95": round(percentile(search_times, 0.95) * 1000, 3),
                "samples": len(search_times),
                "query": "import",
            },
            "database_bytes": database.stat().st_size if database.exists() else 0,
            "python_tracemalloc_peak_bytes": peak_bytes,
            "limitations": [
                "Single local run on the CI runner; not a representative multi-size benchmark.",
                "Tracemalloc reports Python-tracked allocations, not total process RSS.",
                "Search latency is for one fixed lexical query and 30 in-process samples.",
                "The second pass is an unchanged-tree incremental baseline, not an edit workload.",
            ],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure RepoPilot indexing and search on a local repository.")
    parser.add_argument("root", type=Path, help="Repository directory to benchmark")
    parser.add_argument("--output", type=Path, default=Path("repository_benchmark_results.json"))
    args = parser.parse_args()
    report = run(args.root)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
