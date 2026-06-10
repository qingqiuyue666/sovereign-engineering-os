# Workflow Dry-Run Plan V1

Workflow Dry-Run Plan V1 converts structured task intent plus a workflow graph
descriptor into a deterministic planning record. It sits after the
Task-to-Workflow Router Skeleton and before tool binding, risk binding, and
operator snapshot aggregation.

## Boundary

The component is descriptor-only. It does not execute workflow nodes, invoke
tools, contact providers, open browsers, launch DCC applications, launch
ComfyUI, execute MCP tools, execute CLI tools, execute plugins, call networks,
mutate files, or mutate assets.

## Output

`WorkflowDryRunPlan` contains:

- `plan_id`
- `task_id`
- `workflow_id`
- `workflow_graph_hash`
- `plan_steps`
- `required_tools`
- `required_assets`
- `approval_requirements`
- `evidence_requirements`
- `rollback_plan`
- `evaluation_plan`
- `blockers`
- `warnings`
- `dry_run_only`
- `executable`
- `content_hash`
- `generated_at`

Each `PlanStep` is fixed at `status = PLANNED` and `executable = false`.

## Determinism

The `content_hash` is computed from stable plan fields and excludes
`generated_at`. The `plan_id` is derived from that hash, so repeated planning
over the same intent and graph produces the same identity even when timestamps
change.

## Fail-Closed Rules

The planner rejects unsupported domains, missing rollback plans, missing
evaluation plans, and forbidden execution surfaces such as raw command fields,
command-line fields, argv fields, executable paths, cwd/env/path overrides, and
timeouts. High-risk workflow nodes add approval requirement placeholders rather
than approval tokens.
