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


def _read_ignore_file(path: Path) -> list[str]:
    try:
        return [
            line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except (OSError, UnicodeError):
        return []


def _gitignore_patterns(root: Path) -> list[str]:
    """Return root ignore patterns, retaining negations in gitignore order."""
    return _read_ignore_file(root / ".gitignore")


def _matches_gitignore(root: Path, path: Path, patterns: list[str]) -> bool:
    """Approximate gitignore matching while preserving ordered negation semantics.

    Root patterns are anchored to root when they contain a slash; basename patterns
    apply at any depth. Nested .gitignore files are evaluated relative to their
    containing directory. A negation cannot re-include a file beneath an excluded
    parent directory, matching Git's traversal rule.
    """
    rel = path.relative_to(root).as_posix()
    components = Path(rel).parts
    ignore_files = [(root, patterns)]
    for index in range(1, len(components)):
        directory = root.joinpath(*components[:index])
        local = directory / ".gitignore"
        if local.is_file():
            ignore_files.append((directory, _read_ignore_file(local)))

    ignored = False
    excluded_dirs: set[str] = set()
    for base, entries in ignore_files:
        candidate = path.relative_to(base).as_posix()
        for raw in entries:
            negated = raw.startswith("!")
            pattern = raw[1:] if negated else raw
            if not pattern:
                continue
            directory_only = pattern.endswith("/")
            pattern = pattern.rstrip("/")
            anchored = pattern.startswith("/")
            pattern = pattern.lstrip("/")
            if not pattern:
                continue
            has_slash = "/" in pattern
            targets = [candidate]
            if not has_slash and not anchored:
                targets += [part for part in Path(candidate).parts]
            matched = any(
                fnmatch.fnmatchcase(target, pattern)
                or (target == pattern and path.is_dir())
                or (directory_only and target.startswith(pattern + "/"))
                for target in targets
            )
            # A negated basename can re-include a file matched by a wildcard
            # earlier in the same ignore file. Match the basename explicitly.
            if negated and not has_slash:
                matched = fnmatch.fnmatchcase(path.name, pattern)
            if matched:
                if negated:
                    # Git cannot re-include a child while its parent is excluded.
                    parent_rel = Path(candidate).parent.as_posix()
                    if not any(parent_rel == item or parent_rel.startswith(item + "/") for item in excluded_dirs):
                        ignored = False
                else:
                    ignored = True
                    if directory_only or path.is_dir():
                        excluded_dirs.add(candidate)
    return ignored


def should_ignore(root: Path, path: Path, patterns: list[str]) -> bool:
    try:
        root_resolved = root.resolve(strict=True)
        # Don't follow symlinks or accept a path which escaped the chosen root.
        if path.is_symlink():
            return True
        resolved = path.resolve(strict=True)
        if os.path.commonpath((str(root_resolved), str(resolved))) != str(root_resolved):
            return True
        rel = path.relative_to(root)
    except (OSError, ValueError):
        return True

    if {part.lower() for part in rel.parts} & DEFAULT_IGNORES or is_secret_path(path):
        return True
    if path.is_file() and path.suffix.lower() not in TEXT_SUFFIXES and path.name.lower() not in {
        "dockerfile", "makefile", "justfile"
    }:
        return True
    return _matches_gitignore(root, path, patterns)


def safe_repository_root(raw: str | Path) -> Path:
    root = Path(raw).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Repository path must point to a directory.")
    if not (root / ".git").exists() and not any((root / marker).exists() for marker in (
        "pyproject.toml", "package.json", "pom.xml", "Cargo.toml", "go.mod", "README.md"
    )):
        raise ValueError("Directory does not look like a repository (no .git or common project marker).")
    return root


def read_safe_text(path: Path, *, root: Path | None = None) -> str | None:
    """Read bounded UTF-8 text; re-check symlink and root containment immediately before I/O."""
    try:
        if path.is_symlink() or is_secret_path(path):
            return None
        resolved = path.resolve(strict=True)
        if root is not None:
            root_resolved = root.resolve(strict=True)
            if os.path.commonpath((str(root_resolved), str(resolved))) != str(root_resolved):
                return None
        stat_before = path.stat()
        if stat_before.st_size > MAX_FILE_BYTES or not path.is_file():
            return None
        raw = path.read_bytes()
        stat_after = path.stat()
        if path.is_symlink() or stat_before.st_ino != stat_after.st_ino or stat_before.st_size != stat_after.st_size:
            return None
        if len(raw) > MAX_FILE_BYTES or b"\x00" in raw:
            return None
        return raw.decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        return None
