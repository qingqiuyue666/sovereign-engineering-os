# Claude Project Memory

Claude Code should treat `AGENTS.md` as the repository-level default and this
file as Claude-compatible project memory for the same operating boundary.

## Project Context

This repository is the Sovereign Economic Intelligence System. It layers SEIS
strategy, evidence, trusted delivery, validation, and maturity gates above a
large local-first governance and runtime substrate. Current repository
readiness does not equal real-world validation, paid signal, production
deployment, customer acceptance, or Stage 16 completion.

The AOOS layer under `docs/aoos/` extends this into cross-domain human-AI
organization operations. It is a Stage 4/5 review skeleton until repeated
operating evidence, human acceptance, and real-world source records support
stronger claims.

## Agent Behavior Defaults

- Start from current repository state, not prior chat memory.
- Inspect branch, remote, worktree status, and relevant PR state before edits.
- Create a working branch before any requested commit or PR flow.
- Keep changes scoped to the requested repository layer.
- Preserve known local generated artifacts unless the user explicitly asks to
  change them.
- Prefer narrow documentation, checkpoint, and validation fixes over broad
  rewrites.
- Use `docs/aoos/` only as the cross-domain routing and interface layer; do
  not create duplicate protocol authorities beside `AGENTS.md` and
  `docs/agent-protocols/`.
- Stop at the human review gate after opening a draft PR unless explicitly
  authorized to continue.

## Permission Boundaries

Claude may edit repository files, run local checks, commit scoped changes, push
the working branch, and open draft PRs when the user requests that flow.

Claude must stop before:

- merging PRs
- pushing directly to `main`
- deleting branches or assets
- production deployment
- external outreach
- handling secrets, tokens, accounts, or credentials
- claiming paid, customer, revenue, delivery, or real validation evidence
- changing architecture authority boundaries
- adding dependencies, services, or permissions
- performing irreversible destructive actions

## Stop Conditions

Stop with a blocker report when the repository identity does not match the
requested target, the worktree contains ambiguous unrelated changes, required
checks still fail after one narrow retry, CI remains failing for this branch,
authentication is unavailable, or the next step requires a high-risk human
gate.

## Evidence and Check Expectations

Record command results, changed files, commit hashes, PR URL, CI status when
available, risks, blockers, and the next human approval gate. If evidence is
missing, report the missing evidence instead of upgrading the claim.
