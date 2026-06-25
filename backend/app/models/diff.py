"""Parsed-diff models.

These describe the structured representation of a unified diff once it has been
parsed. The parser itself is implemented in a later phase; this module only
defines the shape of its output so the rest of the contract can depend on it.
"""

from typing import Literal, Optional

from pydantic import Field

from .base import CamelModel

LineKind = Literal["added", "removed", "context"]
"""Whether a diff line was added, removed, or is unchanged context."""

FileChangeType = Literal["added", "modified", "deleted", "renamed", "unknown"]
"""How a file changed in the diff. `unknown` when it can't be reliably detected."""


class DiffLine(CamelModel):
    """A single line within a hunk."""

    kind: LineKind
    content: str
    old_line_no: Optional[int] = Field(
        default=None,
        description="1-based line number in the original file (None for added lines).",
    )
    new_line_no: Optional[int] = Field(
        default=None,
        description="1-based line number in the new file (None for removed lines).",
    )


class DiffHunk(CamelModel):
    """A contiguous block of changes within a file."""

    header: str = Field(description="The raw @@ hunk header line.")
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: list[DiffLine] = Field(default_factory=list)


class DiffFile(CamelModel):
    """All changes to a single file."""

    old_path: Optional[str] = Field(
        default=None,
        description="Original path (None when the file was added).",
    )
    new_path: Optional[str] = Field(
        default=None,
        description="New path (None when the file was deleted).",
    )
    change_type: FileChangeType
    hunks: list[DiffHunk] = Field(default_factory=list)


class DiffStats(CamelModel):
    """Aggregate counts across a parsed diff."""

    files_changed: int = 0
    added_lines: int = 0
    removed_lines: int = 0
    total_hunks: int = 0


class ParsedDiff(CamelModel):
    """The full structured result of parsing a unified diff."""

    files: list[DiffFile] = Field(default_factory=list)
    stats: DiffStats = Field(default_factory=DiffStats)
