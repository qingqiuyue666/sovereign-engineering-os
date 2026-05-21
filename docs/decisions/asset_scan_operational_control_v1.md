# Asset Scan Operational Control v1 Decision

Verdict: `APPROVE_NARROW_ASSET_SCAN_OPERATIONAL_CONTROL_V1`

## Repository

- URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`
- Canonical local repository: `/Users/qqy/Documents/GitHub/sovereign-engineering-os`
- Branch: `feat/asset-scan-operational-control-v1`

## Objective

Upgrade `launch-local-asset-scan` from a success-only launcher workflow into a
controlled operational workflow with a success receipt, safe failure bundle,
failure summary, failure-stage classification, retry/replay hints,
output-pollution checks, and preserved artifact index binding.

## Changed Files

- `kernel/personal_ai/asset_scan_operational_control.py`
- `kernel/personal_ai/local_launcher.py`
- `tests/tracer_bullet/test_asset_scan_operational_control.py`
- `tests/tracer_bullet/test_local_asset_runtime_artifact_binding.py`
- `tests/tracer_bullet/test_local_asset_runtime_cli_launcher.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/asset_scan_operational_control_v1.md`

## Behavior Added

`run_local_asset_scan_launcher` now has an operational control layer around the
existing read-only asset runtime. It classifies failures into deterministic
stages, detects pre-runtime output collisions, returns structured CLI failure
payloads, and writes safe failure artifacts only when `output_dir` already
exists and is safe to write into.

## Success Receipt Behavior

Successful scans write `asset_scan_run_receipt.json` after runtime outputs and
`launcher_summary.md` are written and before artifact indexing runs. The
receipt records scan counts, input/output paths, project flags, quarantine
status, retry/replay guidance, artifact index paths, and explicit false
no-scope-expansion flags for input mutation, movement, renaming, deletion,
media-organizer behavior, overwrite, network, model API, and external runtime
activation.

## Failure Bundle Behavior

Safe failure cases write `asset_scan_failure_bundle.json` and
`asset_scan_failure_summary.md`. The bundle stores a sanitized error message,
safe error hash, failure stage, partial output status, output-pollution status,
retry guidance, recommended human action, and explicit no-scope-expansion
flags. Raw tracebacks and raw secret-looking tokens are not persisted.

If `output_dir` is missing, the launcher does not create it. It returns a
structured failure payload with no failure bundle path.

## Soft Quarantine Distinction

Secret-looking files, symlinks, and other quarantine-classified paths inside
`input_dir` remain successful scans when the runtime treats them as soft
quarantine. The receipt exposes `scan_completed_with_quarantine` and points the
recommended next action to human review of the quarantine manifest.

## Artifact Index Relationship

On success, artifact indexing still uses
`kernel.personal_ai.artifact_index.build_artifact_index`. Because the run
receipt is written before indexing, `artifact_index.json` now includes nine
asset scan artifacts, including `asset_scan_run_receipt`.

Failure artifacts are not indexed in this branch.

## Explicit Non-Goals Preserved

- no UI
- no desktop app behavior
- no SQLite
- no Operator Console
- no real-folder smoke
- no network
- no model API
- no external runtime
- no ComfyUI, Blender, Houdini, After Effects, DaVinci, or browser runtime activation
- no HFX change
- no input mutation
- no file movement, renaming, or deletion
- no duplicate deletion
- no media organizer behavior
- no production autonomy

## Validation Commands Run

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

## Next Recommended Branch

`feat/task-graph-local-asset-scan-node-v1`
