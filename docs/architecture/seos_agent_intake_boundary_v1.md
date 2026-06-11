# SEOS Agent Intake Boundary V1

Status: `SEOS_AGENT_INTAKE_BOUNDARY_READY_FOR_REVIEW`

This document defines how SEOS should absorb useful ideas from modern agent
protocols and coding assistants without allowing them to become an authority
surface.

## Why This Exists

Modern agent systems increasingly expose two useful primitives:

- read-only context surfaces
- action-like tools

MCP formalizes this split with resources, tools, and prompts. The useful lesson
for SEOS is the boundary, not a mandatory dependency. Resources are read-only
context. Tools may have side effects. SEOS must therefore treat external agent
requests as untrusted until they are converted into bounded proposals and passed
through normal task, approval, permit, execution, receipt, and evidence gates.

## SEOS Mapping

| Agent concept | SEOS mapping | Authority |
| --- | --- | --- |
| resource | read-only mirror/status/evidence summary | `mirror` |
| prompt | reusable operator/agent template | `proposal` |
| tool request | proposed action requiring SEOS review | `proposal` |
| tool result | candidate evidence, not final evidence | `proposal` or `mirror` |
| execution request | rejected unless converted through SEOS gates | none |

## Allowed Agent Intents

- `proposal`
- `task_draft`
- `patch_proposal`
- `failure_explanation`
- `test_plan`
- `evidence_request`
- `repair_job_draft`
- `knowledge_query`
- `readonly_status`

Accepted requests are admitted only as proposal/read-only artifacts.

## Forbidden Agent Intents

- `approve`
- `create_permit`
- `execute`
- `run_local_command`
- `read_secret`
- `write_secret`
- `desktop_control`
- `browser_control`
- `rpa`
- `mutate_authority_store`
- `bypass_human_review`

## Required Flow

```text
external agent request
  -> agent boundary evaluator
  -> accepted proposal or rejected decision
  -> normal SEOS task intake
  -> human approval/rejection
  -> execution permit if needed
  -> controlled runner
  -> execution receipt
  -> materialization/evidence trace
  -> replay explanation
```

## Implementation

```text
kernel/agent_intake/
  boundary.py      # pure request classifier
  proposals.py     # proposal writer under .seos/agent_intake/proposals
  mcp_manifest.py  # dependency-free MCP-inspired manifest
  cli.py           # seos-agent and seos.py agent CLI
```

The implementation does not import the MCP SDK. It records a manifest inspired by
MCP resource/tool separation so SEOS can later expose a true MCP server if that
becomes useful, without making the protocol dependency part of the authority
kernel.

## Invariants

Every accepted proposal records:

- `task_created: false`
- `approval_created: false`
- `permit_created: false`
- `execution_performed: false`
- `execution_authority_granted: false`

Every rejected decision records the boundary reason.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_agent_intake_boundary_v1 -v
python3 -m kernel.agent_intake.cli --help
python3 seos.py agent --help
```
