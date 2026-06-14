# AOOS Core Module Map

## Purpose

Map the cross-domain AOOS modules to current repository anchors, define the
minimum Stage 4 responsibilities, and expose Stage 5 interfaces without
overstating evidence.

## Existing Work Reconciliation

| Surface | Classification | Rationale | Action |
| --- | --- | --- | --- |
| `AGENTS.md` | UPDATE | Correct root entrypoint for all repository agents. | Link AOOS navigation without changing authority gates. |
| `CLAUDE.md` | UPDATE | Model-specific memory mirrors `AGENTS.md`. | Keep concise; point to AOOS as cross-domain context. |
| `docs/agent-protocols/` | KEEP / LINK | Already holds execution, evidence, gates, failure, memory, and tool rules. | Reuse as execution protocol layer. |
| `SEIS_*`, `BRAIN_GOVERNANCE.md`, `EIGHT_ENGINES.md` | KEEP | Existing strategic and authority context. | Treat as strategy/proof substrate, not duplicate AOOS. |
| `validation/` and `reports/real-world-validation/` | KEEP / LINK | Existing real-world validation and no-fake-traction layer. | Use for Reality Validation and Business Validation packs. |
| `docs/operations/incident_response_v1.md` | LINK | Existing incident response anchor. | Expose through Stage 5 interface map. |
| `docs/security/`, `SECURITY.md` | KEEP / LINK | Existing secret/context/supply-chain controls. | Use for Security / Compliance pack. |
| `reports/creative/production_spine_v1/` | PRESERVE | Local untracked generated artifacts are present. | Do not stage, delete, or treat as AOOS-owned evidence. |

## Core Modules

| Module | Stage 4 responsibility | Stage 5 interface | Existing anchors | Evidence gap |
| --- | --- | --- | --- | --- |
| Strategy / Portfolio Governance | Decide priority, opportunity cost, bet sizing, sequencing, kill criteria, and stop-loss before execution. | Decision log event with chosen bet, rejected alternatives, and review date. | `SEIS_STRATEGIC_OPERATING_SYSTEM_V1.md`, `BATTLEFIELD_SCORECARD.md`, `ROADMAP.md` | No repeated cross-domain portfolio operating cycles yet. |
| Truth / Evidence Governance | Separate verified facts, assumptions, stale memory, AI inference, source hierarchy, and evidence levels. | Evidence ledger row with level, source, actor, timestamp, and claim boundary. | `docs/agent-protocols/evidence-and-no-fake-completion.md`, `SEIS_DOCTRINE.md` | No central AOOS evidence ledger runtime yet. |
| Authority / Risk Governance | Enforce ALLOW / ASK / DENY / REPORT, risk matrix, human gates, irreversible-action gates, and credential boundaries. | Approval event with requested authority, risk tier, human gate, and rollback path. | `AGENTS.md`, `docs/agent-protocols/high-risk-human-gates.md`, `BRAIN_GOVERNANCE.md` | Human approval queue is interface-only. |
| Execution State Machine | Run classify, inspect, define, plan, act, verify, repair, escalate, report. | Task state snapshot with current gate, evidence, retries, and stop condition. | `docs/agent-protocols/continuous-stage-gated-execution.md` | No centralized scheduler or dashboard claim. |
| Runtime Backlog / Queue | Preserve the next executable AOOS increments with priority, dependency, A0-A6 risk, evidence, checks, rollback, owner role, evaluator, and promotion rules. | Backlog item record with status, next action, acceptance gate, and stop boundary. | `docs/aoos/runtime-backlog.md`, `reports/aoos/runtime-backlog-v1.json`, `docs/aoos/schemas/runtime-backlog.schema.json` | No live scheduler, approval queue, or repeated backlog operating history yet. |
| Observability / Audit | Log event, decision, task state, checkpoint, and traceability from goal to evidence. | Append-only audit event schema and checkpoint report template. | `docs/contracts/evidence_trace_v1.md`, `docs/operations/real_world_operation_evidence_program_v1.md` | Cross-domain dashboard remains unimplemented. |
| Evaluator / Metrics | Define false_done_rate, manual_intervention_rate, retry_success_rate, repeated_failure_rate, cost_per_verified_task, time_to_verified_done, and real_world_validation_rate. | Metrics snapshot with numerator, denominator, time window, and limitations. | `docs/aoos/stage-5-interfaces.md` | Metrics are placeholders until repeated runs exist. |
| Learning / Memory Lifecycle | Govern memory source, confidence, expiry, conflict resolution, and promotion path from memory to checklist, playbook, script, CI, evaluator, or policy. | Learning promotion event with source failure and promoted control. | `docs/agent-protocols/memory-governance.md` | No AOOS-wide memory registry runtime yet. |
| Tool / Complexity Governance | Classify tools as USE_NOW, USE_LATER, REFERENCE_ONLY, or REJECT with ROI, maintenance, risk, and exit plan. | Tool ROI review record. | `docs/agent-protocols/tool-selection-gate.md` | No recurring tool-retirement review evidence yet. |
| Security / Threat Model | Cover secrets, prompt injection, malicious instructions, dependency risk, supply chain, platform/account risk, shell risk, and data exfiltration. | Threat event and mitigation record. | `SECURITY.md`, `docs/security/`, `docs/audits/red_team_checklist_v1.md` | No AOOS-specific threat-model review cycle yet. |
| Reality Validation | Block repository-complete, script-success, demo-success, and CI-success from becoming customer or market claims. | Reality validation log with actor, source record, acceptance, and claim limit. | `validation/`, `reports/real-world-validation/` | Real buyer/payment/delivery records remain human gated. |
| Incident Response | Define severity, containment, rollback, root cause, remediation, prevention, postmortem, and rule/playbook/script updates. | Incident record template and post-incident learning event. | `docs/operations/incident_response_v1.md` | AOOS incident drills are not proven. |
| Anti-Goodhart / Anti-Delusion | Keep metrics subordinate to goals and stop activity, reports, tools, or internal coherence from replacing outcomes. | Evaluator note requiring counterevidence and metric failure modes. | `SEIS_DOCTRINE.md`, `docs/agent-protocols/evidence-and-no-fake-completion.md` | No evaluator history for metric gaming yet. |

## Stage 4/5 Readiness Rules

The AOOS Stage 4/5 skeleton is ready for review only when:

- the root agent instructions link to AOOS without weakening existing gates
- domain packs exist with acceptance rubrics and evidence boundaries
- a persistent runtime backlog record exists with A0-A6, evidence, acceptance,
  check, rollback, evaluator, owner-role, and promotion fields
- templates exist for evidence, failure learning, incidents, real-world
  validation, tool ROI, model/tool routing, and domain acceptance
- the Stage 5 interface map defines event, audit, metric, incident, memory,
  evaluator, and routing fields
- `docs/aoos/schemas/` and `examples/aoos/stage45-interface-fixture-v1.json`
  provide a machine-checkable interface fixture
- `scripts/aoos_stage45_check_v1.py` passes locally
- checkpoint reporting states what is not proven

Anything stronger requires CI, human review, and real-world source records at
the matching evidence level.
