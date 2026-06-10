# Operator Task Snapshot Binding V1

Operator Task Snapshot Binding V1 combines dry-run planning, tool binding,
risk approval binding, asset summaries, journal summaries, and operator state
metadata into one deterministic task-level snapshot for future console use.

## Boundary

This PR does not implement UI. The snapshot is read-only and advisory. It does
not authorize execution, execute tools, execute MCP tools, execute CLI tools,
execute plugins, call networks, open browsers, call providers, launch DCC
applications, launch ComfyUI, mutate files, mutate assets, store raw payloads,
or store credential material.

## Output

`OperatorTaskSnapshot` contains:

- `snapshot_id`
- `task_id`
- `workflow_id`
- `generated_at`
- `dry_run_plan_summary`
- `tool_binding_summary`
- `risk_approval_summary`
- `asset_summary`
- `journal_summary`
- `approval_summary`
- `blockers`
- `warnings`
- `next_actions`
- `operator_state`
- `snapshot_hash`

## Determinism

The `snapshot_hash` is computed from stable summaries and excludes
`generated_at`. The `snapshot_id` is derived from that hash.

## Next Actions

Allowed next actions are review and repair intents only. Forbidden execution
actions, tool launches, provider calls, dependency installs, network access,
file deletion, asset mutation, MCP execution, CLI execution, and plugin
execution are rejected.
