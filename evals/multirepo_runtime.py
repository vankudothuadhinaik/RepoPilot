"""Runtime orchestration for offline multi-repository source-grounded evaluation."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from evals.multirepo_corpus import _prepare_corpora, _register_corpora
    from evals.multirepo_scoring import _build_report, _evaluate_question
except ModuleNotFoundError:
    from multirepo_corpus import _prepare_corpora, _register_corpora
    from multirepo_scoring import _build_report, _evaluate_question


def _validate_dataset(
    dataset: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    questions = dataset["questions"]
    repositories = {item["id"]: item for item in dataset["repositories"]}
    if not questions or not repositories:
        raise ValueError("dataset must include repositories and questions")
    for question in questions:
        if question.get("repository") not in repositories:
            raise ValueError(f"unknown repository in case {question.get('id')!r}")
        if question.get("expected_path") and not _has_expected_range(question):
            raise ValueError(f"positive case {question.get('id')!r} must include expected line bounds")
    return questions, repositories


def _has_expected_range(question: dict[str, Any]) -> bool:
    return (
        isinstance(question.get("expected_start_line"), int)
        and isinstance(question.get("expected_end_line"), int)
    )


def _load_dataset(
    dataset_path: Path,
) -> tuple[bytes, dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes)
    questions, repositories = _validate_dataset(dataset)
    return dataset_bytes, dataset, questions, repositories


def _run_offline_evaluation(
    root: Path,
    dataset: dict[str, Any],
    dataset_bytes: bytes,
    questions: list[dict[str, Any]],
    repositories: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    token = "multirepo-ground-truth-local-token"
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
                client,
                question,
                repo_ids[question["repository"]],
                corpus_roots[question["repository"]],
                headers,
            )
            for question in questions
        ]
        return _build_report(dataset, dataset_bytes, questions, details)


def evaluate(root: Path, dataset_path: Path | None = None) -> dict[str, Any]:
    """Run the deterministic multi-repository evaluation without an LLM provider."""
    root = root.expanduser().resolve(strict=True)
    path = dataset_path or Path(__file__).parent / "datasets" / "ground_truth_multirepo.json"
    dataset_bytes, dataset, questions, repositories = _load_dataset(path)
    previous_token = os.environ.get("REP_PILOT_API_TOKEN")
    previous_data_dir = os.environ.get("REP_PILOT_DATA_DIR")
    try:
        return _run_offline_evaluation(root, dataset, dataset_bytes, questions, repositories)
    finally:
        if previous_token is None:
            os.environ.pop("REP_PILOT_API_TOKEN", None)
        else:
            os.environ["REP_PILOT_API_TOKEN"] = previous_token
        if previous_data_dir is None:
            os.environ.pop("REP_PILOT_DATA_DIR", None)
        else:
            os.environ["REP_PILOT_DATA_DIR"] = previous_data_dir
