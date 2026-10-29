"""Pinned corpus snapshot materialization and source-integrity helpers."""
from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any


def _valid_relative_citation_path(path: str) -> bool:
    candidate = Path(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts and "\\" not in path


def _valid_citation_bounds(start: Any, end: Any) -> bool:
    return (
        isinstance(start, int)
        and isinstance(end, int)
        and start >= 1
        and end >= start
    )


def _parse_cited_lines(snippet: str) -> dict[int, str]:
    cited: dict[int, str] = {}
    for line in snippet.splitlines():
        number, separator, text = line.partition(": ")
        if separator and number.isdigit():
            cited[int(number)] = text
    return cited


def _cited_lines_match_source(cited: dict[int, str], source_lines: list[str]) -> bool:
    return bool(cited) and all(
        1 <= number <= len(source_lines) and source_lines[number - 1] == text
        for number, text in cited.items()
    )


def _citation_matches_source(item: dict[str, Any], root: Path) -> bool:
    path = str(item.get("path", ""))
    start, end = item.get("start_line"), item.get("end_line")
    if not _valid_relative_citation_path(path) or not _valid_citation_bounds(start, end):
        return False
    source = root / Path(path)
    if not source.is_file():
        return False
    source_lines = source.read_text(encoding="utf-8").splitlines()
    if end > len(source_lines):
        return False
    cited = _parse_cited_lines(str(item.get("snippet", "")))
    return _cited_lines_match_source(cited, source_lines)


def _query(question: dict[str, Any]) -> str:
    if question.get("query"):
        return str(question["query"])
    return "".join(chr(value) for value in question.get("query_codepoints", []))


def _remove_evaluation_artifacts(destination: Path) -> None:
    eval_dir = destination / "evals"
    for relative in (
        "datasets/ground_truth.json",
        "datasets/ground_truth_multirepo.json",
        "datasets/retrieval_50.json",
    ):
        candidate = eval_dir / relative
        if candidate.is_file():
            candidate.unlink()
    audit_report = destination / "docs" / "evaluation_audit.md"
    if audit_report.is_file():
        audit_report.unlink()


def _clean_root(root: Path, destination: Path) -> None:
    shutil.copytree(
        root,
        destination,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".venv", "node_modules", ".pytest_cache",
            ".mypy_cache", "dist", "build", "corpora",
            "retrieval_benchmark_results.json", "repository_benchmark_results.json",
            "provider-evaluation.json", "coverage.xml",
        ),
    )
    _remove_evaluation_artifacts(destination)


def _materialize_repo_revision(root: Path, revision: str, destination: Path) -> Path:
    """Materialize an exact local Git revision without copying the worktree."""
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision.lower()):
        raise ValueError(f"RepoPilot source revision must be a full SHA: {revision!r}")
    try:
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{revision}^{{commit}}"],
            check=True,
            capture_output=True,
            text=True,
        )
        archive = subprocess.run(
            ["git", "-C", str(root), "archive", "--format=tar", revision],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(
            f"required RepoPilot source revision {revision!r} is unavailable in {root}"
        ) from exc

    destination.mkdir(parents=True)
    with tarfile.open(fileobj=BytesIO(archive.stdout), mode="r:") as bundle:
        for member in bundle.getmembers():
            relative = Path(member.name)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or "\\" in member.name
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError("Git source archive contains an unsafe path")
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Git source archive contains an unsafe path")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise ValueError("Git source archive contains an unreadable file")
                target.write_bytes(source.read())
    _remove_evaluation_artifacts(destination)
    return destination


def _validate_snapshot_metadata(
    snapshot: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, str]:
    if snapshot.get("commit") != metadata.get("commit"):
        raise ValueError(f"pinned source revision mismatch for {metadata['id']!r}")
    if snapshot.get("upstream") != metadata.get("upstream"):
        raise ValueError(f"pinned source origin mismatch for {metadata['id']!r}")
    files = snapshot.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"source snapshot is empty or malformed for {metadata['id']!r}")
    return files


def _safe_snapshot_path(raw_path: str, repository_id: str) -> Path:
    relative = Path(raw_path)
    if relative.is_absolute():
        raise ValueError(f"absolute snapshot path in {repository_id!r}")
    if ".." in relative.parts:
        raise ValueError(f"snapshot path traversal in {repository_id!r}")
    if "\\" in raw_path:
        raise ValueError(f"backslash snapshot path in {repository_id!r}")
    return relative


def _write_snapshot_file(
    destination: Path, relative: Path, source_text: str, repository_id: str
) -> None:
    if not isinstance(source_text, str):
        raise ValueError(f"snapshot file must contain text for {repository_id!r}")
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source_text, encoding="utf-8")


def _materialize_snapshot(
    source_root: Path, destination: Path, metadata: dict[str, Any]
) -> Path:
    snapshot = json.loads((source_root / "snapshot.json").read_text(encoding="utf-8"))
    files = _validate_snapshot_metadata(snapshot, metadata)
    destination.mkdir(parents=True)
    for raw_path, source_text in files.items():
        relative = _safe_snapshot_path(raw_path, metadata["id"])
        _write_snapshot_file(destination, relative, source_text, metadata["id"])
    return destination


def _prepare_external_corpus(
    root: Path, name: str, metadata: dict[str, Any], destination: Path
) -> Path:
    source_root = (root / metadata["snapshot"]).resolve(strict=True)
    if not source_root.is_relative_to(root):
        raise ValueError(f"corpus path escapes checkout for {name!r}")
    return _materialize_snapshot(source_root, destination, metadata)


def _prepare_corpus(
    root: Path,
    name: str,
    metadata: dict[str, Any],
    temporary_root: Path,
    *,
    use_checkout: bool = False,
) -> Path:
    destination = temporary_root / "corpus" / name
    if name == "RepoPilot":
        if use_checkout:
            _clean_root(root, destination)
        else:
            _materialize_repo_revision(root, str(metadata["commit"]), destination)
        return destination
    return _prepare_external_corpus(root, name, metadata, destination)


def _prepare_corpora(
    root: Path,
    repositories: dict[str, dict[str, Any]],
    temporary_root: Path,
    *,
    use_checkout: bool = False,
) -> dict[str, Path]:
    return {
        name: _prepare_corpus(
            root, name, metadata, temporary_root, use_checkout=use_checkout
        )
        for name, metadata in repositories.items()
    }


def _register_corpora(client: Any, corpus_roots: dict[str, Path], headers: dict[str, str]) -> dict[str, str]:
    repo_ids: dict[str, str] = {}
    for name, corpus_root in corpus_roots.items():
        response = client.post("/api/repos", json={"path": str(corpus_root)}, headers=headers)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "registration failed")
            except ValueError:
                detail = "registration failed with a non-JSON response"
            raise RuntimeError(
                f"failed to register corpus {name!r}: HTTP {response.status_code}: {detail}"
            )
        repo_ids[name] = response.json()["id"]
    return repo_ids
