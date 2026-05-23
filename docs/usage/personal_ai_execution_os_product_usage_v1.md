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

## Local Asset Human-Approved Smoke Run

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-human-smoke-run \
  --candidate-input-dir /path/to/candidate-assets \
  --output-dir /path/to/human-smoke-output-root \
  --readiness-report /path/to/readiness/local_asset_smoke_readiness_report.json \
  --human-approval-id reviewer-ticket-123 \
  --human-approval-phrase I_APPROVE_LOCAL_ASSET_SMOKE_RUN \
  --recursive \
  --project-id demo_project \
  --max-smoke-files 25 \
  --max-smoke-bytes 100000000 \
  --max-smoke-depth 4
```

Required arguments are `--candidate-input-dir`, `--output-dir`,
`--readiness-report`, `--human-approval-id`, and
`--human-approval-phrase`. The approval phrase must match exactly:
`I_APPROVE_LOCAL_ASSET_SMOKE_RUN`. The phrase plaintext is never persisted;
only its SHA-256 hash is written to the approval artifact.

Optional arguments are `--recursive`, `--include-hidden`, `--project-id`,
`--max-smoke-files`, `--max-smoke-bytes`, `--max-smoke-depth`, and
`--previous-scan-output-dir`. Default smoke limits are:

- `--max-smoke-files 100`
- `--max-smoke-bytes 2000000000`
- `--max-smoke-depth 8`

The command consumes a previous
`local_asset_smoke_readiness_report.json`. The readiness report must come from
the metadata-only readiness harness, must require human approval, must have
`readiness_decision = allow_human_review_for_future_smoke`, and must have
`readiness_status = ready` or `ready_with_warnings`. It rejects
`blocked_safety_risk`, `blocked_limit_exceeded`, and `failed_preflight`.

The smoke run root `output_dir` must already exist and must not be a symlink.
The candidate input directory and readiness report must exist and must not be
symlinks. Candidate path, `recursive`, and `include_hidden` must match the
readiness report; `project_id` must match when both are present. The smoke
root and candidate directory must not overlap in either direction.

This command uses a subdirectory layout:

- `output_dir/control/local_asset_human_smoke_approval.json`
- `output_dir/control/local_asset_human_smoke_admission_receipt.json`
- `output_dir/local_asset_human_smoke_run_summary.md`
- `output_dir/scan/` for the normal `launch-local-asset-scan` output stack
- `output_dir/artifact_index.json`
- `output_dir/artifact_index_manifest.json`

Before invoking the existing scan launcher, it performs a metadata-only
bounded precheck and fails closed if the candidate would exceed
`max_smoke_files`, `max_smoke_bytes`, or `max_smoke_depth`. It also rejects
smoke limits that exceed the corresponding readiness report limits where
available. It does not silently truncate, sample, or partially scan.

The actual scan is delegated to the existing local asset scan launcher using
the deterministic `output_dir/scan/` subdirectory. The scan remains read-only
and writes the normal scan artifacts there, including `asset_manifest.json`,
`asset_index.json`, `duplicates_report.json`, `media_inventory.md`,
`asset_runtime_audit_log.jsonl`, validation and quarantine reports,
`launcher_summary.md`, `asset_scan_run_receipt.json`,
`local_asset_index.sqlite`, SQLite query/index manifests, incremental scan
plan artifacts, and the scan-level `artifact_index.json` and
`artifact_index_manifest.json`.

The root artifact index is an explicit control-and-scan reference index. It
does not recursively crawl private assets, does not copy raw content, and
includes the approval, admission, smoke summary, scan artifact index, scan
artifact index manifest, and key scan output paths when present.

This is human-approved bounded smoke only. It does not add automatic approval,
production scanning, watcher/daemon behavior, UI, desktop app behavior,
Operator Console behavior, global database state, input mutation, file
movement, file renaming, file deletion, duplicate deletion, media organizer
behavior, network access, model API calls, external runtime activation,
browser runtime activation, ComfyUI/Blender/Houdini/After Effects/DaVinci
activation, HFX changes, or production autonomy.

## Local Asset Smoke Review Packet

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-review-packet \
  --smoke-output-dir /path/to/human-smoke-output-root \
  --output-dir /path/to/review-packet-output \
  --project-id demo_project
```

