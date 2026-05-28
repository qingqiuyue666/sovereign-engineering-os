# Artifact Store Persistence Implementation V1

## Decision

Status: IMPLEMENTATION_READY

This branch adds a bounded local file-backed artifact persistence layer for
Artifact Store Contract V1. It stores artifact bytes under digest-addressed
paths, appends immutable JSONL manifest records, and binds each artifact event
to the merged real WAL storage backend.

## Safety Boundary

- Local-only file storage.
- Content-addressed artifact ids and storage paths.
- SHA-256 content hashes.
- Temp-file write followed by local rename.
- No overwrite of existing artifact paths or artifact ids.
- Fail-closed path validation for traversal, symlink, `.git`, and secret-like
  paths.
- JSON-safe metadata only; raw output, execution material, and secret-like keys
  are rejected.
- Deterministic manifest listing by artifact id.
- Replay verifies manifest hashes, record chaining, artifact bytes, and real WAL
  bindings.

## WAL Binding

`FileBackedArtifactStore` binds each artifact manifest to
`FileBackedRealWalStorage` with an `ARTIFACT_EVENT` record. Replay rejects
missing, corrupted, mismatched, or tampered WAL records.

## Deferred Integration

Durable job queue and broader runtime integration are intentionally deferred.
The safe V1 boundary is the persistence spine only; queue/runtime call sites can
bind to this store in a later small PR once their artifact ownership and
idempotency semantics are explicit.
