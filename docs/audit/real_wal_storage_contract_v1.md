# Real WAL Storage Contract V1

## Decision

Status: CONTRACT_READY

This branch introduces the narrow contract for future local append-only WAL
storage. It does not write files, open SQLite, run commands, start daemons,
schedule work, call providers, control browsers, or touch DCC/MCP surfaces.

## Contract Boundary

The contract defines `RealWalStorageRecord` as a deterministic digest-only WAL
envelope with:

- global positive `sequence`
- `previous_hash` chain binding
- `record_hash` computed from canonical JSON
- `created_at` excluded from the hash
- `record_type`, `task_id`, `run_id`, and `payload_hash`
- optional sorted digest-only bindings

Replay validates record hashes, monotonic sequence, sequence gaps, and previous
hash continuity. JSON-line parsing fails closed on malformed JSON and
non-newline-terminated partial records.

## Safety Rules

The contract rejects raw stdout/stderr, raw logs, command material, secret-like
field names, secret-like digest binding names, malformed hashes, unsupported
record types, hash mismatch, sequence gaps, and previous-hash mismatch.

Allowed record types are fixed to system evidence categories only, including
Minimal Controlled Execution, queue, artifact, snapshot, approval, failure
bundle, worker registry, watchdog, console, replay, install health, AI router,
DCC/media, and system acceptance events.

## Deferred Work

The next PR should implement `storage/real-wal-storage-implementation-v1` with
root-isolated local JSONL append, `flush`/`fsync`, read/replay APIs, and
fail-closed corruption handling. This contract PR intentionally does not add
the file-backed implementation or Minimal Controlled Execution adapter binding.
