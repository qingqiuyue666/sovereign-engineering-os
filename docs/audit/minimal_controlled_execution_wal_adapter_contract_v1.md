# Minimal Controlled Execution WAL Adapter Contract V1

## Purpose

This document defines a narrow, digest-only WAL adapter contract for Minimal
Controlled Execution evidence. The contract gives future runner integration a
stable record, batch, and replay shape before any real storage coupling is
introduced.

## Scope

The contract covers immutable evidence records for:

- minimal controlled execution request hashes
- policy decision hashes
- admission record hashes
- runner receipt hashes
- failure bundle hashes
- verifier input hashes
- verifier binding hashes
- preflight result hashes
- child step evidence hashes in exact command order

The implementation is pure contract code. Creating a WAL adapter record or batch
does not append to storage, write files, write SQLite, call subprocess, run a
CLI, schedule work, start a daemon, or import broad runtime modules.

## Non-Goals

- No real SQLite WAL connection.
- No repository store integration.
- No broad runtime, runner, scheduler, daemon, provider, browser, DCC, MCP, or
  network integration.
- No new command runner.
- No new execution capability.
- No change to existing Minimal Controlled Execution runner behavior.
- No raw stdout or stderr persistence.

## Record Types

Allowed WAL adapter record types are exactly:

- `EXECUTION_ADMISSION`
- `EXECUTION_RECEIPT`
- `EXECUTION_FAILURE`
- `EXECUTION_VERIFIER_BINDING`
- `PREFLIGHT_RESULT`

No other record type is valid.

## Required Hash Bindings

Every contract object is canonicalized as JSON with sorted keys and stable
tuple/list handling. The object hash excludes its own hash field and is prefixed
with `sha256:`. A supplied mismatched hash is rejected by construction.

`EXECUTION_ADMISSION` records bind:

- `request_hash`
- `decision_hash`
- `admission_record_hash`

`EXECUTION_RECEIPT` records bind:

- `request_hash`
- `decision_hash`
- `admission_record_hash`
- `receipt_hash`
- `verifier_input_hash` or `verifier_binding_hash` when present

`EXECUTION_FAILURE` records bind:

- `request_hash`
- `decision_hash`
- `failure_bundle_hash`

`EXECUTION_VERIFIER_BINDING` records bind:

- `verifier_binding_hash`

`PREFLIGHT_RESULT` records bind:

- `preflight_result_hash`
- `ordered_command_ids`
- `child_request_hashes`
- `child_decision_hashes`
- `child_admission_hashes`
- `child_receipt_hashes`
- `child_failure_bundle_hashes`
- `child_verifier_input_hashes`
- `child_verifier_binding_hashes`
- `pre_snapshot_hashes`
- `post_snapshot_hashes`

Preflight child evidence lists must match `ordered_command_ids` exactly by
position. Receipt and failure child slots may be empty only where that child step
did not produce that evidence type; each child position must still bind at least
one receipt or failure bundle hash.

## Replay Semantics

Replay verifies the supplied record hash chain and sequence order only. It checks
that:

- each record hash is valid
- the batch hash is valid
- `ordered_record_hashes` matches records sorted by positive sequence
- `record_count` matches the supplied records
- `first_sequence` and `last_sequence` match the supplied records
- replay input and result hashes are deterministic and valid

Replay does not execute commands, re-open raw output, append to WAL storage, or
consult SQLite. A rejected replay result is itself hash-bound and includes only
rejection reason codes.

## Append-Before-Execution Future Rule

Future runner integration must treat adapter append failure as
execution-blocking before any subprocess attempt. The safe integration point is:

1. construct digest-only admission evidence
2. append it through the future adapter
3. fail closed if the append fails
4. attempt the fixed runner subprocess only after a successful append
5. append receipt, failure, verifier, snapshot, and preflight evidence after the
   attempted run

This PR does not implement that append path. It only defines the contract that a
future integration guard can enforce.

## Why Real SQLite Coupling Is Deferred

Real SQLite coupling is deferred because it would introduce storage lifecycle,
transaction, retry, lock, path, migration, and failure-mode behavior that belongs
behind a separate integration guard. The current safe step is to freeze the
digest-only shape and replay verifier without importing `sqlite3` or
`kernel.stores.sqlite.*`.

## Why unittest_discover_tests And make_ci Still Remain Blocked

`unittest_discover_tests` remains blocked as a Minimal Controlled Execution
command because it still needs a fixed Python environment contract, timeout
policy, output digest policy, verifier coverage, and command-registry migration.

`make_ci` remains blocked as a Minimal Controlled Execution command because it
depends on the narrower unittest runner and a reviewed Makefile surface. It also
needs the future WAL adapter integration guard before it can be considered for
controlled execution.

These blockers do not prevent repository-level validation from running
`python3 -m unittest discover tests` or `make ci` manually for this PR.

## Forbidden Surfaces

The contract forbids raw output and execution material fields including:

- `stdout`
- `stderr`
- `raw_stdout`
- `raw_stderr`
- `stdout_text`
- `stderr_text`
- `command_line`
- `argv`
- `cwd`
- `env`
- `path`
- `executable`
- `timeout`
- `shell`

The contract must not import or call:

- `kernel.runtime.*`
- `sqlite3`
- `kernel.stores.sqlite.*`
- `kernel.os_engine.*`
- `tools.local_execution_kernel.*`
- `subprocess`
- `os.system`
- `Popen`
- `exec`
- `eval`
- `argparse`
- `click`
- `typer`
- `requests`
- `httpx`
- `urllib`
- `socket`
- `webbrowser`
- `playwright`
- `selenium`
- `openai`
- `anthropic`
- `bpy`
- `hou`
- `unreal`
- `comfyui`
- `mcp`

## Next Safe PR

The next safe PR after this contract is:

Minimal Controlled Execution WAL Adapter Integration Guard V1

That PR should prove append-before-execution failure blocks runner subprocess
attempts before any real SQLite coupling or broader command runner work. It
should not be a unittest runner PR and should not be a make ci runner PR.
