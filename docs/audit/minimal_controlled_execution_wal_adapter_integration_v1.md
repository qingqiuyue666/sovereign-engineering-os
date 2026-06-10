# Minimal Controlled Execution WAL Adapter Integration V1

## Current state

`MINIMAL_CONTROLLED_EXECUTION_WAL_ADAPTER_INTEGRATION_GUARD_READY`

## Purpose

This change adds a narrow, pure WAL adapter evidence integration layer for Minimal Controlled Execution.

The integration layer maps existing Minimal Controlled Execution evidence into the existing WAL adapter contract without adding real WAL storage, SQLite coupling, broad runtime coupling, runner mutation, CLI entrypoints, schedulers, daemons, background workers, or new command execution capability.

## What this PR adds

- Evidence-to-WAL-adapter mappers:
  - admission evidence to `EXECUTION_ADMISSION`
  - receipt evidence to `EXECUTION_RECEIPT`
  - failure evidence to `EXECUTION_FAILURE`
  - verifier binding evidence to `EXECUTION_VERIFIER_BINDING`
  - preflight result evidence to `PREFLIGHT_RESULT`

- Callable-based append result contracts:
  - append success result
  - append failure result
  - fail-closed rejection reasons

- Append-before-execution planning:
  - admission append must succeed before execution may proceed
  - append failure before execution blocks execution
  - preflight result remains last

- Batch and replay integration:
  - builds `MinimalControlledWalAdapterBatch`
  - replays records through the existing WAL adapter contract
  - returns deterministic integration result evidence

## Non-goals

This change does not add:

- real WAL writes
- SQLite writes
- broad runtime imports
- production runner behavior changes
- preflight API behavior changes
- CLI entrypoints
- scheduler
- daemon
- background worker
- autonomous execution
- new command IDs
- `unittest_discover_tests` runner
- `make_ci` runner
- DCC / provider / browser / MCP integration

## Append-before-execution rule

Future runner integration must append the `EXECUTION_ADMISSION` adapter record before subprocess execution is allowed.

If the admission adapter append does not succeed, execution must not proceed.

## Append-failure-blocks-execution rule

If adapter append fails before subprocess execution:

- `execution_may_proceed` must be false
- `execution_performed` must remain false
- rejection reasons must include append failure evidence
- no receipt may claim successful execution

## Digest-only rule

WAL adapter integration must not persist raw execution material.

Forbidden evidence fields include:

- raw stdout
- raw stderr
- command line
- argv
- cwd
- env
- path
- executable
- timeout
- shell

Only digest-shaped evidence is allowed.

## Replay rule

Replay must verify:

- record hash chain
- sequence order
- batch hash
- preflight child bindings
- deterministic integration result hash

## Remaining blocked surfaces

The following remain blocked after this PR:

- `run_minimal_controlled_preflight_with_wal_adapter`
- `unittest_discover_tests` runner
- `make_ci` runner
- real SQLite WAL coupling
- broad runtime integration
- CLI / scheduler / daemon

## Next safe PR

`Minimal Controlled Execution WAL-Gated Preflight Wrapper V1`

That future PR may introduce a deliberate preflight wrapper, but it must remain human-invoked, append-before-execution gated, digest-only, and free of real WAL, SQLite, and broad runtime coupling unless a separate storage-backed WAL PR explicitly authorizes that boundary.
