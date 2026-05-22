# Personal AI Execution OS Product Usage v1

All commands are local-first. They produce JSON on stdout and write a
human-readable summary into the requested output directory. Existing outputs
are not overwritten.

## Office Workflow

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-office-workflow \
  --input-workbook /path/to/input.xlsx \
  --output-dir /path/to/output
```

Performs readonly XLSX inspection and output planning only. Approved output
writing is a separate approval-gated workflow.

## Local Asset Scan

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-scan \
  --input-dir /path/to/assets \
  --output-dir /path/to/output \
  --previous-scan-output-dir /path/to/previous-output \
  --recursive \
  --project-id demo_project
```

Performs a read-only local asset scan. By default it does not scan nested
directories and excludes hidden files; use `--recursive` and `--include-hidden`
only when those paths should be included.

`--previous-scan-output-dir` is optional. When omitted, the launcher writes a
baseline incremental plan with `plan_mode = baseline_no_previous_scan`; all
current scanned assets are classified as `new`, with no missing, changed, or
unchanged assets. When provided, it must point to an existing non-symlink
previous scan output directory that is separate from the current `output_dir`;
the launcher writes `plan_mode = compare_previous_scan` and compares only
generated scan artifacts from the previous output directory.

The scan writes reports only to `output_dir` and fails closed if expected
output files already exist. It does not move, rename, delete, or reorganize
input files, and it is not a media organizer. It does not call model APIs, does
not call the network, and does not launch ComfyUI, Blender, Houdini, After
Effects, DaVinci, or a browser.

On success, the launcher also writes `launcher_summary.md`,
`asset_scan_run_receipt.json`, `local_asset_index.sqlite`,
`local_asset_sqlite_index_manifest.json`, and
`local_asset_sqlite_query_summary.md`. It then writes the incremental planning
artifacts `local_asset_incremental_scan_plan.json`,
`local_asset_incremental_scan_manifest.json`, and
`local_asset_incremental_scan_summary.md`, then binds the scan outputs into the
existing artifact index surface by emitting `artifact_index.json` and
`artifact_index_manifest.json`. The receipt records the completed scan counts,
quarantine count, retry/replay hint, and explicit no-scope-expansion
boundaries.

The SQLite index is a per-scan output artifact only. It stays inside that
scan's `output_dir`, is a metadata/query index over generated scan artifacts,
does not copy raw private asset content, and does not attach to the global OS
engine database. It does not add UI, desktop app behavior, Operator Console
behavior, external runtime activation, or production autonomy.

The incremental scan plan is also non-authoritative and review-only. It does
not execute a cache, does not automatically skip hashing or scanning, does not
mutate inputs, does not move, rename, delete, deduplicate, or organize media
files, does not write to a global database, does not add UI or Operator
Console behavior, does not run real-folder smoke, does not activate external
runtimes, and does not add production autonomy.

On safe failure cases where `output_dir` already exists and is safe to write
into, the launcher writes `asset_scan_failure_bundle.json` and
`asset_scan_failure_summary.md`. If `output_dir` is missing, the launcher does
not create it and returns a structured failure payload without writing a
failure bundle.

## Local Asset Smoke Readiness

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-readiness \
  --candidate-input-dir /path/to/candidate-assets \
  --output-dir /path/to/output \
  --recursive \
  --include-hidden \
  --project-id demo_project
```

Required arguments are `--candidate-input-dir` and `--output-dir`. Optional
arguments are `--recursive`, `--include-hidden`, `--project-id`,
`--max-entries`, `--max-depth`, and `--max-total-bytes`.

This command performs metadata-only readiness inspection before any future
human-approved real-folder smoke run. It inspects path names, path type,
directory structure, file sizes from filesystem metadata, extensions, hidden
path status, symlink status, unsafe directory names, and secret-looking path
names. It does not run a real asset scan, does not hash raw candidate files,
does not read raw candidate file contents, does not copy private content, and
does not mutate, move, rename, or delete input files.

The default safety limits are:

- `--max-entries 50000`
- `--max-depth 20`
- `--max-total-bytes 500000000000`

`output_dir` must already exist, must not be a symlink, and must not overlap
with `candidate_input_dir` in either direction. The candidate input directory
must exist, be a directory, and not be a symlink. If a limit is exceeded, the
command writes readiness artifacts with
`readiness_status = blocked_limit_exceeded` and exits successfully because the
readiness harness safely blocked the future smoke.

The command writes:

- `local_asset_smoke_readiness_report.json`
- `local_asset_smoke_readiness_manifest.json`
- `local_asset_smoke_readiness_summary.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are inside `output_dir` and fail closed if any expected output
already exists. The artifact index remains metadata-only and
non-authoritative.

Readiness statuses are:

- `ready`
- `ready_with_warnings`
- `blocked_safety_risk`
- `blocked_limit_exceeded`
- `failed_preflight`

Readiness decisions are `allow_human_review_for_future_smoke` or
`block_future_smoke_until_review`. Human approval is required before any
future real-folder smoke. This command does not enable real-folder smoke by
itself and does not add UI, Operator Console behavior, watcher/daemon behavior,
network access, model API calls, external runtime activation, global database
state, or production autonomy.

## Model Workflows

Deterministic mock:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-model-fixture \
  --input-artifact-path /path/to/input.json \
  --output-dir /path/to/output \
  --schema-name job_route_classification_v1
