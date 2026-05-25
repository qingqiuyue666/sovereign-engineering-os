# Sovereign OS Delivery Backlog V1

## Purpose

This backlog is the repository-owned delivery contract for the Sovereign
Engineering OS PR train. It turns chat-driven milestone intent into bounded,
reviewable, dependency-aware repository work.

This document is governance only. It adds no executable runtime behavior, no
merge automation, and no branch automation.

## Milestone Queue

| Order | Milestone | Branch | PR title | Independence | Dependency state |
| --- | --- | --- | --- | --- | --- |
| A1 | Delivery Backlog V1 | `feat/delivery-backlog-v1` | `feat: add delivery backlog v1` | yes | current document |
| A2 | Milestone Dependency Graph V1 | `feat/milestone-dependency-graph-v1` | `feat: add milestone dependency graph v1` | yes | may merge independently after review |
| A3 | PR Factory And Merge Audit V1 | `feat/pr-factory-merge-audit-v1` | `feat: add pr factory and merge audit v1` | yes | may merge independently after review |
| C1 | Artifact Ledger Viewer V1 | `feat/artifact-ledger-viewer-v1` | `feat: add artifact ledger viewer v1` | yes | read-only evidence surface |
| D1 | Bounded Worker Registry V1 | `feat/bounded-worker-registry-v1` | `feat: add bounded worker registry v1` | yes | provider execution disabled |
| C2 | Operator Dashboard Model V1 | `feat/operator-dashboard-model-v1` | `feat: add operator dashboard model v1` | yes | read-only model/view |
| D2 | Domain Adapter Foundation V1 | `feat/domain-adapter-foundation-v1` | `feat: add domain adapter foundation v1` | yes | no live DCC execution |
| B1 | Real Local Runner Boundary V1 | `feat/real-local-runner-boundary-v1` | `feat: add real local runner boundary v1` | conditional | first bounded execution admission |
| E1 | End-To-End Acceptance Matrix V1 | `feat/e2e-acceptance-matrix-v1` | `feat: add end-to-end acceptance matrix v1` | yes | acceptance/governance only |
| E2 | Mainline Release Readiness Gate V1 | `feat/mainline-release-readiness-gate-v1` | `feat: add mainline release readiness gate v1` | yes | no release automation |
| B2 | Capability Token Lifecycle V1 | `feat/capability-token-lifecycle-v1` | `feat: add capability token lifecycle v1` | no | waits for B1 merge unless contract-only |
| B3 | Local Job Queue V1 | `feat/local-job-queue-v1` | `feat: add local job queue v1` | no | waits for runner/token contracts unless contract-only |
| B4 | Replay Engine V1 | `feat/replay-engine-v1` | `feat: add replay engine v1` | no | waits for runner receipt/replay manifest unless contract-only |
| D3 | ComfyUI Local Adapter Contract V1 | `feat/comfyui-local-adapter-contract-v1` | `feat: add comfyui local adapter contract v1` | conditional | waits for D2 merge unless standalone contract-only |
| D4 | DCC Adapter Foundation V1 | `feat/dcc-adapter-foundation-v1` | `feat: add dcc adapter foundation v1` | conditional | waits for D2 merge unless standalone contract-only |

## Dependency Map

- A1 owns the delivery contract and can merge independently.
- A2 formalizes this queue as a machine-readable graph and can merge
  independently of A1 if it includes its own tests and does not import A1
  content.
- A3 can merge independently as read-only readiness and audit tooling.
- C1 and C2 are read-only evidence/operator visibility surfaces and can merge
  independently when they do not depend on unmerged runner artifacts.
- D1 is a contract/model layer for worker declarations only. It must keep live
  provider calls disabled by default.
- D2 is a contract/model layer for domain adapters only. It must not launch DCC
  tools or mutate source assets.
- B1 is the first controlled real local execution boundary. It admits only
  immutable allowlisted repository validation commands by `command_id`.
- B2 waits for B1 if it needs concrete runner approval or receipt code.
- B3 waits for runner and token contracts if it needs concrete execution
  integration.
- B4 waits for B1 if it needs concrete receipt or replay manifest artifacts.
- D3 and D4 wait for D2 if they would duplicate shared domain-adapter types.
- E1 and E2 are acceptance/release-governance surfaces and do not grant
  execution, merge, release, or promotion authority.

## Branch Naming Rules

- Use one branch per milestone.
- Use the exact `feat/<milestone-slug>-v1` branch in the queue unless a human
  reviewer requests a replacement branch.
- Start from the latest available `main` for independent milestones.
- Do not build on an unmerged PR unless the milestone explicitly allows it.
- Never push directly to `main`.
- Never delete local or remote milestone branches as part of this train.

## PR Title Rules

- Use the exact PR title listed in the milestone queue.
- Keep each PR scope bounded to one milestone.
- Use a non-final title. No PR may claim full system completion.

## Validation Rules

Each PR must include focused tests plus:

- `python3 -m unittest discover tests`
- `make ci`
- `git diff --check`
- `git status --short`
- GitHub Actions CI status and run URL

If validation fails, the PR remains not ready until the failure is fixed and the
validation is rerun. Failing tests must not be skipped or weakened to obtain a
green result.

## Forbidden Surface Rules

No milestone in this backlog grants any of the following unless a future
reviewed milestone explicitly admits a narrower bounded surface:

- arbitrary shell command execution
- `shell=True`
- arbitrary argv or command-line strings
- browser opening
- Playwright live execution
- network access
- live website access
- account login, registration, payment, scraping, bypass, or CAPTCHA workflows
- credential storage
- provider API live calls
- production autonomy
- unbounded daemon, worker loop, or scheduler
- source asset overwrite
- silent failure
- test skipping
- direct push to main
- auto-merge
- branch deletion

## Audit Packet Format

Each PR must record:

- milestone id and name
- base main SHA
- branch
- PR URL
- head SHA
- changed files
- focused tests
- `python3 -m unittest discover tests` result
- `make ci` result
- `git diff --check` result
- GitHub Actions run URL and final status
- dependency notes
- blockers
- forbidden-surface confirmation
- independent mergeability statement

## Merge Readiness Criteria

A PR is ready for human review only when:

- implementation is complete for its milestone
- focused tests pass
- full unittest discovery passes
- `make ci` passes
- `git diff --check` passes
- GitHub Actions CI passes
- the PR body contains the required audit packet
- changed files stay within milestone scope
- no forbidden capability is introduced
- working tree is clean

No auto-merge is permitted. Human reviewers retain merge authority.

## Waiting-For-Merge State Definition

Use `WAITING_FOR_PREVIOUS_PR_MERGE` when a milestone needs code or contracts
from an earlier unmerged PR and cannot be implemented as an independent,
contract-only preparation branch.

Use `WAITING_FOR_DOMAIN_ADAPTER_FOUNDATION_MERGE` when D3 or D4 needs shared D2
types that are not yet merged.

Waiting states are non-failure states. They must be recorded in the audit packet
with the blocking PR and the smallest safe standalone work that was attempted or
identified.

## Non-Authority Statement

This backlog is a planning and governance artifact. It does not execute code,
issue tokens, enqueue jobs, launch adapters, call providers, open browsers,
access networks, merge PRs, push to main, enable auto-merge, or delete branches.
