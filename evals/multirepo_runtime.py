"""Runtime orchestration for offline multi-repository source-grounded evaluation."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from evals.multirepo_corpus import _prepare_corpora, _register_corpora
    from evals.multirepo_scoring import QuestionContext, _build_report, _evaluate_question
except ModuleNotFoundError:
    from multirepo_corpus import _prepare_corpora, _register_corpora
    from multirepo_scoring import QuestionContext, _build_report, _evaluate_question


@dataclass(frozen=True)
class EvaluationDataset:
    raw_bytes: bytes
    data: dict[str, Any]
    questions: list[dict[str, Any]]
    repositories: dict[str, dict[str, Any]]


def _validate_question_repositories(
    questions: list[dict[str, Any]], repositories: dict[str, dict[str, Any]]
) -> None:
    invalid = next(
        (question for question in questions if question.get("repository") not in repositories),
        None,
    )
    if invalid:
        raise ValueError(f"unknown repository in case {invalid.get('id')!r}")


def _validate_positive_ranges(questions: list[dict[str, Any]]) -> None:
    invalid = next(
        (
            question for question in questions
            if question.get("expected_path") and not _has_expected_range(question)
        ),
        None,
    )
    if invalid:
        raise ValueError(
            f"positive case {invalid.get('id')!r} must include expected line bounds"
        )


def _has_expected_range(question: dict[str, Any]) -> bool:
    return (
        isinstance(question.get("expected_start_line"), int)
        and isinstance(question.get("expected_end_line"), int)
    )


def _validate_dataset(
    dataset: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    questions = dataset["questions"]
    repositories = {item["id"]: item for item in dataset["repositories"]}
    if not questions or not repositories:
        raise ValueError("dataset must include repositories and questions")
    _validate_question_repositories(questions, repositories)
    _validate_positive_ranges(questions)
    return questions, repositories


def _load_dataset(dataset_path: Path) -> EvaluationDataset:
    raw_bytes = dataset_path.read_bytes()
    data = json.loads(raw_bytes)
    questions, repositories = _validate_dataset(data)
    return EvaluationDataset(raw_bytes, data, questions, repositories)


def _run_offline_evaluation(
    root: Path, dataset: EvaluationDataset, *, use_checkout: bool = False
) -> dict[str, Any]:
    token = "multirepo-ground-truth-local-token"
    with tempfile.TemporaryDirectory(prefix="repopilot-multirepo-eval-") as temporary:
        temporary_root = Path(temporary)
        os.environ["REP_PILOT_API_TOKEN"] = token
        os.environ["REP_PILOT_DATA_DIR"] = str(temporary_root / "data")
        corpus_roots = _prepare_corpora(
            root, dataset.repositories, temporary_root, use_checkout=use_checkout
        )
        from fastapi.testclient import TestClient

        from repopilot.api import app

        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        repo_ids = _register_corpora(client, corpus_roots, headers)
        details = [
            _evaluate_question(
                question,
                QuestionContext(
                    client=client,
                    repo_id=repo_ids[question["repository"]],
                    corpus_root=corpus_roots[question["repository"]],
                    headers=headers,
                ),
            )
            for question in dataset.questions
        ]
        report = _build_report(dataset.data, dataset.raw_bytes, dataset.questions, details)
        report["source_mode"] = "checkout_relative" if use_checkout else "git_revision"
        report["repo_pilot_revision_verified"] = not use_checkout
        return report


def evaluate(
    root: Path, dataset_path: Path | None = None, *, use_checkout: bool = False
) -> dict[str, Any]:
    """Run the deterministic evaluation without an LLM provider.

    By default RepoPilot is materialized from the dataset's exact Git revision.
    ``use_checkout`` is an explicit opt-in for evaluating proposed worktree changes.
    """
    root = root.expanduser().resolve(strict=True)
    path = dataset_path or Path(__file__).parent / "datasets" / "ground_truth_multirepo.json"
    dataset = _load_dataset(path)
    previous_token = os.environ.get("REP_PILOT_API_TOKEN")
    previous_data_dir = os.environ.get("REP_PILOT_DATA_DIR")
    try:
        return _run_offline_evaluation(root, dataset, use_checkout=use_checkout)
    finally:
        if previous_token is None:
            os.environ.pop("REP_PILOT_API_TOKEN", None)
        else:
            os.environ["REP_PILOT_API_TOKEN"] = previous_token
        if previous_data_dir is None:
            os.environ.pop("REP_PILOT_DATA_DIR", None)
        else:
            os.environ["REP_PILOT_DATA_DIR"] = previous_data_dir
