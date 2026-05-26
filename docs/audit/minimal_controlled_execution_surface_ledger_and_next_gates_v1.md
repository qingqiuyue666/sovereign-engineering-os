# Minimal Controlled Execution Surface Ledger And Next Gates V1

## Decision

Status: LEDGER_ONLY

This document records the Minimal Controlled Execution surface after the
current PR train. It adds no execution capability, no runner, no command
registry mutation, no WAL adapter, no CLI, no scheduler, no daemon, and no
provider, browser, DCC, MCP, plugin, or network surface.

## Current PR Train

| Phase | PR | Branch | Base | Status |
| --- | --- | --- | --- | --- |
| 1 | #482 | `execution/minimal-controlled-execution-core-preflight-v1` | `main` | Core preflight implementation |
| 2 | #483 | `execution/minimal-controlled-execution-shared-runner-base-v1` | `execution/minimal-controlled-execution-core-preflight-v1` | Shared narrow runner helpers |
| 3 | #484 | `audit/minimal-controlled-execution-real-wal-coupling-readiness-v1` | `main` | WAL readiness blocker audit |
| 4 | #485 | `audit/minimal-controlled-execution-unittest-discover-runner-blocker-v1` | `main` | Unittest runner blocker audit |
| 5 | #486 | `audit/minimal-controlled-execution-make-ci-runner-blocker-v1` | `main` | Make CI runner blocker audit |
| 6 | #487 | `execution/minimal-controlled-execution-human-invoked-preflight-api-v1` | `execution/minimal-controlled-execution-shared-runner-base-v1` | Human-invoked API implementation |
| 7 | #488 | `acceptance/minimal-controlled-execution-end-to-end-v1` | `execution/minimal-controlled-execution-human-invoked-preflight-api-v1` | End-to-end acceptance tests |

## Current Executable Command IDs

After the implementation stack lands, the only executable Minimal Controlled
Execution command ids are:

- `git_status_short`
- `git_diff_check`

Both command ids are repository read-only checks. Each runner keeps a
runner-local executable allowlist:

- `git_status_short` runner allowlist: exactly `{"git_status_short"}`
- `git_diff_check` runner allowlist: exactly `{"git_diff_check"}`

The fixed argv values are:

- `git_status_short`: `["git", "status", "--short"]`
- `git_diff_check`: `["git", "diff", "--check"]`

Both runners use only `subprocess.run`, `shell=False`, the fixed repository
root cwd, a deterministic git-safe environment, fixed timeout, bounded
stdout/stderr capture, digest-only output metadata, receipt/failure/verifier
evidence, and fail-closed rejection paths.

## Current Non-Executable Command IDs

The current deferred command ids remain:

- `unittest_discover_tests`
- `make_ci`

Unknown command ids are policy rejected. A known command id presented to the
wrong runner slice is rejected as `COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE`.
Payload-provided argv, cwd, env, path, executable, timeout, shell, command, or
command line material is rejected before execution.

## Current WAL State

Minimal Controlled Execution has contract WAL evidence objects and runner-local
pre-execution WAL callback evidence for admission. A real repository WAL
coupling is not implemented.

Current WAL boundary:

- Admission WAL evidence is digest-only.
- Runners can fail closed if the pre-execution WAL callback raises.
- Real SQLite WAL coupling remains blocked.
- No broad runtime router, command envelope router, local execution kernel, or
  scheduler/daemon surface is imported by Minimal Controlled Execution.
- There is not yet a narrow post-execution WAL adapter that persists receipt,
  failure, verifier, and snapshot hashes.

The safe next WAL step is a narrow adapter contract under `kernel/execution/`
that binds request, decision, admission, receipt, failure, verifier input,
verifier binding, pre-snapshot, and post-snapshot hashes without importing the
broad runtime execution router.

## Current Preflight State

After Phase 1 lands, Minimal Controlled Execution has a fixed human-invoked
two-step preflight sequence:

1. `git_status_short`
2. `git_diff_check`

The preflight sequence:

- accepts governance metadata only;
- rejects payload command lists and execution material;
- has no CLI, scheduler, daemon, retry, parallel execution, task graph, or
  background loop;
- binds child request, decision, admission, receipt, failure, verifier input,
  verifier binding, pre-snapshot, and post-snapshot hashes;
- returns one of `PREFLIGHT_PASSED`, `PREFLIGHT_FAILED`,
  `PREFLIGHT_NOT_ATTEMPTED`, or `PREFLIGHT_PARTIAL_FAILURE`.

## Current API State

After Phase 6 lands, the importable Python API is:

- `run_human_invoked_minimal_controlled_preflight(payload)`

The API:

- accepts governance metadata only;
- rejects command lists and execution material;
- invokes only the fixed preflight sequence;
- returns a digest-bound evidence manifest;
- does not mutate GitHub;
- does not run as a CLI, daemon, scheduler, retry loop, background worker, or
  autonomous executor.

## Current Acceptance State

After Phase 7 lands, acceptance tests cover:

