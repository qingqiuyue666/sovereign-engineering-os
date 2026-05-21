# Task Graph Artifact Output Binding v1

Repository URL: https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch: `feat/task-graph-artifact-output-binding-v1`

## Objective

Add a graph-level artifact output binding surface for local task graph fixture
execution results. The new surface records node-produced artifacts and
graph-level manifests in a deterministic, hash-bound, metadata-only,
non-authoritative manifest.

## Changed Files

- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `tests/tracer_bullet/test_task_graph_artifact_output_binding.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/task_graph_artifact_output_binding_v1.md`

## Behavior Added

`run_local_task_graph_fixture` now emits
`task_graph_artifact_outputs.json` into the graph `output_dir` after node
execution, graph execution manifest writing, replay manifest writing, and graph
failure bundle writing when applicable.

The execution manifest now records:

- `task_graph_artifact_outputs_path`
- `task_graph_artifact_outputs_written`
- `task_graph_artifact_count`

The replay manifest now records the artifact output path, a non-circular
artifact output binding hash, the binding scope, and
`task_graph_artifact_outputs_manifest_bound: true`.

## Graph-Level Artifact Output Manifest Behavior

The manifest has type `personal_ai_task_graph_artifact_outputs_v1`, authority
`non_authority`, and execution capability `local_task_graph_fixture_only`.
It records the graph id, graph path, graph SHA-256, graph execution mode, graph
success, node order, artifact count, artifacts, node artifact counts, failed
node artifact references, skipped nodes, and explicit no-scope-expansion
flags.

Each artifact entry records deterministic metadata only:

- deterministic `artifact_id`
- `node_id`
- `adapter_id`
- `capability`
- `node_status`
- `artifact_role`
- `artifact_type`
- path and safe relative path when derivable
- SHA-256 and size for existing produced files
- `content_indexed: false`
- `raw_content_copied: false`
- `producer: task_graph_node_output`
- `required_human_approval: true`

## Supported Node Artifact Types

Local asset scan node artifact roles:

- `asset_scan_run_receipt`
- `asset_scan_failure_bundle`
- `asset_scan_failure_summary`
- `artifact_index`
- `artifact_index_manifest`
- `asset_manifest`
- `asset_index`
- `duplicates_report`
- `media_inventory`
- `asset_runtime_audit_log`
- `asset_runtime_validation_report`
- `asset_runtime_quarantine_manifest`
- `launcher_summary`

Runtime delivery validation node artifact roles:

- `runtime_delivery_manifest`
- `runtime_delivery_validation`

Task graph-level artifact roles:

- `task_graph_execution_manifest`
- `task_graph_replay_manifest`
- `task_graph_failure_bundle` when graph execution fails after node execution

## Replay Binding Strategy

Directly hashing `task_graph_artifact_outputs.json` from the replay manifest
would create a circular dependency because the artifact output manifest also
hashes `task_graph_replay_manifest.json`.

This branch uses a deterministic non-circular projection:

- `task_graph_artifact_outputs.json` hashes the final replay manifest file.
- `task_graph_replay_manifest.json` hashes a canonical projection of
  `task_graph_artifact_outputs.json` where only the replay-manifest artifact
  entry's own `exists`, `size_bytes`, and `sha256` fields are normalized.
- The replay manifest records the scope as
  `canonical_manifest_projection_excluding_task_graph_replay_manifest_file_hash`.

This preserves deterministic replay binding without a circular file hash.

## Failure Behavior

The new output is fail-closed on overwrite. A pre-existing
`task_graph_artifact_outputs.json` rejects execution before node artifacts are
written.

If graph validation fails before node execution, existing failure behavior is
preserved: the graph writes the existing task graph failure bundle and does not
produce execution, replay, or artifact output manifests.

If node execution completes with failed nodes, the graph writes the execution
manifest, graph failure bundle, replay manifest, and artifact output manifest.
The artifact output manifest includes failed node artifacts and the graph
failure bundle when those files exist.

Skipped dependency nodes do not fabricate artifacts. They are listed in
`skipped_nodes`.

## Deterministic Ordering Strategy

Node artifact entries are ordered by the graph's topological `node_order`.
Within a node, supported artifact roles are emitted in a fixed role order.
Graph-level artifacts are emitted after node artifacts in fixed manifest order.
Duplicate artifact ids receive a deterministic suffix derived from role and
path.

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

- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`: passed, 8 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`: passed, 7 tests.
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`: passed, 5 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`: passed, 4 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`: passed, 12 tests.
- `python3 -m unittest discover -s tests/schemas -v`: passed, 133 tests.
- `python3 -m unittest discover -s validation/tests/acceptance -v`: passed, 156 tests.
- `python3 -m unittest discover -s tests/tracer_bullet -v`: passed, 6409 tests, 4 skipped.
- Extra check `python3 -m unittest tests.personal_ai.test_task_graph -v`: passed, 7 tests.
- Pre-commit `make ci`: test suites passed; final clean-tree gate failed only because intended branch files were still uncommitted.
- `git diff --check`: passed.
- `git status --short`: showed only intended branch files before commit.

The pre-commit `make ci` failure was the expected clean-tree gate result from
uncommitted branch files, not a test or implementation failure.

## Next Recommended Branch

`feat/local-asset-sqlite-index-v1`

Implementation note: the graph-level metadata binding is now present, so the
next storage-oriented slice can evaluate a local asset SQLite index without
mixing database work into this artifact output binding branch.