Required arguments are `--smoke-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The review `output_dir` is not created
automatically. It must not equal `smoke_output_dir`, must not be inside it,
and must not contain it. If the generated admission receipt safely exposes a
`candidate_input_dir`, the review `output_dir` must also not be inside that
candidate input directory.

This command consumes generated human-approved smoke-run artifacts only. It
reads the smoke root control artifacts, smoke summary, root artifact index,
scan artifact index, scan reports, generated SQLite manifest/query summary,
incremental plan artifacts, and generated failure artifacts when present. It
may hash generated artifact files. It does not run a scan, does not re-run
readiness, does not hash candidate files, does not read raw candidate file
contents, does not copy raw private content, does not mutate inputs, and does
not mutate the smoke output root.

The command writes these review artifacts into `output_dir`:

- `local_asset_smoke_review_packet.json`
- `local_asset_smoke_review_packet_manifest.json`
- `local_asset_smoke_review_summary.md`
- `local_asset_smoke_human_decision_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed if any of those files already exist.
The review packet summarizes approval, admission, readiness, scan counts,
duplicate groups, quarantine counts and top reasons, generated SQLite manifest
row counts, incremental plan counts, failure state, warning state, and the
explicit no-scope-expansion boundaries.

Review packet statuses are:

- `review_ready`
- `review_ready_with_warnings`
- `review_blocked_missing_required_artifacts`
- `review_blocked_failed_smoke_run`
- `review_blocked_untrusted_artifacts`

Recommended human decisions are:

- `approve_next_bounded_smoke_iteration`
- `inspect_quarantine_before_next_run`
- `inspect_duplicates_before_next_run`
- `inspect_incremental_changes_before_next_run`
- `reject_and_repair_smoke_run`

The checklist is for human review only. It does not suggest deleting, moving,
renaming, or deduplicating files, does not grant automatic approval, does not
enable production scanning, does not add UI, desktop app behavior, Operator
Console behavior, watcher/daemon behavior, network access, model API calls,
external creative runtime activation, HFX changes, global database state, or
production autonomy.

## Local Asset Smoke Promotion Gate

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-promotion-gate \
  --review-output-dir /path/to/review-packet-output \
  --output-dir /path/to/promotion-gate-output \
  --project-id demo_project
```

Required arguments are `--review-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The promotion `output_dir` is not
created automatically. It must not equal `review_output_dir`, must not be
inside it, and must not contain it. If the generated review packet safely
exposes a `smoke_output_dir` or `candidate_input_dir`, the promotion
`output_dir` must not be inside either upstream directory.

This command consumes generated review packet artifacts only:

- `local_asset_smoke_review_packet.json`
- `local_asset_smoke_review_packet_manifest.json`
- `local_asset_smoke_review_summary.md` when present
- `local_asset_smoke_human_decision_checklist.md` when present
- `artifact_index.json`
- `artifact_index_manifest.json`

It may hash those generated review artifacts. It does not scan, run
readiness, run human smoke, hash candidate files, read raw candidate file
contents, copy raw private content, mutate review packet outputs, mutate smoke
outputs, mutate inputs, move files, rename files, delete files, delete
duplicates, perform media organizer behavior, use network access, call model
APIs, invoke external runtimes, or approve production use.

The command writes these promotion gate artifacts into `output_dir`:

