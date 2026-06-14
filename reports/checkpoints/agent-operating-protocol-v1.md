# Agent Operating Protocol v1 Checkpoint

## Purpose

Record the repository-level AI-agent operating protocol layer added in this
branch and the remaining human gate.

## What Was Added

- `AGENTS.md`
- `CLAUDE.md`
- `docs/agent-protocols/continuous-stage-gated-execution.md`
- `docs/agent-protocols/high-risk-human-gates.md`
- `docs/agent-protocols/evidence-and-no-fake-completion.md`
- `docs/agent-protocols/failure-handling-if-then.md`
- `docs/agent-protocols/pr-stack-migration-playbook.md`
- `docs/agent-protocols/tool-selection-gate.md`
- `docs/agent-protocols/memory-governance.md`
- `playbooks/README.md`
- `playbooks/pr-stack-migration-v1.md`
- `checklists/agent-final-report-checklist.md`

## Why It Was Added

The repository already contains strategy, validation, delivery, evidence, and
human-action gates. This checkpoint records the operating protocol that tells
AI agents how to work inside those gates without creating new strategy,
performing real-world validation, or faking evidence.

## Scope Boundary

This is protocol institutionalization only. It does not add a new SEIS strategy
layer, expand business scope, perform outreach, deploy software, handle
secrets, claim customer validation, claim paid signal, or claim delivery
completion.

## Checks Run

Local verification run after adding the protocol layer:

- `python3 scripts/identity_boundary_check_v1.py` passed.
- `python3 scripts/observation_check_v1.py` passed.
- `python3 scripts/creative_total_check_v3.py` passed.
- `python3 scripts/secret_context_safety_check_v1.py` passed.
- `git diff --check` passed.
- `git diff --cached --check` passed with no staged diff at the time of the
  initial verification run.

CI / GitHub checks are pending until the branch is pushed and the draft PR is
opened.

## Remaining Human Gate

Human review is required before merge. The agent must stop at the draft PR
review gate.
