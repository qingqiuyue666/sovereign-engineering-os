# Snapshot Replay Reconstruction Implementation V1

## Decision

Status: IMPLEMENTATION_READY

This branch adds a bounded local snapshot/replay reconstruction layer for the
final-system landing #517 priority. It reconstructs deterministic state from
persisted real WAL records, artifact store records, and optional durable queue
records.

## Safety Boundary

- Local-only reconstruction over caller-configured paths under one runtime root.
- Explicit input manifest with expected WAL, artifact, queue, and root hashes.
- Explicit output receipt for accepted and rejected replay attempts.
- Content-addressed snapshot IDs from deterministic source record material.
- Snapshot manifests are written through atomic no-overwrite paths.
- Existing snapshot/input/receipt files may be reused only when deterministic
  material matches; timestamp-only metadata differences do not rewrite files.
- Path traversal, symlink roots, `.git`, and secret-like path names fail closed.
- Missing WAL files, missing records, corrupted stores, hash mismatches,
  unknown input manifest versions, and reordered input manifests fail closed.
- Rejected replay receipts do not carry trusted snapshot manifest hashes.

## Store Binding

The implementation consumes existing validators before trusting source state:

- `FileBackedRealWalStorage.read_records()` for real WAL replay validation.
- `FileBackedArtifactStore.read_records()` for artifact bytes, manifests, and
  artifact WAL bindings.
- `DurableJobQueue.records` for queue projection and queue WAL bindings when a
  queue source is configured.

The reconstructor does not silently repair or truncate corrupted stores. If a
source validator rejects, replay emits a rejected receipt and does not persist
an accepted snapshot manifest.

## Deferred Work

Rollback execution, recovery orchestration, operator console mutation, failure
bundle center integration, approval runtime integration, worker runtime
integration, and system E2E acceptance remain separate later priorities.

## Forbidden Surfaces

This implementation introduces no subprocess execution, provider calls, network
access, browser control, credential access, daemon loop, queue mutation during
replay, artifact writes outside snapshot evidence, or rollback execution.
