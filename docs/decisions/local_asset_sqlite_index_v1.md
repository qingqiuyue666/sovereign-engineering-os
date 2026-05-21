# Local Asset SQLite Index v1

Verdict: `APPROVE_NARROW_LOCAL_ASSET_SQLITE_INDEX_V1`

Repository: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`

Canonical local repository: `/Users/qqy/Documents/GitHub/sovereign-engineering-os`

Branch: `feat/local-asset-sqlite-index-v1`

## Objective

Add a per-scan, output-dir-local SQLite query index for generated local asset
scan results. The index is metadata/query-only, non-authoritative, and scoped
to one scan `output_dir`.

## Changed Files

- `kernel/assets/local_asset_sqlite_index.py`
- `kernel/personal_ai/local_launcher.py`
- `kernel/personal_ai/asset_scan_operational_control.py`
- `kernel/personal_ai/task_graph.py`
- `kernel/personal_ai/task_graph_artifact_outputs.py`
- `tests/tracer_bullet/test_local_asset_sqlite_index.py`
- `tests/tracer_bullet/test_local_asset_runtime_artifact_binding.py`
- `tests/tracer_bullet/test_task_graph_artifact_output_binding.py`
- `tests/tracer_bullet/test_asset_scan_operational_control.py`
- `tests/tracer_bullet/test_task_graph_local_asset_scan_node.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/local_asset_sqlite_index_v1.md`

## Behavior Added

Successful `launch-local-asset-scan` runs now write:

- `local_asset_index.sqlite`
- `local_asset_sqlite_index_manifest.json`
- `local_asset_sqlite_query_summary.md`

The launcher writes these after the runtime outputs, launcher summary, and
operational receipt, and before `artifact_index.json` /
`artifact_index_manifest.json`. If SQLite index creation fails, the launcher
returns a structured `sqlite_index_failure`, writes a safe failure bundle when
possible, and does not create the artifact index.

## SQLite Index Schema

Schema version: `local_asset_sqlite_index_schema_v1`

Tables:

- `scan_runs`
- `assets`
- `duplicate_groups`
- `quarantine_events`
- `artifact_sources`
- `index_metadata`

IDs are deterministic:

- `scan_run_id` is derived from the asset manifest hash plus input/output scan
  metadata.
- `asset_id` is derived from `relative_path` and `sha256`.
- `duplicate_group_id` is derived from `sha256`.
- `quarantine_event_id` is derived from `relative_path` and `reason`.

## Query Surface

The query summary includes table row counts, scan counts, duplicate and
quarantine counts, top extensions by count, media class counts, and safe
read-only example queries for counting assets, listing duplicate groups,
listing quarantined paths, filtering by extension, listing largest assets, and
summarizing media classes.

The query surface does not include raw private file contents, secret values, or
suggested deletion, move, rename, deduplication, or organizer operations.

## Artifact Index Relationship

The existing artifact index now includes:

- `local_asset_index`
- `local_asset_sqlite_index_manifest`
- `local_asset_sqlite_query_summary`

The SQLite manifest records source artifact hashes and the SQLite database hash.
The artifact index remains metadata-only and non-authoritative.

## Task Graph Artifact Output Relationship

Local asset scan node execution records now expose:

- `local_asset_sqlite_index_path`
- `local_asset_sqlite_index_manifest_path`
- `local_asset_sqlite_query_summary_path`

Graph-level `task_graph_artifact_outputs.json` includes the three SQLite
artifact roles with paths, sizes, and SHA-256 hashes when the node succeeds.

## Failure Behavior

Pre-runtime collision checks fail closed when any SQLite output already exists:

- `local_asset_index.sqlite`
- `local_asset_sqlite_index_manifest.json`
- `local_asset_sqlite_query_summary.md`

Post-runtime SQLite build failures use `failure_stage = sqlite_index_failure`.
Failure bundles include runtime outputs, launcher summary, receipt, and any
SQLite files already written before the failure. Artifact indexing is skipped
on SQLite failure.

## Deterministic Ordering Strategy

Source artifact records, inserts, metadata rows, assets, duplicate groups,
quarantine events, manifest fields, and summary sections are ordered
deterministically. SQLite connections are closed explicitly. The branch uses
Python stdlib `sqlite3` rather than the global OS engine WAL database.

## Scope Boundaries

The SQLite DB is per-scan and lives only inside the scan `output_dir`.

No global database state is added. No global OS engine database migrations are
added. No UI, desktop app behavior, Operator Console behavior, real-folder
smoke, network access, model API calls, external runtime activation,
ComfyUI/Blender/Houdini/After Effects/DaVinci activation, HFX change, input
mutation, file movement, file renaming, duplicate deletion, media organizer
behavior, or production autonomy is introduced.

## Validation Commands Run

- `python3 -m unittest tests.tracer_bullet.test_local_asset_sqlite_index -v`
- `python3 -m unittest tests.tracer_bullet.test_task_graph_artifact_output_binding -v`
- `python3 -m unittest tests.tracer_bullet.test_task_graph_local_asset_scan_node -v`
- `python3 -m unittest tests.tracer_bullet.test_asset_scan_operational_control -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_artifact_binding -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime_cli_launcher -v`
- `python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v`
- `python3 -m unittest discover -s tests/schemas -v`
- `python3 -m unittest discover -s validation/tests/acceptance -v`
- `python3 -m unittest discover -s tests/tracer_bullet -v`
- `make ci`
- `git diff --check`
- `git status --short`

Result: all targeted unittest, schema, acceptance, tracer discovery, and
`git diff --check` commands passed before commit. A pre-commit `make ci` run
completed its test phases and stopped at the final clean-tree check because the
intended branch changes were still uncommitted; `make ci` was rerun after the
commit and passed from a clean tree.

## Next Recommended Branch

`feat/local-asset-incremental-scan-v1`
