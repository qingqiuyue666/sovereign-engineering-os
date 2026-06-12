# Budget Source Map

## Purpose

Map where money can come from for the readiness audit and what each budget
source needs to believe before approving.

## Budget Sources

| Budget Source | Controller | Buying Logic | Required Proof |
| --- | --- | --- | --- |
| Engineering productivity | CTO, VP Engineering, founder | AI coding saves time only if review and release risk stay controlled. | Workflow map, review bottleneck, remediation plan. |
| Developer tooling | Engineering or platform lead | Governance audit is part of the toolchain adoption cost. | Clear integration with PR, test, release, and evidence processes. |
| Security/compliance readiness | Security lead, compliance owner | AI-assisted code needs admissibility, provenance, and approval evidence. | Evidence matrix and human approval points. |
| Release quality | Engineering manager, release owner | Bad AI-code changes increase regression and rollback cost. | Risk-tier map and rollback plan. |
| Incident prevention | CTO, operations owner | A small audit is cheaper than a production incident or customer escalation. | Incident/near-miss pattern and risk-reduction hypothesis. |
| Audit/customer review | Executive sponsor, compliance owner | External stakeholders need credible answers before approving AI-enabled delivery. | Readiness report and limits clearly marked. |

## Price Sensitivity

Lower price sensitivity is expected when:

- a release, audit, board, or customer review is scheduled
- AI-code volume is already high
- production defects or review bottlenecks are visible
- the buyer owns both AI adoption and production risk

Higher price sensitivity is expected when:

- AI use is experimental
- the buyer lacks workflow authority
- the team wants generic training
- no deadline or risk event exists

## Budget Qualification

Ask:

- Which budget would this come from if the audit is useful?
- Who approves that spend?
- What deadline would make the spend worthwhile now?
- What evidence would make the audit easy to approve?
- What would make this a no-decision?

## Non-Claims

This map does not prove willingness to pay. It is a hypothesis for discovery
and must be updated from real objections, quotes, approvals, and losses.
