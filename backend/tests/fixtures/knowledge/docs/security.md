# Security and unsafe path rejection

This document covers input safety: allow-listed paths, path traversal rejection, and
why URL-like inputs are never fetched.

## Path allow-listing

Ingestion resolves a path and rejects anything outside the configured allow-list. Path
traversal attempts using parent directory segments are rejected before any read.

## Unsafe inputs

URL-like sources are rejected and never fetched. Binary and non-text files are rejected.
This keeps the local pipeline safe, offline, and predictable.
