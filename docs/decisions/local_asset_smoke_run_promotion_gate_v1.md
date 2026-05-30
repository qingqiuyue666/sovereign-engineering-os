# Local Asset Smoke Run Promotion Gate v1

## Repository

- Repository URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`
- Canonical local repository path: `<repo-root>`
- Branch name: `feat/local-asset-smoke-run-promotion-gate-v1`

## Objective

Add a non-authoritative promotion gate for local asset smoke run review
packets. The gate consumes generated review packet artifacts only and decides
whether a clean review packet is eligible for the next bounded smoke
iteration. It does not approve production promotion or production scanning.

## Changed Files

- `kernel/assets/local_asset_smoke_promotion_gate.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_smoke_run_promotion_gate.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_smoke_run_promotion_gate_v1.md`

## Behavior Added

The promotion gate reads a smoke review packet output directory and writes a
separate promotion output directory with a decision, manifest, summary, human
signoff checklist, and artifact index. The decision is metadata-only,
non-authoritative, deterministic, and always requires human signoff.

## CLI Command

`launch-local-asset-smoke-promotion-gate`

Required arguments:

- `--review-output-dir`
- `--output-dir`

Optional arguments:

- `--project-id`

The output directory must already exist. The command does not create it.

## Promotion Decision Artifact Schema

The primary decision artifact is
`local_asset_smoke_promotion_decision.json` with:

- `decision_type = local_asset_smoke_promotion_decision_v1`
- `authority = non_authority`
- `execution_capability = local_asset_smoke_promotion_gate_only`
- `review_output_dir`, `output_dir`, and `project_id`
- `promotion_gate_status`
- `promotion_decision`
- `next_bounded_smoke_iteration_allowed`
- `production_promotion_granted = false`
- `production_scan_approved = false`
- review packet status and recommended human decision
- smoke, approval, admission, readiness, scan, duplicate, quarantine,
  SQLite, incremental, failure, warning, and blocker summaries
- promotion blockers, allowed next action, and rejected next actions
- human signoff checklist
- source artifacts, missing review artifacts, and untrusted review artifacts
- explicit false no-scope-expansion flags
- `required_human_approval = true`
- `next_allowed_action = human_review_smoke_promotion_gate`

## Source Artifact Policy

The module reads only generated review packet artifacts from the review output
directory. It never recursively discovers private candidate input files,
never reads candidate raw file contents, and never hashes candidate input
files. It may hash generated review packet artifact files only.

## Required Vs Optional Review Artifacts

Required generated review artifacts:

- `local_asset_smoke_review_packet.json`
- `local_asset_smoke_review_packet_manifest.json`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated review artifacts:

- `local_asset_smoke_review_summary.md`
- `local_asset_smoke_human_decision_checklist.md`

Missing required artifacts produce
`promotion_gate_status = blocked_missing_review_artifacts` and do not allow
the next bounded smoke iteration.

## Gate Decision Rules

The only allowed promotion decision is
`allow_next_bounded_smoke_iteration`, and it is emitted only when all clean
review conditions are true:

- review packet exists and is trusted
- review packet manifest exists and hashes match where applicable
- review packet status is `review_ready`
- review recommended human decision is
  `approve_next_bounded_smoke_iteration`
- smoke run is complete
- scan is complete
- production scan performed is false
- input mutation performed is false
- duplicate deletion performed is false
- quarantine count is zero
- duplicate group count is zero
- suspicious incremental change count is zero
- no blocking warning is present

The gate never produces production approval.

## Blocker Logic

- Quarantine produces `blocked_quarantine` and
  `block_until_human_inspects_quarantine`.
- Duplicate groups produce `blocked_duplicates` and
  `block_until_human_inspects_duplicates`.
- Incremental changes that require inspection produce
  `blocked_incremental_changes` and
  `block_until_human_inspects_incremental_changes`.
- Failed or incomplete smoke output produces `blocked_failed_smoke_run` and
  `block_until_smoke_run_repaired`.
- Missing or untrusted review packet artifacts produce
  `blocked_missing_review_artifacts` or
  `blocked_untrusted_review_packet` and
  `block_until_review_packet_repaired`.
- Blocking warnings produce `blocked_warnings` and
  `block_until_review_packet_repaired`.

## Human Signoff Checklist Logic

The checklist asks a human to verify:

- review packet status is `review_ready`
- recommended decision is `approve_next_bounded_smoke_iteration`
- smoke run is complete
- scan is complete
- `production_scan_performed=false`
- `input_mutation_performed=false`
- `duplicate_deletion_performed=false`
- quarantine count is zero
- duplicate group count is zero
- suspicious incremental changes count is zero
- no blocker is present
- next action is only the next bounded smoke iteration, not production scan

Signoff options are:

- `approve_next_bounded_smoke_iteration`
- `reject_and_repair_review_packet`
- `reject_and_repair_smoke_run`
- `inspect_quarantine`
- `inspect_duplicates`
- `inspect_incremental_changes`

The checklist does not include raw private file contents, does not suggest
moving, renaming, deleting, or deduplicating files, and does not grant
production autonomy.

## Artifact Index Relationship

The promotion output directory gets its own explicit artifact index:

- `artifact_index.json`
- `artifact_index_manifest.json`

The index binds:

- `local_asset_smoke_promotion_decision`
- `local_asset_smoke_promotion_gate_manifest`
- `local_asset_smoke_promotion_summary`
- `local_asset_smoke_promotion_human_signoff_checklist`

## Task Graph Relationship

The existing `local_asset_runtime` adapter exposes
`launch_local_asset_smoke_promotion_gate`. Task graph nodes accept
`review_output_dir`, `output_dir`, and optional `project_id`. Node execution
records expose the promotion decision paths, status, blocker state, explicit
false no-scope-expansion flags, and production approval flags.

`task_graph_artifact_outputs.json` binds the promotion decision, gate
manifest, summary, and human signoff checklist roles.

## Failure Behavior

The promotion output files are exclusive writes. If any expected promotion
output file already exists, the command returns a structured failure payload
and writes no promotion artifacts. If the output directory is missing, it is
not created. If the review output root is missing or lacks required generated
artifacts, a safe existing output directory can receive a blocked promotion
decision. If directories overlap unsafely, the command returns a structured
failure payload and writes no artifacts.

## Deterministic Ordering Strategy

Source artifact specs are fixed and sorted by artifact role. Missing artifact
roles, untrusted artifact roles, blocker roles, rejected next actions,
artifact index entries, checklist items, and signoff options are deterministic.
Tests compare stable fields without relying on absolute path equality.

## Explicit Non-Behavior

- No scan performed.
- No readiness run performed.
- No human smoke run performed.
- No raw candidate content read.
- No candidate file hashing.
- No review packet mutation.
- No smoke output mutation.
- No input mutation.
- No file movement, rename, or delete.
- No duplicate deletion.
- No media organizer behavior.
- No watcher or daemon.
- No global database state.
- No UI.
- No Operator Console.
- No network.
- No model API.
- No external runtime.
- No HFX change.
- No production autonomy.
- No production scan approval.

## Validation

- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_promotion_gate -v`: passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v`: passed, 11 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v`: passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v`: passed, 12 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`: passed, 8 tests.
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`: passed, 7 tests.
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`: passed, 10 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`: passed, 5 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`: passed, 4 tests.
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`: passed, 12 tests.
- `python3 -m unittest discover -s tests/schemas -v`: passed, 133 tests.
- `python3 -m unittest discover -s validation/tests/acceptance -v`: passed, 156 tests.
- `python3 -m unittest discover -s tests/tracer_bullet -v`: passed, 6476 tests, 4 skipped.
- `python3 -m unittest tests.personal_ai.test_product_health_check -v`: passed, 5 tests.
- `python3 -m unittest tests.personal_ai.test_adapter_registry -v`: passed, 8 tests.
- Pre-commit `make ci` result: all invoked test suites passed and
  `git diff --check` passed; the final clean-tree check stopped because the
  intended branch changes were not yet committed.
- Pre-commit `git diff --check` result: passed.
- Pre-commit `git status --short` result: intended branch changes only.
- Final post-commit `make ci` result: passed.
- Final `git diff --check` result: passed.
- Final `git status --short` result: clean.
- Final branch verification state: branch
  `feat/local-asset-smoke-run-promotion-gate-v1` verified before push.

## Next Recommended Branch

Next recommended branch:
`feat/local-asset-bounded-smoke-iteration-v1`.
