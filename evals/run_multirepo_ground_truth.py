"""Evaluate source-grounded retrieval over pinned, local multi-repository snapshots."""
from __future__ import annotations

import argparse
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
