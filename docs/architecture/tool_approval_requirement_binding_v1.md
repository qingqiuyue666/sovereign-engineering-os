# Tool Approval Requirement Binding V1

Tool Approval Requirement Binding V1 turns dry-run tool risk reports into
deterministic `ApprovalRequirement` records. It sits after the tool risk
classifier and, when stacked on Tool Manifest Risk Binding V1, can consume the
manifest-bound risk report directly.

## Boundary

This component is metadata-only. It does not grant approval, mint a human
approval token, create an accepted approval decision, execute a tool, call a
network, open a browser, call a provider, touch credentials, launch DCC apps,
launch ComfyUI, execute MCP tools, execute CLI commands, or run plugins.

## Requirement Shape

Each generated record contains:

- `requirement_id`
- `tool_id`
- `manifest_id`
- `source_type`
- `required_action_type`
- `required_scope_id`
- `target_id`
- `risk_class`
- `approval_required`
- `token_required`
- `reason`
- `expires_required`
- `revocation_required`
- `production_admission_allowed`
- `content_hash`
- `observed_at`

The `content_hash` is deterministic and excludes `observed_at`.

## Policy Summary

Read-only tools can avoid explicit approval when they have no private or
filesystem scope. Bounded local-file reads may require a scoped token without an
explicit approval decision. Local file writes, process launch, network access,
browser control, provider APIs, model execution, DCC control, ComfyUI execution,
and plugin execution require human approval. MCP tools require approval unless
they are read-only and explicitly bounded. Credential-touching and other
`HIGH_RISK` cases cannot be implicitly approved and are not eligible for
production admission.

Plugin execution is only represented as an approval requirement and must carry a
sandbox strategy before any future admission path can consider it. This PR does
not implement plugin execution.

## Dependency

This PR is stacked on Tool Manifest Risk Binding V1 so it can accept
`ToolManifestRiskBindingReport` records without duplicating manifest-to-risk
logic. The binding also accepts direct `ToolRiskAssessment` records for tests and
future dry-run callers.