- `local_asset_smoke_promotion_decision.json`
- `local_asset_smoke_promotion_gate_manifest.json`
- `local_asset_smoke_promotion_summary.md`
- `local_asset_smoke_promotion_human_signoff_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed if any of those files already exist.
If required review artifacts are missing and the promotion output directory is
safe, the gate writes a blocked decision rather than pretending promotion is
allowed.

Promotion gate status values are:

- `promotion_candidate`
- `blocked_missing_review_artifacts`
- `blocked_untrusted_review_packet`
- `blocked_failed_smoke_run`
- `blocked_quarantine`
- `blocked_duplicates`
- `blocked_incremental_changes`
- `blocked_warnings`
- `blocked_unknown`

Promotion decision values are:

- `allow_next_bounded_smoke_iteration`
- `block_until_human_inspects_quarantine`
- `block_until_human_inspects_duplicates`
- `block_until_human_inspects_incremental_changes`
- `block_until_smoke_run_repaired`
- `block_until_review_packet_repaired`

The gate only allows the next bounded smoke iteration when the review packet
is clean: `review_packet_status=review_ready`, recommended decision is
`approve_next_bounded_smoke_iteration`, smoke and scan are complete,
production scan is false, input mutation is false, duplicate deletion is
false, quarantine count is zero, duplicate group count is zero, suspicious
incremental changes are zero, and no blocking warnings are present. It never
grants production promotion and never approves production scanning.

## Local Asset Bounded Smoke Iteration

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-bounded-smoke-iteration \
  --promotion-output-dir /path/to/promotion-gate-output \
  --candidate-input-dir /path/to/candidate-assets \
  --readiness-report /path/to/readiness/local_asset_smoke_readiness_report.json \
  --output-dir /path/to/iteration-output \
  --human-signoff-id reviewer-ticket-456 \
  --human-signoff-phrase I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION \
  --recursive \
  --project-id demo_project \
  --max-smoke-files 100 \
  --max-smoke-bytes 1073741824 \
  --max-smoke-depth 12
```

Required arguments are `--promotion-output-dir`, `--candidate-input-dir`,
`--readiness-report`, `--output-dir`, `--human-signoff-id`, and
`--human-signoff-phrase`. The required signoff phrase is exactly
`I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION`; the provided phrase plaintext is not
persisted. Optional arguments are `--project-id`,
`--previous-scan-output-dir`, `--recursive`, `--include-hidden`,
`--max-smoke-files`, `--max-smoke-bytes`, and `--max-smoke-depth`.

Default bounded iteration limits are:

- `--max-smoke-files 100`
- `--max-smoke-bytes 1073741824`
- `--max-smoke-depth 12`

The command consumes generated promotion gate artifacts only:

- `local_asset_smoke_promotion_decision.json`
- `local_asset_smoke_promotion_gate_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

It admits the next bounded smoke iteration only when the promotion decision is
`promotion_gate_status=promotion_candidate`,
`promotion_decision=allow_next_bounded_smoke_iteration`,
`next_bounded_smoke_iteration_allowed=true`,
`production_promotion_granted=false`, `production_scan_approved=false`, and
the review recommendation was `approve_next_bounded_smoke_iteration` with no
promotion blockers. It also verifies promotion manifest hashes and the
promotion artifact index manifest hash.

`output_dir` must already exist, must be a real directory, must not be a
symlink, and is never created automatically. It must not equal or overlap
`promotion_output_dir` or `candidate_input_dir` in either direction, and must
not be inside the review, smoke, or previous candidate directories when those
paths are discoverable from the promotion decision.

On valid promotion gate review and valid explicit human signoff, this command
creates only `output_dir/control/` and `output_dir/smoke/`, then delegates to
the existing `launch-local-asset-human-smoke-run` controls in the `smoke/`
subdirectory. The delegated smoke run still requires readiness, uses the
existing human-approved smoke launcher path, preserves bounded max files,
bytes, and depth, and writes the normal human smoke output stack under
`output_dir/smoke/`.

The iteration writes:

- `control/local_asset_bounded_smoke_iteration_signoff.json`
- `control/local_asset_bounded_smoke_iteration_admission.json`
- `local_asset_bounded_smoke_iteration_result.json`
- `local_asset_bounded_smoke_iteration_manifest.json`
- `local_asset_bounded_smoke_iteration_summary.md`
- `local_asset_bounded_smoke_iteration_human_review_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`
- `smoke/` delegated human smoke outputs when admitted

All writes are exclusive and fail closed if expected iteration outputs already
exist. If the promotion gate is blocked or the signoff phrase is invalid, the
command writes blocked iteration artifacts when the output directory is safe,
does not create `smoke/`, and does not invoke the smoke launcher.

This command only enables another bounded smoke iteration after promotion-gate
review and explicit human signoff. It does not approve production scan, does
not grant production promotion, does not add automatic approval, does not add
watcher/daemon behavior, does not add UI or Operator Console behavior, does
not mutate inputs or upstream outputs, does not move, rename, delete, or
deduplicate files, does not perform media organizer behavior, does not use
network access, does not call model APIs, and does not invoke external
creative runtimes.

## Local Asset Smoke Iteration Review Packet

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-smoke-iteration-review-packet \
  --iteration-output-dir /path/to/iteration-output \
  --output-dir /path/to/iteration-review-output \
  --project-id demo_project
```

