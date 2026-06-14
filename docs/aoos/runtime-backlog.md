# AOOS Runtime Backlog

## Purpose

The AOOS runtime backlog is the smallest persistent task queue for moving from
prompt-driven execution toward backlog-driven, policy-driven, evaluator-driven
repository work.

It does not create a live scheduler, approval queue, daemon, dashboard, or
autonomous production runtime. It records the next executable repository
increments and their authority, evidence, rollback, and promotion gates.

## Record

The current machine-readable backlog record is:

- `reports/aoos/runtime-backlog-v1.json`

The record is validated by:

- `docs/aoos/schemas/runtime-backlog.schema.json`
- `scripts/aoos_stage45_check_v1.py`

## Selection Policy

Select the highest-priority backlog item when all of these are true:

- its dependencies are satisfied
- its risk class is inside A0-A4 for autonomous repository work
- its acceptance gate is checkable
- its rollback path is explicit
- it does not require real-world outreach, payment, credential handling,
  production deployment, external service introduction, direct `main` push, or
  merge authorization

A5 items may be drafted as packets only. A6 items stop at the human gate.

## Required Item Fields

Each backlog item must include:

- `id`
- `title`
- `domain`
- `maturity_target`
- `priority`
- `dependencies`
- `risk_class`
- `evidence_requirement`
- `acceptance_gate`
- `checks_required`
- `rollback_path`
- `status`
- `next_action`
- `owner_role`
- `evaluator_required`
- `promotion_rule_if_repeated_failure`

## Claim Boundary

A valid AOOS runtime backlog proves only repository-level planning and local
validation readiness. It does not prove Stage 6/7 operation, L8/L9 operation,
customer acceptance, payment, delivery completion, production deployment, or
real-world validation.
