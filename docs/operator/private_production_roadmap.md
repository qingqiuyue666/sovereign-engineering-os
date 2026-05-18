# Private Production Roadmap

## Purpose

This private roadmap prevents further engineering drift after the durable control-plane foundation. The roadmap keeps the repository focused on private operator production assets and deterministic workbenches.

## Current Phase

Private production operating layer for the operator.

## Completed Layers

- Durable operator decision store.
- Durable operator review store.
- Operator recovery.
- Operator audit export.
- Read-only status surface.
- Operator work queue.
- Symbolic runbook shell.
- Provider worker boundary preflight.
- System readiness matrix.
- Code audit workbench.
- Mainline audit report.
- Public-safe asset overview.
- Public-safe asset manifest.

## Frozen Layers

Kernel expansion is frozen after durable/recovery/audit/export/report layers. Governance, security, classification, task manifest, CLI, audit, evidence, provider transport, local runtime, review gate, durable stores, code audit workbench, public asset manifest, health, and CI contracts are protected.

## Next Workbenches

Output workbenches are next.

1. Code Audit Daily Report is first.
2. Creative Asset Factory is second.
3. Macro Signal Research Boundary is research-only.
4. AI Worker Handoff Packet supports future implementation safety.
5. Private Operator State Report keeps operator context current.

## Forbidden Directions

- Automatic financial execution is forbidden.
- No automatic financial execution.
- No provider execution until separately authorized.
- No production autonomy until separately authorized.
- No trading automation.
- No broker/API execution.
- No order routing.
- No full-position execution logic.
- No leverage execution.
- No network execution inside new runtime modules.
- No subprocess execution inside new runtime modules.
- No environment value access.
- No SQLite mutation or introduction.

## Decision Rules

- Prefer output assets over kernel expansion.
- Add deterministic validators only when they directly support an operator output.
- Keep blocked capabilities blocked unless a separate authorized slice adds tests, audit coverage, and human review.
- Never treat blocked as hidden-ready.
- Do not modify root README, Makefile, root integrity manifests, or health gate wiring for private output slices.

## Success Metrics

- Private operator docs exist and are covered by tracer-bullet tests.
- Deterministic report builders reject forbidden material.
- Content hashes exclude observation metadata.
- Required verification commands pass before success is claimed.
- Future AI workers start from a handoff packet instead of guessing context.

## Stop Conditions

- A slice requires live provider execution.
- A slice requires production autonomy.
- A slice requires financial execution or trading automation.
- A slice requires external actions without separate authorization.
- A slice would weaken protected governance, security, audit, evidence, durable store, health, or CI contracts.

## Rollback

Rollback should revert the affected private roadmap files and matching validators together. Rollback must not mutate durable stores or enable blocked capabilities.
