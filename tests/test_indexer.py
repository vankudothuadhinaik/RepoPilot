import pytest

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
    with pytest.raises(ValueError):
        index_repository(tmp_path)



def test_known_hashes_skip_parsing_unchanged_files(fixture_repo, monkeypatch):
    import repopilot.indexer as indexer

    initial = indexer.index_repository(fixture_repo)
    known_hashes = {item["path"]: item["sha256"] for item in initial["files"]}

    def fail_if_parsed(*args, **kwargs):
        raise AssertionError("unchanged file should not be parsed")

    monkeypatch.setattr(indexer, "parse_python", fail_if_parsed)
    result = indexer.index_repository(fixture_repo, known_hashes=known_hashes)
    assert result["files"]
    assert result["symbols"] == []
    assert result["imports"] == []
