from repopilot.indexer import index_repository, parse_python


def test_extracts_python_symbols_and_skips_secrets(fixture_repo):
    result = index_repository(fixture_repo)
    paths = {item["path"] for item in result["files"]}
    assert "app.py" in paths
    assert ".env" not in paths
    names = {item["name"] for item in result["symbols"]}
    assert {"greet", "Service"} <= names


def test_parse_syntax_error_returns_empty():
    assert parse_python("broken.py", "def broken(:\n") == []


def test_refuses_arbitrary_non_project_directory(tmp_path):
    import pytest
    from repopilot.indexer import index_repository

    with pytest.raises(ValueError):
        index_repository(tmp_path)
