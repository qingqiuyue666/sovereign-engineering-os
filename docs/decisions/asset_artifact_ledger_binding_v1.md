# Asset Artifact Ledger Binding v1 Decision

Verdict: `APPROVE_NARROW_ASSET_ARTIFACT_LEDGER_BINDING_V1`

## Repository

- URL: `https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os`
- Canonical local repository: `<repo-root>`
- Branch: `feat/asset-artifact-ledger-binding-v1`

## Objective

Bind `launch-local-asset-scan` outputs into the existing system artifact index
surface after the local asset runtime and launcher summary complete.

## Changed Files

- `kernel/personal_ai/local_launcher.py`
- `tests/tracer_bullet/test_local_asset_runtime_artifact_binding.py`
- `docs/usage/personal_ai_execution_os_product_usage_v1.md`
- `docs/decisions/asset_artifact_ledger_binding_v1.md`

## Behavior Added

`run_local_asset_scan_launcher` now fails closed before runtime execution if
`launcher_summary.md`, `artifact_index.json`, or
`artifact_index_manifest.json` already exists in `output_dir`.

After successful local asset runtime execution and `launcher_summary.md`
generation, the launcher calls the existing
`kernel.personal_ai.artifact_index.build_artifact_index` builder for
`output_dir`.

The generated artifact index records these local asset scan artifacts:

- `asset_manifest.json`
- `asset_index.json`
- `duplicates_report.json`
- `media_inventory.md`
- `asset_runtime_audit_log.jsonl`
- `asset_runtime_validation_report.json`
- `asset_runtime_quarantine_manifest.json`
- `launcher_summary.md`

The CLI payload includes artifact index paths, indexed artifact count, artifact
hashes, and explicit non-authority metadata for the binding.

## Mechanism Reused

This branch reuses the existing artifact index mechanism in
`kernel/personal_ai/artifact_index.py`.

No new ledger system is invented.

## Explicit Non-Goals Preserved

- no UI
- no SQLite
- no Operator Console
- no real-folder smoke
- no network
- no model API
- no external runtime
- no HFX change
- no input mutation
- no media organizer behavior
- no production autonomy

## Validation Commands Run

Run during branch validation:

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

`feat/asset-scan-failure-bundle-v1`
