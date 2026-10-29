"""Evaluate source-grounded retrieval over pinned, local multi-repository snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch


def _citation_matches_source(item: dict[str, Any], root: Path) -> bool:
    path = str(item.get("path", ""))
    start, end = item.get("start_line"), item.get("end_line")
    if (
        not path or not isinstance(start, int) or not isinstance(end, int)
        or start < 1 or end < start or Path(path).is_absolute()
        or ".." in Path(path).parts or "\\" in path
    ):
        return False
    source = root / Path(path)
    if not source.is_file():
        return False
    lines = source.read_text(encoding="utf-8").splitlines()
    if end > len(lines):
        return False
    cited: dict[int, str] = {}
    for line in str(item.get("snippet", "")).splitlines():
        number, separator, text = line.partition(": ")
        if separator and number.isdigit():
            cited[int(number)] = text
    return bool(cited) and all(
        1 <= number <= len(lines) and lines[number - 1] == text
        for number, text in cited.items()
    )


def _query(question: dict[str, Any]) -> str:
    if question.get("query"):
        return str(question["query"])
    return "".join(chr(value) for value in question.get("query_codepoints", []))


def _clean_root(root: Path, destination: Path) -> None:
    shutil.copytree(
        root,
        destination,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".venv", "node_modules", ".pytest_cache",
            ".mypy_cache", "dist", "build", "corpora",
            "retrieval_benchmark_results.json", "repository_benchmark_results.json",
            "provider-evaluation.json", "coverage.xml",
        ),
    )
    eval_dir = destination / "evals"
    for relative in (
        "datasets/ground_truth.json",
        "datasets/ground_truth_multirepo.json",
        "datasets/retrieval_50.json",
    ):
        candidate = eval_dir / relative
        if candidate.is_file():
            candidate.unlink()


def evaluate(root: Path, dataset_path: Path | None = None) -> dict[str, Any]:
    """Run the deterministic multi-repository evaluation without an LLM provider."""
    root = root.expanduser().resolve(strict=True)
    dataset_path = dataset_path or Path(__file__).parent / "datasets" / "ground_truth_multirepo.json"
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    questions = dataset["questions"]
    repositories = {item["id"]: item for item in dataset["repositories"]}
    if not questions or not repositories:
        raise ValueError("dataset must include repositories and questions")
    for question in questions:
        if question.get("repository") not in repositories:
            raise ValueError(f"unknown repository in case {question.get('id')!r}")
        if question.get("expected_path") and (
            not isinstance(question.get("expected_start_line"), int)
            or not isinstance(question.get("expected_end_line"), int)
        ):
            raise ValueError(f"positive case {question.get('id')!r} must include expected line bounds")

    token = "multirepo-ground-truth-local-token"
    previous_token = os.environ.get("REP_PILOT_API_TOKEN")
    previous_data_dir = os.environ.get("REP_PILOT_DATA_DIR")
    details: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="repopilot-multirepo-eval-") as temporary:
            temporary_root = Path(temporary)
            data_dir = temporary_root / "data"
            os.environ["REP_PILOT_API_TOKEN"] = token
            os.environ["REP_PILOT_DATA_DIR"] = str(data_dir)
            corpus_roots: dict[str, Path] = {}
            for name, metadata in repositories.items():
                if name == "RepoPilot":
                    corpus_root = temporary_root / "corpus" / "RepoPilot"
                    _clean_root(root, corpus_root)
                else:
                    corpus_root = temporary_root / "corpus" / name
                    source_root = root / metadata["snapshot"]
                    source_root = source_root.resolve(strict=True)
                    if not source_root.is_relative_to(root):
                        raise ValueError(f"corpus path escapes checkout for {name!r}")
                    shutil.copytree(source_root, corpus_root)
                corpus_roots[name] = corpus_root

            from fastapi.testclient import TestClient

            from repopilot.api import app

            client = TestClient(app)
            headers = {"Authorization": f"Bearer {token}"}
            repo_ids: dict[str, str] = {}
            for name, corpus_root in corpus_roots.items():
                response = client.post(
                    "/api/repos", json={"path": str(corpus_root)}, headers=headers
                )
                if response.status_code >= 400:
                    try:
                        detail = response.json().get("detail", "registration failed")
                    except ValueError:
                        detail = "registration failed with a non-JSON response"
                    raise RuntimeError(
                        f"failed to register corpus {name!r}: HTTP {response.status_code}: {detail}"
                    )
                repo_ids[name] = response.json()["id"]

            positive = [item for item in questions if item.get("expected_path")]
            negative = [item for item in questions if not item.get("expected_path")]
            symbol_cases = [item for item in positive if item.get("expected_symbol")]
            category_counts: dict[str, dict[str, int]] = {}
            reciprocal_ranks: list[float] = []
            path_hits = top1_hits = citation_hits = symbol_hits = 0

            for question in questions:
                name = question["repository"]
                repo_id = repo_ids[name]
                query = _query(question)
                payload = {"question": query, "limit": 5}
                search = client.post(
                    f"/api/repos/{repo_id}/search", json=payload, headers=headers
                )
                with patch("repopilot.api.generate_grounded_answer", return_value=None):
                    ask = client.post(
                        f"/api/repos/{repo_id}/ask", json=payload, headers=headers
                    )
                search.raise_for_status()
                ask.raise_for_status()
                results = search.json()["results"]
                answer = ask.json()
                category = str(question.get("category", "uncategorized"))
                category_counts.setdefault(category, {"total": 0, "passed": 0})
                category_counts[category]["total"] += 1
                expected_path = question.get("expected_path")

                if expected_path:
                    rank = next(
                        (i for i, item in enumerate(results, 1) if item["path"] == expected_path),
                        None,
                    )
                    path_ok = rank is not None
                    reciprocal_ranks.append(1 / rank if rank else 0.0)
                    path_hits += int(path_ok)
                    top1_hits += int(rank == 1)
                    expected_start = question["expected_start_line"]
                    expected_end = question["expected_end_line"]
                    evidence = answer.get("evidence") or []
                    evidence_checks = [
                        {
                            "path": item.get("path"),
                            "start_line": item.get("start_line"),
                            "end_line": item.get("end_line"),
                            "source_lines_valid": _citation_matches_source(
                                item, corpus_roots[name]
                            ),
                        }
                        for item in evidence if isinstance(item, dict)
                    ]
                    citation_ok = any(
                        item["path"] == expected_path
                        and isinstance(item["start_line"], int)
                        and isinstance(item["end_line"], int)
                        and item["start_line"] <= expected_end
                        and item["end_line"] >= expected_start
                        and item["source_lines_valid"]
                        for item in evidence_checks
                    )
                    citation_hits += int(citation_ok)
                    symbol_ok: bool | None = None
                    if question.get("expected_symbol"):
                        symbols = client.get(
                            f"/api/repos/{repo_id}/symbols",
                            params={"q": question["expected_symbol"]},
                            headers=headers,
                        )
                        symbols.raise_for_status()
                        candidates = [
                            item for item in symbols.json()
                            if item["path"] == expected_path
                            and item["name"] == question["expected_symbol"]
                        ]
                        symbol_ok = any(
                            item["start_line"] == expected_start
                            and item["end_line"] == expected_end
                            for item in candidates
                        )
                        symbol_hits += int(symbol_ok)
                    passed = path_ok and citation_ok and (
                        symbol_ok is not False
                    )
                    category_counts[category]["passed"] += int(passed)
                    details.append({
                        "id": question["id"], "repository": name, "category": category,
                        "expected_path": expected_path, "expected_range": [expected_start, expected_end],
                        "rank_at_5": rank, "path_found": path_ok, "symbol_range_valid": symbol_ok,
                        "citation_range_valid": citation_ok, "evidence_checks": evidence_checks,
                        "passed": passed,
                    })
                else:
                    evidence = answer.get("evidence") or []
                    abstained = bool(answer.get("abstained")) and not evidence
                    passed = abstained
                    category_counts[category]["passed"] += int(passed)
                    details.append({
                        "id": question["id"], "repository": name, "category": category,
                        "unsupported_abstained": abstained, "evidence_count": len(evidence),
                        "passed": passed,
                    })

            positive_count, negative_count = len(positive), len(negative)
            metrics = {
                "positive_queries": positive_count,
                "negative_queries": negative_count,
                "symbol_range_cases": len(symbol_cases),
                "recall_at_1": round(top1_hits / positive_count, 4) if positive_count else None,
                "recall_at_5": round(path_hits / positive_count, 4) if positive_count else None,
                "mrr_at_5": round(sum(reciprocal_ranks) / positive_count, 4) if positive_count else None,
                "citation_range_validity": round(citation_hits / positive_count, 4) if positive_count else None,
                "symbol_range_accuracy": round(symbol_hits / len(symbol_cases), 4) if symbol_cases else None,
                "unsupported_abstention_rate": (
                    round(sum(bool(item.get("unsupported_abstained")) for item in details
                               if "unsupported_abstained" in item) / negative_count, 4)
                    if negative_count else None
                ),
                "passed_cases": sum(bool(item["passed"]) for item in details),
                "total_cases": len(details),
            }
            category_metrics = {
                key: {
                    "passed": value["passed"], "total": value["total"],
                    "accuracy": round(value["passed"] / value["total"], 4),
                }
                for key, value in sorted(category_counts.items())
            }
            passed = all(item["passed"] for item in details)
            report = {
                "schema_version": 1,
                "title": dataset.get("title"),
                "dataset_version": dataset.get("version"),
                "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
                "authoring": dataset.get("authoring"),
                "repositories": dataset.get("repositories"),
                "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
                "metrics": metrics,
                "category_metrics": category_metrics,
                "passed": passed,
                "results": details,
                "limitations": [
                    "Maintainer-authored expected ranges are not independent review; check authoring metadata.",
                    "Lexical retrieval, valid source lines, and symbol spans do not prove semantic entailment.",
                    "Unsupported-query scores depend on this curated set and do not establish general abstention safety.",
                    "No LLM provider is called by this offline evaluator.",
                ],
            }
            return report
    finally:
        if previous_token is None:
            os.environ.pop("REP_PILOT_API_TOKEN", None)
        else:
            os.environ["REP_PILOT_API_TOKEN"] = previous_token
        if previous_data_dir is None:
            os.environ.pop("REP_PILOT_DATA_DIR", None)
        else:
            os.environ["REP_PILOT_DATA_DIR"] = previous_data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="RepoPilot checkout root")
    parser.add_argument(
        "--dataset", type=Path,
        default=Path(__file__).parent / "datasets" / "ground_truth_multirepo.json",
        help="Versioned multi-repository dataset JSON",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report destination")
    args = parser.parse_args()
    report = evaluate(args.root, args.dataset)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
