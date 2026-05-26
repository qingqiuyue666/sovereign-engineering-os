# Artifact Store Contract V1

## Decision

Status: CONTRACT_READY

This branch defines digest-addressed artifact manifests and verification
receipts without adding storage writes, file reads, large binary ingestion,
networking, subprocess execution, or runtime coupling.

## Contract Boundary

`ArtifactManifest` binds:

- artifact id and type
- task/run identity
- content SHA-256 and byte size
- digest-addressed storage relative path
- WAL record hash
- provenance hash
- retention marker
- quarantine marker
- local-only marker

`verify_artifact_manifest` compares an observed digest and size to the manifest
and fails closed on digest mismatch, size mismatch, manifest hash tampering, or
quarantine.

## Deferred Work

The next artifact-store branch should add bounded local ingest/verify
implementation after the real WAL storage contract is available on `main`.
This contract PR intentionally does not read artifact bytes, write artifact
files, persist manifests, or bind to the existing SQLite metadata store.

## Forbidden Surfaces

The contract rejects raw content, raw bytes, raw stdout/stderr, raw logs,
secret-like fields, path traversal, non-digest-addressed storage paths, bad
hashes, unsupported artifact types, and manifest hash mismatch.
