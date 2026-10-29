"""Evaluate API retrieval, symbols, citations, and abstention on a reviewed corpus."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch


def _citation_matches_source(item: dict[str, Any], root: Path) -> bool:
    path = str(item.get("path", ""))
    start = item.get("start_line")
    end = item.get("end_line")
    if not path or not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        return False
    source = root / Path(path)
    if not source.is_file() or Path(path).is_absolute() or ".." in Path(path).parts:
        return False
    lines = source.read_text(encoding="utf-8").splitlines()
    if end > len(lines):
        return False
    cited_lines: dict[int, str] = {}
    for line in str(item.get("snippet", "")).splitlines():
        number, separator, content = line.partition(": ")
        if separator and number.isdigit():
            cited_lines[int(number)] = content
    return bool(cited_lines) and all(lines[number - 1] == content for number, content in cited_lines.items())


def evaluate(root: Path) -> dict[str, Any]:
    os.environ.setdefault("REP_PILOT_API_TOKEN", "ground-truth-validation-token")
    with tempfile.TemporaryDirectory() as directory:
        os.environ["REP_PILOT_DATA_DIR"] = directory
        # Keep the labels and literal query strings out of the indexed corpus.
        # Otherwise the evaluator can retrieve its own ground-truth JSON as evidence,
        # inflating scores through benchmark leakage rather than source retrieval.
        corpus_root = Path(directory) / "corpus" / root.name
        shutil.copytree(
            root,
            corpus_root,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", ".venv", "node_modules",
                ".pytest_cache", ".mypy_cache", "dist", "build",
                "retrieval_benchmark_results.json", "repository_benchmark_results.json",
                "provider-evaluation.json", "coverage.xml",
            ),
        )
        ground_truth_file = corpus_root / "evals" / "datasets" / "ground_truth.json"
        if ground_truth_file.is_file():
            ground_truth_file.unlink()

        from fastapi.testclient import TestClient

        from repopilot.api import app

        client = TestClient(app)
        headers = {"Authorization": "Bearer ground-truth-validation-token"}
        registration = client.post("/api/repos", json={"path": str(corpus_root)}, headers=headers)
        registration.raise_for_status()
        repo_id = registration.json()["id"]
        questions = json.loads(
            (Path(__file__).parent / "datasets" / "ground_truth.json").read_text(encoding="utf-8")
        )["questions"]

        positive = [question for question in questions if question["expected_path"]]
        negative = [question for question in questions if not question["expected_path"]]
        details: list[dict[str, Any]] = []
        reciprocal_ranks: list[float] = []
        path_hits = top1_hits = symbol_hits = citation_hits = 0
        category_counts: dict[str, dict[str, int]] = {}

        for question in questions:
            query = question.get("query") or "".join(chr(value) for value in question["query_codepoints"])
            payload = {"question": query, "limit": 5}
            search = client.post(f"/api/repos/{repo_id}/search", json=payload, headers=headers)
            # This evaluator measures deterministic retrieval/evidence behavior.
            # Keep provider calls out of CI; provider-backed answer quality is covered
            # by the separate opt-in live-provider evaluation.
            with patch("repopilot.api.generate_grounded_answer", return_value=None):
                ask = client.post(f"/api/repos/{repo_id}/ask", json=payload, headers=headers)
            search.raise_for_status()
            ask.raise_for_status()
            results = search.json()["results"]
            expected_path = question["expected_path"]
            category = str(question.get("category", "uncategorized"))
            category_counts.setdefault(category, {"total": 0, "passed": 0})
            category_counts[category]["total"] += 1
            if expected_path:
                rank = next(
                    (index for index, result in enumerate(results, 1) if result["path"] == expected_path),
                    None,
                )
                path_ok = rank is not None
                if path_ok:
                    path_hits += 1
                    if rank == 1:
                        top1_hits += 1
                    reciprocal_ranks.append(1.0 / rank)
                else:
                    reciprocal_ranks.append(0.0)
                symbols = client.get(
                    f"/api/repos/{repo_id}/symbols",
                    params={"q": question["expected_symbol"]},
                    headers=headers,
                )
                symbols.raise_for_status()
                symbol_candidates = [
                    {
                        "qualified_name": symbol["qualified_name"],
                        "start_line": symbol["start_line"],
                        "end_line": symbol["end_line"],
                    }
                    for symbol in symbols.json()
                    if symbol["path"] == expected_path and symbol["name"] == question["expected_symbol"]
                ]
                symbol_ok = any(
                    symbol["start_line"] == question["expected_start_line"]
                    and symbol["end_line"] == question["expected_end_line"]
                    for symbol in symbol_candidates
                )
                symbol_hits += int(symbol_ok)
                evidence_candidates = [
                    {
                        "path": item["path"],
                        "start_line": item["start_line"],
                        "end_line": item["end_line"],
                        "source_lines_valid": _citation_matches_source(item, corpus_root),
                    }
                    for item in ask.json()["evidence"]
                ]
                citation_ok = any(
                    item["path"] == expected_path
                    and item["start_line"] <= question["expected_end_line"]
                    and item["end_line"] >= question["expected_start_line"]
                    and item["source_lines_valid"]
                    for item in evidence_candidates
                )
                citation_hits += int(citation_ok)
                category_counts[category]["passed"] += int(path_ok and symbol_ok and citation_ok)
                details.append({"id": question["id"], "category": category, "rank": rank, "path": path_ok,
                                "symbol": symbol_ok, "symbol_candidates": symbol_candidates,
                                "citation": citation_ok, "evidence_candidates": evidence_candidates})
            else:
                body = ask.json()
                abstained = body["abstained"] and not body["evidence"]
                category_counts[category]["passed"] += int(abstained)
                details.append({"id": question["id"], "category": category, "abstained": abstained,
                                "evidence_count": len(body["evidence"])})

        positive_count = len(positive)
        negative_count = len(negative)
        metrics = {
            "positive_queries": positive_count,
            "negative_queries": negative_count,
            "recall_at_5": round(path_hits / positive_count, 4),
            "recall_at_1": round(top1_hits / positive_count, 4),
            "mrr_at_5": round(sum(reciprocal_ranks) / positive_count, 4),
            "symbol_accuracy": round(symbol_hits / positive_count, 4),
            "citation_accuracy": round(citation_hits / positive_count, 4),
            "unsupported_abstention_rate": round(
                sum(item["abstained"] for item in details if "abstained" in item) / negative_count,
                4,
            ),
        }
        category_metrics = {
            category: {
                "total": values["total"],
                "accuracy": round(values["passed"] / values["total"], 4) if values["total"] else 0.0,
            }
            for category, values in sorted(category_counts.items())
        }
        passed = all(
            metrics[key] == 1.0
            for key in ("recall_at_5", "symbol_accuracy", "citation_accuracy", "unsupported_abstention_rate")
        )
        return {
            "title": "RepoPilot source-grounded validation",
            "root": str(root),
            "excluded_self_referential_dataset": "evals/datasets/ground_truth.json",
            "metrics": metrics,
            "category_metrics": category_metrics,
                "passed": passed, "results": details}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
