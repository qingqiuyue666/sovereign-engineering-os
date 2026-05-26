# Minimal Controlled Execution WAL Adapter Integration Guard V1

## Current State

MINIMAL_CONTROLLED_EXECUTION_WAL_ADAPTER_CONTRACT_READY

## Purpose

Guard future WAL adapter integration before implementation. This guard proves
the safe integration rules while keeping the repository in a contract-only
state for WAL adapter behavior.

## Non-Goals

- No real WAL.
- No SQLite.
- No broad runtime.
- No runner mutation.
- No CLI.
- No scheduler.
- No daemon.
- No new command IDs.
- No unittest runner.
- No make ci runner.

## Required Future Integration Order

1. Admission record append before execution.
2. Receipt or failure record after attempt or blocked failure.
3. Verifier binding record.
4. Preflight result record last.

## Append-Before-Execution Rule

Future runner integration must not call `subprocess` until admission adapter
record append succeeds. Admission evidence must be digest-only and must be
committed through the future adapter before a fixed runner subprocess attempt is
allowed.

## Append-Failure-Blocks-Execution Rule

If adapter append fails before subprocess, `execution_performed` must remain
false and failure evidence must record WAL append failure. The blocked failure
must not create receipt evidence that implies an attempted execution.

## Digest-Only Rule

Adapter records must not persist raw stdout, raw stderr, command line,
arbitrary argv, cwd, env, path, executable, timeout, or execution material.
Evidence must remain hash-bound through request, decision, admission, receipt,
failure, verifier, preflight, and snapshot digests.

## Replay Rule

Replay verifies the record hash chain, sequence order, batch hash, and preflight
child bindings. Replay must accept a correctly ordered digest-only batch and
reject reordered records, tampered record hashes, missing preflight result
records, or mismatched child bindings.

## Forbidden Surfaces

- `sqlite3`
- `kernel.runtime.*`
- `kernel.stores.sqlite.*`
- Broad runner.
- CLI.
- Scheduler.
- Daemon.
- Provider, browser, DCC, or MCP integration.
- Raw output.

## Command Boundary

Expected current command IDs remain exactly:

- `git_status_short`
- `git_diff_check`

`unittest_discover_tests` and `make_ci` remain blocked until WAL adapter
integration is implemented and verified. This guard adds no new command IDs and
does not make either deferred command executable.

## Current Guard Assertions

The guard test proves:

- The WAL adapter contract module exposes the required contract dataclasses and
  validation/replay functions.
- Existing git status, git diff check, preflight sequence, and human preflight
  API modules do not import the WAL adapter contract yet.
- Future integration API names are reserved and absent.
- Minimal Controlled Execution sources do not import real WAL, SQLite, broad
  runtime, CLI, scheduler, daemon, provider, browser, DCC, or MCP surfaces.
- Adapter-facing dataclasses do not add raw stdout, stderr, raw output text, or
  command line fields.
- Representative future adapter records replay successfully only in the
  required order.
- Reordered records, tampered hashes, and missing preflight result records are
  rejected by the guard.
- The WAL adapter contract remains contract-only, with no subprocess, file write
  API, SQLite, or runtime import.

## Next Safe PR

Minimal Controlled Execution WAL Adapter Integration V1

That PR may introduce the deliberate integration API only after this guard is
updated with implementation-specific fail-closed tests. It must still keep
`unittest_discover_tests` and `make_ci` blocked until WAL adapter integration is
implemented and verified.
