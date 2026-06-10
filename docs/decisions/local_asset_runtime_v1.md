# Local Asset Runtime v1 Decision

Verdict: `APPROVE_NARROW_LOCAL_ASSET_RUNTIME_V1`

## Decision

This branch adds the first narrow real local asset runtime slice.

The approved scope is read-only local filesystem scanning and deterministic
output generation only. The runtime may read non-quarantined local files for
streaming SHA-256 hashing and conservative asset classification. It may write
only the required report artifacts inside `output_dir`.

This branch does not authorize external creative runtime activation, browser
runtime activation, model runtime activation, network access, desktop UI, or
unrestricted filesystem automation.

## Authorized Components

- `kernel/assets/local_asset_runtime.py`
- `kernel/assets/local_asset_schema.py`
- `kernel/assets/local_asset_classifier.py`
- `kernel/assets/local_asset_reporter.py`
- `kernel/assets/local_asset_quarantine.py`
- `tests/tracer_bullet/test_local_asset_runtime.py`
- `docs/runbooks/local_asset_runtime_v1.md`

## Authorized Outputs

The runtime may create only these files, and only when absent:

- `asset_manifest.json`
- `asset_index.json`
- `duplicates_report.json`
- `media_inventory.md`
- `asset_runtime_audit_log.jsonl`
- `asset_runtime_validation_report.json`
- `asset_runtime_quarantine_manifest.json`

Existing output files are an immediate failure condition. The runtime does not
overwrite existing outputs.

## Boundary Invariants

- input files are never modified, moved, renamed, deleted, or overwritten
- output writes are confined to `output_dir`
- `output_dir` must be outside `input_dir`
- SHA-256 hashing uses streaming reads
- JSON outputs use sorted keys and stable ordering
- audit output contains deterministic sequence IDs, not wall-clock timestamps
- duplicate detection is by SHA-256 only
- secret-looking files are skipped before content reads
- symlinks are skipped and never followed
- unsafe dependency/cache/source-control directories are not traversed
- no subprocess execution is introduced
- no network execution is introduced
- no model API call is introduced
- no ComfyUI, Blender, Houdini, or browser runtime is launched
- no UI or desktop application layer is introduced

## Quarantine Policy

The runtime records skipped unsafe paths in
`asset_runtime_quarantine_manifest.json`.

Quarantine is skip-only. It does not move files into a quarantine directory and
does not mutate input paths. In v1, quarantine means the path was detected,
not read when unsafe, not traversed when unsafe, and recorded for review.

## Non-Goals

This branch does not claim production autonomy.

This branch does not claim final creative output readiness.

This branch does not turn asset inventory into an execution plan.

This branch does not activate any external creative, browser, model, network,
or desktop runtime.

## Merge Gate

This branch is merge-ready only if:

1. Local asset runtime tracer-bullet tests pass.
2. Full tracer-bullet discovery passes.
3. Schema discovery passes.
4. `make ci` passes.
5. `git diff --check` passes.
6. Worktree status is understood.
