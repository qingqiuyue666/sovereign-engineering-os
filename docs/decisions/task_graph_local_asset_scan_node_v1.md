# Task Graph Local Asset Scan Node v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch: `feat/task-graph-local-asset-scan-node-v1`

## Objective

Promote the already-merged `launch-local-asset-scan` workflow into a
first-class task graph node while preserving the existing controlled launcher
path, operational receipt, failure bundle, artifact index binding, replay
hints, human-review requirement, and no-scope-expansion boundaries.

## Changed Files

- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `tests/tracer_bullet/test_task_graph_local_asset_scan_node.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/task_graph_local_asset_scan_node_v1.md`

## Behavior Added

Task graphs now admit and execute a controlled local asset scan node with:

- adapter route: `local_asset_runtime`
- capability: `launch_local_asset_scan`
- graph execution mode: `fixture_execution`
- node execution mode: `fixture`
- required human approval checkpoint
- no real runtime activation authority

The graph delegates execution to `run_local_asset_scan_launcher` and does not
duplicate local asset runtime logic.

## Node Schema

```json
{
  "node_id": "scan_assets",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_scan",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "input_dir": "/path/to/assets",
    "output_dir": "/path/to/asset-scan-output",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project"
  }
}
```

## Success Behavior

On success, the node is recorded with `status: completed`,
`local_asset_scan_complete: true`, `output_dir`,
`asset_scan_run_receipt_path`, `artifact_index_path`,
`artifact_index_manifest_path`, `indexed_artifacts`, `quarantined_paths`,
`safe_to_retry`, `replay_hint`, and explicit false values for input mutation,
file movement, file rename, file delete, media organizer behavior, network
access, model API calls, UI addition, browser runtime, creative runtime, and
external runtime invocation.

Soft quarantine remains a successful scan. The receipt continues to record
`scan_completed_with_quarantine: true` and recommends quarantine review.

## Failure Behavior

If the launcher reports failure, the node is recorded with `status: failed`.
The graph result is `success: false`, and `task_graph_failure_bundle.json`
records the failed `node_id`, `failure_stage`, safe retry state, replay hint,
and any local asset scan failure bundle or summary references. The local asset
scan failure bundle remains in the node `output_dir` when the launcher deems it
safe to write.

Preflight output collisions fail before local asset runtime execution and keep
input files untouched.

## Dependency Behavior

Task graph topological ordering remains deterministic. If a dependency fails,
dependent nodes are recorded as `status: skipped`, include their blocked
dependency IDs, and do not execute.

## Replay Binding

The task graph replay manifest now includes:

- `node_output_refs_sha256`
- `local_asset_scan_receipts_sha256`
- `local_asset_scan_failure_refs_sha256`

These fields hash deterministic references and file digests. They do not embed
raw file contents or raw private asset contents.

## Artifact Relationship

The local asset scan node preserves the existing artifact index relationship by
referencing the launcher-produced `artifact_index.json` and
`artifact_index_manifest.json`. The task graph records those references at node
level and binds them through replay hash fields.

## Explicit Non-Goals Preserved

- No UI.
- No desktop app behavior.
- No SQLite.
- No Operator Console.
- No real-folder smoke.
- No network access.
- No model API calls.
- No external runtime activation.
- No browser runtime activation.
- No ComfyUI, Blender, Houdini, After Effects, or DaVinci runtime activation.
- No HFX change.
- No input mutation.
- No file movement.
- No file rename.
- No file deletion.
- No duplicate deletion.
- No media organizer behavior.
- No production autonomy.

## Validation Commands Run

- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`: passed, 7 tests.
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`: passed, 5 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`: passed, 4 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`: passed, 12 tests.
- `python3 -m unittest discover -s tests/schemas -v`: passed, 133 tests.
- `python3 -m unittest discover -s validation/tests/acceptance -v`: passed, 156 tests.
- `python3 -m unittest discover -s tests/tracer_bullet -v`: passed, 6401 tests, 4 skipped.
- `make ci`: test suites passed; final clean-tree gate failed before commit because the intended branch files were still uncommitted.
- `git diff --check`: passed.
- `git status --short`: showed only intended branch files before commit.

## Next Recommended Branch

`feat/task-graph-artifact-output-binding-v1`

Implementation finding: local asset scan now has node-specific receipt and
artifact references, so the next useful slice is to generalize artifact output
binding across task graph node types rather than adding SQLite storage.
