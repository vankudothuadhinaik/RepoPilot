from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from repopilot.security import (
    _gitignore_patterns,
    read_safe_text,
    safe_repository_root,
    should_ignore,
)

PARSER_VERSION = "2"


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
        ".ts": "typescript", ".tsx": "typescript", ".mjs": "javascript", ".cjs": "javascript",
        ".java": "java", ".kt": "kotlin",
        ".go": "go", ".rs": "rust", ".c": "c", ".h": "c/c++", ".cc": "cpp",
        ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby",
        ".php": "php", ".swift": "swift", ".scala": "scala", ".sql": "sql",
        ".md": "markdown", ".yml": "yaml", ".yaml": "yaml", ".json": "json",
    }.get(path.suffix.lower(), "text")


def parse_python(path: str, content: str) -> list[dict[str, Any]]:
    """Extract Python definitions with lexical qualified names and readable signatures."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    class DefinitionVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []
            self.symbols: list[dict[str, Any]] = []

        @staticmethod
        def signature(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(base) for base in node.bases]
                return f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            result = f"{prefix}{node.name}({ast.unparse(node.args)})"
            if node.returns is not None:
                result += f" -> {ast.unparse(node.returns)}"
            return result

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._record(node, "class")
            self.scope.append(node.name)
            for child in node.body:
                self.visit(child)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._record(node, "function")
            self.scope.append(node.name)
            for child in node.body:
                self.visit(child)
            self.scope.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._record(node, "function")
            self.scope.append(node.name)
            for child in node.body:
                self.visit(child)
            self.scope.pop()

        def _record(
            self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, kind: str
        ) -> None:
            self.symbols.append({
                "name": node.name,
                "qualified_name": ".".join([*self.scope, node.name]),
                "kind": kind,
                "path": path,
                "start_line": int(node.lineno),
                "end_line": int(getattr(node, "end_lineno", node.lineno)),
                "signature": self.signature(node),
            })

    visitor = DefinitionVisitor()
    visitor.visit(tree)
    return sorted(visitor.symbols, key=lambda item: (item["start_line"], item["qualified_name"]))


def extract_imports(path: str, content: str, language: str) -> list[dict[str, str]]:
    """Extract conservative static import/include edges without executing source code."""
    imports: list[dict[str, str]] = []

    def add(target: str, kind: str) -> None:
        normalized = target.strip()
        if normalized and not any(
            item["target"] == normalized and item["kind"] == kind for item in imports
        ):
            imports.append({"source": path, "target": normalized, "kind": kind})

    if language == "python":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    add(alias.name, "import")
            elif isinstance(node, ast.ImportFrom) and node.module:
                add("." * node.level + node.module, "import")
        return imports

    if language in {"javascript", "typescript"}:
        patterns = (
            (r"""^\s*import\s+(?:[^;\n]*?\s+from\s+)?["']([^"']+)["']""", "import"),
            (r"""^\s*export\s+[^;\n]*?\s+from\s+["']([^"']+)["']""", "import"),
            (r"""\b(?:require|import)\s*\(\s*["']([^"']+)["']\s*\)""", "require"),
        )
        for pattern, kind in patterns:
            for match in re.finditer(pattern, content, flags=re.MULTILINE):
                add(match.group(1), kind)
        return imports

    if language in {"java", "kotlin"}:
        for match in re.finditer(
            r"^\s*import\s+(?:static\s+)?([\w.*]+)", content, flags=re.MULTILINE
        ):
            add(match.group(1), "import")
        return imports

    if language == "go":
        in_import_block = False
        for line in content.splitlines():
            stripped = line.strip()
            if not in_import_block and re.match(r"^import\s*\(", stripped):
                in_import_block = True
                continue
            if in_import_block:
                if stripped == ")":
                    in_import_block = False
                    continue
                block_match = re.match(r"""(?:[\w.]+\s+)?["']([^"']+)["']""", stripped)
                if block_match:
                    add(block_match.group(1), "import")
                continue
            line_match = re.match(r"""import\s+(?:[\w.]+\s+)?["']([^"']+)["']""", stripped)
            if line_match:
                add(line_match.group(1), "import")
        return imports

    if language in {"c", "c/c++", "cpp"}:
        for match in re.finditer(
            r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', content, flags=re.MULTILINE
        ):
            add(match.group(1), "include")
        return imports

    if language == "rust":
        for match in re.finditer(r"^\s*use\s+([^;]+);", content, flags=re.MULTILINE):
            add(match.group(1), "use")
        for match in re.finditer(r"^\s*mod\s+(\w+)\s*;", content, flags=re.MULTILINE):
            add(match.group(1), "module")
        return imports

    if language == "csharp":
        for match in re.finditer(r"^\s*using\s+([\w.]+)\s*;", content, flags=re.MULTILINE):
            add(match.group(1), "using")
    return imports


def index_repository(
    raw_root: str | Path,
    known_hashes: dict[str, str] | None = None,
    known_parser_version: str | None = None
) -> dict[str, Any]:
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
            content = read_safe_text(path, root=root)
            if content is None:
                # Oversized files are intentionally outside the indexing contract.
                # Other safe-looking text files that fail to read must mark the scan
                # partial so persistence does not interpret them as deletions.
                try:
                    path.stat()
                    if not path.is_symlink():
                        rel = path.relative_to(root).as_posix()
                        reason = (
                            "File exceeds the 1 MB indexing limit or could not be safely read; "
                            "previous indexed content will be preserved."
                        )
                        errors.append({"path": rel, "error": reason})
                except (OSError, ValueError):
                    errors.append({
                        "path": str(path),
                        "error": "File changed or became unavailable during indexing; previous indexed content will be preserved.",
                    })
                continue
            rel = path.relative_to(root).as_posix()
            language = language_for(path)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            files.append({
                "path": rel, "language": language, "content": content,
                "sha256": digest, "size_bytes": len(content.encode("utf-8")),
            })
            # Reuse the persisted symbol/import records for byte-identical files.
            # The file body is still read and hashed so deletions and edits are detected.
            if (
                known_hashes is None
                or known_parser_version != PARSER_VERSION
                or known_hashes.get(rel) != digest
            ):
                if language == "python":
                    symbols.extend(parse_python(rel, content))
                imports.extend(extract_imports(rel, content, language))
        except (OSError, ValueError) as exc:
            errors.append({"path": str(path), "error": str(exc)})
    return {
        "root": str(root),
        "parser_version": PARSER_VERSION,
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
