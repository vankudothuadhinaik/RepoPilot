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


def test_provider_corpus_excludes_labels_and_external_fixtures(tmp_path):
    from evals.run_provider_eval import _prepare_provider_corpus

    root = tmp_path / "checkout"
    (root / "src").mkdir(parents=True)
    (root / "evals" / "datasets").mkdir(parents=True)
    (root / "evals" / "corpora" / "other").mkdir(parents=True)
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "src" / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (root / "evals" / "datasets" / "ground_truth.json").write_text(
        '{"answer":"label"}', encoding="utf-8"
    )
    (root / "evals" / "corpora" / "other" / "secret.py").write_text(
        "fixture data", encoding="utf-8"
    )

    corpus = _prepare_provider_corpus(root, tmp_path / "provider-corpus")

    assert (corpus / "src" / "app.py").is_file()
    assert not (corpus / "evals" / "datasets").exists()
    assert not (corpus / "evals" / "corpora").exists()
