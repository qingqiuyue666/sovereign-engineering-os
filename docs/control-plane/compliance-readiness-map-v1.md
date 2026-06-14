# Compliance Readiness Map V1

Status: `implemented_local_no_certification_claim`

This map prepares SOC 2 / ISO-style evidence collection without claiming
certification.

| Control Area | Local Evidence | External Requirement | Status |
| --- | --- | --- | --- |
| access review | AGENTS human-gate rules and pilot data boundary | customer access review artifact | pending external evidence |
| change management | PR, CI, branch, commit, and validation records | approved change-management process | local only |
| incident response | incident workflow and existing `docs/operations/incident_response_v1.md` | incident drill or reviewer signoff | pending external evidence |
| data handling | pilot data boundary and no-secret rule | customer data processing agreement | pending external evidence |
| retention | audit export and ledger paths | retention policy approval | pending external evidence |
| third-party risk | external matrix and tool-risk registry | vendor/tool review | pending external evidence |
| evidence collection | JSON/JSONL ledgers and scorecards | auditor handoff packet | local only |

## Auditor Handoff Checklist

- repo commit and PR URL;
- validation commands and results;
- evidence ledger export;
- external evidence ledger;
- production blocker ledger;
- incident workflow;
- security review workflow;
- unsupported claim list;
- residual-risk register.

No certification is claimed by this map.

