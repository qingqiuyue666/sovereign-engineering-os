# Operator Console Runtime Surface V1

Priority: #524

## Scope

`FileBackedOperatorConsoleRuntimeSurface` builds a read-only operator projection from existing local evidence stores:

- real WAL files
- durable queue records
- artifact manifests
- approval runtime state
- failure bundle center state
- snapshot/replay receipts
- worker registry state
- watchdog receipts and operator state

The surface does not render a UI, create missing stores, repair corruption, dispatch work, execute commands, call providers, inspect credentials, or write console state.

## Safety Properties

- Read-only flags are enforced on every panel and on the final snapshot.
- Missing evidence is reported as red/failure state.
- Hash mismatch or replay rejection is reported as red/failure state.
- Stale lease/watchdog state is explicit through stale panel IDs.
- Direct console mutation routes are rejected unless they present approval and controlled-execution receipt evidence.
- Console route validation never performs the mutation itself.
- The read path uses persisted evidence only and avoids hidden network, subprocess, provider, browser, or environment access.

## Evidence Binding

The runtime surface binds panel hashes into the existing operator console read-only contract snapshot. The final snapshot records digest references for WAL head, artifact store root, approval runtime, failure center, worker registry, watchdog chain, and replay/snapshot state.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_operator_console_runtime_surface_v1 -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_operator_console_runtime_surface_v1 -v`
