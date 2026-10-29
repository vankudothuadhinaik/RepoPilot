"""Pinned corpus snapshot materialization and source-integrity helpers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def _citation_matches_source(item: dict[str, Any], root: Path) -> bool:
    path = str(item.get("path", ""))
    start, end = item.get("start_line"), item.get("end_line")
    if (
        not path
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 1
        or end < start
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or "\\" in path
    ):
        return False
    source = root / Path(path)
    if not source.is_file():
        return False
    lines = source.read_text(encoding="utf-8").splitlines()
    if end > len(lines):
        return False
    cited: dict[int, str] = {}
    for line in str(item.get("snippet", "")).splitlines():
        number, separator, text = line.partition(": ")
        if separator and number.isdigit():
            cited[int(number)] = text
    return bool(cited) and all(
        1 <= number <= len(lines) and lines[number - 1] == text
        for number, text in cited.items()
    )


def _query(question: dict[str, Any]) -> str:
    if question.get("query"):
        return str(question["query"])
    return "".join(chr(value) for value in question.get("query_codepoints", []))


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
    eval_dir = destination / "evals"
    for relative in (
        "datasets/ground_truth.json",
        "datasets/ground_truth_multirepo.json",
        "datasets/retrieval_50.json",
    ):
        candidate = eval_dir / relative
        if candidate.is_file():
            candidate.unlink()


def _materialize_snapshot(source_root: Path, destination: Path, metadata: dict[str, Any]) -> Path:
    snapshot = json.loads((source_root / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("commit") != metadata.get("commit"):
        raise ValueError(f"pinned source revision mismatch for {metadata['id']!r}")
    if snapshot.get("upstream") != metadata.get("upstream"):
        raise ValueError(f"pinned source origin mismatch for {metadata['id']!r}")
    files = snapshot.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"source snapshot is empty or malformed for {metadata['id']!r}")
    destination.mkdir(parents=True)
    for raw_path, source_text in files.items():
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in raw_path:
            raise ValueError(f"unsafe snapshot path in {metadata['id']!r}")
        if not isinstance(source_text, str):
            raise ValueError(f"snapshot file must contain text for {metadata['id']!r}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source_text, encoding="utf-8")
    return destination


def _prepare_external_corpus(
    root: Path, name: str, metadata: dict[str, Any], destination: Path
) -> Path:
    source_root = (root / metadata["snapshot"]).resolve(strict=True)
    if not source_root.is_relative_to(root):
        raise ValueError(f"corpus path escapes checkout for {name!r}")
    return _materialize_snapshot(source_root, destination, metadata)


def _prepare_corpus(
    root: Path, name: str, metadata: dict[str, Any], temporary_root: Path
) -> Path:
    destination = temporary_root / "corpus" / name
    if name == "RepoPilot":
        _clean_root(root, destination)
        return destination
    return _prepare_external_corpus(root, name, metadata, destination)


def _prepare_corpora(
    root: Path, repositories: dict[str, dict[str, Any]], temporary_root: Path
) -> dict[str, Path]:
    return {
        name: _prepare_corpus(root, name, metadata, temporary_root)
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
