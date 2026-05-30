# SEOS Control Plane V1

## Purpose

This document describes the SEOS governance control plane at a level suitable
for external engineering review.

SEOS is a local control plane for engineering evidence. It coordinates local
objects and validation gates; it does not provide OS isolation, computer
control, autonomous execution, live provider execution, or secret custody.

## Core Objects

- Task contract: records requested work, objective, classification, source
  references, and policy version.
- Approval receipt: records an operator decision before a governed dry run.
- Rejection receipt: records an operator rejection and prevents execution.
- Execution receipt: records dry-run outcome, policy binding, and code state.
- Evidence trace: connects a task to receipts, artifacts, validation commands,
  and results.
- Replay explanation: states which parts of a run can be explained from
  evidence and which cannot.
- Failure bundle: records bounded, digest-oriented failure information.
- Release check: records release-candidate and observation invariants.

## Flow

1. Operator creates a task contract.
2. Operator approves or rejects the task.
3. Approved tasks may run through the bounded dry-run path.
4. SEOS records receipts and evidence artifacts.
5. Reviewer inspects evidence traces and replay explanations.
6. Validation scripts and CI gates check repository-level invariants.

## Fail-Closed Rules

- Missing task evidence must fail.
- Missing approval must fail.
- Rejected tasks must not run.
- Corrupted receipts must fail.
- Missing replay evidence must not claim reconstruction.
- Failed validation must not print a passing result.
- Tag mismatch must block readiness.
- Secret access must block autonomous work.

## Boundary

The control plane records governance evidence. It does not:

- isolate code at the OS level
- manage host permissions
- control browsers or desktops
- execute arbitrary subprocesses as an AI authority
- call live providers by default
- hold or inspect secrets
- replace human approval

## Evidence Chain

| Claim | Risk | Control | Implementation | Validation command | Gate | Evidence artifact | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SEOS has explicit governance objects | Reviewers cannot audit implicit state | Object contracts and CLI surfaces | Operator CLI and docs | `python3 -m apps.operator_cli.main --help` | tracer-bullet tests | task, receipt, evidence, replay artifacts | Workspace artifacts are local unless exported |
| SEOS fails closed on missing approval | Unauthorized work could run | Approval gate | approval and run commands | `make ci` | existing CLI and runtime tests | approval receipts | Human misuse remains possible |
| SEOS has no live provider default | AI could bypass governance | Provider-disabled boundary | policies and docs | `python3 scripts/identity_boundary_check_v1.py` | identity check | README, SECURITY, AI docs | Future provider admission requires separate review |
