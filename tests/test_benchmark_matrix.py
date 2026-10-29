import pytest

from evals import benchmark_matrix


def test_run_matrix_records_commit_and_redacts_root(monkeypatch, tmp_path):
    root = tmp_path / "private-project"
    root.mkdir()
    monkeypatch.setattr(
        benchmark_matrix,
        "run",
        lambda path: {
            "repository": path.name,
            "root": str(path),
            "commit": "abc123",
            "file_count": 4,
        },
    )

    report = benchmark_matrix.run_matrix([root], redact_paths=True)

    assert report["schema_version"] == 2
    assert report["repository_count"] == 1
    assert report["path_redaction"] == "enabled"
    assert report["reports"][0]["root"] == "<redacted>"
    assert report["reports"][0]["commit"] == "abc123"
    assert str(root) not in str(report)


def test_run_matrix_rejects_duplicate_roots(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(benchmark_matrix, "run", lambda path: {"root": str(path)})

    with pytest.raises(ValueError, match="distinct"):
        benchmark_matrix.run_matrix([root, root])


def test_run_matrix_requires_existing_repository_roots(tmp_path):
    with pytest.raises(FileNotFoundError):
        benchmark_matrix.run_matrix([tmp_path / "missing"])
