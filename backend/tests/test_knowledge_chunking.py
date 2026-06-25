"""Tests for deterministic, offline document chunking (v0.4, Phase 2).

`chunk_document` is a pure function: identical input yields identical chunks (ids,
ordering, line ranges). No embeddings, scoring, or retrieval are involved — only
structural splitting by headings, paragraphs, and fenced code blocks.
"""

from app.models import KnowledgeChunk, KnowledgeDocument, KnowledgeSourceType
from app.services.knowledge import chunk_document

_MARKDOWN = """# Title

Intro paragraph one.

## Section A

Paragraph under section A.

```python
def hello():
    return "world"
```

## Section B

Another paragraph here.
"""


def _doc(content: str = _MARKDOWN, doc_id: str = "doc-test") -> KnowledgeDocument:
    return KnowledgeDocument(
        id=doc_id,
        title="Title",
        source_type=KnowledgeSourceType.REPO_DOC,
        source_path="docs/sample.md",
        content=content,
    )


# 1. Chunks a Markdown document by heading/paragraph structure.
def test_chunks_by_structure():
    chunks = chunk_document(_doc())
    assert len(chunks) >= 3
    headings = {c.heading for c in chunks}
    assert "Section A" in headings
    assert "Section B" in headings


# 2. Produces deterministic stable chunk ids.
def test_stable_chunk_ids():
    chunks = chunk_document(_doc(doc_id="doc-abc"))
    ids = [c.id for c in chunks]
    assert ids[0] == "doc-abc#chunk-0"
    assert ids == [f"doc-abc#chunk-{i}" for i in range(len(chunks))]


# 3. Preserves heading metadata.
def test_preserves_heading_metadata():
    chunks = chunk_document(_doc())
    section_a = [c for c in chunks if c.heading == "Section A"]
    assert section_a
    assert any("section A" in c.content for c in section_a)


# 4. Preserves startLine/endLine metadata.
def test_preserves_line_metadata():
    chunks = chunk_document(_doc())
    for chunk in chunks:
        assert chunk.start_line is not None
        assert chunk.end_line is not None
        assert chunk.start_line <= chunk.end_line
    # Lines are non-decreasing across chunks.
    starts = [c.start_line for c in chunks]
    assert starts == sorted(starts)


# 5. Avoids empty chunks.
def test_avoids_empty_chunks():
    content = "# Title\n\n\n\n## Section\n\n\n\nText.\n\n\n"
    chunks = chunk_document(_doc(content=content))
    assert chunks
    for chunk in chunks:
        assert chunk.content.strip() != ""


# 6. Keeps fenced code block content together when practical.
def test_keeps_code_fence_together():
    chunks = chunk_document(_doc())
    code_chunks = [c for c in chunks if "```python" in c.content]
    assert len(code_chunks) == 1
    code = code_chunks[0].content
    assert 'def hello():' in code
    assert code.count("```") == 2  # opening and closing fence intact


# 7. Splits oversized content deterministically when max_chars is small.
def test_splits_oversized_content_deterministically():
    long_para = " ".join(f"word{i}" for i in range(200))
    content = f"# Title\n\n{long_para}\n"
    first = chunk_document(_doc(content=content), max_chars=80)
    second = chunk_document(_doc(content=content), max_chars=80)
    assert len(first) > 1
    assert [c.id for c in first] == [c.id for c in second]
    assert [c.content for c in first] == [c.content for c in second]


# 8. Produces tokenEstimate.
def test_produces_token_estimate():
    chunks = chunk_document(_doc())
    for chunk in chunks:
        assert chunk.token_estimate is not None
        assert chunk.token_estimate >= 1


# 9. Is idempotent across repeated calls.
def test_idempotent():
    doc = _doc()
    first = chunk_document(doc)
    second = chunk_document(doc)
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]


# 10. Produces valid KnowledgeChunk models.
def test_valid_models_with_camelcase():
    chunks = chunk_document(_doc())
    for chunk in chunks:
        assert isinstance(chunk, KnowledgeChunk)
        assert chunk.document_id == "doc-test"
        assert chunk.source_path == "docs/sample.md"
    payload = chunks[0].model_dump(by_alias=True)
    assert "documentId" in payload
    assert "startLine" in payload
    assert "tokenEstimate" in payload
