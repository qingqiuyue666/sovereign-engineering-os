# Snapshot Replay Contract V1

## Decision

Status: CONTRACT_READY

This branch defines digest-only pre/post snapshot manifests and replay
reconstruction receipts. It does not capture filesystem state, read paths,
write snapshots, or execute rollback.

## Contract Boundary

`SnapshotManifest` binds:

- pre/post snapshot kind
- task/run identity
- snapshot root hash
- changed path digest list
- artifact manifest hash
- WAL record hash
- rollback plan hash

`reconstruct_snapshot_pair` verifies manifest hash integrity, pre/post kind,
task/run identity, rollback-plan consistency, and emits a deterministic replay
root hash. The receipt is a reconstruction proof only.

## Deferred Work

The next snapshot branch should implement bounded local snapshot manifest
capture after the real WAL and artifact-store contracts are available on
`main`. Destructive rollback execution remains explicitly out of scope.

## Forbidden Surfaces

The contract rejects raw path fields, absolute/raw path material, raw content,
stdout/stderr, secret-like fields, malformed digests, duplicate changed path
digests, manifest hash mismatch, and pre/post identity mismatch.
