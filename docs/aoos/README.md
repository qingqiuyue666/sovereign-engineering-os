# Agentic Organization Operating System

## Purpose

AOOS is the cross-domain operating layer for durable human-AI collaboration
across repository work, creative production, research, sales, delivery,
business validation, security, asset governance, operator control, evaluation,
and learning.

This directory extends the existing SEIS and agent-protocol work. It must not
create a parallel authority system. Repository agents should treat
`AGENTS.md`, `CLAUDE.md`, and `docs/agent-protocols/` as the execution
protocol entrypoint, then use this directory for cross-domain module routing
and Stage 4/5 interface checks.

## Stage Boundary

Current target: `AOOS_STAGE_4_5_EXECUTABLE_SKELETON_READY_FOR_REVIEW`.

Stage 4 means the repository has a coherent protocol stack, repository
instructions, mission templates, evidence schemas, domain-pack structure,
governance documents, initial check scripts, and checkpoint reporting.

Stage 5 interface means the repository defines observability hooks, evaluator
interfaces, metric placeholders, audit logs, incident protocol, memory
lifecycle, threat model, and failure taxonomy. It does not mean those
interfaces have been proven in real operating cycles.

Stage 6 and Stage 7 remain roadmap or future-evidence territory until real
operation, recovery, learning, and cross-domain repetition records exist.

## Navigation

- `docs/aoos/core-module-map.md` maps the AOOS core modules to existing
  repository anchors and missing evidence.
- `docs/aoos/domain-packs.md` defines the replaceable domain-pack contract and
  the initial cross-domain pack set.
- `docs/aoos/runtime-backlog.md` defines the persistent AOOS backlog selection
  policy and required item fields.
- `docs/aoos/stage-5-interfaces.md` defines observability, evaluator, audit,
  incident, memory, and routing interfaces.
- `docs/aoos/schemas/` contains JSON Schema contracts for the Stage 5
  interface records.
- `reports/aoos/evidence-ledger-v1.jsonl` is the initial AOOS evidence ledger
  seed mapping repository claims to evidence levels and forbidden stronger
  claims.
- `reports/aoos/runtime-backlog-v1.json` is the current machine-checkable AOOS
  backlog record.
- `examples/aoos/stage45-interface-fixture-v1.json` is the minimal fixture
  checked against those contracts.
- `templates/aoos/` contains reusable mission brief, evidence, failure,
  incident, reality, tool ROI, routing, and acceptance-rubric templates.
- `scripts/aoos_stage45_check_v1.py` verifies the required Stage 4/5 anchors
  exist, contain the minimum safety terms, and have schema/fixture coverage.

## Existing Protocol Reuse

AOOS uses these existing repository surfaces instead of replacing them:

- execution state machine: `docs/agent-protocols/continuous-stage-gated-execution.md`
- authority gates: `docs/agent-protocols/high-risk-human-gates.md`
- evidence/no-fake rules: `docs/agent-protocols/evidence-and-no-fake-completion.md`
- failure handling: `docs/agent-protocols/failure-handling-if-then.md`
- memory governance: `docs/agent-protocols/memory-governance.md`
- tool governance: `docs/agent-protocols/tool-selection-gate.md`
- incident response: `docs/operations/incident_response_v1.md`
- real-world validation: `validation/` and `reports/real-world-validation/`
- security and secret boundaries: `SECURITY.md` and `docs/security/`

## Claim Boundary

Repository readiness is not real-world completion. A green Stage 4/5 check
proves only that the repository has the expected documentation and interface
anchors. It does not prove customer acceptance, payment, production deployment,
audience retention, external audit, operational reliability, or product-market
fit.
