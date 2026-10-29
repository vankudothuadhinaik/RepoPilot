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
    (fixture_repo / "important.py").write_text("include this", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "ignored.log" not in paths
    assert "important.py" in paths


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


def test_safe_read_rejects_symlinked_parent_directory(fixture_repo, tmp_path):
    from repopilot.security import read_safe_text

    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "module.py"
    target.write_text("def outside_secret(): pass\n", encoding="utf-8")
    link = fixture_repo / "linked_dir"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    assert read_safe_text(link / "module.py", root=fixture_repo) is None


def test_safe_read_rejects_paths_outside_selected_root(fixture_repo, tmp_path):
    from repopilot.security import read_safe_text

    outside = tmp_path / "outside.py"
    outside.write_text("private data", encoding="utf-8")
    assert read_safe_text(outside, root=fixture_repo) is None


def test_safe_read_accepts_regular_bounded_file(fixture_repo):
    from repopilot.security import read_safe_text

    target = fixture_repo / "safe.py"
    target.write_text("def safe_function(): return 1\n", encoding="utf-8")
    content = read_safe_text(target, root=fixture_repo)
    assert content is not None
    assert content.replace("\r\n", "\n") == "def safe_function(): return 1\n"

def test_gitignore_directory_patterns_and_case_sensitivity(fixture_repo):
    (fixture_repo / ".gitignore").write_text("logs/\n", encoding="utf-8")
    ignored_dir = fixture_repo / "logs"
    ignored_dir.mkdir()
    (ignored_dir / "secret.py").write_text("def hidden(): pass\n", encoding="utf-8")
    visible_dir = fixture_repo / "logs2"
    visible_dir.mkdir()
    (visible_dir / "public.py").write_text("def visible(): pass\n", encoding="utf-8")

    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "logs/secret.py" not in paths
    assert "logs2/public.py" in paths

    # A negation with different case must not re-include a case-sensitive pattern.
    (fixture_repo / ".gitignore").write_text("*.py\n!Keep.PY\n", encoding="utf-8")
    (fixture_repo / "Keep.PY").write_text("def uppercase_extension(): pass\n", encoding="utf-8")
    (fixture_repo / "keep.py").write_text("def lowercase_extension(): pass\n", encoding="utf-8")
    indexed = index_repository(fixture_repo)
    paths = {item["path"] for item in indexed["files"]}
    assert "Keep.PY" in paths
    assert "keep.py" not in paths
