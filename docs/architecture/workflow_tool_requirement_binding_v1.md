# Workflow Tool Requirement Binding V1

Workflow Tool Requirement Binding V1 maps `WorkflowDryRunPlan` step
requirements to normalized tool manifest summaries. The output is advisory
metadata for later review and risk aggregation.

## Boundary

The binder does not execute tools, call MCP servers, run CLI tools, run plugins,
install dependencies, vendor toolchains, query networks, call providers, open
browsers, launch DCC applications, or launch ComfyUI. GitHub repository, MCP,
DCC, and ComfyUI candidates remain metadata-only.

## Output

`WorkflowToolRequirementBindingReport` contains:

- `binding_id`
- `plan_id`
- `workflow_id`
- `required_tool_bindings`
- `missing_tool_requirements`
- `candidate_tool_matches`
- `incompatible_tools`
- `blockers`
- `warnings`
- `binding_hash`
- `observed_at`

Each `RequiredToolBinding` records the step, required capability, optional
matched manifest fields, match status, and reason.

## Determinism

The `binding_hash` is computed from stable report fields and excludes
`observed_at`. Missing required tools and incompatible matches become blockers.
High-risk matches are marked `REQUIRES_APPROVAL` rather than accepted for
runtime execution.
