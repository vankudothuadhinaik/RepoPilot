"""Per-case scoring and aggregate reporting for source-grounded evaluations."""
from __future__ import annotations

import hashlib
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

try:
    from evals.multirepo_corpus import _citation_matches_source, _query
except ModuleNotFoundError:
    from multirepo_corpus import _citation_matches_source, _query


@dataclass(frozen=True)
class QuestionContext:
    client: Any
    repo_id: str
    corpus_root: Path
    headers: dict[str, str]


def _run_retrieval_query(
    context: QuestionContext, query: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = {"question": query, "limit": 5}
    search = context.client.post(
        f"/api/repos/{context.repo_id}/search", json=payload, headers=context.headers
    )
    with patch("repopilot.api.generate_grounded_answer", return_value=None):
        ask = context.client.post(
            f"/api/repos/{context.repo_id}/ask", json=payload, headers=context.headers
        )
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
    context: QuestionContext, question: dict[str, Any]
) -> bool | None:
    symbol = question.get("expected_symbol")
    if not symbol:
        return None
    response = context.client.get(
        f"/api/repos/{context.repo_id}/symbols",
        params={"q": symbol},
        headers=context.headers,
    )
    response.raise_for_status()
    return any(
        item["path"] == question["expected_path"]
        and item["name"] == symbol
        and item["start_line"] == question["expected_start_line"]
        and item["end_line"] == question["expected_end_line"]
        for item in response.json()
    )


def _citation_covers_expected_range(
    checks: list[dict[str, Any]], expected_path: str, start: int, end: int
) -> bool:
    return any(
        item["path"] == expected_path
        and isinstance(item["start_line"], int)
        and isinstance(item["end_line"], int)
        and item["start_line"] <= end
        and item["end_line"] >= start
        and item["source_lines_valid"]
        for item in checks
    )


def _score_supported_question(
    question: dict[str, Any],
    context: QuestionContext,
    results: list[dict[str, Any]],
    answer: dict[str, Any],
) -> dict[str, Any]:
    expected_path = question["expected_path"]
    expected_start, expected_end = question["expected_start_line"], question["expected_end_line"]
    checks = _evidence_checks(answer, context.corpus_root)
    citation_ok = _citation_covers_expected_range(
        checks, expected_path, expected_start, expected_end
    )
    rank = _expected_path_rank(results, expected_path)
    symbol_ok = _expected_symbol_valid(context, question)
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
    question: dict[str, Any], context: QuestionContext
) -> dict[str, Any]:
    results, answer = _run_retrieval_query(context, _query(question))
    if not question.get("expected_path"):
        return _score_unsupported_question(question, answer)
    return _score_supported_question(question, context, results, answer)


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


@dataclass(frozen=True)
class ResultGroups:
    positive_results: list[dict[str, Any]]
    negative_results: list[dict[str, Any]]
    symbol_results: list[dict[str, Any]]


def _group_results(
    questions: list[dict[str, Any]], details: list[dict[str, Any]]
) -> ResultGroups:
    by_id = {item["id"]: item for item in details}
    positives = [item for item in questions if item.get("expected_path")]
    negatives = [item for item in questions if not item.get("expected_path")]
    symbol_cases = [item for item in positives if item.get("expected_symbol")]
    return ResultGroups(
        positive_results=[by_id[item["id"]] for item in positives],
        negative_results=[by_id[item["id"]] for item in negatives],
        symbol_results=[by_id[item["id"]] for item in symbol_cases],
    )


def _build_metrics(
    questions: list[dict[str, Any]], details: list[dict[str, Any]], groups: ResultGroups
) -> dict[str, Any]:
    positives = sum(bool(item.get("expected_path")) for item in questions)
    negatives = len(questions) - positives
    return {
        "positive_queries": positives,
        "negative_queries": negatives,
        "symbol_range_cases": len(symbol_results),
        **_retrieval_metrics(groups.positive_results),
        **_evidence_metrics(groups.positive_results, groups.symbol_results),
        **_abstention_metrics(groups.negative_results),
        "passed_cases": sum(bool(item["passed"]) for item in details),
        "total_cases": len(details),
    }


def _report_limitations() -> list[str]:
    return [
        "Maintainer-authored expected ranges are not independent review; check authoring metadata.",
        "Lexical retrieval, valid source lines, and symbol spans do not prove semantic entailment.",
        "Unsupported-query scores depend on this curated set and do not establish general abstention safety.",
        "No LLM provider is called by this offline evaluator.",
    ]


def _build_report(
    dataset: dict[str, Any],
    dataset_bytes: bytes,
    questions: list[dict[str, Any]],
    details: list[dict[str, Any]],
) -> dict[str, Any]:
    groups = _group_results(questions, details)
    metrics = _build_metrics(questions, details, groups)
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
        "limitations": _report_limitations(),
    }
