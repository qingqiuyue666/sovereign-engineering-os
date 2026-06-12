# AI Production Governance Readiness Audit

## Purpose

Define the entry transaction for teams that are already using AI-assisted
engineering and need production trust before the workflow creates avoidable
risk.

## Offer Statement

In 5-10 delivery days, SEIS reviews one bounded AI-assisted engineering
workflow and produces an evidence-backed readiness report covering code
admission, review gates, risk tiers, tests, rollback, ownership, audit trail,
and acceptance criteria.

## Buyer

Primary buyer:

- VP Engineering, Head of Engineering, CTO, founder, platform lead, or AI
  adoption owner

Secondary stakeholders:

- security lead
- compliance or audit owner
- release manager
- staff engineer
- product owner for AI-enabled development

## Budget Controller

The budget controller is usually the engineering leader or founder who can
approve developer tooling, release quality, incident-prevention, or security
readiness spend. If a security or compliance budget is used, the engineering
owner must still participate because workflow change is required.

## Trigger

The offer should be pitched only when at least one trigger is present:

- AI-written code is already reaching pull requests or production.
- Leadership needs a policy before a major release.
- A customer, auditor, investor, or board member asks how AI code is
  controlled.
- A near miss, incident, flaky release, or review bottleneck exposes risk.
- The team wants to scale AI coding without turning review into guesswork.

## Scope

Included:

- intake of one current AI-code workflow
- artifact review for tickets, PRs, tests, review notes, release gates, and
  rollback evidence supplied by the client
- governance risk map
- readiness scorecard
- evidence matrix
- review-gate recommendations
- rollback and remediation plan
- acceptance criteria for the audited workflow
- proof-asset capture plan

Excluded:

- production code changes
- direct deployment authority
- secret access
- legal, compliance, or certification opinion
- live provider integration or model procurement
- broad company transformation

## Deliverables

| Deliverable | Acceptance Test |
| --- | --- |
| Readiness scorecard | Buyer can see rating, evidence, limitation, and remediation for each control area. |
| Evidence matrix | Every readiness claim maps to supplied evidence or is marked `EVIDENCE_PENDING`. |
| Risk-tier map | High, medium, and low workflow risks have owners and next actions. |
| Review-gate map | Required human and automated gates are named before production readiness is claimed. |
| Rollback/remediation plan | Buyer can name what happens when an AI-code change fails review or release. |
| Prioritized action plan | Next actions are ordered by risk reduction and operational feasibility. |

## Price Ladder

Use `first-wedge/pricing-ladder.md`. Do not present a custom quote without
recording scope, assumptions, exclusions, and close/loss outcome.

## Completion Boundary

Repository package status can be `EXECUTION_KIT_READY`.

Real market status remains `MARKET_PROOF_PENDING` until a buyer accepts a
paid or equivalent high-commitment audit and evidence is recorded.
