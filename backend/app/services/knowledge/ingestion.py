"""Local, offline knowledge ingestion (v0.4, Phase 2).

Reads **allow-listed local text files** into `KnowledgeDocument`s. This module is
deliberately offline and deterministic:

* no network, no URL support, no HTTP client,
* no GitHub/GitLab fetching, no tokens, no OAuth,
* no embeddings, no chunking, no retrieval (those live elsewhere / later).

Paths are resolved against a `repo_root` and validated against an allow-list of roots
(files or directories), with path-traversal and symlink escapes rejected. Binary/
non-text files are rejected clearly. See `docs/v0.4-plan-rag-grounded-review.md`.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Union

from app.models.knowledge import KnowledgeDocument, KnowledgeSourceType

PathLike = Union[str, Path]

# Default allow-list (repo-relative): the project's docs-oriented sources.
DEFAULT_ALLOWED_ROOTS: tuple[str, ...] = ("README.md", "docs")

# Files larger than this are rejected (defensive bound for a local-doc ingester).
_MAX_FILE_BYTES = 5 * 1024 * 1024

_H1_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*#*\s*$")


class IngestionError(ValueError):
    """Raised when a path cannot be safely ingested as a local text document."""


def _resolve_repo_root(repo_root: PathLike | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()


def _resolve_allowed_roots(
    repo_root: Path, allowed_roots: list[PathLike] | None
) -> list[Path]:
    roots = (
        list(allowed_roots)
        if allowed_roots is not None
        else list(DEFAULT_ALLOWED_ROOTS)
    )
    resolved: list[Path] = []
    for root in roots:
        root_path = Path(root)
        # Relative roots are interpreted against repo_root; absolute roots as-is.
        resolved.append(
            (root_path if root_path.is_absolute() else repo_root / root_path).resolve()
        )
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    """True if `path` is `root` or lives under it (both already resolved)."""
    if path == root:
        return True
    return root in path.parents


def _looks_binary(raw: bytes) -> bool:
    # A NUL byte is a strong, simple binary signal for a text ingester.
    if b"\x00" in raw:
        return True
    # If it cannot be decoded as UTF-8, treat it as non-text.
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _document_id(relative_path: str) -> str:
    """Deterministic id derived only from the repo-relative path.

    Stable across calls and processes (no timestamps, no randomness).
    """
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]
    return f"doc-{digest}"


def _infer_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        match = _H1_RE.match(line)
        if match:
            return match.group(1).strip()
        # Only scan a leading non-empty stretch; the first heading should be early.
        if line.strip() and not line.lstrip().startswith("#"):
            break
    return fallback


def ingest_local_file(
    path: PathLike,
    *,
    repo_root: PathLike | None = None,
    allowed_roots: list[PathLike] | None = None,
    source_type: KnowledgeSourceType = KnowledgeSourceType.REPO_DOC,
) -> KnowledgeDocument:
    """Read a single allow-listed local text file into a `KnowledgeDocument`.

    Args:
        path: File to ingest (absolute, or relative to `repo_root`).
        repo_root: Root the relative `path`/`allowed_roots` resolve against
            (defaults to the current working directory).
        allowed_roots: Files/directories ingestion is restricted to (defaults to
            `README.md` and `docs/`, relative to `repo_root`).
        source_type: The `KnowledgeSourceType` to tag the document with.

    Raises:
        IngestionError: if the path is outside the allow-list, escapes via traversal,
            is missing, is a directory, or is binary/non-text.
    """
    repo_root_resolved = _resolve_repo_root(repo_root)
    roots = _resolve_allowed_roots(repo_root_resolved, allowed_roots)

    raw_path = Path(path)
    candidate = (
        raw_path if raw_path.is_absolute() else repo_root_resolved / raw_path
    )
    # Resolve to collapse `..` and symlinks; this is what defeats path traversal.
    resolved = candidate.resolve()

    if not any(_is_within(resolved, root) for root in roots):
        raise IngestionError(
            f"Path is outside the allowed roots: {raw_path!s}. "
            f"Allowed: {[str(r) for r in roots]}."
        )

    if not resolved.exists():
        raise IngestionError(f"File does not exist: {raw_path!s}.")
    if resolved.is_dir():
        raise IngestionError(f"Path is a directory, not a file: {raw_path!s}.")
    if not resolved.is_file():
        raise IngestionError(f"Path is not a regular file: {raw_path!s}.")

    size = resolved.stat().st_size
    if size > _MAX_FILE_BYTES:
        raise IngestionError(
            f"File is too large to ingest ({size} bytes > {_MAX_FILE_BYTES})."
        )

    raw = resolved.read_bytes()
    if _looks_binary(raw):
        raise IngestionError(
            f"File does not appear to be UTF-8 text (binary/non-text): {raw_path!s}."
        )
    content = raw.decode("utf-8")

    # Repo-relative path for stable ids/metadata; fall back to the name if the file
    # lives outside repo_root (e.g. an absolute allowed root elsewhere).
    try:
        relative_path = resolved.relative_to(repo_root_resolved).as_posix()
    except ValueError:
        relative_path = resolved.name

    title = _infer_title(content, fallback=resolved.name)
    metadata = {
        "relative_path": relative_path,
        "extension": resolved.suffix.lstrip("."),
    }

    return KnowledgeDocument(
        id=_document_id(relative_path),
        title=title,
        source_type=source_type,
        source_path=relative_path,
        content=content,
        metadata=metadata,
    )
