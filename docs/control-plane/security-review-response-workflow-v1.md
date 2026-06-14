# Security Review Response Workflow V1

Status: `implemented_local_external_reviewer_pending`

This workflow handles security findings without claiming certification.

## Finding Intake

Each finding must record finding id, reviewer, source artifact, date, severity,
affected gate, affected files or workflow, reproduction notes, evidence, and
claim impact.

## Severity

| Severity | Examples | Response |
| --- | --- | --- |
| critical | secret exposure, destructive bypass, customer data exfiltration | stop operation, incident workflow, human review |
| high | policy gate bypass, unsafe tool descriptor, uncontrolled external action | mitigation, regression test, residual risk |
| medium | evidence gap, weak authorization, ambiguous file scope | backlog with owner and check |
| low | documentation clarity or hardening improvement | queue and sync docs |

## Response Steps

1. Preserve evidence.
2. Classify severity and affected gate.
3. Mitigate or document blocker.
4. Add or update regression test.
5. Record residual risk.
6. Require reviewer signoff for closure when the finding came from an external
   reviewer.

## Certification Boundary

Security review records do not equal independent certification. Certification
requires a formal external auditor artifact recorded in the external evidence
ledger.

