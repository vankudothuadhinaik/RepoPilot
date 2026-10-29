import pytest

from repopilot.indexer import index_repository, parse_python


def test_extracts_python_symbols_and_skips_secrets(fixture_repo):
    result = index_repository(fixture_repo)
    paths = {item["path"] for item in result["files"]}
    assert "app.py" in paths
    assert ".env" not in paths
    names = {item["name"] for item in result["symbols"]}
    assert {"greet", "Service"} <= names


def test_python_symbols_include_nested_qualified_names_and_signatures():
    source = """\
def outer(value: int) -> str:
    class Inner(Base):
        def method(self, item: str) -> bool:
            return bool(item)

    async def child(flag: bool = False) -> None:
        return None

    return str(value)
"""
    symbols = parse_python("nested.py", source)
    by_qualified = {item["qualified_name"]: item for item in symbols}

    assert {"outer", "outer.Inner", "outer.Inner.method", "outer.child"} <= set(by_qualified)
    assert by_qualified["outer"]["signature"] == "outer(value: int) -> str"
    assert by_qualified["outer.Inner"]["signature"] == "class Inner(Base)"
    assert by_qualified["outer.Inner.method"]["signature"] == "method(self, item: str) -> bool"
    assert by_qualified["outer.child"]["signature"].startswith("async child(")


def test_parser_version_change_forces_symbol_rebuild(fixture_repo, monkeypatch):
    import repopilot.indexer as indexer

    initial = indexer.index_repository(fixture_repo)
    known_hashes = {item["path"]: item["sha256"] for item in initial["files"]}
    original = indexer.parse_python
    parsed_paths = []

    def record_parse(path, content):
        parsed_paths.append(path)
        return original(path, content)

    monkeypatch.setattr(indexer, "parse_python", record_parse)
    indexer.index_repository(
        fixture_repo,
        known_hashes=known_hashes,
        known_parser_version="older-parser",
    )
    assert "app.py" in parsed_paths


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
    result = indexer.index_repository(
        fixture_repo,
        known_hashes=known_hashes,
        known_parser_version=indexer.PARSER_VERSION,
    )
    assert result["files"]
    assert result["symbols"] == []
    assert result["imports"] == []
