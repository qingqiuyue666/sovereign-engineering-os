# Delivery Scope

## Purpose

Define the exact work boundaries for the AI Production Governance Readiness
Audit before the trusted-delivery playbook is applied.

## Included Work

1. Confirm buyer, technical owner, risk owner, and acceptance decision.
2. Map one AI-assisted engineering workflow from intake to release or use.
3. Review supplied artifacts such as tickets, PRs, test output, review
   notes, release checklists, runbooks, incident notes, and policy docs.
4. Identify risk tiers for AI-assisted work.
5. Define evidence required before readiness claims.
6. Map human approval and review gates.
7. Produce rollback/remediation plan.
8. Produce readiness scorecard and prioritized action plan.
9. Prepare proof-asset capture plan subject to approval and redaction.

## Excluded Work

- production code edits
- live deployment or release operation
- secret handling
- direct access to private production systems unless separately approved
- legal, compliance, or certification opinion
- broad AI transformation roadmap
- SaaS or app implementation
- provider procurement or model benchmarking

## Required Inputs

- named workflow
- buyer and risk owner
- business trigger
- current process artifacts
- known constraints
- permitted evidence access
- desired decision or deadline

## Output Package

- `readiness-scorecard`
- `evidence-matrix`
- `risk-tier-map`
- `review-gate-map`
- `rollback-remediation-plan`
- `prioritized-action-plan`
- `proof-asset-capture-plan`

Actual output files are created during real delivery. Until then, this scope
is a template and remains `REAL_DELIVERY_PENDING`.

## Change Control

Any scope expansion must name:

- new buyer approval
- additional risk
- additional evidence
- revised acceptance
- revised price or timeline
- effect on proof claims
