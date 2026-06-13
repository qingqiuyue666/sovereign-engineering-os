# AOOS Stage 5 Interfaces

## Purpose

Define the interfaces required for observability, evaluation, audit, incidents,
memory, routing, and reality validation. These are interface contracts and
templates, not proof of a live Stage 5 operating system.

## Observability Event

Required fields:

- `event_id`
- `timestamp_utc`
- `agent_or_operator`
- `domain_pack`
- `goal_id`
- `task_class`
- `state_gate`
- `action_taken`
- `authority_level`
- `risk_level`
- `evidence_refs`
- `decision_refs`
- `rollback_path`
- `next_gate`

## Decision Log

Required fields:

- decision id
- date
- domain pack
- options considered
- chosen option
- rejected alternatives
- opportunity cost
- evidence level
- counterevidence
- review date
- kill or revise condition

## Evidence Ledger

Required fields:

- evidence id
- claim supported
- evidence level L0 through L5
- source path or external source record
- actor
- timestamp
- validation command when applicable
- limitations
- stronger claim explicitly forbidden

## Evaluator Metrics

Initial metrics are placeholders until repeated task records exist:

- `false_done_rate`
- `manual_intervention_rate`
- `retry_success_rate`
- `repeated_failure_rate`
- `cost_per_verified_task`
- `time_to_verified_done`
- `real_world_validation_rate`

Each metric must state numerator, denominator, time window, exclusions, and
known gaming risk. Metrics must not replace the underlying goal.

## Failure Taxonomy

Minimum failure classes:

- stale context
- wrong repository or branch
- duplicate protocol surface
- unsupported completion claim
- missing evidence
- check failure
- CI failure
- human gate required
- secret or credential boundary
- tool complexity overrun
- domain acceptance failure
- real-world validation missing

## Incident Interface

Use `templates/aoos/incident-record-template.md` for AOOS incidents and link
the record to `docs/operations/incident_response_v1.md`.

Minimum incident stages:

- severity
- detection
- containment
- rollback
- root cause
- remediation
- prevention
- postmortem
- promotion into rule, playbook, script, CI, evaluator, or policy when needed

## Memory Lifecycle Interface

Required fields:

- memory id
- source
- confidence
- expiry
- conflict status
- owner
- promotion candidate
- promoted artifact
- stale-removal rule

Repository files win over chat memory when conflicts exist.

## Reality Validation Interface

Use `templates/aoos/reality-validation-log-template.md`.

Reality validation must distinguish:

- repository completion versus real use
- script success versus visible software behavior
- demo success versus repeatable workflow
- CI success versus customer acceptance
- customer interest versus payment
- payment versus repeatable product-market fit

## Model / Tool Routing Interface

Use `templates/aoos/model-tool-routing-decision-template.md`.

Required fields:

- routing id
- candidate model/tool
- classification: USE_NOW, USE_LATER, REFERENCE_ONLY, or REJECT
- exact bottleneck removed
- authority boundary
- permission or credential risk
- reviewer separation
- fallback policy
- exit plan
- evidence that the routing worked

## Audit Boundary

A Stage 5 interface pass is not enough for Stage 6/7 claims. Stronger claims
require repeated, dated operating records and human or real-world acceptance at
the evidence level appropriate to the domain.
