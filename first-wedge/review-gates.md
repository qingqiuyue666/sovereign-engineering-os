# Review Gates

## Purpose

Define the gates that prevent unverified AI output, unsupported readiness
claims, or unsafe scope expansion from entering client-facing delivery.

## Gates

| Gate | Applies When | Required Reviewer | Exit Criteria |
| --- | --- | --- | --- |
| Scope Gate | Before delivery starts. | Buyer sponsor and SEIS executor. | Workflow, exclusions, evidence access, and acceptance are documented. |
| Evidence Gate | Before findings are drafted. | Technical owner or approved evidence owner. | Sources are available or gaps are marked `EVIDENCE_PENDING`. |
| Risk Gate | Before prioritization. | Risk owner. | Risk tiers and owners are accepted or disputed. |
| Claim Gate | Before client-facing readiness language. | SEIS auditor. | Claims are lower than evidence and limitations are visible. |
| External Gate | Before any proof/public language. | Buyer sponsor and risk owner. | Redaction, permission, and limitation wording are approved. |
| Handoff Gate | Before delivery closes. | Buyer sponsor. | Deliverables meet acceptance criteria or incomplete items are logged. |

## Executor/Auditor Separation

When findings are Tier 3 or Tier 4, the person or model chain that produced
the finding cannot be the final auditor. The auditor checks evidence,
language, risk tier, limitation, and acceptance.

## Gate Failures

If a gate fails:

- stop the affected claim or deliverable
- record the failure
- name the missing evidence or approval
- propose remediation or rescope
- do not hide the failure in final delivery

## Boundary

Review gates are not bureaucracy. They are the mechanism that lets SEIS
produce trustworthy work without pretending AI output is fact.
