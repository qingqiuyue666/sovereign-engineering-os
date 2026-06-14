# Incident Operation Workflow V1

Status: `implemented_local`

This workflow covers unsafe command attempts, protected path access, secret
exposure suspicion, bad MCP/tool descriptor, policy bypass attempt, failed
execution loop, corrupted ledger, CI failure, rollback, and resume.

## Incident Types

| Type | Trigger | Immediate Action |
| --- | --- | --- |
| unsafe command attempt | destructive, deploy, merge, release, tag, paid API, or secret operation | deny, record failure ledger, stop if real side effect was possible |
| protected path access | path outside allowed scope | require human review |
| secret exposure suspicion | credential-like data discovered or requested | stop, do not print, ask human to rotate/review |
| bad tool descriptor | prompt injection, tool poisoning, shadowed name, rug-pull descriptor | deny and add tool-risk record |
| policy bypass attempt | task tries to override gates or no-fake-completion rule | deny and log |
| failed execution loop | repeated failed check or repair loop | reduce to smallest valid slice, keep target unchanged |
| corrupted ledger | invalid JSON/JSONL or missing evidence | stop final report and repair ledger |
| CI failure | GitHub or local validation failure | inspect, repair smallest safe cause, rerun |

## Incident Record Fields

Incident id, timestamp, trigger, severity, affected gate, containment action,
evidence preserved, rollback or recovery action, validation command, residual
risk, resume point, and human approval requirement.

## Rollback And Resume

Repository rollback is a follow-up commit or human-authorized revert. Do not
rewrite public history, delete preserved artifacts, or hide incident evidence.

