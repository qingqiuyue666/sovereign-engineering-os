# Watchdog Runtime Integration V1

## Scope

Priority #523 adds a manual, file-backed watchdog runtime integration over the
durable queue, watchdog receipt contract, failure bundle center, worker
quarantine, artifact store, and real WAL storage. It does not enable a
background daemon by default and exposes no process launch, provider, browser,
network, scheduler, or credential surface.

## Runtime Boundary

`FileBackedWatchdogRuntimeIntegration` supports:

- explicit queue heartbeat recording
- human-invoked watchdog sweeps
- queue lease timeout detection
- stale lease recovery through the durable queue lifecycle
- retry and dead-letter linkage from queue state
- resource breach observations
- failure bundle binding for unsafe watchdog states
- worker quarantine receipts for runaway jobs
- real WAL records of type `WATCHDOG_EVENT`
- local `audit_json` artifacts and operator-visible watchdog state

All persisted watchdog material is digest-only. Raw stdout, stderr, commands,
environment, paths, tracebacks, provider payloads, and credentials are rejected
before WAL, artifact, failure-bundle, queue, or worker-state mutation.

## Fail-Closed Properties

Manual sweeps require explicit `human_invoked=True`. Unsafe states are not
silently mutated: stale leases and resource breaches produce queue transition
evidence, watchdog WAL evidence, watchdog artifacts, failure bundles, worker
quarantine receipts, deterministic watchdog observation receipts, and
operator-visible state.

Rejected requests do not write watchdog WAL records or artifacts and do not
modify the durable queue.

## Evidence

Tracer and acceptance coverage exercise:

- heartbeat receipt recording and lease extension
- manual stale lease sweep with retry scheduling
- manual resource breach sweep with dead-letter linkage
- failure bundle and worker quarantine binding
- watchdog WAL and audit artifact evidence
- operator-visible watchdog state replay
- fail-closed missing human invocation and bypass material
- source guards for daemon, scheduler, process, network, provider, browser, and
  environment surfaces
