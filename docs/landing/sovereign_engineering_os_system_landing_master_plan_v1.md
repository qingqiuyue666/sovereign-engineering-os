# Sovereign Engineering OS System Landing Master Plan V1

## Purpose

This document is the authoritative landing plan for completing the
Sovereign Engineering OS from the verified main state
`MINIMAL_CONTROLLED_EXECUTION_WAL_GATED_PREFLIGHT_WRAPPER_READY`.

The missing system areas listed here are required completion targets. They
are not optional future work, nice-to-have expansions, or documentation-only
milestones.

## Definition Of 100 Percent Landing

The system is 100 percent landed only when a local-first operator can complete
the full task lifecycle without external services:

1. admit a task with explicit human approval;
2. queue the task durably;
3. execute only an authorized controlled runner;
4. append deterministic evidence to real local WAL storage;
5. bind outputs to digest-addressed artifacts and snapshots;
6. generate canonical failure bundles for rejected or failed work;
7. replay cold local evidence into the same task truth;
8. project that truth into a read-only operator console and replay browser;
9. verify install/config health without a network dependency;
10. prove all rejection, corruption, disabled-worker, and expired-approval
    paths fail closed before execution.

No module can be marked production complete when it only has a document,
shallow contract, schema, or isolated fixture. Production completion requires
implementation, integration with relevant system paths, failure-path handling,
replay/audit binding, focused tests, integration tests, acceptance tests, and
audit documentation.

## Current State

Main is verified at the merge state:

- state label: `MINIMAL_CONTROLLED_EXECUTION_WAL_GATED_PREFLIGHT_WRAPPER_READY`
- known main head: `a57a45592ad003b136e153ab39f02b826e17f2cc`
- current strongest capability: minimal controlled execution WAL-gated
  preflight wrapper, contract-only WAL adapter surfaces, and guard coverage
  preserving explicit opt-in behavior.

The current state is foundation-plus-guardrail maturity. It is not integration
completion, alpha completion, beta completion, or production completion for the
full system.

## Required Missing System Areas

The completion train must land these required targets as far as safely possible:

1. real WAL storage
2. durable job queue
3. artifact store
4. snapshot/replay store
5. approval/policy runtime
6. failure bundle center
7. worker registry
8. resource watchdog
9. operator console
10. replay browser
11. install/config/packaging
12. AI worker router
13. DCC/media adapter integration
14. system-level E2E acceptance

## Module Weight Model

Progress is measured by production landing value, not by file count or PR count.
The weight model sums to 100.

| Module | Weight |
| --- | ---: |
| Minimal controlled execution completion | 9 |
| Real WAL storage | 10 |
| Durable job queue | 8 |
| Artifact store | 7 |
| Snapshot/replay store | 7 |
| Approval/policy runtime | 8 |
| Failure bundle center | 6 |
| Worker registry | 6 |
| Resource watchdog | 5 |
| Operator console | 5 |
| Replay browser | 5 |
| Install/config/packaging | 5 |
| AI worker router | 5 |
| DCC/media adapter integration | 4 |
| System-level E2E acceptance | 10 |

Each module earns weight only for completed, validated, reviewable work.
Contracts alone do not earn the implementation, integration, failure-path,
replay, or acceptance portions of a module.

## Completion Stage Definitions

Foundation completion means the module has a stable contract, schema, boundary
statement, guard tests, and audit language. It is not enough for system use.

Integration completion means the module is wired into the relevant local
system paths with explicit opt-in controls, failure handling, and tests that
prove the wiring is used.

Alpha completion means the module can run a bounded local happy path with
focused tests and at least one relevant rejection path. Alpha is operator
supervised and may require manual setup.

Beta completion means the module can run the normal local path and known
failure paths repeatedly from clean storage, with replay/audit bindings and
integration tests.

Production completion means the module is local-first, deterministic,
bounded, replayable, auditable, fail-closed, covered by focused and acceptance
tests, documented, and included in system-level E2E acceptance. Production
completion also requires no secret persistence, no uncontrolled network calls,
no uncontrolled daemon or scheduler, and no broad runtime jump.

## Dependency Graph

The train must preserve these dependencies:

```text
minimal controlled execution
  -> real WAL storage
  -> durable job queue
  -> artifact store
  -> snapshot/replay store
  -> approval/policy runtime
  -> failure bundle center
  -> worker registry
  -> resource watchdog
  -> operator console
  -> replay browser
  -> install/config/packaging
  -> AI worker router
  -> DCC/media adapter integration
  -> system-level E2E acceptance
```

Cross-cutting dependencies:

- approval/policy runtime must gate human-invoked execution, queue admission,
  worker admission, AI routing, and DCC/media adapter claims.
- real WAL storage must bind controlled execution, queue lifecycle, artifacts,
  snapshots, policy decisions, failure bundles, and replay evidence.
- artifact and snapshot stores must be replayable from cold local state.
- operator console and replay browser must be read-only projections of stored
  evidence, not alternate sources of truth.
- system-level E2E acceptance must not fake missing integration; it must wait
  for the required upstream modules to exist.

