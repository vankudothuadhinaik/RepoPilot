"""Per-case scoring and aggregate reporting for source-grounded evaluations."""
from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

try:
    from evals.multirepo_corpus import _citation_matches_source, _query
except ModuleNotFoundError:
    from multirepo_corpus import _citation_matches_source, _query


def _run_retrieval_query(
    client: Any, repo_id: str, query: str, headers: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = {"question": query, "limit": 5}
    search = client.post(f"/api/repos/{repo_id}/search", json=payload, headers=headers)
    with patch("repopilot.api.generate_grounded_answer", return_value=None):
        ask = client.post(f"/api/repos/{repo_id}/ask", json=payload, headers=headers)
    search.raise_for_status()
    ask.raise_for_status()
    return search.json()["results"], ask.json()


def _score_unsupported_question(
    question: dict[str, Any], answer: dict[str, Any]
) -> dict[str, Any]:
    evidence = answer.get("evidence") or []
    abstained = bool(answer.get("abstained")) and not evidence
    return {
        "id": question["id"], "repository": question["repository"],
        "category": str(question.get("category", "uncategorized")),
        "unsupported_abstained": abstained, "evidence_count": len(evidence),
        "passed": abstained,
    }


def _evidence_checks(answer: dict[str, Any], corpus_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": item.get("path"),
            "start_line": item.get("start_line"),
            "end_line": item.get("end_line"),
            "source_lines_valid": _citation_matches_source(item, corpus_root),
        }
        for item in (answer.get("evidence") or [])
        if isinstance(item, dict)
    ]


def _expected_path_rank(results: list[dict[str, Any]], expected_path: str) -> int | None:
    return next(
        (index for index, item in enumerate(results, 1) if item["path"] == expected_path),
        None,
    )


def _expected_symbol_valid(
    client: Any, question: dict[str, Any], repo_id: str, headers: dict[str, str]
) -> bool | None:
    symbol = question.get("expected_symbol")
    if not symbol:
        return None
    response = client.get(
        f"/api/repos/{repo_id}/symbols", params={"q": symbol}, headers=headers
    )
    response.raise_for_status()
    return any(
        item["path"] == question["expected_path"]
        and item["name"] == symbol
        and item["start_line"] == question["expected_start_line"]
        and item["end_line"] == question["expected_end_line"]
        for item in response.json()
    )


def _score_supported_question(
    client: Any,
    question: dict[str, Any],
    repo_id: str,
    corpus_root: Path,
    headers: dict[str, str],
    results: list[dict[str, Any]],
    answer: dict[str, Any],
) -> dict[str, Any]:
    expected_path = question["expected_path"]
    expected_start, expected_end = question["expected_start_line"], question["expected_end_line"]
    checks = _evidence_checks(answer, corpus_root)
    citation_ok = any(
        item["path"] == expected_path
        and isinstance(item["start_line"], int)
        and isinstance(item["end_line"], int)
        and item["start_line"] <= expected_end
        and item["end_line"] >= expected_start
        and item["source_lines_valid"]
        for item in checks
    )
    rank = _expected_path_rank(results, expected_path)
    symbol_ok = _expected_symbol_valid(client, question, repo_id, headers)
    return {
        "id": question["id"], "repository": question["repository"],
        "category": str(question.get("category", "uncategorized")),
        "expected_path": expected_path, "expected_range": [expected_start, expected_end],
        "rank_at_5": rank, "path_found": rank is not None,
        "symbol_range_valid": symbol_ok, "citation_range_valid": citation_ok,
        "evidence_checks": checks,
        "passed": rank is not None and citation_ok and symbol_ok is not False,
    }


def _evaluate_question(
    client: Any,
    question: dict[str, Any],
    repo_id: str,
    corpus_root: Path,
    headers: dict[str, str],
) -> dict[str, Any]:
    results, answer = _run_retrieval_query(client, repo_id, _query(question), headers)
    if not question.get("expected_path"):
        return _score_unsupported_question(question, answer)
    return _score_supported_question(
        client, question, repo_id, corpus_root, headers, results, answer
    )


def _retrieval_metrics(positive_results: list[dict[str, Any]]) -> dict[str, Any]:
    ranks = [item.get("rank_at_5") for item in positive_results]
    total = len(positive_results)
    return {
        "recall_at_1": round(sum(rank == 1 for rank in ranks) / total, 4),
        "recall_at_5": round(sum(rank is not None for rank in ranks) / total, 4),
        "mrr_at_5": round(sum(1 / rank if rank else 0.0 for rank in ranks) / total, 4),
    }


def _evidence_metrics(
    positive_results: list[dict[str, Any]],
    symbol_results: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(positive_results)
    return {
        "citation_range_validity": round(
            sum(bool(item["citation_range_valid"]) for item in positive_results) / total, 4
        ),
        "symbol_range_accuracy": (
            round(
                sum(bool(item["symbol_range_valid"]) for item in symbol_results)
                / len(symbol_results), 4
            ) if symbol_results else None
        ),
    }


def _abstention_metrics(negative_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "unsupported_abstention_rate": round(
            sum(bool(item["unsupported_abstained"]) for item in negative_results)
            / len(negative_results), 4
        )
    }


def _category_metrics(details: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for detail in details:
        values = counts.setdefault(detail["category"], {"total": 0, "passed": 0})
        values["total"] += 1
        values["passed"] += int(bool(detail["passed"]))
    return {
        name: {
            "passed": value["passed"], "total": value["total"],
            "accuracy": round(value["passed"] / value["total"], 4),
        }
        for name, value in sorted(counts.items())
    }


def _build_report(
    dataset: dict[str, Any], dataset_bytes: bytes, questions: list[dict[str, Any]],
    details: list[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {item["id"]: item for item in details}
    positives = [item for item in questions if item.get("expected_path")]
    negatives = [item for item in questions if not item.get("expected_path")]
    symbol_cases = [item for item in positives if item.get("expected_symbol")]
    positive_results = [by_id[item["id"]] for item in positives]
    negative_results = [by_id[item["id"]] for item in negatives]
    symbol_results = [by_id[item["id"]] for item in symbol_cases]
    metrics = {
        "positive_queries": len(positives),
        "negative_queries": len(negatives),
        "symbol_range_cases": len(symbol_cases),
        **_retrieval_metrics(positive_results),
        **_evidence_metrics(positive_results, symbol_results),
        **_abstention_metrics(negative_results),
        "passed_cases": sum(bool(item["passed"]) for item in details),
        "total_cases": len(details),
    }
    return {
        "schema_version": 1,
        "title": dataset.get("title"),
        "dataset_version": dataset.get("version"),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "authoring": dataset.get("authoring"),
        "repositories": dataset.get("repositories"),
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
        "metrics": metrics,
        "category_metrics": _category_metrics(details),
        "passed": all(bool(item["passed"]) for item in details),
        "results": details,
        "limitations": [
            "Maintainer-authored expected ranges are not independent review; check authoring metadata.",
            "Lexical retrieval, valid source lines, and symbol spans do not prove semantic entailment.",
            "Unsupported-query scores depend on this curated set and do not establish general abstention safety.",
            "No LLM provider is called by this offline evaluator.",
        ],
    }
