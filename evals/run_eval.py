"""Run deterministic smoke and synthetic multi-repository retrieval evaluations."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from repopilot.indexer import index_repository
from repopilot.store import Store


def run_smoke(store: Store, temp: Path) -> dict[str, Any]:
    dataset = json.loads(
        (Path(__file__).parent / "datasets/smoke.json").read_text(encoding="utf-8")
    )
    root = temp / "smoke-fixture"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "app.py").write_text(
        "def greet(name):\n    return name\nclass Service:\n    pass\n",
        encoding="utf-8",
    )
    repo = store.index(index_repository(root))
    results = []
    for case in dataset:
        query = case["query"]
        found = store.search(repo["id"], query, limit=10)
        if case["expected_path"] is None:
            ok = not found
        else:
            ok = any(item["path"] == case["expected_path"] for item in found)
        results.append({"id": case["id"], "passed": ok})
    return {
        "passed": sum(int(item["passed"]) for item in results),
        "total": len(results),
        "results": results,
    }


def run_retrieval_benchmark(store: Store, temp: Path) -> dict[str, Any]:
    dataset_path = Path(__file__).parent / "datasets/retrieval_50.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    repository_ids: dict[str, str] = {}

    for name, files in dataset["repositories"].items():
        root = temp / f"benchmark-{name}"
        root.mkdir()
        (root / ".git").mkdir()
        for relative_path, content in files.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        repository_ids[name] = store.index(index_repository(root))["id"]

    positive_cases = [case for case in dataset["cases"] if case["expected_path"] is not None]
    negative_cases = [case for case in dataset["cases"] if case["expected_path"] is None]
    reciprocal_ranks: list[float] = []
    hit_at_5 = 0
    hit_at_10 = 0
    details: list[dict[str, Any]] = []

    for case in positive_cases:
        found = store.search(repository_ids[case["repo"]], case["query"], limit=10)
        rank = next(
            (index for index, item in enumerate(found, start=1)
             if item["path"] == case["expected_path"]),
            None,
        )
        if rank is not None:
            reciprocal_ranks.append(1.0 / rank)
            hit_at_10 += 1
            if rank <= 5:
                hit_at_5 += 1
        else:
            reciprocal_ranks.append(0.0)
        details.append({
            "id": case["id"],
            "repo": case["repo"],
            "query": case["query"],
            "expected_path": case["expected_path"],
            "rank": rank,
            "passed": rank is not None and rank <= 5,
        })

    correct_abstentions = 0
    for case in negative_cases:
        found_any = any(
            store.search(repository_ids[name], case["query"], limit=10)
            for name in repository_ids
        )
        ok = not found_any
        correct_abstentions += int(ok)
        details.append({
            "id": case["id"],
            "repo": case["repo"],
            "query": case["query"],
            "expected_path": None,
            "rank": None,
            "passed": ok,
        })

    positive_count = len(positive_cases)
    negative_count = len(negative_cases)
    metrics = {
        "positive_queries": positive_count,
        "negative_queries": negative_count,
        "recall_at_5": round(hit_at_5 / positive_count, 4) if positive_count else 0.0,
        "recall_at_10": round(hit_at_10 / positive_count, 4) if positive_count else 0.0,
        "mrr_at_10": round(sum(reciprocal_ranks) / positive_count, 4) if positive_count else 0.0,
        "abstention_accuracy": round(
            correct_abstentions / negative_count, 4
        ) if negative_count else 0.0,
    }
    passed = (
        metrics["recall_at_5"] >= 0.95
        and metrics["abstention_accuracy"] == 1.0
    )
    return {
        "title": dataset["title"],
        "scope": dataset["description"],
        "case_count": len(dataset["cases"]),
        "repository_count": len(repository_ids),
        "metrics": metrics,
        "passed": passed,
        "results": details,
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        store = Store(temp / "eval.sqlite3")
        smoke = run_smoke(store, temp)
        benchmark = run_retrieval_benchmark(store, temp)
        report = {
            "smoke": smoke,
            "retrieval_benchmark": benchmark,
        }
        rendered = json.dumps(report, indent=2, sort_keys=True)
        Path("retrieval_benchmark_results.json").write_text(
            rendered + "\n", encoding="utf-8"
        )
        print(rendered)
        if smoke["passed"] != smoke["total"] or not benchmark["passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
