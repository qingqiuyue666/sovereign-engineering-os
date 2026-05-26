# Minimal Controlled Execution WAL-Gated Preflight Wrapper V1

## Current state

MINIMAL_CONTROLLED_EXECUTION_WAL_ADAPTER_INTEGRATION_READY

## Purpose

This PR adds a narrow human-invoked WAL-gated preflight wrapper for Minimal Controlled Execution.

## What this PR adds

- Wrapper input contract.
- Wrapper result contract.
- Evidence to record assembly.
- Callable append invocation.
- Append-before-execution plan binding.
- Replay/integration result binding.

## Non-goals

- No real WAL.
- No SQLite.
- No broad runtime.
- No runner mutation.
- No preflight API mutation.
- No CLI.
- No scheduler.
- No daemon.
- No new command IDs.
- No unittest runner.
- No make ci runner.

## Append-before-execution rule

Admission append must succeed before `execution_may_proceed` can be true.

## Append-failure-blocks-execution rule

Append failure means `execution_may_proceed=false` and `accepted=false`.

## Digest-only rule

Wrapper input and wrapper result are digest-only surfaces. They do not carry raw stdout, raw stderr, command line, argv, cwd, env, path, executable, timeout, or shell material.

## Replay rule

The wrapper result binds ordered record hashes, append result hashes, append plan hash, batch hash, replay result hash, and integration result hash.

## Remaining blocked

- Preflight API integration.
- `unittest_discover_tests` runner.
- `make_ci` runner.
- Real SQLite WAL coupling.

## Next safe PR

Minimal Controlled Execution Human-Invoked WAL-Gated Preflight API V1
