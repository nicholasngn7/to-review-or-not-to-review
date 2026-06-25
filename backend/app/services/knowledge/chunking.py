"""Deterministic, offline Markdown/text chunking (v0.4, Phase 2).

`chunk_document` is a **pure** function: the same `KnowledgeDocument` and `max_chars`
always produce identical `KnowledgeChunk`s (stable ids, ordering, and line ranges), so
calling it repeatedly is idempotent. It splits content by headings, paragraphs, and
fenced code blocks, keeps code fences intact where practical, and splits oversized
prose by line/character boundaries deterministically.

There are **no** embeddings, no vector values, no scoring, and no retrieval here — only
structural chunking. See `docs/v0.4-plan-rag-grounded-review.md`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


@dataclass
class _Block:
    kind: str  # "heading" | "paragraph" | "code"
    text: str
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    heading: str | None = None


@dataclass
class _Group:
    heading: str | None
    blocks: list[_Block] = field(default_factory=list)


def _heading(line: str) -> tuple[int, str] | None:
    match = _HEADING_RE.match(line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _fence_open(line: str) -> str | None:
    """Return the fence marker (e.g. '```') if `line` opens a code fence."""
    match = _FENCE_RE.match(line)
    if not match:
        return None
    return match.group(2)


def _fence_closes(line: str, marker: str) -> bool:
    match = _FENCE_RE.match(line)
    if not match:
        return False
    fence = match.group(2)
    # Same fence char, at least as long, and nothing but whitespace after it.
    return (
        fence[0] == marker[0]
        and len(fence) >= len(marker)
        and match.group(3).strip() == ""
    )


def _split_blocks(content: str) -> list[_Block]:
    lines = content.splitlines()
    n = len(lines)
    blocks: list[_Block] = []
    i = 0
    while i < n:
        line = lines[i]
        if line.strip() == "":
            i += 1
            continue

        marker = _fence_open(line)
        if marker is not None:
            start = i
            body = [line]
            i += 1
            while i < n and not _fence_closes(lines[i], marker):
                body.append(lines[i])
                i += 1
            if i < n:  # include the closing fence line
                body.append(lines[i])
                i += 1
            blocks.append(
                _Block(
                    kind="code",
                    text="\n".join(body),
                    start_line=start + 1,
                    end_line=start + len(body),
                )
            )
            continue

        head = _heading(line)
        if head is not None:
            blocks.append(
                _Block(
                    kind="heading",
                    text=line.rstrip(),
                    start_line=i + 1,
                    end_line=i + 1,
                    heading=head[1],
                )
            )
            i += 1
            continue

        # Paragraph: contiguous lines until a blank, heading, or fence.
        start = i
        para = [line]
        i += 1
        while i < n:
            nxt = lines[i]
            if nxt.strip() == "" or _heading(nxt) or _fence_open(nxt):
                break
            para.append(nxt)
            i += 1
        blocks.append(
            _Block(
                kind="paragraph",
                text="\n".join(para),
                start_line=start + 1,
                end_line=start + len(para),
            )
        )
    return blocks


def _char_slices(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)] or [text]


def _split_oversized_paragraph(block: _Block, max_chars: int) -> list[_Block]:
    """Split a too-large paragraph into ≤ max_chars sub-blocks, deterministically."""
    lines = block.text.split("\n")
    subs: list[_Block] = []
    cur: list[str] = []
    cur_len = 0
    cur_start = block.start_line
    line_no = block.start_line

    def flush(end_line: int) -> None:
        nonlocal cur, cur_len, cur_start
        if cur:
            subs.append(
                _Block(
                    kind="paragraph",
                    text="\n".join(cur),
                    start_line=cur_start,
                    end_line=end_line,
                    heading=block.heading,
                )
            )
            cur = []
            cur_len = 0

    for ln in lines:
        if len(ln) > max_chars:
            flush(line_no - 1)
            for piece in _char_slices(ln, max_chars):
                subs.append(
                    _Block(
                        kind="paragraph",
                        text=piece,
                        start_line=line_no,
                        end_line=line_no,
                        heading=block.heading,
                    )
                )
            line_no += 1
            cur_start = line_no
            continue
        if cur and cur_len + len(ln) + 1 > max_chars:
            flush(line_no - 1)
            cur_start = line_no
        cur.append(ln)
        cur_len += len(ln) + 1
        line_no += 1
    flush(line_no - 1)
    return subs


def _group_blocks(blocks: list[_Block], max_chars: int) -> list[_Group]:
    groups: list[_Group] = []
    current = _Group(heading=None)
    current_len = 0
    current_heading: str | None = None

    def flush() -> None:
        nonlocal current, current_len
        if current.blocks:
            groups.append(current)
        current = _Group(heading=current_heading)
        current_len = 0

    for blk in blocks:
        if blk.kind == "heading":
            flush()
            current_heading = blk.heading
            current = _Group(heading=current_heading, blocks=[blk])
            current_len = len(blk.text)
            continue

        if blk.kind == "paragraph" and len(blk.text) > max_chars:
            flush()
            for sub in _split_oversized_paragraph(blk, max_chars):
                groups.append(_Group(heading=current_heading, blocks=[sub]))
            continue

        if current.blocks and current_len + len(blk.text) > max_chars:
            flush()
        current.blocks.append(blk)
        current_len += len(blk.text)

    if current.blocks:
        groups.append(current)
    return groups


def _estimate_tokens(text: str) -> int:
    # Simple, deterministic approximation (whitespace-delimited words).
    return max(1, len(text.split()))


def chunk_document(
    document: KnowledgeDocument, *, max_chars: int = 1200
) -> list[KnowledgeChunk]:
    """Split a `KnowledgeDocument` into stable, deterministic `KnowledgeChunk`s.

    Chunk ids are `f"{document.id}#chunk-{ordinal}"`. Empty/whitespace-only groups are
    never emitted. Pure and idempotent: identical input yields identical output.
    """
    blocks = _split_blocks(document.content)
    groups = _group_blocks(blocks, max_chars)

    chunks: list[KnowledgeChunk] = []
    ordinal = 0
    for group in groups:
        text = "\n\n".join(blk.text for blk in group.blocks)
        if text.strip() == "":
            continue
        start_line = group.blocks[0].start_line
        end_line = group.blocks[-1].end_line
        chunks.append(
            KnowledgeChunk(
                id=f"{document.id}#chunk-{ordinal}",
                document_id=document.id,
                source_path=document.source_path,
                heading=group.heading,
                content=text,
                start_line=start_line,
                end_line=end_line,
                token_estimate=_estimate_tokens(text),
                metadata={},
            )
        )
        ordinal += 1
    return chunks
