# External Pattern Assimilation v1

This branch absorbs selected architecture patterns as small native OS-engine primitives. It is OS core durability work, not VFX final completion.

## Absorbed Now

- Dagster -> asset-centric materialization: jobs are framed around materializing target artifacts when missing, stale, or invalid.
- Temporal -> event-sourced job history: job state is replayed from append-only events instead of trusting a mutable status field alone.
- SQLite WAL -> durable local brain: the core state store uses a local SQLite database in WAL mode with deterministic schema setup.
- GUI/worker split -> desktop safety boundary: the desktop control plane submits requests and reads projected state; execution remains behind queue and worker boundaries.

## Deferred

- qasync -> GUI async hardening: keep as future P1 after the API/queue boundary is stable.
- AYON -> DCC environment injection: represent DCC execution as a worker/materialization boundary before adding environment package injection.
- Aider/Tree-sitter -> AST context compression: record the structural-context direction without integrating Tree-sitter in this branch.
- DuckDB/FSEvents -> large asset indexing: prepare durable records now and defer out-of-core incremental indexing.
- ComfyUI DAG/status streaming -> future ComfyUIWorker: no ComfyUI runtime integration is added here.
- OTIO -> future DaVinci handoff: durable handoff metadata can be stored, but OTIO integration is deferred.

## Rejected For Now

- direct Temporal dependency
- direct Dagster dependency
- NATS message bus
- Memray runtime watchdog
- sandbox-exec enforcement
- OpenUSD/MaterialX deep integration
- random MCP plugin sprawl
- GUI automation before API/CLI control

## Boundaries

- No final HFX claim is made in this branch.
- No raw asset vendoring is introduced.
- `hfx-pipeline-scaffolding` remains out of scope and is not a dependency.
- This branch is OS core durability, not VFX final completion.
