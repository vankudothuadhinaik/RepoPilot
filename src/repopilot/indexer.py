from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path
from typing import Any

from repopilot.security import _gitignore_patterns, read_safe_text, safe_repository_root, should_ignore


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            timeout=3, check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def language_for(path: Path) -> str:
    return {
        ".py": "python", ".pyi": "python", ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".kt": "kotlin",
        ".go": "go", ".rs": "rust", ".c": "c", ".h": "c/c++", ".cc": "cpp",
        ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby",
        ".php": "php", ".swift": "swift", ".scala": "scala", ".sql": "sql",
        ".md": "markdown", ".yml": "yaml", ".yaml": "yaml", ".json": "json",
    }.get(path.suffix.lower(), "text")


def parse_python(path: str, content: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    symbols: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            symbols.append({
                "name": node.name,
                "qualified_name": node.name,
                "kind": kind,
                "path": path,
                "start_line": int(node.lineno),
                "end_line": int(getattr(node, "end_lineno", node.lineno)),
                "signature": node.name,
            })
    return sorted(symbols, key=lambda item: (item["start_line"], item["name"]))


def extract_imports(path: str, content: str, language: str) -> list[dict[str, str]]:
    imports: list[dict[str, str]] = []
    if language == "python":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend({"source": path, "target": alias.name, "kind": "import"} for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append({"source": path, "target": node.module, "kind": "import"})
    return imports


def index_repository(raw_root: str | Path) -> dict[str, Any]:
    root = safe_repository_root(raw_root)
    patterns = _gitignore_patterns(root)
    files: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    imports: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            if should_ignore(root, path, patterns):
                continue
            content = read_safe_text(path)
            if content is None:
                continue
            rel = path.relative_to(root).as_posix()
            language = language_for(path)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            files.append({
                "path": rel, "language": language, "content": content,
                "sha256": digest, "size_bytes": len(content.encode("utf-8")),
            })
            if language == "python":
                symbols.extend(parse_python(rel, content))
            imports.extend(extract_imports(rel, content, language))
        except (OSError, ValueError) as exc:
            errors.append({"path": str(path), "error": str(exc)})
    return {
        "root": str(root),
        "name": root.name,
        "branch": git_value(root, "branch", "--show-current"),
        "commit": git_value(root, "rev-parse", "HEAD"),
        "files": files,
        "symbols": symbols,
        "imports": imports,
        "errors": errors,
        "coverage": {
            "files_indexed": len(files), "symbols_found": len(symbols),
            "files_with_errors": len(errors),
        },
    }