## Phase Roadmap

Phase A creates this master landing plan and validates the required completion
targets.

Phase B completes the minimal controlled execution spine through explicit
human-invoked WAL-gated preflight APIs, opt-in preflight wiring, controlled
test runners, failure bundle compatibility, WAL evidence compatibility, and
final MCE acceptance.

Phase C lands real local WAL storage through contract, implementation, adapter
integration, corruption/recovery acceptance, and cold replay acceptance.

Phase D lands the durable job queue through contract, persistence,
human-invoked runner, WAL integration, and crash/recovery acceptance.

Phase E lands the artifact store through contract, ingest/verify,
WAL/evidence binding, corruption/quarantine acceptance, and replay acceptance.

Phase F lands the snapshot/replay store through contract, capture manifests,
replay reconstruction, artifact/WAL integration, and cold replay acceptance.

Phase G lands approval/policy runtime through contract, runtime enforcement,
execution integration, rejection/expiration acceptance, and policy replay
acceptance.

Phase H lands failure bundle center through contract, implementation, runner
integration, queue/policy integration, and replay/report acceptance.

Phase I lands worker registry through contract, implementation, queue/admission
integration, approval/resource binding, and disabled-worker rejection
acceptance.

Phase J lands resource watchdog through contract, receipt implementation,
runner integration, failure bundle integration, and timeout/runaway acceptance.

Phase K lands operator console through model, report generator, static local
report output, projection integration, and console acceptance.

Phase L lands replay browser through model, loader, evidence verification,
audit pack export, and cold replay acceptance.

Phase M lands install/config/packaging through config schema, environment
health checker, bootstrap verifier, backup/restore contract, and install
acceptance.

Phase N lands AI worker router through contract, routing policy, worker
registry integration, queue/approval/budget integration, and no-provider-call
acceptance.

Phase O lands DCC/media adapter integration through contracts, registry
integration, asset/artifact binding, approval/resource binding, and
no-execution acceptance.

Phase P lands system-level E2E acceptance through separate PRs proving the
complete local-first task, failure, rejection, corruption, cold replay, console,
and install readiness paths.

## Acceptance Gates

Every PR in the train must pass these gates before it is opened as draft:

- focused tests for the PR scope;
- relevant guard tests for forbidden surfaces and existing behavior;
- full `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests`;
- `make ci`;
- `git diff --check`;
- clean `git status --short`;
- audit documentation for the changed surface.

Acceptance tests must prove real behavior. They must not assert only that a
plan exists when the phase requires implementation or integration.

## Blocker Policy

A blocker is valid only when the current PR cannot be completed without one of
these violations:

- broad runtime integration outside the authorized phase;
- uncontrolled daemon, scheduler, CLI, browser, provider, DCC, or MCP
  execution;
- arbitrary argv, cwd, env, path, executable, or timeout execution;
- raw stdout/stderr persistence;
- secret persistence;
- uncontrolled network calls;
- deleting branches, merging PRs, pushing main, or weakening tests.

When blocked, fix only the current PR if possible. If the blocker is
architectural, stop with the exact missing dependency, failed validation, and
safe next step.

## PR Train Policy

The train uses small validated draft PRs. Each PR must have its own branch,
target main, contain only files appropriate for its phase, include focused
tests, include integration or acceptance tests where applicable, include audit
documentation, and report branch, PR number, PR URL, head SHA, changed files,
validation results, GitHub Actions status, and blockers.

After a locally validated draft PR is opened, execution returns to clean main
and continues to the next authorized PR unless the current PR has unresolved
validation failure.

## No Giant PR Policy

One giant PR is forbidden because it hides integration failures and makes
review ineffective. Large areas must be split by contract, implementation,
integration, failure acceptance, replay acceptance, and system-level acceptance.

## Local-First Policy

The production path must work from local storage and local deterministic
evidence. Network calls, external providers, browser automation, DCC execution,
MCP execution, and GUI automation are forbidden unless a later phase explicitly
authorizes a bounded local implementation with tests.

## Evidence And Replay Policy

Evidence must be deterministic, digest-addressed where possible, and replayable
from cold local state. WAL, artifacts, snapshots, policy decisions, worker
admission, queue transitions, failure bundles, and report projections must share
stable replay bindings.

Raw stdout, raw stderr, raw prompts, raw provider responses, secrets, tokens,
environment dumps, and key material must not be persisted as evidence.

## Production-Grade Criteria

Production-grade modules must be:

- local-first and deterministic;
- bounded and explicit opt-in;
- human-invoked where execution is involved;
- approval-aware before execution;
- append-only where audit history is relevant;
- fail-closed on missing, malformed, corrupt, expired, revoked, disabled, or
  unauthorized inputs;
- covered by focused tests, integration tests, acceptance tests, and guard
  tests;
- bound to replay/audit evidence;
- documented with operator-facing audit notes;
- free of uncontrolled network, provider, daemon, scheduler, browser, DCC, MCP,
  or broad runtime behavior.

This document is a foundation artifact for Phase A only. It authorizes the
train and defines the landing criteria; it does not by itself complete any
runtime module.
