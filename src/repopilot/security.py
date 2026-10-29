from __future__ import annotations

import fnmatch
import os
from pathlib import Path

DEFAULT_IGNORES = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", "target",
    "coverage", ".next", ".nuxt", ".repopilot", ".idea", ".vscode",
}
SECRET_NAMES = {
    ".env", ".env.local", ".env.production", ".npmrc", ".pypirc",
    "id_rsa", "id_ed25519", "credentials", "secrets.yaml", "secrets.yml",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}
TEXT_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".md", ".rst", ".txt", ".toml", ".yaml", ".yml", ".json", ".xml", ".html",
    ".css", ".scss", ".sql", ".sh", ".bash", ".zsh", ".dockerfile", ".make",
    ".ini", ".cfg", ".conf", ".gradle", ".properties", ".graphql", ".proto",
}
MAX_FILE_BYTES = 1_000_000


def is_secret_path(path: Path) -> bool:
    name = path.name.lower()
    return name in SECRET_NAMES or name.startswith(".env.") or path.suffix.lower() in SECRET_SUFFIXES


def _gitignore_patterns(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    try:
        return [
            line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#") and not line.startswith("!")
        ]
    except (OSError, UnicodeError):
        return []


def should_ignore(root: Path, path: Path, patterns: list[str]) -> bool:
    rel = path.relative_to(root)
    parts = {part.lower() for part in rel.parts}
    if parts & DEFAULT_IGNORES or is_secret_path(path):
        return True
    if path.is_symlink():
        return True
    if path.is_file() and path.suffix.lower() not in TEXT_SUFFIXES and path.name.lower() not in {
        "dockerfile", "makefile", "justfile"
    }:
        return True
    rel_posix = rel.as_posix()
    for pattern in patterns:
        pattern = pattern.rstrip("/")
        if fnmatch.fnmatch(rel_posix, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
        if rel_posix.startswith(pattern + "/"):
            return True
    return False


def safe_repository_root(raw: str | Path) -> Path:
    root = Path(raw).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Repository path must point to a directory.")
    if not (root / ".git").exists() and not any((root / marker).exists() for marker in (
        "pyproject.toml", "package.json", "pom.xml", "Cargo.toml", "go.mod", "README.md"
    )):
        raise ValueError("Directory does not look like a repository (no .git or common project marker).")
    return root


def read_safe_text(path: Path) -> str | None:
    try:
        if path.is_symlink() or is_secret_path(path) or path.stat().st_size > MAX_FILE_BYTES:
            return None
        raw = path.read_bytes()
        if b"\x00" in raw:
            return None
        return raw.decode("utf-8")
    except (OSError, UnicodeError):
        return None
