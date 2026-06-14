# AI Agent Control Plane Classifier And Policy Gate V1

Status: `implemented_local`

This gate is the V4 classifier, risk router, policy decision, command scope,
file scope, tool-risk, and executor-adapter registry for the full stack
operation-readiness package.

## Task Classifier

| Task Type | Definition | Default Risk |
| --- | --- | --- |
| `documentation` | Markdown, JSON fixture, checklist, runbook, scorecard, or non-executable report update | low |
| `code` | Runtime, script, library, CLI, or app logic change | medium |
| `test` | Unit, smoke, acceptance, fixture, or validation target update | low |
| `ci` | Workflow, Makefile, or required validation surface change | medium |
| `audit` | Evidence review, claim review, no-fake-completion audit, or blocker ledger update | low |
| `external_tool` | MCP, browser, hosted benchmark, customer system, paid provider, or live external API action | high |
| `human_only` | merge, release, deploy, outreach, customer contact, payment, auditor signoff, security certification | high |
| `forbidden` | destructive, secret-handling, unsupported claim, policy bypass, prompt-injection compliance, untrusted tool instruction | forbidden |

## Risk Classifier

| Risk | Signals | Required Decision |
| --- | --- | --- |
| low | docs, local fixture, bounded report, local deterministic check, no external side effect | ALLOW |
| medium | code, CI, tests, broad path, dependency or workflow change | DRY_RUN_ONLY or REQUIRE_HUMAN unless bounded and reviewed |
| high | deploy, merge, release, tag, customer, payment, production, external benchmark, security auditor, secret-adjacent action | REQUIRE_HUMAN |
| forbidden | destructive command, secret print/move/modify, paid/live API without approval, unsupported claim, prompt-injection/tool-poisoning instruction | DENY |

## Policy Decision Contract

Policy output must be one of:

- `ALLOW`: local low-risk action may run and must produce an evidence ledger entry.
- `DRY_RUN_ONLY`: simulate and record expected action without external side effects.
- `REQUIRE_HUMAN`: prepare packet, blocker, resume point, and next action.
- `DENY`: block execution and write failure ledger evidence.

## Command And File-Scope Gate

Commands are denied or escalated when they include merge, release, tag,
deployment, destructive filesystem operation, credential handling, paid/live API
operation, untrusted tool instruction execution, package publishing, branch
deletion, protected path mutation, or unsupported external authority.

Allowed file scopes for this package:

- `docs/control-plane/`
- `reports/control-plane/`
- `scripts/real_world_operation_readiness_check_v1.py`
- `tests/tracer_bullet/test_real_world_operation_readiness_v1.py`
- `Makefile`
- `.github/workflows/ci.yml`

Known preserved local residue remains outside this scope:

- `reports/creative/production_spine_v1/`

## Tool-Risk Registry

| Tool Family | Allowed Local Use | Risk Gate |
| --- | --- | --- |
| local shell | read repo state, run deterministic tests, run git status/diff, run local validators | deny destructive commands and secret operations |
| GitHub CLI | inspect PR, checks, branch, and run state; push scoped branch commits when requested by the execution package | human gate for merge, release, tag, admin changes |
| MCP/browser tools | inspect local UI or fixtures only | require human for external account actions or live customer systems |
| coding agents | propose or apply repo-local patches under file scope | require evidence ledger and no-fake-completion audit |
| CI | run repository validators and publish check status | do not treat CI pass as external validation |

## Executor Adapter Registry

| Executor | Current Adapter Status | Allowed Surface | Denied Surface |
| --- | --- | --- | --- |
| Codex local shell | active local adapter | repo-local docs, scripts, tests, git branch push | merge, deploy, release, secrets, external outreach |
| GitHub Actions | active CI adapter | deterministic static checks and unit tests | deployment, release, paid/live APIs |
| Claude Code | future compatible adapter | same policy gates through `AGENTS.md` and `CLAUDE.md` | unsupported external claims |
| OpenHands-style runtime | future adapter slot | sandbox-readiness interface and action trajectory import | direct uncontrolled runtime execution |
| MCP tool server | future adapter slot | allowlisted tool descriptors after trust review | prompt injection, tool poisoning, shadowed tool names, rug-pull descriptors |

## Negative Tests Required

The validation package must contain fixtures for:

- low-risk allowed task;
- dangerous denied command;
- medium or high task requiring human review;
- evidence ledger write;
- failure ledger write;
- resume point existence;
- recurring queue generation;
- tool-risk registry existence;
- prompt-injection or tool-poisoning unsafe instruction denial;
- final report withheld until V4 through V7 are locally passing or externally blocked.

