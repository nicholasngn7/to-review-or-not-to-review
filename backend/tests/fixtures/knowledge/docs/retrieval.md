# Retrieval, chunking, and citations

This document explains the local retrieval pipeline: ingestion, deterministic chunking,
lexical embedding, the in-memory index, and provenance citations.

## Chunking

Documents are split into chunks by headings and paragraphs. Each chunk has a stable
chunk identifier, preserved heading context, and start and end line metadata.

## Lexical index and citations

A deterministic local embedding provider turns each chunk into a vector. The in-memory
index ranks chunks by cosine similarity for a query. Retrieved chunks become citations
that show which context was used, as provenance only.
