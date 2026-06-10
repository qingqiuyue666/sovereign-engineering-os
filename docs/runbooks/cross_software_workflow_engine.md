# Cross-Software Workflow Engine Runbook

## Command

```bash
python3 seos.py rpc invoke examples/rpc/run_cross_dcc_workflow.json --json
```

## Expected Local Behavior

The command loads `examples/workflows/cross_dcc_workflow_v1.json`, schedules the Houdini, ComfyUI, and DaVinci nodes topologically, and writes physical workflow evidence under:

```text
work/rpc/run_cross_dcc_workflow/
```

The workflow engine writes:

```text
workflow_definition.json
workflow_receipt.json
workflow_state_ledger.jsonl
artifact_manifest.json
failure_bundle.json when terminal failed
rerun_from_failed_node.json when a node fails
<node_id>/node_receipt.json
<node_id>/node_input_payload.json
<node_id>/failure_bundle.json when node failed or dependency-blocked
<node_id>/artifact_routing_receipt.json when upstream ArtifactRefs are routed
```

If Houdini, ComfyUI, or DaVinci Resolve are unavailable, the workflow must not claim success. The unavailable adapter produces its adapter failure bundle; downstream dependent nodes are marked `BLOCKED` with `DEPENDENCY_FAILED`, and the workflow writes a terminal `failure_bundle.json`.

## CI-Safe Path

`tests/tracer_bullet/test_cross_software_workflow_engine_v1.py` uses an injected dispatcher to exercise scheduling, ArtifactRef routing, node receipts, failure propagation, and rerun generation without requiring local DCC applications.
