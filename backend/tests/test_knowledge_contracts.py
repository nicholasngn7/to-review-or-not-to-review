"""Tests for the v0.4 knowledge/retrieval contract models (Phase 1A).

Contracts only: no ingestion, chunking, embedding, retrieval, endpoints, or UI. These
tests pin down the model shapes, camelCase serialization, and the small deterministic
validations a future local retrieval pipeline will rely on. The review contract is
intentionally unchanged in this phase.
"""

import pytest
from pydantic import ValidationError

from app.models import (
    EmbeddingProviderType,
    EmbeddingVector,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSourceType,
    RetrievalEvaluationCase,
    RetrievalQuery,
    RetrievalResult,
    RetrievedCitation,
)


# 1. Enum values validate and invalid enum values fail.
def test_enum_values_validate_and_invalid_fail():
    assert KnowledgeSourceType("repo_doc") is KnowledgeSourceType.REPO_DOC
    assert KnowledgeSourceType("architecture_note") is KnowledgeSourceType.ARCHITECTURE_NOTE
    assert KnowledgeSourceType("diff") is KnowledgeSourceType.DIFF
    assert KnowledgeSourceType("manual_note") is KnowledgeSourceType.MANUAL_NOTE
    assert EmbeddingProviderType("deterministic_local") is EmbeddingProviderType.DETERMINISTIC_LOCAL
    assert (
        EmbeddingProviderType("bedrock_optional_future")
        is EmbeddingProviderType.BEDROCK_OPTIONAL_FUTURE
    )

    with pytest.raises(ValueError):
        KnowledgeSourceType("not_a_source")
    with pytest.raises(ValueError):
        EmbeddingProviderType("openai")

    # Through a model field, an unknown enum value is a validation error.
    with pytest.raises(ValidationError):
        KnowledgeDocument(id="d1", title="T", source_type="nope", content="x")
    with pytest.raises(ValidationError):
        EmbeddingVector(chunk_id="c1", provider="nope", dimensions=0, values=[])


# 2. CamelCase serialization across the new fields.
def test_camel_case_serialization():
    doc = KnowledgeDocument(
        id="d1",
        title="Architecture",
        source_type=KnowledgeSourceType.REPO_DOC,
        source_path="docs/architecture.md",
        content="body",
    )
    doc_data = doc.model_dump(by_alias=True)
    assert doc_data["sourceType"] == "repo_doc"
    assert doc_data["sourcePath"] == "docs/architecture.md"
    assert "source_type" not in doc_data and "source_path" not in doc_data

    chunk = KnowledgeChunk(
        id="c1",
        document_id="d1",
        source_path="docs/architecture.md",
        content="chunk",
        start_line=1,
        end_line=9,
        token_estimate=12,
    )
    chunk_data = chunk.model_dump(by_alias=True)
    assert chunk_data["documentId"] == "d1"
    assert chunk_data["startLine"] == 1
    assert chunk_data["endLine"] == 9
    assert chunk_data["tokenEstimate"] == 12

    cite = RetrievedCitation(snippet="s", score=0.5, chunk_id="c1")
    assert cite.model_dump(by_alias=True)["chunkId"] == "c1"

    query = RetrievalQuery(query="q", file_path="app/x.py", diff_summary="sum")
    q_data = query.model_dump(by_alias=True)
    assert q_data["topK"] == 5
    assert q_data["filePath"] == "app/x.py"
    assert q_data["diffSummary"] == "sum"

    case = RetrievalEvaluationCase(
        id="e1",
        query="q",
        expected_chunk_ids=["c1"],
        expected_source_paths=["docs/architecture.md"],
        minimum_top_k_hit_count=2,
    )
    c_data = case.model_dump(by_alias=True)
    assert c_data["expectedChunkIds"] == ["c1"]
    assert c_data["expectedSourcePaths"] == ["docs/architecture.md"]
    assert c_data["minimumTopKHitCount"] == 2


# 3. Required fields validate (missing required -> error).
def test_required_fields_validate():
    with pytest.raises(ValidationError):
        KnowledgeDocument(title="T", source_type=KnowledgeSourceType.REPO_DOC, content="x")
    with pytest.raises(ValidationError):
        KnowledgeChunk(id="c1", content="x")  # missing document_id
    with pytest.raises(ValidationError):
        RetrievalQuery()  # missing query
    with pytest.raises(ValidationError):
        RetrievalResult(chunk_id="c1", document_id="d1", score=0.1)  # missing snippet
    with pytest.raises(ValidationError):
        RetrievedCitation(snippet="s", score=0.1)  # missing chunk_id
    with pytest.raises(ValidationError):
        RetrievalEvaluationCase(query="q")  # missing id


