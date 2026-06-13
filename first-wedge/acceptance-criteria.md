# Acceptance Criteria

## Purpose

Define what counts as accepted delivery for the readiness audit and what
must remain marked pending.

## Buyer Acceptance

The buyer accepts the audit only when:

- the audited workflow is named and bounded
- buyer, technical owner, and risk owner are identified
- every readiness statement maps to evidence or is marked
  `EVIDENCE_PENDING`
- high-risk gaps have owners and next actions
- review gates and human approval points are explicit
- rollback/remediation path is documented
- recommendations are prioritized by risk and feasibility
- exclusions are restated
- buyer confirms the report is actionable for the intended decision

## Deliverable Acceptance Table

| Deliverable | Accepted When | Not Accepted When |
| --- | --- | --- |
| Readiness scorecard | Ratings include evidence, limitations, and remediation. | Ratings are asserted without evidence. |
| Evidence matrix | Claims, sources, dates, owners, and gaps are visible. | Evidence is vague or missing. |
| Risk-tier map | Risks are tiered with owner and approval path. | All risks are treated equally. |
| Review-gate map | Gates are specific to workflow risk. | Gates are generic slogans. |
| Rollback/remediation plan | Failure path and owner are named. | "Monitor manually" is the only response. |
| Prioritized action plan | Buyer can choose immediate next steps. | Recommendations are unordered or unrealistic. |

## Proof Acceptance

Proof assets may be generated only if:

- sensitive data is redacted
- buyer approves use or internal-only storage
- proof wording is lower than evidence
- no paid traction, certification, ROI, or customer-success claim is implied
  beyond the actual record

## Repository Completion Boundary

The existence of this file supports `EXECUTION_KIT_READY`.

It does not prove `REAL_DELIVERY_PENDING` has been closed.
