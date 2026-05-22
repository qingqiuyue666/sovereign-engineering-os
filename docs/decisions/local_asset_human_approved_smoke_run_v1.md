# Local Asset Human-Approved Smoke Run v1

Repository URL:
https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os

Canonical local repository path:
`/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch:
`feat/local-asset-human-approved-smoke-run-v1`

## Objective

Add a controlled, human-approved, bounded smoke run path for local asset
scanning. The path consumes a prior local asset smoke readiness report, requires
an explicit approval id and exact approval phrase, writes approval and admission
control artifacts, performs a metadata-only bounded smoke precheck, delegates
the actual scan to the existing local asset scan launcher, and binds control and
scan outputs into artifact surfaces.

This is not production scanning, automatic approval, a watcher, a daemon, a UI,
desktop app behavior, Operator Console behavior, global database state, or
production autonomy.

## Changed Files

- `kernel/assets/local_asset_human_smoke.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_human_approved_smoke_run.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_human_approved_smoke_run_v1.md`

## Behavior Added

The new `launch-local-asset-human-smoke-run` capability admits a bounded local
asset smoke run only after a human supplies:

- `--human-approval-id`
- `--human-approval-phrase I_APPROVE_LOCAL_ASSET_SMOKE_RUN`

The phrase must match exactly. Its plaintext is not persisted. The approval
artifact stores only the SHA-256 hash of the phrase.

## Output Layout Strategy

The selected layout uses a smoke run root with deterministic subdirectories:

- `output_dir/control/` contains
  `local_asset_human_smoke_approval.json` and
  `local_asset_human_smoke_admission_receipt.json`.
- `output_dir/scan/` is passed to the existing
  `run_local_asset_scan_launcher` and receives the normal local asset scan
  output stack.
- `output_dir/local_asset_human_smoke_run_summary.md` is the root human smoke
  summary.
- `output_dir/artifact_index.json` and
  `output_dir/artifact_index_manifest.json` are root-level explicit indexes of
  control artifacts and selected scan artifacts.

This avoids mixing control artifacts into the scan launcher's output directory
and preserves the launcher's existing fail-closed collision behavior.

The root artifact index does not recursively crawl the smoke output root. It is
an explicit control-and-scan reference index to avoid recursive artifact index
collisions between the root index and the scan-level `scan/artifact_index.json`.

## CLI Command

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-local-asset-human-smoke-run \
  --candidate-input-dir /path/to/candidate-assets \
  --output-dir /path/to/human-smoke-output-root \
  --readiness-report /path/to/readiness/local_asset_smoke_readiness_report.json \
  --human-approval-id reviewer-ticket-123 \
  --human-approval-phrase I_APPROVE_LOCAL_ASSET_SMOKE_RUN \
  --recursive \
  --project-id demo_project
```

Optional bounded controls:

- `--include-hidden`
- `--max-smoke-files`
- `--max-smoke-bytes`
- `--max-smoke-depth`
- `--previous-scan-output-dir`

Default smoke limits:

- `max_smoke_files = 100`
- `max_smoke_bytes = 2000000000`
- `max_smoke_depth = 8`

## Approval Artifact Schema

`local_asset_human_smoke_approval.json` has
`artifact_type = local_asset_human_smoke_approval_v1` and records:

- human approval id
- approval phrase SHA-256
- `approval_phrase_stored = false`
- `approval_phrase_plaintext_persisted = false`
- approved action and bounded smoke scope
- candidate, output, readiness report path, readiness report SHA-256
- readiness status and decision
- project id, recursion flags, hidden flag, smoke limits
- required human approval and approved-by-user flags
- false permissions for production autonomy, input mutation, file movement,
  file rename, file delete, network, model API, and external runtime

## Admission Receipt Schema

`local_asset_human_smoke_admission_receipt.json` has
`receipt_type = local_asset_human_smoke_admission_receipt_v1` and records:

- admitted status and admission reason
- readiness report path and SHA-256
- approval artifact path and SHA-256 when an approval artifact exists
- candidate, smoke root output, scan output, and control output paths
- project id, recursion flags, hidden flag, and smoke limits
- readiness status and decision
- metadata precheck status, file count, total bytes, max depth observed, and
  limit-exceeded flag
- scan launcher invocation and scan completion flags
- failure stage when failed
- next allowed action
- explicit false values for production scan, input mutation, move, rename,
  delete, media organizer behavior, output overwrite, network access, model API,
  and external runtime

## Smoke Run Summary

`local_asset_human_smoke_run_summary.md` records the admission result,
readiness status and decision, candidate and output paths, scan and control
output dirs, human approval id, project id, smoke limits, precheck counts,
scan completion, scan artifact paths, and boundaries:

- bounded smoke only
- no production autonomy
- no input mutation
- no file move/rename/delete
- no network
- no model API
- no external runtime
- human review required

It does not include the approval phrase plaintext or raw private file contents.

## Readiness Report Relationship

The human smoke run requires a prior
`local_asset_smoke_readiness_report.json` from the metadata-only readiness
harness. The report must have:

