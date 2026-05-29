# Controlled Execution Runtime V1

Status: READY_FOR_REVIEW

## Purpose

This priority adds the first file-backed controlled execution runtime lifecycle.
The runtime is disabled by default. When explicitly enabled, it admits a
human-invoked single-run request, consumes an approval-runtime receipt, queues
and leases exactly one durable job, runs the existing fixed Minimal Controlled
Execution preflight boundary, writes a digest-only result artifact, appends a
real WAL transition, captures snapshot/replay receipts, and returns a
deterministic final receipt.

## Lifecycle

1. Admission validates governance metadata only.
2. Approval is consumed through `FileBackedApprovalRuntimeIntegration`.
3. Queue state moves through submit, queue, lease, and terminal completion.
4. Execution uses the fixed human-invoked minimal preflight API.
5. Result material is persisted as a digest-only artifact.
6. A controlled execution transition is appended to real WAL storage.
7. Snapshot/replay reconstruction binds WAL, artifact, and queue state.
8. The final receipt binds approval, queue, artifact, WAL, snapshots, and any
   failure bundle.

## Boundary Rules

- No caller-selected command id, command list, argv, cwd, env, path, executable,
  shell, timeout, or output material is accepted.
- No background loop, scheduler, daemon, retry graph, provider, browser,
  plugin, DCC, MCP, or network surface is exposed.
- The runtime does not import process-launch or network libraries.
- All runtime writes are constrained below the configured runtime root.
- Approval rejection, queue transition failure, execution-boundary failure, and
  replay reconstruction failure fail closed with digest-only evidence.
- Execution-boundary failures produce a failure bundle through the failure
  bundle center integration.

## Evidence

Implemented in:

- `kernel/runtime/controlled_execution_runtime.py`
- `tests/tracer_bullet/test_controlled_execution_runtime_v1.py`
- `validation/tests/acceptance/test_controlled_execution_runtime_v1.py`

The tests cover the successful lifecycle, default-disabled behavior, direct
bypass rejection, approval rejection, execution failure bundle binding, result
artifact binding, transition WAL binding, snapshot receipts, and source-surface
guards.
