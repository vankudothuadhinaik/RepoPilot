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
        not path
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 1
        or end < start
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or "\\" in path
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


def _materialize_snapshot(source_root: Path, destination: Path, metadata: dict[str, Any]) -> Path:
    snapshot = json.loads((source_root / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("commit") != metadata.get("commit"):
        raise ValueError(f"pinned source revision mismatch for {metadata['id']!r}")
    if snapshot.get("upstream") != metadata.get("upstream"):
        raise ValueError(f"pinned source origin mismatch for {metadata['id']!r}")
    files = snapshot.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"source snapshot is empty or malformed for {metadata['id']!r}")
    destination.mkdir(parents=True)
    for raw_path, source_text in files.items():
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in raw_path:
            raise ValueError(f"unsafe snapshot path in {metadata['id']!r}")
        if not isinstance(source_text, str):
            raise ValueError(f"snapshot file must contain text for {metadata['id']!r}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source_text, encoding="utf-8")
    return destination


def _prepare_corpora(
    root: Path, repositories: dict[str, dict[str, Any]], temporary_root: Path
) -> dict[str, Path]:
    corpus_roots: dict[str, Path] = {}
    for name, metadata in repositories.items():
        destination = temporary_root / "corpus" / name
        if name == "RepoPilot":
            _clean_root(root, destination)
        else:
            source_root = (root / metadata["snapshot"]).resolve(strict=True)
            if not source_root.is_relative_to(root):
                raise ValueError(f"corpus path escapes checkout for {name!r}")
            _materialize_snapshot(source_root, destination, metadata)
        corpus_roots[name] = destination
    return corpus_roots


def _register_corpora(client: Any, corpus_roots: dict[str, Path], headers: dict[str, str]) -> dict[str, str]:
    repo_ids: dict[str, str] = {}
    for name, corpus_root in corpus_roots.items():
        response = client.post("/api/repos", json={"path": str(corpus_root)}, headers=headers)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "registration failed")
            except ValueError:
                detail = "registration failed with a non-JSON response"
            raise RuntimeError(
                f"failed to register corpus {name!r}: HTTP {response.status_code}: {detail}"
            )
        repo_ids[name] = response.json()["id"]
    return repo_ids


def _evaluate_question(
    client: Any,
    question: dict[str, Any],
    repo_id: str,
    corpus_root: Path,
    headers: dict[str, str],
) -> dict[str, Any]:
    name = question["repository"]
    category = str(question.get("category", "uncategorized"))
    payload = {"question": _query(question), "limit": 5}
    search = client.post(f"/api/repos/{repo_id}/search", json=payload, headers=headers)
    with patch("repopilot.api.generate_grounded_answer", return_value=None):
        ask = client.post(f"/api/repos/{repo_id}/ask", json=payload, headers=headers)
    search.raise_for_status()
    ask.raise_for_status()
    results = search.json()["results"]
    answer = ask.json()
    expected_path = question.get("expected_path")

    if not expected_path:
        evidence = answer.get("evidence") or []
        abstained = bool(answer.get("abstained")) and not evidence
        return {
            "id": question["id"], "repository": name, "category": category,
            "unsupported_abstained": abstained, "evidence_count": len(evidence),
            "passed": abstained,
        }

    rank = next(
        (index for index, item in enumerate(results, 1) if item["path"] == expected_path),
        None,
    )
    expected_start = question["expected_start_line"]
    expected_end = question["expected_end_line"]
    evidence_checks = [
        {
            "path": item.get("path"),
            "start_line": item.get("start_line"),
            "end_line": item.get("end_line"),
            "source_lines_valid": _citation_matches_source(item, corpus_root),
        }
        for item in (answer.get("evidence") or [])
        if isinstance(item, dict)
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
            if item["path"] == expected_path and item["name"] == question["expected_symbol"]
        ]
        symbol_ok = any(
            item["start_line"] == expected_start and item["end_line"] == expected_end
            for item in candidates
        )
    path_ok = rank is not None
    passed = path_ok and citation_ok and symbol_ok is not False
    return {
        "id": question["id"], "repository": name, "category": category,
        "expected_path": expected_path, "expected_range": [expected_start, expected_end],
        "rank_at_5": rank, "path_found": path_ok, "symbol_range_valid": symbol_ok,
        "citation_range_valid": citation_ok, "evidence_checks": evidence_checks,
        "passed": passed,
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
    ranks = [item.get("rank_at_5") for item in positive_results]
    category_counts: dict[str, dict[str, int]] = {}
    for detail in details:
        values = category_counts.setdefault(detail["category"], {"total": 0, "passed": 0})
        values["total"] += 1
        values["passed"] += int(bool(detail["passed"]))
    metrics = {
        "positive_queries": len(positives),
        "negative_queries": len(negatives),
        "symbol_range_cases": len(symbol_cases),
        "recall_at_1": round(sum(rank == 1 for rank in ranks) / len(positives), 4),
        "recall_at_5": round(sum(rank is not None for rank in ranks) / len(positives), 4),
        "mrr_at_5": round(
            sum(1 / rank if rank else 0.0 for rank in ranks) / len(positives), 4
        ),
        "citation_range_validity": round(
            sum(bool(item["citation_range_valid"]) for item in positive_results) / len(positives), 4
        ),
        "symbol_range_accuracy": (
            round(
                sum(bool(by_id[item["id"]]["symbol_range_valid"]) for item in symbol_cases)
                / len(symbol_cases), 4
            ) if symbol_cases else None
        ),
        "unsupported_abstention_rate": round(
            sum(bool(item["unsupported_abstained"]) for item in negative_results) / len(negatives), 4
        ),
        "passed_cases": sum(bool(item["passed"]) for item in details),
        "total_cases": len(details),
    }
    category_metrics = {
        name: {
            "passed": value["passed"], "total": value["total"],
            "accuracy": round(value["passed"] / value["total"], 4),
        }
        for name, value in sorted(category_counts.items())
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
        "category_metrics": category_metrics,
        "passed": all(bool(item["passed"]) for item in details),
        "results": details,
        "limitations": [
            "Maintainer-authored expected ranges are not independent review; check authoring metadata.",
            "Lexical retrieval, valid source lines, and symbol spans do not prove semantic entailment.",
            "Unsupported-query scores depend on this curated set and do not establish general abstention safety.",
            "No LLM provider is called by this offline evaluator.",
        ],
    }


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
    try:
        with tempfile.TemporaryDirectory(prefix="repopilot-multirepo-eval-") as temporary:
            temporary_root = Path(temporary)
            os.environ["REP_PILOT_API_TOKEN"] = token
            os.environ["REP_PILOT_DATA_DIR"] = str(temporary_root / "data")
            corpus_roots = _prepare_corpora(root, repositories, temporary_root)
            from fastapi.testclient import TestClient

            from repopilot.api import app

            client = TestClient(app)
            headers = {"Authorization": f"Bearer {token}"}
            repo_ids = _register_corpora(client, corpus_roots, headers)
            details = [
                _evaluate_question(
                    client, question, repo_ids[question["repository"]],
                    corpus_roots[question["repository"]], headers,
                )
                for question in questions
            ]
            return _build_report(dataset, dataset_bytes, questions, details)
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
