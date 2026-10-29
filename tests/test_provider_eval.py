from evals.run_provider_eval import citation_is_valid, citation_paths, score_case


def test_citation_paths_only_accept_closed_tokens():
    assert citation_paths("Claim [[src/a.py]].") == ["src/a.py"]
    assert citation_paths("Claim [[src/a.py].") == []

def test_citation_is_valid_against_source_lines(tmp_path):
    source = tmp_path / "src" / "a.py"
    source.parent.mkdir()
    source.write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
    evidence = {"path": "src/a.py", "start_line": 1, "end_line": 2,
                "snippet": "1: def greet():\n2:     return 'hi'"}
    assert citation_is_valid(evidence, tmp_path)
    evidence["snippet"] = "1: forged"
    assert not citation_is_valid(evidence, tmp_path)

def test_citation_rejects_path_traversal(tmp_path):
    assert not citation_is_valid({"path": "../secret", "start_line": 1,
                                  "end_line": 1, "snippet": "1: secret"}, tmp_path)

def test_positive_case_reports_structural_metrics(tmp_path):
    source = tmp_path / "src" / "a.py"
    source.parent.mkdir()
    source.write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
    question = {"id": "positive", "expected_path": "src/a.py"}
    response = {"answer": "Defined here [[src/a.py]].", "abstained": False,
                "evidence": [{"path": "src/a.py", "start_line": 1, "end_line": 2,
                              "snippet": "1: def greet():\n2:     return 'hi'"}]}
    scored = score_case(question, response, tmp_path)
    assert scored["expected_path_found"] and scored["source_lines_valid"]
    assert scored["answer_citations_supported"]

def test_negative_case_requires_no_answer_and_no_evidence(tmp_path):
    question = {"id": "negative", "expected_path": None}
    assert score_case(question, {"abstained": True, "answer": "", "evidence": []}, tmp_path)["unsupported_question_abstained"]
    assert not score_case(question, {"abstained": False, "answer": "Guess", "evidence": []}, tmp_path)["unsupported_question_abstained"]


def test_live_evaluation_skips_without_provider_key(monkeypatch, tmp_path):
    from evals.run_provider_eval import evaluate

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = evaluate(tmp_path)
    assert result["status"] == "skipped"
    assert "no provider score" in result["reason"]


def test_provider_diagnostic_capture_records_only_safe_error_categories(caplog):
    import logging

    from evals.run_provider_eval import _ProviderDiagnosticCapture

    handler = _ProviderDiagnosticCapture()
    logger = logging.getLogger("provider-eval-test")
    logger.addHandler(handler)
    try:
        logger.warning("Grounded answer provider timed out.")
        logger.warning(
            "Grounded answer provider returned HTTP status 429 "
            "(code=credit_balance_exhausted, type=insufficient_quota)."
        )
    finally:
        logger.removeHandler(handler)

    assert handler.codes == ["provider_timeout", "provider_http_error"]
    assert "secret" not in caplog.text.lower()


def test_provider_pinned_corpus_excludes_evaluation_artifacts(tmp_path):
    import subprocess
    from pathlib import Path

    from evals.multirepo_corpus import _materialize_repo_revision

    root = Path(__file__).resolve().parents[1]
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    corpus = _materialize_repo_revision(root, revision, tmp_path / "provider-corpus")

    assert (corpus / "src" / "repopilot").is_dir()
    assert not (corpus / "evals" / "datasets" / "ground_truth.json").exists()
    assert not (corpus / "evals" / "corpora").exists()
    assert not (corpus / "docs" / "evaluation_audit.md").exists()


def test_positive_case_checks_expected_fact_anchor_range_and_quoted_evidence(tmp_path):
    source = tmp_path / "src" / "a.py"
    source.parent.mkdir()
    source.write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
    question = {
        "id": "positive-anchor",
        "expected_path": "src/a.py",
        "expected_start_line": 1,
        "expected_end_line": 2,
        "expected_fact": "The greet function returns the greeting string.",
        "expected_fact_anchor": "def greet",
    }
    evidence = {
        "path": "src/a.py",
        "start_line": 1,
        "end_line": 2,
        "snippet": "1: def greet():\n2:     return 'hi'",
    }
    response = {
        "answer": '"def greet():" [[src/a.py]]',
        "abstained": False,
        "evidence": [evidence],
        "mode": "llm",
    }

    scored = score_case(question, response, tmp_path)

    assert scored["expected_fact"] == question["expected_fact"]
    assert scored["expected_fact_anchor_valid"]
    assert scored["expected_range_covered"]
    assert scored["answer_quote_supported"]
