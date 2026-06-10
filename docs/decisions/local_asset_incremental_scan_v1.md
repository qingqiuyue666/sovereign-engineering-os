# Local Asset Incremental Scan v1

Repository: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`

Canonical local repository: `<repo-root>`

Branch: `feat/local-asset-incremental-scan-v1`

## Objective

Add a safe, deterministic, metadata-only incremental scan planning layer after
a normal local asset scan. The planner compares the current generated scan
artifacts against an optional previous scan output directory and emits an
auditable human-review plan.

## Changed Files

- `kernel/assets/local_asset_incremental_plan.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/asset_scan_operational_control.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `tests/tracer_bullet/test_local_asset_incremental_scan_plan.py`
- `tests/tracer_bullet/test_local_asset_sqlite_index.py`
- `tests/tracer_bullet/test_local_asset_runtime_artifact_binding.py`
- `tests/tracer_bullet/test_task_graph_artifact_output_binding.py`
- `tests/tracer_bullet/test_asset_scan_operational_control.py`
- `tests/tracer_bullet/test_task_graph_local_asset_scan_node.py`
- `tests/tracer_bullet/test_local_asset_runtime_cli_launcher.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_incremental_scan_v1.md`

## Behavior Added

The launcher now writes these metadata-only artifacts inside the current scan
`output_dir` after SQLite index generation and before artifact index binding:

- `local_asset_incremental_scan_plan.json`
- `local_asset_incremental_scan_manifest.json`
- `local_asset_incremental_scan_summary.md`

The CLI accepts optional `--previous-scan-output-dir`. Task graph local asset
scan nodes accept optional `previous_scan_output_dir`.

## Incremental Plan Schema

The plan uses `plan_type = local_asset_incremental_scan_plan_v1`,
`authority = non_authority`, and
`execution_capability = local_asset_incremental_planning_only`. It records the
current and previous output directories, project and scan flags, source
artifact hashes, counts, deterministic lists of unchanged, changed, new, and
missing assets, duplicate and quarantine state changes, suspicious changes,
and no-scope-expansion flags. It is marked `safe_to_use_as_plan = true` and
`required_human_approval = true`.

The manifest uses `manifest_type = local_asset_incremental_scan_manifest_v1`
and records plan and summary hashes, current and previous source artifact
hashes, count summaries, deterministic ordering, and the same no-scope
boundary flags.

## Baseline Mode

When no previous scan output directory is provided, the planner writes
`plan_mode = baseline_no_previous_scan`. All current assets are classified as
`new`; missing, changed, and unchanged lists are empty.

## Compare Previous Scan Mode

When a previous scan output directory is provided, the planner writes
`plan_mode = compare_previous_scan` and compares generated previous scan
artifacts to current generated scan artifacts.

## Classification Rules

`relative_path` is the primary identity. An asset is unchanged when
`relative_path`, `sha256`, and `size_bytes` match. It is changed when the same
`relative_path` exists in both scans and `sha256` or `size_bytes` differs. It
is new when present only in the current scan and missing when present only in
the previous scan.

Duplicate-state changes are recorded when the same `relative_path` has changed
duplicate membership. Quarantine-state changes are recorded when a quarantine
item appears, disappears, or changes reason for a `relative_path`.
Suspicious changes include same-path same-size digest changes and conservative
duplicate/quarantine contradictions.

Raw secret-looking files are not classified as content changes from their raw
contents; they remain quarantine metadata only.

## Previous Scan Validation Rules

`previous_scan_output_dir` is optional. When provided it must exist, be a
directory, not be a symlink, not equal the current `output_dir`, not be inside
the current `output_dir`, and not contain the current `output_dir`.

The planner reads only generated previous scan artifacts:

- `asset_manifest.json`
- `asset_index.json`
- `duplicates_report.json`
- `asset_runtime_quarantine_manifest.json`
- `local_asset_index.sqlite` when present
- `local_asset_sqlite_index_manifest.json` when present

It does not read raw previous input assets.

## Artifact Index Relationship

`artifact_index.json` and `artifact_index_manifest.json` are built after the
SQLite outputs and incremental plan outputs exist. The artifact index therefore
includes:

- `local_asset_incremental_scan_plan`
- `local_asset_incremental_scan_manifest`
- `local_asset_incremental_scan_summary`

## Task Graph Artifact Output Relationship

Task graph node records expose the incremental plan paths and mode. The graph
level `task_graph_artifact_outputs.json` records the three incremental artifact
roles with file existence, size, and SHA-256 hash metadata.

## Failure Behavior

Before runtime execution, the launcher fails closed if any incremental output
file already exists. Invalid previous scan paths fail before runtime. If
incremental planning fails after runtime and SQLite success, the launcher
returns `failure_stage = incremental_plan_failure`, writes a safe failure
bundle when possible, and does not write `artifact_index.json`.

## Deterministic Ordering Strategy

Assets are sorted by `relative_path`. Duplicate groups are sorted by digest and
relative paths. Quarantine records are sorted by relative path, reason, path
type, and detail. Source artifacts are sorted by artifact role. JSON artifacts
are written with sorted keys.

## Explicit Non-Goals

This branch adds no automatic cache execution, no automatic skip, no global
database state, no UI, no Operator Console behavior, no real-folder smoke, no
watcher or daemon, no network access, no model API call, no external runtime
activation, no HFX change, no input mutation, no file move, no file rename, no
file delete, no duplicate deletion, no media organizer behavior, and no
production autonomy.

## Validation Commands Run

- `python3 -m unittest tests.tracer_bullet.test_local_asset_incremental_scan_plan -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`
- `python3 -m unittest discover -s tests/schemas -v`
- `python3 -m unittest discover -s validation/tests/acceptance -v`
- `python3 -m unittest discover -s tests/tracer_bullet -v`
- `make ci` reached the final clean-tree gate after passing its test gates; the
  pre-commit run failed only because this branch still had the intended
  uncommitted changes.
- `git diff --check`
- `git status --short`
- Post-commit `make ci`
- Post-commit `git diff --check`
- Post-commit `git status --short`

Post-commit validation passed with a clean working tree.

## Next Recommended Branch

`feat/local-asset-real-folder-smoke-readiness-v1`
