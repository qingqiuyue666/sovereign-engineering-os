# Runtime Snapshot Aggregator V1

Runtime Snapshot Aggregator V1 produces a deterministic dry-run read model for
future Operator Console consumption. It aggregates summaries that already exist
in the train, including journal event summaries, asset summaries, workflow graph
descriptors, normalized tool manifests, tool risk assessments, approval
requirements, approval token summaries, and the operator console state model
reference.

## Boundary

This component is read-only. It does not implement UI, mutate journals, execute
tools, execute MCP tools, execute CLI commands, execute plugins, call networks,
open browsers, call providers, touch credentials, launch DCC apps, launch
ComfyUI, store raw payloads, or enable production autonomy.

## Snapshot Shape

`RuntimeSnapshot` contains:

- `snapshot_id`
- `generated_at`
- `system_state`
- `journal_summary`
- `asset_summary`
- `workflow_summary`
- `tool_summary`
- `risk_summary`
- `approval_summary`
- `queue_summary`
- `next_actions`
- `blockers`
- `warnings`
- `snapshot_hash`

The `snapshot_hash` is deterministic and excludes `generated_at`. The
`snapshot_id` is derived from that stable hash.

## Advisory Next Actions

Allowed next actions are limited to:

- `review_risk_assessment`
- `issue_scoped_approval`
- `run_dry_run_plan`
- `inspect_asset_inventory`
- `inspect_quarantine`
- `fix_manifest`
- `reject_tool_candidate`

Forbidden next actions are rejected, including raw command execution, DCC
launches, ComfyUI runs, provider calls, browser opens, network access, file
deletion, and asset mutation.

## Operator Console Consumption

This PR does not build the Operator Console UI. It only emits a structured,
digest-oriented snapshot shape that a future read-only console can consume. The
operator console state model reference is summarized as metadata only, including
model version, panel count, UI runtime presence, and production autonomy status.
