# Durable Job Queue Contract V1

## Decision

Status: CONTRACT_READY

This branch defines the durable job queue event envelope and replay projection
rules without adding persistence, a runner, a daemon, a scheduler, or execution
authority.

## Contract Boundary

`DurableQueueEvent` binds queue lifecycle records to:

- `job_id`, `task_id`, and `run_id`
- idempotency key digest
- payload digest
- attempt and max-attempt policy
- lease id, worker id, and lease expiration
- retry-after marker for retryable failures
- cancellation request marker
- dead-letter reason
- WAL record hash
- human-invoked marker for lease and heartbeat events

The projection validates sequence continuity, previous-event hash continuity,
legal lifecycle transitions, terminal-state immutability, retry/dead-letter
rules, and deterministic projection hashes.

## Deferred Work

The next queue branch should add persistence using a local append-only store
after the real WAL storage contract is available on `main`. This contract does
not implement queue storage, crash recovery, runner execution, worker admission,
or WAL append integration.

## Forbidden Surfaces

The contract introduces no arbitrary argv, cwd, env, executable, timeout,
stdout/stderr persistence, scheduler, daemon, network, provider, browser, DCC,
MCP, SQLite, or subprocess surface.
