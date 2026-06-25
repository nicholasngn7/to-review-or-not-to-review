"""A practical unified-diff parser.

Turns raw `git diff` / unified-diff text into the shared `ParsedDiff` model.
It is intentionally pragmatic rather than a full Git implementation: it handles
the common markers produced by `git diff` and standard unified diffs, and falls
back gracefully (change type `unknown`) when something can't be determined.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.models.diff import (
    DiffFile,
    DiffHunk,
    DiffLine,
    DiffStats,
    FileChangeType,
    ParsedDiff,
)

# @@ -oldStart,oldLines +newStart,newLines @@ optional section heading
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@"
)

_DIFF_GIT_RE = re.compile(r"^diff --git (?:a/)?(?P<a>.+?) (?:b/)?(?P<b>.+)$")


def _strip_prefix(path: str) -> Optional[str]:
    """Normalize a `---`/`+++` path: drop a/ b/ prefixes, tabs, /dev/null."""
    # Trailing tab + timestamp that some tools append.
    path = path.split("\t", 1)[0].strip()
    if path == "/dev/null" or path == "":
        return None
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


@dataclass
class _FileBuilder:
    """Mutable accumulator for a single file while parsing."""

    old_path: Optional[str] = None
    new_path: Optional[str] = None
    explicit_change_type: Optional[FileChangeType] = None
    saw_dev_null_old: bool = False
    saw_dev_null_new: bool = False
    hunks: list[DiffHunk] = field(default_factory=list)
    added: int = 0
    removed: int = 0

    def resolve_change_type(self) -> FileChangeType:
        if self.explicit_change_type is not None:
            return self.explicit_change_type
        if self.saw_dev_null_old:
            return "added"
        if self.saw_dev_null_new:
            return "deleted"
        if (
            self.old_path is not None
            and self.new_path is not None
            and self.old_path != self.new_path
        ):
            return "renamed"
        if self.hunks or self.old_path is not None or self.new_path is not None:
            return "modified"
        return "unknown"

    def to_model(self) -> DiffFile:
        change_type = self.resolve_change_type()
        old_path = self.old_path
        new_path = self.new_path
        # A /dev/null side (or an add/delete) means that side has no path.
        if self.saw_dev_null_old or change_type == "added":
            old_path = None
        if self.saw_dev_null_new or change_type == "deleted":
            new_path = None
        return DiffFile(
            old_path=old_path,
            new_path=new_path,
            change_type=change_type,
            hunks=self.hunks,
        )


def parse_diff(diff_text: str) -> ParsedDiff:
    """Parse unified diff text into a `ParsedDiff`.

    Args:
        diff_text: Raw unified diff or `git diff` output.

    Returns:
        A `ParsedDiff` with per-file hunks and aggregate stats.
    """
    lines = diff_text.splitlines()
    builders: list[_FileBuilder] = []
    current: Optional[_FileBuilder] = None

    i = 0
    n = len(lines)

    def ensure_current() -> _FileBuilder:
        """Return the active file builder, starting one if a header was implicit."""
        nonlocal current
        if current is None:
            current = _FileBuilder()
            builders.append(current)
        return current

    while i < n:
        line = lines[i]

        # --- New file section ---
        git_match = _DIFF_GIT_RE.match(line)
        if git_match:
            current = _FileBuilder(
                old_path=_strip_prefix(git_match.group("a")),
                new_path=_strip_prefix(git_match.group("b")),
            )
            builders.append(current)
            i += 1
            continue

        if line.startswith("new file mode"):
            ensure_current().explicit_change_type = "added"
            i += 1
            continue
        if line.startswith("deleted file mode"):
            ensure_current().explicit_change_type = "deleted"
            i += 1
            continue
        if line.startswith("rename from "):
            b = ensure_current()
            b.old_path = line[len("rename from ") :].strip()
            b.explicit_change_type = "renamed"
            i += 1
            continue
        if line.startswith("rename to "):
            b = ensure_current()
            b.new_path = line[len("rename to ") :].strip()
            b.explicit_change_type = "renamed"
            i += 1
            continue
        # copy from/to, similarity index, index, mode lines: structural noise.
        if line.startswith(
            ("index ", "similarity index", "dissimilarity index", "old mode", "new mode")
        ):
            i += 1
            continue
        if line.startswith("copy from "):
            ensure_current().old_path = line[len("copy from ") :].strip()
            i += 1
            continue
        if line.startswith("copy to "):
            ensure_current().new_path = line[len("copy to ") :].strip()
            i += 1
            continue

        # --- File path markers ---
        if line.startswith("--- "):
            b = ensure_current()
            path = _strip_prefix(line[4:])
            if path is None:
                b.saw_dev_null_old = True
            else:
                b.old_path = path
            i += 1
            continue
        if line.startswith("+++ "):
            b = ensure_current()
            path = _strip_prefix(line[4:])
            if path is None:
                b.saw_dev_null_new = True
            else:
                b.new_path = path
            i += 1
            continue

        # --- Hunk ---
        hunk_match = _HUNK_HEADER_RE.match(line)
        if hunk_match:
            b = ensure_current()
            old_start = int(hunk_match.group("old_start"))
            old_lines = int(hunk_match.group("old_lines") or 1)
            new_start = int(hunk_match.group("new_start"))
            new_lines = int(hunk_match.group("new_lines") or 1)

            hunk = DiffHunk(
                header=line,
                old_start=old_start,
                old_lines=old_lines,
                new_start=new_start,
                new_lines=new_lines,
                lines=[],
            )

            old_cursor = old_start
            new_cursor = new_start
            old_remaining = old_lines
            new_remaining = new_lines

            i += 1
            # Consume body lines until the hunk's line budget is exhausted or a
            # new structural marker appears.
            while i < n and (old_remaining > 0 or new_remaining > 0):
                body = lines[i]
                if body.startswith("\\"):  # "\ No newline at end of file"
                    i += 1
                    continue
                if (
                    body.startswith("diff --git ")
                    or body.startswith("--- ")
                    or body.startswith("+++ ")
                    or _HUNK_HEADER_RE.match(body)
                ):
                    break

                if body.startswith("+"):
                    hunk.lines.append(
                        DiffLine(kind="added", content=body[1:], new_line_no=new_cursor)
                    )
                    new_cursor += 1
                    new_remaining -= 1
                    b.added += 1
                elif body.startswith("-"):
                    hunk.lines.append(
                        DiffLine(kind="removed", content=body[1:], old_line_no=old_cursor)
                    )
                    old_cursor += 1
                    old_remaining -= 1
                    b.removed += 1
                else:
                    # Context line: leading space, or a truly empty line.
                    content = body[1:] if body.startswith(" ") else body
                    hunk.lines.append(
                        DiffLine(
                            kind="context",
                            content=content,
                            old_line_no=old_cursor,
                            new_line_no=new_cursor,
                        )
                    )
                    old_cursor += 1
                    new_cursor += 1
                    old_remaining -= 1
                    new_remaining -= 1
                i += 1

            b.hunks.append(hunk)
            continue

        # Unrecognized line (preamble, commit text, etc.) -> skip.
        i += 1

    files = [b.to_model() for b in builders]
    stats = DiffStats(
        files_changed=len(files),
        added_lines=sum(b.added for b in builders),
        removed_lines=sum(b.removed for b in builders),
        total_hunks=sum(len(b.hunks) for b in builders),
    )
    return ParsedDiff(files=files, stats=stats)