Required arguments are `--iteration-output-dir` and `--output-dir`.
`--project-id` is optional. Both directories must already exist, must be real
directories, and must not be symlinks. The review `output_dir` is not created
automatically. It must not equal `iteration_output_dir`, must not be inside
it, and must not contain it. If generated iteration artifacts safely expose
the candidate input directory, promotion output directory, or delegated smoke
output directory, the review `output_dir` must not be inside any of them.

This command consumes generated bounded smoke iteration artifacts only,
including the iteration result, manifest, root artifact index, signoff,
admission, delegated smoke artifacts under `smoke/`, and delegated scan
artifacts under `smoke/scan/`. It may hash generated artifact files. It does
not run a scan, run readiness, run human smoke, run bounded smoke iteration,
run promotion gate, hash candidate files, read raw candidate file contents,
copy raw private content, mutate inputs, mutate iteration outputs, mutate
smoke outputs, approve production scanning, or grant production promotion.

The command writes these review artifacts into `output_dir`:

- `local_asset_smoke_iteration_review_packet.json`
- `local_asset_smoke_iteration_review_packet_manifest.json`
- `local_asset_smoke_iteration_review_summary.md`
- `local_asset_smoke_iteration_human_decision_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed if any of those files already exist.
The review packet summarizes outer iteration signoff, admission, promotion
gate validation, delegated human smoke state, delegated scan state,
quarantine, duplicates, generated SQLite manifest/query summary, incremental
plan counts, failure state, warning state, and explicit boundaries.

Iteration review status values are:

- `review_ready`
- `review_ready_with_warnings`
- `review_blocked_missing_required_artifacts`
- `review_blocked_failed_iteration`
- `review_blocked_untrusted_artifacts`

Recommended human decision values are:

- `generate_promotion_gate_for_iteration`
- `inspect_iteration_quarantine_before_promotion`
- `inspect_iteration_duplicates_before_promotion`
- `inspect_iteration_incremental_changes_before_promotion`
- `reject_and_repair_iteration`

A clean review can recommend generating a promotion gate for the iteration.
It never recommends production scan. The checklist is for human review only:
it does not suggest deleting, moving, renaming, or deduplicating files, does
not grant automatic approval, and does not add UI, desktop app behavior,
Operator Console behavior, watcher/daemon behavior, network access, model API
calls, external creative runtime activation, HFX changes, global database
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

Task graphs can include a human-approved bounded local asset smoke node:

```json
{
  "node_id": "human_smoke_assets",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_human_smoke_run",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "candidate_input_dir": "/path/to/candidate-assets",
    "output_dir": "/path/to/human-smoke-output-root",
    "readiness_report": "/path/to/readiness/local_asset_smoke_readiness_report.json",
    "human_approval_id": "reviewer-ticket-123",
    "human_approval_phrase": "I_APPROVE_LOCAL_ASSET_SMOKE_RUN",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project",
    "max_smoke_files": 25,
    "max_smoke_bytes": 100000000,
    "max_smoke_depth": 4,
    "previous_scan_output_dir": "/path/to/previous-scan-output"
  }
}
```

The node runs the same `launch-local-asset-human-smoke-run` launcher path and
records approval, admission receipt, smoke summary, control and scan output
directories, readiness status and decision, admission status, scan invocation
status, scan completion, bounded smoke status, and explicit false values for
production scan, input mutation, network access, model API calls, and external
runtime invocation.

Task graphs can include a post-smoke-run review packet node:

```json
{
  "node_id": "review_human_smoke",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_review_packet",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "smoke_output_dir": "/path/to/human-smoke-output-root",
    "output_dir": "/path/to/review-packet-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-smoke-review-packet` and records the packet,
manifest, summary, decision checklist, artifact index paths, review packet
status, recommended human decision, and explicit false values for scan
execution, readiness execution, raw candidate content reads, candidate file
hashing, smoke output mutation, input mutation, file movement, file renaming,
file deletion, duplicate deletion, media organizer behavior, network access,
model API calls, and external runtime invocation.

Task graphs can include a local asset smoke promotion gate node:

```json
{
  "node_id": "promote_human_smoke",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_promotion_gate",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "review_output_dir": "/path/to/review-packet-output",
    "output_dir": "/path/to/promotion-gate-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-smoke-promotion-gate` and records the
decision, gate manifest, summary, human signoff checklist, artifact index
paths, promotion gate status, promotion decision, next bounded smoke
iteration allowance, blocker list, and explicit false values for scan
execution, readiness execution, human smoke execution, review packet mutation,
raw candidate content reads, candidate file hashing, production promotion, and
production scan approval.

Task graphs can include a bounded smoke iteration node:

```json
{
  "node_id": "iterate_human_smoke",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_bounded_smoke_iteration",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "promotion_output_dir": "/path/to/promotion-gate-output",
    "candidate_input_dir": "/path/to/candidate-assets",
    "readiness_report": "/path/to/readiness/local_asset_smoke_readiness_report.json",
    "output_dir": "/path/to/iteration-output",
    "human_signoff_id": "reviewer-ticket-456",
    "human_signoff_phrase": "I_APPROVE_NEXT_BOUNDED_SMOKE_ITERATION",
    "recursive": true,
    "include_hidden": false,
    "project_id": "demo_project",
    "max_smoke_files": 100,
    "max_smoke_bytes": 1073741824,
    "max_smoke_depth": 12,
    "previous_scan_output_dir": "/path/to/previous-scan-output"
  }
}
```

The node runs `launch-local-asset-bounded-smoke-iteration` and records the
iteration result, manifest, summary, human review checklist, signoff,
admission, artifact index paths, iteration status and decision, bounded smoke
iteration status, and explicit false values for production promotion,
production scan approval, production scan execution, automatic approval,
watcher/daemon behavior, input mutation, file movement, file renaming, file
deletion, duplicate deletion, media organizer behavior, network access, model
API calls, and external runtime invocation.

Task graphs can include a bounded smoke iteration review packet node:

```json
{
  "node_id": "review_iteration",
  "adapter_id": "local_asset_runtime",
  "capability": "launch_local_asset_smoke_iteration_review_packet",
  "execution_mode": "fixture",
  "depends_on": [],
  "approval_checkpoint_required": true,
  "inputs": {
    "iteration_output_dir": "/path/to/iteration-output",
    "output_dir": "/path/to/iteration-review-output",
    "project_id": "demo_project"
  }
}
```

The node runs `launch-local-asset-smoke-iteration-review-packet` and records
the packet, manifest, summary, decision checklist, artifact index paths,
iteration review status, recommended human decision, iteration status,
bounded smoke iteration status, smoke completion, scan completion, and
explicit false values for production promotion, production scan approval,
production scan execution, scan execution by the review packet, readiness
execution, human smoke execution, bounded iteration execution by the review
packet, promotion gate execution, raw candidate content reads, candidate file
hashing, input mutation, iteration output mutation, smoke output mutation,
file movement, file renaming, file deletion, duplicate deletion, media
organizer behavior, network access, model API calls, and external runtime
invocation.

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
