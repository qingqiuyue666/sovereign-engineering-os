# AI Worker Handoff Packet

## Purpose

The AI Worker Handoff Packet is the required private context packet for future AI workers. It prevents a worker from starting with missing repository state, unclear boundaries, or stale merge rules.

## Required First Reading

AI worker must read operator command center first: `docs/operator/operator_command_center.md`.

Then read:

- `docs/operator/current_state.md`
- `docs/operator/operating_rules.md`
- `docs/operator/blocked_capabilities.md`
- `docs/operator/private_operator_state_report.md`
- `docs/operator/code_audit_daily_report_workflow.md`

## Current State Summary

The current repository has a durable local control plane and public-safe report assets. The next layer is private production support for the operator through deterministic reports, handoff packets, planning documents, research boundaries, and roadmaps.

## Allowed Work

- Private operator reports.
- Deterministic Markdown renderers.
- Caller-provided material validators.
- Code Audit Daily Report workflow.
- Creative Asset Factory planning.
- Macro signal research boundary.
- Private production roadmap.

## Forbidden Work

- Provider execution is forbidden.
- Production autonomy is forbidden.
- Financial execution is forbidden.
- Trading automation is forbidden.
- Network execution is forbidden in new runtime modules.
- Subprocess execution is forbidden in new runtime modules.
- Environment value access is forbidden.
- SQLite mutation and new SQLite introduction are forbidden.
- Root README edits are forbidden in this slice.
- No Makefile/root integrity/health wiring edits.
- Do not edit Makefile, root integrity manifests, or health gate wiring.

## Required Verification

- Run the priority-specific `python3 -m unittest ... -v` command.
- Run full tracer-bullet discovery before final success is claimed.
- Run schema discovery before final success is claimed.
- Run acceptance discovery before final success is claimed.
- Run `make ci`.
- Run `git diff --check`.
- Run `git status --short`.

## Merge Rules

- Start from latest `main`.
- Use a dedicated branch.
- Keep priority slices reviewable.
- Do not rename public APIs.
- Do not weaken governance, security, classification, task manifest, CLI, audit, evidence, provider transport, local runtime, review gate, durable stores, code audit workbench, public asset manifest, health, or CI contracts.
- Merge only after tests actually pass.

## Rollback Rules

- Revert the completed priority commit if validation fails.
- Revert private docs and matching validators together.
- Do not mutate durable stores as part of rollback.
- Do not use rollback to enable blocked capabilities.

## Blocked Capabilities

- Real provider execution remains blocked.
- Production autonomy remains blocked.
- External actions remain blocked.
- Financial execution remains blocked.
- Trading automation remains blocked.
- Blocked does not mean hidden-ready.
- Blocked does not mean enabled by operator preference.
