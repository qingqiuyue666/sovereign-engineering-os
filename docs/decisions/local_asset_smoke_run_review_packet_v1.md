# Local Asset Smoke Run Review Packet v1

## Repository

- Repository URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`
- Canonical local repository path: `<repo-root>`
- Branch name: `feat/local-asset-smoke-run-review-packet-v1`

## Objective

Add a post-smoke-run review packet generator for human-approved local asset
smoke runs. The generator consumes generated smoke-run artifacts only and
emits a compact, non-authoritative packet for human decision.

## Changed Files

- `kernel/assets/local_asset_smoke_review_packet.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `kernel/personal_ai/adapters/adapter_registry.py`
- `kernel/personal_ai/product_health_check.py`
- `tests/tracer_bullet/test_local_asset_smoke_run_review_packet.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_smoke_run_review_packet_v1.md`

## Behavior Added

The new review packet capability reads a completed or failed
human-approved smoke output root and writes a separate review packet output
directory. It summarizes approval, admission, readiness, scan counts,
quarantine, duplicates, generated SQLite manifest state, incremental scan
plan state, failure state, warnings, source artifacts, missing artifacts, and
decision options.

## CLI Command

`launch-local-asset-smoke-review-packet`

Required arguments:

- `--smoke-output-dir`
- `--output-dir`

Optional arguments:

- `--project-id`

The output directory must already exist. The command does not create it.

## Review Packet Artifact Schema

The primary packet is `local_asset_smoke_review_packet.json` with:

- `packet_type = local_asset_smoke_review_packet_v1`
- `authority = non_authority`
- `execution_capability = local_asset_smoke_review_packet_only`
- `review_packet_status`
- `recommended_human_decision`
- summaries for smoke run, approval, admission, readiness, scan, artifacts,
  duplicates, quarantine, SQLite, incremental state, failure, and warnings
- `decision_checklist`
- `source_artifacts`
- `missing_artifacts`
- explicit false no-scope-expansion flags
- `required_human_approval = true`
- `next_allowed_action = human_review_smoke_review_packet`

The packet manifest is
`local_asset_smoke_review_packet_manifest.json` with packet, summary, and
checklist hashes plus source artifact path, SHA-256, size, and existence
metadata.

## Source Artifact Policy

The module reads only a fixed allowlist of generated artifacts under the smoke
output root. It never recursively discovers private candidate input files and
never reads candidate raw file contents. It may hash generated artifact files,
including generated JSON, Markdown, JSONL, and SQLite artifacts.

## Required Vs Optional Artifacts

Required generated artifacts:

- `control/local_asset_human_smoke_admission_receipt.json`
- `local_asset_human_smoke_run_summary.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Optional generated artifacts include the approval artifact, scan artifact
index files, scan reports, generated SQLite artifacts, incremental scan
artifacts, and generated scan failure artifacts.

If required artifacts are missing, the packet status is
`review_blocked_missing_required_artifacts`.

## Summary Logic

The review summary derives counts and decisions from generated smoke and scan
artifacts. It prefers structured JSON reports for counts and never opens the
candidate input files. It reports duplicate group and duplicate asset counts
without suggesting deletion. It reports quarantine counts and top reasons
without copying raw private content. It reads generated SQLite row counts from
the SQLite manifest without opening candidate files. It reads incremental
plan mode and counts from the generated incremental plan.

## Decision Checklist Logic

The checklist asks a human to verify approval, non-persistence of the approval
phrase, bounded smoke admission, no production scan, no input mutation, scan
completion, quarantine summary, duplicate summary, SQLite summary, and
incremental plan summary. It presents these decision options:

- `approve_next_bounded_smoke_iteration`
- `inspect_quarantine_before_next_run`
- `inspect_duplicates_before_next_run`
- `inspect_incremental_changes_before_next_run`
- `reject_and_repair_smoke_run`

It does not suggest deleting, moving, renaming, or automatically deduplicating
files, and it does not grant production autonomy.

## Artifact Index Relationship

The review output directory gets its own explicit artifact index:

- `artifact_index.json`
- `artifact_index_manifest.json`

The index binds:

- `local_asset_smoke_review_packet`
- `local_asset_smoke_review_packet_manifest`
- `local_asset_smoke_review_summary`
- `local_asset_smoke_human_decision_checklist`

## Task Graph Relationship

The existing `local_asset_runtime` adapter now exposes
`launch_local_asset_smoke_review_packet`. Task graph nodes accept
`smoke_output_dir`, `output_dir`, and optional `project_id`. Node execution
records expose packet paths, status, recommended decision, and explicit false
values for scan execution, readiness execution, raw candidate content reads,
candidate hashing, and mutation boundaries.

`task_graph_artifact_outputs.json` now binds the review packet, manifest,
summary, and human decision checklist roles.

## Failure Behavior

The review output files are exclusive writes. If any expected review output
file already exists, the command returns a structured failure payload and
writes no review artifacts. If the output directory is missing, it is not
created. If the smoke output root is missing or lacks required generated
artifacts, a safe existing output directory can receive a blocked review
packet. If directories overlap unsafely, the command returns a structured
failure payload and writes no artifacts.

## Deterministic Ordering Strategy

Source artifact specs are fixed and sorted by artifact role. Missing artifact
roles, warning roles, source records, artifact index entries, checklist
decision options, and summary counts are deterministic. The review packet
does not compare absolute paths for deterministic equivalence.

## Explicit Non-Behavior

- No scan performed.
- No readiness run performed.
- No raw candidate content read.
- No candidate file hashing.
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

## Validation

- `python3 -m unittest tests.tracer_bullet.test_local_asset_smoke_run_review_packet -v`: passed, 11 tests.
- Required focused validation command set:
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_human_approved_smoke_run -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_real_folder_smoke_readiness -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`: passed.
  - `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`: passed.
  - `python3 -m unittest discover -s tests/schemas -v`: passed.
  - `python3 -m unittest discover -s validation/tests/acceptance -v`: passed.
  - `python3 -m unittest discover -s tests/tracer_bullet -v`: passed.
  - `python3 -m unittest tests.personal_ai.test_product_health_check -v`: passed.
  - `python3 -m unittest tests.personal_ai.test_adapter_registry -v`: passed.
- Pre-commit `make ci`: test suites passed; final clean-tree check stopped because intended branch changes were not yet committed.
- Final post-commit `make ci` result: passed.
- Final `git diff --check` result: passed.
- Final `git status --short` result: clean.
- Final branch verification state: branch `feat/local-asset-smoke-run-review-packet-v1` verified before push.

## Next Recommended Branch

Next recommended branch:
`feat/local-asset-smoke-run-promotion-gate-v1`.
