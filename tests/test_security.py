from repopilot.indexer import index_repository


def test_secret_files_are_excluded(fixture_repo):
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != ".env" for item in indexed["files"])


def test_gitignore_is_respected(fixture_repo):
    (fixture_repo / ".gitignore").write_text("private.txt\n", encoding="utf-8")
    (fixture_repo / "private.txt").write_text("private marker", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    assert all(item["path"] != "private.txt" for item in indexed["files"])



def test_gitignore_negation_and_case_sensitivity(fixture_repo):
    (fixture_repo / ".gitignore").write_text("*.log\n!important.log\n", encoding="utf-8")
    (fixture_repo / "ignored.log").write_text("no index", encoding="utf-8")
    (fixture_repo / "important.log").write_text("include this", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "ignored.log" not in paths
    assert "important.log" in paths


def test_nested_gitignore_patterns_are_respected(fixture_repo):
    nested = fixture_repo / "src"
    nested.mkdir()
    (nested / ".gitignore").write_text("private.py\n", encoding="utf-8")
    (nested / "private.py").write_text("def secret_local(): pass\n", encoding="utf-8")
    (nested / "public.py").write_text("def public_local(): pass\n", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "src/private.py" not in paths
    assert "src/public.py" in paths


def test_symlink_escape_is_not_indexed(fixture_repo, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("def outside_secret(): pass\n", encoding="utf-8")
    link = fixture_repo / "linked.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    indexed = index_repository(fixture_repo)
    assert "linked.py" not in {item["path"] for item in indexed["files"]}
