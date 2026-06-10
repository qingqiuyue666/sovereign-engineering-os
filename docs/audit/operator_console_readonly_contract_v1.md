# Operator Console Read-Only Contract V1

This change adds a contract-only read model for the operator console. It binds
read-only data sources and a console snapshot to WAL, artifact store, approval
runtime, failure bundle center, worker registry, watchdog receipt, replay, and
snapshot/replay evidence hashes.

The module does not render a UI, mutate state, dispatch work, call providers,
launch tools, persist console output, or read environment state.

## Guarantees

- Data sources and snapshots are deterministic and digest-only.
- `observed_at` is metadata and excluded from content hashes.
- Required panels include summary, queue, artifacts, receipts, failures,
  approvals, replay, workers, watchdog, and system health.
- Data sources must be read-only.
- Mutation, command, dispatch, live fetch, and external tool flags must be false.
- Raw stdout/stderr, raw payloads, command material, argv, cwd, env, paths,
  prompts, content, output, and secret-like fields are rejected.
- Snapshots reject missing required panels, duplicate data sources, duplicate
  data source hashes, malformed evidence hashes, and tampered snapshot hashes.

## Deferred Work

Actual console rendering, event streaming, operator navigation state, persisted
view caches, and integration with real WAL/artifact stores remain follow-on work
behind their prerequisite PRs.
