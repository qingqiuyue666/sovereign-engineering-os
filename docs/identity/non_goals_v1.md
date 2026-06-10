# SEOS Non-Goals V1

## Purpose

This document lists claims SEOS must not make during the real-operation
observation and external-review readiness period.

## Non-Goals

SEOS is not:

- an OS-level sandbox
- a filesystem permission system
- an EDR, VM, or container system
- a secret manager or credential custody service
- RPA
- a browser-control framework
- a desktop-control framework
- a computer-control framework
- an autonomous AI executor
- a live-provider execution runtime by default
- a commercial SaaS platform
- proof that external recognition has happened
- proof that global recognition has happened

## Boundary Rules

AI output may support proposals and evidence. AI output must not directly patch
repository files without proposal-first review, human approval, and validation.

Local CLI workflows may create task, approval, receipt, evidence, replay,
failure, and release-check artifacts. They must not be interpreted as authority
to control the host OS, browse the web, operate desktop software, call live AI
providers, mutate secrets, or bypass the operator.

## Claim Handling

Unsupported claims must be handled in one of three ways:

- remove or narrow the claim
- add a control and validation
- record the claim as a limitation or accepted risk

## Evidence Chain

| Claim | Risk | Control | Implementation | Validation command | Gate | Evidence artifact | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Non-goals are explicit | Reviewers may infer hidden capability | Public non-goals list | This document and README | `python3 scripts/identity_boundary_check_v1.py` | identity check | `docs/identity/non_goals_v1.md` | Historical docs may require context |
| Runtime expansion is not authorized | A docs change could imply product expansion | Observation stop rules | Observation policy and identity checker | `python3 scripts/observation_check_v1.py` | `make ci` | observation policy and log | Human operators can still approve future scoped work |
| Global recognition is not self-certified | External signoff could be falsely implied | Explicit final authority boundary | README and audit docs | `python3 scripts/identity_boundary_check_v1.py` | identity check | README and final audit packet | External verification remains pending |
