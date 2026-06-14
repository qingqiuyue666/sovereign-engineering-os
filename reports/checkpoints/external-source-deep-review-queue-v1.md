# External Source Deep Review Queue V1

Status: `QUEUED_FOR_HUMAN_SECURITY_LICENSE_REVIEW`

## Queue

| Item | Current state | Why not complete now | Next smallest action | Required authority | Expected evidence |
| --- | --- | --- | --- | --- | --- |
| Benchmark dataset use | `NEEDS_REVIEW` | No license/access/contamination review | Pick one allowed subset | data/license reviewer | Review note and benchmark plan |
| Runtime dependency adoption | `NEEDS_REVIEW` | No dependency/security review | Evaluate one candidate | security reviewer | Risk note and dependency diff |
| Sandbox vendor use | `NEEDS_REVIEW` | Would involve external service/cost/data flow | Compare E2B/Daytona locally from docs | production owner/security reviewer | Sandbox decision record |
| MCP/A2A adoption | `REFERENCE_ONLY` | Protocol security model not reviewed | Threat-model protocol use | security reviewer | Threat model |
| Observability tool adoption | `REFERENCE_ONLY` | No live runtime target | Select local telemetry schema | Codex-only then reviewer | Trace schema proposal |

## Non-Claim Boundary

Queued review is not approval.