- `report_type = local_asset_real_folder_smoke_readiness_report_v1`
- `execution_capability = real_folder_smoke_readiness_only`
- `metadata_only = true`
- `required_human_approval = true`
- `readiness_decision = allow_human_review_for_future_smoke`
- `readiness_status = ready` or `ready_with_warnings`

It rejects `blocked_safety_risk`, `blocked_limit_exceeded`, and
`failed_preflight`.

## Bounded Smoke Limits

The smoke run fails before invoking the scan launcher if:

- metadata precheck file count exceeds `max_smoke_files`
- metadata precheck total bytes exceeds `max_smoke_bytes`
- metadata precheck observed depth exceeds `max_smoke_depth`

It also rejects smoke limits that exceed readiness report limits where
available:

- `max_smoke_files <= readiness inspected_file_count`
- `max_smoke_bytes <= readiness max_total_bytes`
- `max_smoke_depth <= readiness max_depth`

The scan is not silently truncated and no sampling behavior is introduced.

## Smoke Precheck Rules

The precheck is metadata-only. It traverses the candidate using the same
recursive and hidden-path flags as the readiness report and runtime request,
counts files that the runtime would scan, sums filesystem metadata sizes, and
tracks observed relative path depth. It does not hash candidate files, read raw
contents, mutate inputs, call the network, call model APIs, or invoke external
runtimes.

## Artifact Index Relationship

The scan-level `scan/artifact_index.json` remains produced by the existing
local asset scan launcher. The smoke root `artifact_index.json` is an explicit
reference surface for:

- `local_asset_human_smoke_approval`
- `local_asset_human_smoke_admission_receipt`
- `local_asset_human_smoke_run_summary`
- `local_asset_human_smoke_scan_artifact_index`
- `local_asset_human_smoke_scan_artifact_index_manifest`
- selected normal scan outputs when present

No raw private asset contents are copied into either artifact binding surface.

## Task Graph Relationship

The existing `local_asset_runtime` adapter now exposes
`launch_local_asset_human_smoke_run`. Task graph nodes can provide:

- `candidate_input_dir`
- `output_dir`
- `readiness_report`
- `human_approval_id`
- `human_approval_phrase`
- `recursive`
- `include_hidden`
- `project_id`
- `max_smoke_files`
- `max_smoke_bytes`
- `max_smoke_depth`
- `previous_scan_output_dir`

The node execution record exposes approval, admission, summary, control dir,
scan dir, readiness status and decision, admission status, scan launcher
invocation, scan completion, bounded smoke status, and explicit false values
for production scan, input mutation, network access, model API calls, and
external runtime invocation.

`task_graph_artifact_outputs.json` now recognizes artifact roles:

- `local_asset_human_smoke_approval`
- `local_asset_human_smoke_admission_receipt`
- `local_asset_human_smoke_run_summary`
- `local_asset_human_smoke_scan_artifact_index`
- `local_asset_human_smoke_scan_artifact_index_manifest`

## Failure Behavior

The capability fails before scan launcher invocation when approval phrase,
approval id, readiness report, readiness state, path matching, input/output
overlap, smoke limits, existing control outputs, existing root artifact index
outputs, or scan output collisions are invalid.

When the root output directory is safe and no expected outputs would be
overwritten, denial paths write an admission receipt, summary, and root artifact
index. When expected outputs already exist, no new artifacts are written and the
preexisting file is preserved.

Failure receipts keep:

- `scan_launcher_invoked = false`
- `real_scan_performed = false`
- `bounded_smoke_run_performed = false`
- `production_scan_performed = false`

## Deterministic Ordering Strategy

Directory iteration for the metadata precheck is sorted by candidate-relative
path. Root artifact index entries are emitted from an explicit role list in a
fixed order. JSON artifacts are written with sorted keys and stable indentation.
Task graph artifact roles are emitted through deterministic field lists.

## Explicit Non-Goals Preserved

- No automatic approval
- No production scan
- No watcher or daemon
- No global database state
- No UI
- No Operator Console behavior
- No network
- No model API
- No external runtime
- No browser runtime activation
- No ComfyUI, Blender, Houdini, After Effects, or DaVinci activation
- No HFX change
- No input mutation
- No file movement
- No file renaming
- No file deletion
- No duplicate deletion
- No media organizer behavior
- No production autonomy

## Validation Commands Run

Required validation:

- `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v` - passed
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v` - passed
- `python3 -m unittest discover -s tests/schemas -v` - passed, 133 tests
- `python3 -m unittest discover -s validation/tests/acceptance -v` - passed, 156 tests
- `python3 -m unittest discover -s tests/tracer_bullet -v` - passed, 6452 tests, 4 skipped
- `python3 -m unittest tests.personal_ai.test_product_health_check -v` - passed
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v` - passed
- Pre-commit `make ci` - tests passed, then stopped at the clean-worktree gate because the intended branch changes were uncommitted
- Pre-commit `git diff --check` - passed

## Final Validation State

Final post-commit `make ci` result:
passed

Final `git diff --check` result:
passed

Final `git status --short` result:
clean

Final branch verification state:
branch `feat/local-asset-human-approved-smoke-run-v1` contains the committed
human-approved bounded smoke run slice and is ready for diff review after push
and PR creation.

Next recommended branch:
`feat/local-asset-smoke-run-review-packet-v1`
