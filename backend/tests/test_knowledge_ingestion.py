"""Tests for local, offline knowledge ingestion (v0.4, Phase 2).

These exercise `ingest_local_file` against a temporary repo root with an explicit
allow-list. Ingestion is offline only: no network, URL, token, embedding, or retrieval
behavior is involved. The contract model (`KnowledgeDocument`) is reused unchanged.
"""

from pathlib import Path

import pytest

from app.models import KnowledgeDocument, KnowledgeSourceType
from app.services.knowledge import IngestionError, ingest_local_file


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "# MR Review Council\n\nLocal-only demo.\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "architecture.md").write_text(
        "# Architecture\n\nFlow overview.\n", encoding="utf-8"
    )
    return tmp_path


# 1. Reads an allowed Markdown file into a KnowledgeDocument.
def test_reads_allowed_markdown_file(tmp_path: Path):
    repo = _make_repo(tmp_path)
    doc = ingest_local_file(
        "docs/architecture.md", repo_root=repo, allowed_roots=["docs"]
    )

    assert isinstance(doc, KnowledgeDocument)
    assert doc.source_type is KnowledgeSourceType.REPO_DOC
    assert doc.source_path == "docs/architecture.md"
    assert doc.content == "# Architecture\n\nFlow overview.\n"
    assert doc.metadata["extension"] == "md"
    assert doc.metadata["relative_path"] == "docs/architecture.md"


# 2. Infers title from the first Markdown heading.
def test_infers_title_from_first_heading(tmp_path: Path):
    repo = _make_repo(tmp_path)
    doc = ingest_local_file("README.md", repo_root=repo, allowed_roots=["README.md"])
    assert doc.title == "MR Review Council"


# 3. Falls back to filename when no heading exists.
def test_falls_back_to_filename_without_heading(tmp_path: Path):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "notes.md").write_text(
        "Just prose, no heading here.\n", encoding="utf-8"
    )
    doc = ingest_local_file("docs/notes.md", repo_root=repo, allowed_roots=["docs"])
    assert doc.title == "notes.md"


# 4. Rejects paths outside allowed roots.
def test_rejects_paths_outside_allowed_roots(tmp_path: Path):
    repo = _make_repo(tmp_path)
    (repo / "secrets.txt").write_text("nope", encoding="utf-8")
    with pytest.raises(IngestionError):
        ingest_local_file("secrets.txt", repo_root=repo, allowed_roots=["docs"])


# 5. Rejects path traversal.
def test_rejects_path_traversal(tmp_path: Path):
    repo = _make_repo(tmp_path)
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    with pytest.raises(IngestionError):
        ingest_local_file(
            "docs/../../outside.md", repo_root=repo, allowed_roots=["docs"]
        )


# 6. Rejects missing files.
def test_rejects_missing_file(tmp_path: Path):
    repo = _make_repo(tmp_path)
    with pytest.raises(IngestionError):
        ingest_local_file("docs/missing.md", repo_root=repo, allowed_roots=["docs"])


# 7. Rejects directories.
def test_rejects_directories(tmp_path: Path):
    repo = _make_repo(tmp_path)
    with pytest.raises(IngestionError):
        ingest_local_file("docs", repo_root=repo, allowed_roots=["docs"])


# 8. Rejects binary/non-text files.
def test_rejects_binary_file(tmp_path: Path):
    repo = _make_repo(tmp_path)
    binary = repo / "docs" / "image.bin"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00binary\x00data")
    with pytest.raises(IngestionError):
        ingest_local_file("docs/image.bin", repo_root=repo, allowed_roots=["docs"])


# 9. Produces deterministic document ids across repeated calls.
def test_deterministic_document_ids(tmp_path: Path):
    repo = _make_repo(tmp_path)
    first = ingest_local_file(
        "docs/architecture.md", repo_root=repo, allowed_roots=["docs"]
    )
    second = ingest_local_file(
        "docs/architecture.md", repo_root=repo, allowed_roots=["docs"]
    )
    assert first.id == second.id
    assert first.id.startswith("doc-")


# 10. Produces camelCase-compatible model serialization through KnowledgeDocument.
def test_camelcase_serialization(tmp_path: Path):
    repo = _make_repo(tmp_path)
    doc = ingest_local_file(
        "docs/architecture.md", repo_root=repo, allowed_roots=["docs"]
    )
    payload = doc.model_dump(by_alias=True)
    assert payload["sourceType"] == "repo_doc"
    assert payload["sourcePath"] == "docs/architecture.md"
    assert "source_type" not in payload


# Extra: default allow-list restricts to README.md and docs/ relative to repo_root.
def test_default_allowed_roots_block_other_files(tmp_path: Path):
    repo = _make_repo(tmp_path)
    (repo / "package.json").write_text("{}", encoding="utf-8")
    with pytest.raises(IngestionError):
        ingest_local_file("package.json", repo_root=repo)
    # README.md is allowed by default.
    doc = ingest_local_file("README.md", repo_root=repo)
    assert doc.source_path == "README.md"
