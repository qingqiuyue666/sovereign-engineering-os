# AOOS Stage 5 Interfaces

## Purpose

Define the interfaces required for observability, evaluation, audit, incidents,
memory, routing, and reality validation. These are interface contracts and
templates, not proof of a live Stage 5 operating system.

Machine-readable interface contracts live under `docs/aoos/schemas/`. The
minimum fixture is `examples/aoos/stage45-interface-fixture-v1.json`, and
`scripts/aoos_stage45_check_v1.py` validates the fixture without adding a new
dependency.

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

Schema: `docs/aoos/schemas/observability-event.schema.json`.

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

Schema: `docs/aoos/schemas/decision-log-entry.schema.json`.

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

Schema: `docs/aoos/schemas/evidence-ledger-entry.schema.json`.

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

Schema: `docs/aoos/schemas/evaluator-metrics-snapshot.schema.json`.

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

Machine-readable failure entries must state the failure class, description,
domain pack, triggers, evidence required, severity hint, repair policy,
promotion path, and forbidden claims.

Schema: `docs/aoos/schemas/failure-taxonomy-entry.schema.json`.

Fixture key: `failure_taxonomy_entry`.

## Threat Model Interface

Required fields:

- threat id
- domain pack
- threat class
- asset or boundary
- attack or failure mode
- risk level
- mitigations
- evidence refs
- human gate
- residual risk
- review cadence
- forbidden actions

Minimum threat classes:

- secret or credential exposure
- prompt injection or malicious instructions
- poisoned repository instructions
- dependency or supply-chain compromise
- unsafe shell command
- platform or account boundary violation
- private data exfiltration
- legal, payment, customer, or market-claim overreach

Schema: `docs/aoos/schemas/threat-model-record.schema.json`.

Fixture key: `threat_model_record`.

## Incident Interface

Use `templates/aoos/incident-record-template.md` for AOOS incidents and link
the record to `docs/operations/incident_response_v1.md`.

Schema: `docs/aoos/schemas/incident-record.schema.json`.

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

Schema: `docs/aoos/schemas/memory-lifecycle-entry.schema.json`.

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

Schema: `docs/aoos/schemas/model-tool-routing-decision.schema.json`.

## Domain Pack Manifest Interface

Each domain pack can be represented as a manifest with scope, non-goals,
inspection checklist, ALLOW / ASK / DENY / REPORT boundaries, inputs, outputs,
evidence records, acceptance rubric, failure triggers, rollback path,
observability events, evaluator metrics, learning promotion path, and forbidden
claims.

Schema: `docs/aoos/schemas/domain-pack-manifest.schema.json`.

## Audit Boundary

A Stage 5 interface pass is not enough for Stage 6/7 claims. Stronger claims
require repeated, dated operating records and human or real-world acceptance at
the evidence level appropriate to the domain.
