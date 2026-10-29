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
            if negated and has_slash:
                matched = fnmatch.fnmatchcase(candidate, pattern)
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
    """Read bounded UTF-8 text without following symlinks during POSIX path traversal.

    Directory-relative opens pin each path component to an already-open directory,
    preventing a concurrent symlink swap from redirecting the read outside root.
    Platforms without dir_fd/O_NOFOLLOW use repeated containment and identity checks.
    """
    import stat

    try:
        if is_secret_path(path) or root is None:
            return None
        root_resolved = root.resolve(strict=True)
        relative = path.relative_to(root)
        if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
            return None
        if path.is_symlink():
            return None

        nofollow = getattr(os, "O_NOFOLLOW", 0)
        directory_flag = getattr(os, "O_DIRECTORY", 0)
        supports_dir_fd = os.name == "posix" and bool(nofollow and directory_flag)
        if supports_dir_fd:
            root_fd = os.open(root_resolved, os.O_RDONLY | directory_flag)
            parent_fd = root_fd
            opened_fds = [root_fd]
            try:
                for component in relative.parts[:-1]:
                    next_fd = os.open(
                        component, os.O_RDONLY | directory_flag | nofollow, dir_fd=parent_fd
                    )
                    opened_fds.append(next_fd)
                    parent_fd = next_fd
                file_fd = os.open(relative.parts[-1], os.O_RDONLY | nofollow, dir_fd=parent_fd)
                try:
                    before = os.fstat(file_fd)
                    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
                        return None
                    chunks: list[bytes] = []
                    remaining = MAX_FILE_BYTES + 1
                    while remaining:
                        chunk = os.read(file_fd, min(65536, remaining))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        remaining -= len(chunk)
                    raw = b"".join(chunks)
                    after = os.fstat(file_fd)
                    current = os.stat(relative.parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                    identity_before = (
                        before.st_dev, before.st_ino, before.st_size,
                        before.st_mtime_ns, before.st_ctime_ns,
                    )
                    identity_after = (
                        after.st_dev, after.st_ino, after.st_size,
                        after.st_mtime_ns, after.st_ctime_ns,
                    )
                    identity_path = (
                        current.st_dev, current.st_ino, current.st_size,
                        current.st_mtime_ns, current.st_ctime_ns,
                    )
                    if identity_before != identity_after or identity_after != identity_path:
                        return None
                finally:
                    os.close(file_fd)
            finally:
                for descriptor in reversed(opened_fds):
                    os.close(descriptor)
        else:
            resolved = path.resolve(strict=True)
            if os.path.commonpath((str(root_resolved), str(resolved))) != str(root_resolved):
                return None
            before = path.stat()
            if before.st_size > MAX_FILE_BYTES or not path.is_file():
                return None
            raw = path.read_bytes()
            after = path.stat()
            resolved_after = path.resolve(strict=True)
            if (
                os.path.commonpath((str(root_resolved), str(resolved_after))) != str(root_resolved)
                or path.is_symlink()
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            ):
                return None

        if len(raw) > MAX_FILE_BYTES or b"\x00" in raw:
            return None
        return raw.decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        return None
