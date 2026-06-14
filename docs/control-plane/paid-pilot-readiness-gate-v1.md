# Paid-Pilot Readiness Gate V1

Status: `implemented_local_external_payment_pending`

This gate prepares, but does not claim, paid pilot readiness.

## Required Before Paid Pilot

| Requirement | Local Artifact | External Evidence Needed |
| --- | --- | --- |
| pilot scope | `docs/control-plane/pilot-operation-workflow-v1.md` | buyer-approved scope |
| success metrics | pilot workflow and final scorecard | buyer acceptance criteria |
| support boundary | operator runbook | buyer acknowledgement |
| pricing hypothesis | `reports/control-plane/pricing-packaging-iteration-tracker-v1.json` | buyer feedback or objection |
| no-fabrication rule | non-claim audit | source evidence for every claim |
| customer evidence requirement | external evidence ledger schema | real customer artifact |
| payment evidence requirement | external evidence ledger schema | invoice, payment, or signed paid scope |

## Decision

The repository is ready to support a paid-pilot conversation. It is not allowed
to claim paid pilot acceptance, payment, enterprise customer adoption, or
procurement approval until the external evidence ledger contains proof.