```

Live provider dry-run boundary:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-model-provider-dry-run \
  --input-artifact-path /path/to/input.json \
  --output-dir /path/to/output \
  --schema-name job_route_classification_v1 \
  --provider-id openai
```

The dry-run path does not call the provider and does not persist or log API
keys.

## Browser Workflows

Local fixture:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-browser-fixture \
  --fixture-path /path/to/fixture.html \
  --actions-path /path/to/actions.json \
  --output-dir /path/to/output
```

Dry-run real browser boundary:

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-browser-dry-run \
  --actions-path /path/to/actions.json \
  --target-url http://127.0.0.1 \
  --output-dir /path/to/output
```

Only loopback targets and allowlisted actions are accepted. No real browser is
launched.

## ComfyUI Dry Run

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-comfyui-dry-run \
  --workflow-path /path/to/workflow.json \
  --input-asset /path/to/asset.png \
  --output-dir /path/to/output
```

Validates the workflow fixture, hashes input assets, writes preview evidence,
and writes a loopback endpoint dry-run plan. No endpoint call is made.

## Blender Dry Run

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-blender-dry-run \
  --scene-path /path/to/scene.blend \
  --operation-plan-path /path/to/plan.json \
  --output-dir /path/to/output
```

Validates the operation plan, hashes the scene, writes preview evidence, and
writes a dry-run plan. Blender is not launched.

## Creative Handoff

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-creative-handoff \
  --family blender_python_mcp \
  --source-asset /path/to/source.blend \
  --output-dir /path/to/output \
  --package-id review-handoff
```

Supported families are:

- `after_effects_extendscript_uxp_aerender`
- `unreal_python_editor_utility_commandlet`
- `houdini_hom_hython_hda`
- `zbrush_support_handoff`
- `blender_python_mcp`
- `comfyui_workflow_api`

The handoff package contains manifests and human instructions only. It does
not control external creative software.

## Task Graph

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-task-graph \
  --graph-path /path/to/task_graph.json \
  --output-dir /path/to/output
```

Task graphs can run fixture/mock execution or dry-run planning. Real runtime
activation requires separate admission and remains fail-closed by default.

Task graphs can include a controlled local asset scan node:

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
    "previous_scan_output_dir": "/path/to/previous-asset-scan-output",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project"
  }
}
```

The node runs the existing `launch-local-asset-scan` launcher path and keeps
the same operational-control behavior. On success, the node record references
`asset_scan_run_receipt.json`, `artifact_index.json`,
`artifact_index_manifest.json`, `local_asset_index.sqlite`,
`local_asset_sqlite_index_manifest.json`,
`local_asset_sqlite_query_summary.md`,
`local_asset_incremental_scan_plan.json`,
`local_asset_incremental_scan_manifest.json`,
`local_asset_incremental_scan_summary.md`, the incremental plan mode, indexed
artifact counts, quarantine counts, and replay hints. On failure, the graph is
marked failed, writes
`task_graph_failure_bundle.json`, records the failed `node_id` and
`failure_stage`, and preserves any safe local asset scan failure bundle in the
node `output_dir`. Dependent nodes are skipped after a failed dependency.

The task graph replay manifest binds node output references by hash and does
not embed raw file contents or private asset contents. The node still requires
human approval and does not add UI, desktop behavior, global SQLite storage,
Operator Console behavior, real-folder smoke, network access, model API calls,
external runtime activation, input mutation, file movement, file renaming,
duplicate deletion, media organizer behavior, or production autonomy.

Task graphs can also include a local asset smoke readiness node:

```json
{
  "node_id": "preflight_assets",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_readiness",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "candidate_input_dir": "/path/to/candidate-assets",
    "output_dir": "/path/to/smoke-readiness-output",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project",
    "max_entries": 50000,
    "max_depth": 20,
    "max_total_bytes": 500000000000
  }
}
```

The node runs `launch-local-asset-smoke-readiness` and records the readiness
report, manifest, summary, artifact index paths, readiness status, readiness
decision, count estimates, and explicit false values for real scan execution,
file hashing, raw content reads, input mutation, and external runtime
activation. It is still review-only and requires human approval before any
future real-folder smoke.

Task graph execution now also emits `task_graph_artifact_outputs.json` in the
graph `output_dir` after node execution. This manifest is a graph-level,
metadata-only, non-authoritative artifact binding surface. It records
node-produced artifact paths, existence, file sizes, and SHA-256 hashes for
already-produced artifacts, plus the graph-level execution, replay, and failure
manifests when present.

`task_graph_artifact_outputs.json` does not copy raw private asset contents,
does not index raw content, does not mutate inputs, and does not move, rename,
delete, deduplicate, or organize media files. It does not add UI, desktop app
behavior, global SQLite storage, Operator Console behavior, network access,
model API calls, browser runtime activation, or external creative runtime
activation.

## Delivery Validation

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-runtime-delivery-validation \
  --package-dir /path/to/delivery-package \
  --output-dir /path/to/output
```

Validates package manifest hashes, replay metadata, and leakage sentinels.

## Product Health

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-product-health-check \
  --output-dir /path/to/output
```

Reports dependency state, adapter registry health, runtime admission defaults,
deferred runtimes, launcher workflow coverage, docs state, and Personal AI test
metadata.

## Default Runtime Posture

The product-complete system is local-first and fail-closed. Live model calls,
real browser execution, ComfyUI endpoint submission, Blender subprocess
execution, and external creative software control are intentionally not
activated by default.