- contract registry shape;
- admission and WAL evidence hash binding;
- `git_status_short` runner behavior;
- `git_diff_check` runner behavior;
- fixed preflight order;
- human-invoked API manifest binding;
- fail-closed rejection behavior;
- raw-output exclusion;
- forbidden import surfaces.

The acceptance phase does not add execution capability.

## Current Forbidden Surfaces

The following surfaces remain forbidden for Minimal Controlled Execution:

- arbitrary argv
- payload-provided cwd, env, path, executable, or timeout
- `shell=True`
- `Popen`
- `os.system`
- `exec`
- `eval`
- uncontrolled CLI
- scheduler
- daemon
- arbitrary task graph execution
- automatic re-execution
- network execution
- provider API execution
- browser control
- plugin execution
- DCC execution
- ComfyUI execution
- MCP execution
- asset mutation
- package installation
- uncontrolled GitHub mutation
- broad runner abstraction
- raw stdout/stderr persistence
- unbounded output persistence
- merge or branch deletion automation

## Current Merge Blockers

Implementation blockers:

1. Real WAL coupling is blocked until a narrow digest-only adapter exists with
   append-before-execution, append-failure, post-execution evidence, and replay
   tests.
2. `unittest_discover_tests` is blocked until the command registry migration,
   Python test env, fixed timeout policy, verifier coverage, and static guards
   are updated together.
3. `make_ci` is blocked until the narrower unittest runner lands, the Makefile
   surface is audited, and a safe WAL/evidence path is available.

Merge-order blockers:

1. PR #483 depends on PR #482.
2. PR #487 depends on PR #483.
3. PR #488 depends on PR #487.
4. PR #484, PR #485, PR #486, and this ledger PR are docs-only independent
   branches targeting `main`.

## Next Highest-Value PRs

1. Minimal WAL adapter contract V1:
   Define a digest-only in-memory adapter contract and replay verifier without
   SQLite coupling or broad runtime imports.

2. Minimal WAL adapter implementation V1:
   Add append-before-execution and post-execution evidence append tests for the
   two git runners, still without widening the command registry.

3. Unittest discover contract migration V1:
   Move `unittest_discover_tests` from deferred to executable with fixed argv,
   deterministic Python env, timeout policy, digest-only output metadata, and
   static guard updates.

4. Unittest discover runner V1:
   Add the command-specific runner only after the contract migration lands.

5. Make CI readiness audit V2:
   Re-audit `make ci` after the unittest runner and WAL adapter land.

## Rollback Plan

If any implementation PR in the stack is found unsafe before merge:

1. Do not merge the unsafe PR or any dependent stacked PRs.
2. Close or supersede the unsafe PR with a blocker audit.
3. Keep independent docs-only blocker PRs mergeable if their findings remain
   accurate.
4. If PR #482 is rolled back, do not merge PR #483, PR #487, or PR #488.
5. If PR #483 is rolled back, do not merge PR #487 or PR #488.
6. If PR #487 is rolled back, do not merge PR #488.
7. Branch deletion should happen only after merge or explicit operator
   approval.

No branch in this train should be deleted by automation.

## Recommended Merge Order

Recommended implementation stack order:

1. PR #482: Minimal Controlled Execution Core Preflight V1
2. PR #483: Minimal Controlled Execution Shared Runner Base V1
3. PR #487: Minimal Controlled Execution Human Invoked Preflight API V1
4. PR #488: Minimal Controlled Execution End To End Acceptance V1

Recommended independent docs order:

1. PR #484: Minimal Controlled Execution Real WAL Coupling Readiness V1
2. PR #485: Minimal Controlled Execution Unittest Discover Runner Blocker V1
3. PR #486: Minimal Controlled Execution Make CI Runner Blocker V1
4. Phase 8 ledger PR: Minimal Controlled Execution Surface Ledger And Next
   Gates V1

The docs-only PRs can merge independently, but this ledger is most useful after
the blocker audits are visible.

## Branch Cleanup List

After the corresponding PRs merge and only with explicit cleanup approval, the
following branches can be deleted:

- `execution/minimal-controlled-execution-core-preflight-v1`
- `execution/minimal-controlled-execution-shared-runner-base-v1`
- `audit/minimal-controlled-execution-real-wal-coupling-readiness-v1`
- `audit/minimal-controlled-execution-unittest-discover-runner-blocker-v1`
- `audit/minimal-controlled-execution-make-ci-runner-blocker-v1`
- `execution/minimal-controlled-execution-human-invoked-preflight-api-v1`
- `acceptance/minimal-controlled-execution-end-to-end-v1`
- `audit/minimal-controlled-execution-surface-ledger-and-next-gates-v1`

## Boundary Statement

This ledger is documentation only. It does not add or modify runners, registry
entries, WAL persistence, subprocess usage, CLI entry points, schedulers,
daemons, provider/browser/DCC/MCP integrations, package installation behavior,
asset mutation, GitHub mutation, branch deletion, or merge automation.
