# SEOS System Identity V1

## Purpose

This document defines the public identity of Sovereign Engineering OS (SEOS)
for external engineering review.

SEOS is a local-first, audit-first, human-gated engineering governance control
plane for AI-assisted repository work. It helps operators create and inspect
task contracts, approval receipts, dry-run execution receipts, evidence traces,
replay explanations, failure bundles, and release checks.

## Current State

Current validated facts:

- `SYSTEM_LANDED`
- `REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE`
- `LOCAL_REAL_USE_VALIDATED`
- `APPROVAL_GATE_VALIDATED`
- `CLEAN_CLONE_VALIDATED`
- `NO_HARD_EVIDENCE_BLOCKER_RECORDED`

Current release-candidate checkpoint: `v0.1.0-rc3`.

External recognition has not been confirmed. External verification and human
audit remain required.

## Problem Statement

AI-assisted engineering can produce useful work while leaving weak audit trails:
unclear task intent, unclear human approval, unclear evidence, unclear replay
scope, and unclear residual risk. SEOS makes those governance objects explicit
and inspectable.

## Scope

In scope:

- local repository governance
- task contract and approval recording
- dry-run execution receipt recording
- evidence trace and replay explanation
- failure bundle explanation
- release and observation checks
- deterministic mock and local-only support artifacts
- validation commands and CI gates

Out of scope:

- OS-level isolation
- filesystem permission enforcement
- secret custody
- browser, desktop, or OS automation
- live provider execution by default
- autonomous AI patching
- hosted SaaS operation

## Public Boundary Statement

SEOS governs approvals, receipts, evidence, replay, and policy checks. It does
not reduce the authority of the host process, isolate untrusted code, custody
secrets, or control a user's computer. Host security controls remain the
operator's responsibility.

## Claim To Evidence Summary

| Claim | Risk | Control | Implementation | Validation command | Gate | Evidence artifact | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SEOS is in observation mode | A reviewer may mistake the repo for a feature-expansion phase | Observation policy and log | Observation runbook, policy, and JSON log | `python3 scripts/observation_check_v1.py` | `make ci` | `reports/observation/real_operation_observation_log_v1.*` | Observation evidence is local until externally audited |
| SEOS is human-gated | AI work could be interpreted as self-authorizing | Approval/rejection receipts | Operator CLI approval flow | `python3 -m apps.operator_cli.main --help` | CLI and tracer-bullet tests | approval receipt artifacts in governed workspaces | Misapproval remains a human operational risk |
| SEOS is local-first | Reviewers may infer a cloud service | Local CLI and local workspace model | `seos` and module entrypoints | `seos --help` | packaging and CLI tests | README and quickstart | Host environment setup can still vary |
| SEOS does not provide OS sandboxing | Users may overtrust host isolation | Explicit non-goals and checks | README, SECURITY, non-goals doc, identity checker | `python3 scripts/identity_boundary_check_v1.py` | identity check | this document and `docs/identity/non_goals_v1.md` | Host controls must be separately configured |
| SEOS does not self-certify recognition | Marketing overclaim risk | Final-state boundary | README and audit-readiness docs | `python3 scripts/identity_boundary_check_v1.py` | identity check | README and audit dossier | Independent verification still required |

## Compatibility Rule

Identity claims must be narrowed or backed by evidence before being expanded.
New public claims require a matching control, validation command, CI or script
gate, evidence artifact, and residual-risk statement.

## Stop Rule

If a change requires secret access, live provider credentials, force pushing,
tag mutation, uncontrolled runtime capability, OS automation, or weakening
existing gates, the work must stop for human decision.