# 4. Optional defaults work.
def test_optional_defaults():
    doc = KnowledgeDocument(
        id="d1", title="T", source_type=KnowledgeSourceType.MANUAL_NOTE, content="x"
    )
    assert doc.source_path is None
    assert doc.metadata == {}

    chunk = KnowledgeChunk(id="c1", document_id="d1", content="x")
    assert chunk.source_path is None
    assert chunk.heading is None
    assert chunk.start_line is None
    assert chunk.end_line is None
    assert chunk.token_estimate is None
    assert chunk.metadata == {}

    result = RetrievalResult(chunk_id="c1", document_id="d1", snippet="s", score=0.3)
    assert result.source_path is None
    assert result.heading is None
    assert result.metadata == {}

    case = RetrievalEvaluationCase(id="e1", query="q")
    assert case.expected_chunk_ids == []
    assert case.expected_source_paths == []
    assert case.minimum_top_k_hit_count == 1


# 5. Metadata defaults are not shared between model instances.
def test_metadata_defaults_not_shared():
    a = KnowledgeDocument(id="a", title="A", source_type=KnowledgeSourceType.REPO_DOC, content="x")
    b = KnowledgeDocument(id="b", title="B", source_type=KnowledgeSourceType.REPO_DOC, content="y")
    a.metadata["k"] = "v"
    assert b.metadata == {}
    assert a.metadata is not b.metadata

    # Same for list defaults on the evaluation case.
    c1 = RetrievalEvaluationCase(id="e1", query="q")
    c2 = RetrievalEvaluationCase(id="e2", query="q")
    c1.expected_chunk_ids.append("x")
    assert c2.expected_chunk_ids == []


# 6. EmbeddingVector accepts matching dimensions and values.
def test_embedding_vector_accepts_matching_dimensions():
    vec = EmbeddingVector(
        chunk_id="c1",
        provider=EmbeddingProviderType.DETERMINISTIC_LOCAL,
        dimensions=3,
        values=[0.1, 0.2, 0.3],
    )
    assert vec.dimensions == len(vec.values) == 3
    data = vec.model_dump(by_alias=True)
    assert data["chunkId"] == "c1"
    assert data["provider"] == "deterministic_local"

    # Zero-dimensional vector is internally consistent and allowed.
    empty = EmbeddingVector(
        chunk_id="c2",
        provider=EmbeddingProviderType.DETERMINISTIC_LOCAL,
        dimensions=0,
        values=[],
    )
    assert empty.dimensions == 0


# 7. EmbeddingVector rejects mismatched dimensions.
def test_embedding_vector_rejects_mismatched_dimensions():
    with pytest.raises(ValidationError):
        EmbeddingVector(
            chunk_id="c1",
            provider=EmbeddingProviderType.DETERMINISTIC_LOCAL,
            dimensions=4,
            values=[0.1, 0.2, 0.3],
        )


# 8. RetrievalQuery defaults topK to 5.
def test_retrieval_query_defaults_top_k():
    q = RetrievalQuery(query="hello")
    assert q.top_k == 5
    assert q.persona is None
    assert q.filters == {}


# 9. RetrievalQuery rejects top_k < 1.
def test_retrieval_query_rejects_top_k_below_one():
    with pytest.raises(ValidationError):
        RetrievalQuery(query="hello", top_k=0)
    with pytest.raises(ValidationError):
        RetrievalQuery(query="hello", top_k=-3)


# 10. RetrievalEvaluationCase defaults minimumTopKHitCount to 1.
def test_evaluation_case_defaults_minimum_hit_count():
    case = RetrievalEvaluationCase(id="e1", query="q")
    assert case.minimum_top_k_hit_count == 1


# 11. RetrievalEvaluationCase rejects minimumTopKHitCount < 1.
def test_evaluation_case_rejects_minimum_hit_count_below_one():
    with pytest.raises(ValidationError):
        RetrievalEvaluationCase(id="e1", query="q", minimum_top_k_hit_count=0)


# 12. Construction via camelCase aliases is supported (populate_by_name).
def test_construction_via_camel_case_aliases():
    chunk = KnowledgeChunk.model_validate(
        {"id": "c1", "documentId": "d1", "content": "x", "startLine": 2, "endLine": 4}
    )
    assert chunk.document_id == "d1"
    assert chunk.start_line == 2
    assert chunk.end_line == 4
