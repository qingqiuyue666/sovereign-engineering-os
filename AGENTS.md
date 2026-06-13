# Agent Instructions

Default instructions for Codex, Claude, GitHub agents, and other repository
agents working in this repository.

## Current State First

Before editing, inspect the current branch, remote, worktree status, open PR
state when relevant, and the current repository status documents. Do not assume
older chat context is current.

## Continuous Stage-Gated Execution

Execute safe repository work continuously until the requested scope is complete
or a stop condition is reached. Move through explicit gates: intake, current
state, scope, implementation, checks, commit or PR, and human review.

## Low-Risk Auto-Execute Authorization

Agents may auto-execute low-risk repository tasks such as documentation,
checklists, checkpoint reports, narrow reference updates, local validation
commands, and narrow safe fixes for local validation failures.

## High-Risk Human Approval Gates

Stop for human approval before merges, direct pushes to `main`, branch or asset
deletion, production deployment, real-world outreach, secret or credential
handling, paid/customer/revenue/delivery evidence claims, architecture boundary
changes, new dependencies or services, new permissions, or destructive actions.

## Evidence Requirements

Every material claim must point to evidence: file changes, command output, git
diff, commit, CI or GitHub checks, or real-world source records where external
claims are involved.

## No-Fake-Completion Policy

Do not claim real-world validation, paid signal, customer acceptance, delivery
completion, production deployment, commercial validation, or Stage maturity
without matching evidence records.

## Output Requirements

Final agent reports must include final state, changed files, commits, checks,
CI status when available, risks, blockers, evidence, and the next human gate.

## Detailed Protocols

Detailed rules live under `docs/agent-protocols/`. Start with:

- `docs/agent-protocols/continuous-stage-gated-execution.md`
- `docs/agent-protocols/high-risk-human-gates.md`
- `docs/agent-protocols/evidence-and-no-fake-completion.md`
- `docs/agent-protocols/failure-handling-if-then.md`

Cross-domain AOOS module routing, domain packs, Stage 5 interfaces, and
templates live under `docs/aoos/` and `templates/aoos/`. Use them after the
agent execution protocol has established current state, authority, and evidence
boundaries.
