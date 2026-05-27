# Replay Browser Readonly V1

Status: implemented as a small independent system slice.

## Scope

This slice adds a read-only replay browser for the existing OS engine SQLite WAL
database. It reconstructs job traces from durable job rows, append-only
`job_events`, and artifact metadata without creating, updating, or deleting
records.

Implemented surfaces:

- `kernel/os_engine/replay_browser.py`
- `tools/os_engine_replay_browser.py`
- focused tracer-bullet tests
- acceptance coverage for readonly reconstruction and tamper rejection

## Authoritative Boundaries

The browser is inspection-only.

It does not:

- enqueue, lease, start, retry, replay, or execute jobs
- launch browsers, DCC tools, subprocesses, or external runtimes
- access network resources
- expose raw event payloads or raw artifact paths in rendered output
- mutate or delete SQLite records

SQLite is opened with `mode=ro` and `PRAGMA query_only = ON`.

## Replay And Audit Binding

For each returned job trace, the browser validates and binds:

- stored job row content hash
- per-event content hashes
- event-chain hash
- artifact metadata content hashes
- artifact-chain hash
- deterministic projection hash from `project_job_state`
- audit hash over projection, event chain, artifact chain, and failures

Accepted traces are classified as `exact_event_projection`. Any malformed,
tampered, missing, or projection-inconsistent trace is classified as
`diagnostic_rejected` and surfaced through stable failure codes.

## Failure Paths

Fail-closed outcomes include:

- `database_missing`
- `required_tables_missing`
- `schema_hash_mismatch`
- `job_not_found`
- `malformed_event_payload`
- `event_payload_must_be_object`
- `event_content_hash_mismatch`
- `artifact_content_hash_mismatch`
- `job_content_hash_mismatch`
- `job_status_projection_mismatch`
- `projection_failed`

Rendered summaries carry explicit false flags for mutation, deletion,
execution, network access, browser launch, and raw secret display.

## Dependency Blockers Recorded

The following open draft PRs remain unmerged and are treated as dependency
blockers for their corresponding dependent completion work:

- #497 Real WAL Storage Contract V1
- #498 Durable Job Queue Contract V1
- #499 Artifact Store Contract V1
- #500 Snapshot Replay Contract V1
- #501 Approval Runtime Contract V1
- #502 Failure Bundle Center Contract V1
- #503 Worker Registry Admission Contract V1
- #504 Watchdog Receipts Contract V1
- #505 Operator Console Readonly Contract V1

This replay-browser slice does not duplicate those contract PRs. It consumes
the already-merged OS engine database, event log, projection, and artifact
metadata surfaces on `main`.

## Validation

Focused validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_os_engine_replay_browser -v
```

Acceptance validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_replay_browser_readonly_v1 -v
```
