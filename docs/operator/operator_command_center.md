# Private Operator Command Center

## Operator Summary

The repository is now a strong local-first control plane with durable decision/review stores, recovery, audit export, read-only status, an operator work queue, a symbolic runbook shell, provider worker preflight, a system readiness matrix, a code audit workbench, and public-safe report assets. The next operating mode is private production support for the operator, centered on deterministic output workbenches and reports.

This command center is private operator documentation. It is not a public launch page, not a marketing asset, and not an autonomy switch.

## Current System State

- Source of truth main commit: `2d25ab23f371a9539855d8271e5743f3e83afa99`.
- Durable operator decision store is present.
- Durable operator review store is present.
- Operator recovery is present.
- Operator audit export is present.
- Read-only status surface is present.
- Operator work queue is present.
- Symbolic runbook shell is present.
- Provider worker boundary preflight is present.
- System readiness matrix is present.
- Code audit workbench is present.
- Mainline audit report, public-safe asset overview, public-safe asset manifest, and reports index are present.
- Full tracer-bullet, schemas, acceptance, and `make ci` were reported green on current main before this private production slice.

## What Is Frozen

- Abstract kernel expansion is frozen unless it is strictly needed to produce operator output assets.
- Governance, security, classification, task manifest, CLI, audit, evidence, provider transport, local runtime, review gate, durable stores, code audit workbench, public asset manifest, health, and CI contracts are frozen except for separately authorized maintenance.
- Root README, Makefile, root integrity manifests, and health gate wiring are frozen for this slice.

## What Is Allowed Next

- Private operator command center documentation.
- Private operator state report.
- Code Audit Daily Report workflow.
- AI worker handoff packet.
- Creative Asset Factory planning layer.
- Macro signal research boundary.
- Private production roadmap.
- Deterministic validators and Markdown output assets that fail closed.

Output assets have priority over kernel expansion.

## What Is Forbidden

- Real provider execution remains blocked.
- Production autonomy remains blocked.
- External actions remain blocked.
- Financial execution is out of scope.
- Trading automation is blocked.
- Network execution is forbidden inside new runtime modules.
- Process launching is forbidden inside new runtime modules.
- Environment value access and secret handling are forbidden.
- SQLite mutation and new SQLite introduction are forbidden.
- Raw prompts, raw provider responses, raw traceback dumps, and raw exception dumps must not be persisted.

## Mandatory Verification Commands

- `python3 -m unittest tests.tracer_bullet.test_operator_command_center_manifest -v`
- `python3 -m unittest tests.tracer_bullet.test_operator_state_report -v`
- `python3 -m unittest tests.tracer_bullet.test_code_audit_daily_report -v`
- `python3 -m unittest tests.tracer_bullet.test_ai_worker_handoff_packet -v`
- `python3 -m unittest tests.tracer_bullet.test_creative_asset_factory_plan -v`
- `python3 -m unittest tests.tracer_bullet.test_macro_signal_research_boundary -v`
- `python3 -m unittest tests.tracer_bullet.test_private_production_roadmap -v`
- `python3 -m unittest tests.tracer_bullet.test_public_asset_manifest -v`
- `python3 -m unittest tests.tracer_bullet.test_code_audit_workbench -v`
- `python3 -m unittest tests.tracer_bullet.test_operator_audit_export -v`
- `python3 -m unittest tests.tracer_bullet.test_operator_recovery -v`
- `python3 -m unittest tests.tracer_bullet.test_system_readiness_matrix -v`
- `python3 -m unittest discover -s tests/tracer_bullet -v`
- `python3 -m unittest discover -s tests/schemas -v`
- `python3 -m unittest discover -s validation/tests/acceptance -v`
- `make ci`
- `git diff --check`
- `git status --short`

## AI Worker Handoff Rules

- Read this command center first.
- Read `docs/operator/current_state.md` second.
- Read `docs/operator/operating_rules.md` and `docs/operator/blocked_capabilities.md` before changing files.
- Treat all material as caller-provided unless verified by explicit command output in the current worktree.
- Do not infer hidden readiness from blocked capability names.
- Do not persist raw prompts, raw provider responses, raw exception dumps, or raw traceback dumps.
- Prefer deterministic validators and private reports over runtime expansion.

## Merge Rules

- Work from latest `main`.
- Use a dedicated branch.
- Keep the slice narrow and reviewable.
- Preserve root integrity, Makefile, root README, health gate wiring, and existing public APIs.
- Merge only after required tests have actually passed.
- Do not claim green without command results.

## Rollback Rules

- Revert the completed slice commit if validation fails after merge.
- Roll back generated private docs and their matching deterministic validators together.
- Do not mutate durable stores as part of rollback.
- Do not use rollback to unblock provider execution, external actions, production autonomy, or trading automation.

## Next Production Priorities

1. Private Operator Command Center.
2. Private Operator State Report.
3. Code Audit Daily Report Workflow.
4. AI Worker Handoff Packet.
5. Creative Asset Factory Planning Layer.
6. Macro Signal Research Boundary.
7. Private Production Roadmap.
