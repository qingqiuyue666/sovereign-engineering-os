# Memory Governance

## Purpose

Keep agent memory useful without making chat history the system of record.

## Memory Layers

## Short High-Level Memory

Use short memory for stable preferences, repository identity, known pitfalls,
and recurring workflow summaries.

## Detailed Repository Protocol

Keep detailed rules in repository files such as `AGENTS.md`,
`docs/agent-protocols/`, `playbooks/`, and `checklists/`. Repository files are
reviewable, versioned, and auditable.

## Playbooks for Repeated Workflows

Use playbooks for workflows that recur, such as PR stack migration, final
reporting, CI failure handling, and evidence boundary enforcement.

## Scripts and CI for Enforceable Rules

Where a rule can be checked mechanically, prefer scripts and CI over memory.
Memory can remind agents to run checks, but it should not be the only control.

## Do Not Rely Only on Chat Memory

Chat memory may be stale, partial, or unavailable. Agents must inspect current
repository files, branch state, and PR state before acting.

## Prune Stale or Conflicting Rules

Periodically remove or revise stale memory and conflicting protocol text. When
rules disagree, prefer current repository files and explicit user instructions.
