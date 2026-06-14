# AI Agent Execution Control Plane Full Stack Operation Registry V1

Status: `CONTROLLED_AUTONOMOUS_ENGINEERING_OS_FULL_STACK_OPERATION_READY_LOCAL`

This registry defines the repository-local operating surface for an AI Agent
Execution Control Plane. It extends, but does not replace, `AGENTS.md`,
`docs/agent-protocols/`, `docs/aoos/`, `CODEX_EXECUTION_SYSTEM.md`,
`validation/`, and `reports/real-world-validation/`.

## Product Category

AI Agent Execution Control Plane.

Business definition: a safety control layer for AI engineering execution. It
lets AI executors such as Codex, Claude Code, local shell agents, GitHub
Actions, MCP tools, OpenHands-style runtimes, and future automation tools
perform controlled engineering work only under policy gates, evidence ledgers,
failure recovery, resume points, recurring checks, human approval boundaries,
security controls, benchmark/evaluation gates, operator review, commercial
validation, and non-claim discipline.

The product sells the control layer above agents. It does not compete as
another coding agent.

## Allowed Local Commercial Claim

`AI Agent Execution Control Plane with controlled local low-risk execution, evidence-backed safety gates, commercial validation package, real-world validation workflow, and commercial operation readiness.`

This claim is repository-local and evidence-bound. It does not assert external
customer, benchmark, production, compliance, revenue, or long-running evidence.

## Forbidden Claims

The following claims require external records and must stay blocked until the
corresponding evidence ledger entry exists:

- enterprise-wide production-ready;
- externally benchmark-proven;
- independently security-certified;
- SOC 2 or ISO certified;
- long-term production autonomy-proven;
- commercially deployed;
- paid by enterprise customer;
- globally mature;
- fully MCP-safe;
- fully secret-safe;
- production-observability-proven;
- customer-validated;
- enterprise procurement-approved.

## Operating Modes

| Mode | Decision Surface | Allowed Action | Stop Rule |
| --- | --- | --- | --- |
| `local_low_risk_execute` | V4 policy gate | Documentation, fixtures, safe local validation, bounded report updates | Stop on protected path, secret, deploy, merge, release, paid API, or destructive command |
| `dry_run_only` | V4/V5 policy gate | Simulated command, task fixture, evidence-only output | Stop if a real external side effect is needed |
| `human_required` | V4/V6/V7 external gate | Prepare packet, blocker, resume point, and next action | Stop before outreach, production, payment, auditor, or benchmark execution |
| `deny` | Forbidden-action gate | Record denial evidence and failure/resume record | Do not execute |
| `external_reality_wait` | V6/V7 tracker | Wait for customer, reviewer, auditor, production, benchmark, or payment evidence | Do not fabricate evidence |

## Control Plane Gates

| Gate | Purpose | Evidence Path |
| --- | --- | --- |
| workspace gate | Verify repo, remote, branch, worktree, PR, and unrelated residue | `reports/control-plane/health-check-v1.json` |
| task input gate | Require structured task id, type, risk hints, action, paths, checks, and evidence | `docs/control-plane/task-input-model-v1.schema.json` |
| task classifier | Classify documentation, code, test, CI, audit, external-tool, human-only, and forbidden tasks | `docs/control-plane/classifier-policy-gate-v1.md` |
| risk classifier | Classify low, medium, high, and forbidden risk | `docs/control-plane/classifier-policy-gate-v1.md` |
| policy gate | Emit ALLOW, DRY_RUN_ONLY, REQUIRE_HUMAN, or DENY | `reports/control-plane/first-controlled-cycle-v1.json` |
| command and file-scope gate | Deny or escalate dangerous command, secret, deploy, merge, release, tag, paid API, destructive operation, unrelated path, external authority, untrusted instruction | `reports/control-plane/failure-ledger-v1.jsonl` |
| safe executor | Execute only safe local actions or dry-run fixture tasks | `reports/control-plane/evidence-ledger-v1.jsonl` |
| evidence ledger | Record task, classifier output, decision, command, output summary, file paths, checks, result, and evidence links | `reports/control-plane/evidence-ledger-v1.jsonl` |
| failure ledger | Record failed gates, failed checks, causes, repair attempts, blockers, and resume points | `reports/control-plane/failure-ledger-v1.jsonl` |
| recurring queue | Queue health, benchmark, security, external absorption, feedback, cleanup, and commercial sync checks | `reports/control-plane/recurring-queue-v1.json` |
| non-claim audit | Block unsupported real-world and commercial claims | `reports/control-plane/non-claim-audit-v1.json` |

## External Reality Gates

| External Reality Task | Required Actor | Required Evidence | Safe Substitute | Resume Point |
| --- | --- | --- | --- | --- |
| customer validation | real buyer or operator | dated feedback artifact with actor and scope | empty tracker plus intake form | `reports/control-plane/real-world-validation-tracker-v1.json` |
| external benchmark | benchmark operator or reviewer | environment, command, result, logs, contamination review | repo-local benchmark workflow and blocker | `docs/control-plane/benchmark-operation-workflow-v1.md` |
| production trial | production owner | deployment mode, approval, telemetry, rollback, incident plan | production blocker ledger | `reports/control-plane/production-operation-blocker-ledger-v1.json` |
| security review | independent reviewer or auditor | finding record, severity, remediation, signoff | response workflow and residual-risk queue | `docs/control-plane/security-review-response-workflow-v1.md` |
| paid pilot | buyer and payment owner | paid scope, success metrics, payment evidence | paid-pilot readiness gate | `docs/control-plane/paid-pilot-readiness-gate-v1.md` |
| compliance certification | auditor | formal certification artifact | readiness map and auditor handoff checklist | `docs/control-plane/compliance-readiness-map-v1.md` |

## Resume Semantics

The deterministic resume point is
`reports/control-plane/resume-point-v1.json`. Resume is allowed only from the
last recorded stage, current branch head, validation command list, unresolved
blockers, and queued next action. Chat memory is not authority.

## Stage Map

| Stage | Local Status | Primary Evidence |
| --- | --- | --- |
| V4 product core landing | `implemented_local` | `reports/control-plane/first-controlled-cycle-v1.json` |
| V5 commercial validation package | `implemented_local` | `reports/control-plane/commercial-readiness-package-v1.json` |
| V6 real-world validation execution track | `implemented_local_external_evidence_pending` | `reports/control-plane/real-world-validation-tracker-v1.json` |
| V7 commercial operation and growth track | `implemented_local_external_evidence_pending` | `reports/control-plane/final-scorecard-v1.json` |

