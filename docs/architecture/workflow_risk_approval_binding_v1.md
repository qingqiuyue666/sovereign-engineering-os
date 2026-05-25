# Workflow Risk Approval Binding V1

Workflow Risk Approval Binding V1 aggregates plan-level tool bindings, tool risk
summaries, and approval requirement summaries into workflow-level admission
state. It is the bridge between normalized tool risk and future operator review.

## Boundary

This component does not issue accepted approval tokens. It does not execute
tools, call providers, open browsers, launch DCC applications, launch ComfyUI,
execute MCP tools, execute CLI tools, execute plugins, call networks, or store
credential material.

## Output

`WorkflowRiskApprovalBindingReport` contains:

- `report_id`
- `plan_id`
- `workflow_id`
- `highest_risk`
- `step_risk_summary`
- `approval_requirements`
- `missing_approvals`
- `blocked_steps`
- `production_admission_allowed`
- `dry_run_admission_allowed`
- `blockers`
- `warnings`
- `report_hash`
- `observed_at`

Production admission is always false in this version. Dry-run admission is true
only when there are no missing tool, incompatible tool, missing risk, missing
approval requirement, or credential-touching blockers.

## Determinism

The `report_hash` is computed from stable report fields and excludes
`observed_at`. Approval requirements are summarized as requirements only; they
are never treated as accepted approval decisions.
