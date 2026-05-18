# Sovereign Production OS Public Asset Manifest

| Field | Value |
| --- | --- |
| manifest_id | sovereign-production-os-public-asset-pack-v1 |
| repository_url | https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os |
| main_commit | 1f4f77b8141e04343ace0d6ee62205d73805381e |
| policy_version | public-asset-manifest-v1 |
| code_version | 0.1.0 |
| content_hash | sha256:d72eb774b8e3cc1bfd9acc3500f341da589928ab8af8f658a4eea52a13aed204 |
| observed_at | 2026-05-19T00:00:00+08:00 |

## Asset Items
### mainline-audit-report
- path: docs/reports/sovereign_engineering_os_mainline_audit_report.md
- asset_type: markdown_report
- public_safe: true
- purpose: Deterministic public-safe engineering audit report generated from caller-provided mainline material.
- verification_status: tracked in tracer-bullet public asset checks
### public-asset-overview
- path: docs/reports/sovereign_production_os_public_asset_overview.md
- asset_type: markdown_overview
- public_safe: true
- purpose: External-facing overview of completed capabilities, blocked capabilities, guarantees, and reproducibility boundaries.
- verification_status: tracked in tracer-bullet public asset checks
### mainline-audit-generator
- path: tools/generate_mainline_audit_report.py
- asset_type: local_report_generator
- public_safe: true
- purpose: Local-only generator for the current mainline audit report sample.
- verification_status: covered by existing code audit workbench tests
### code-audit-workbench
- path: kernel/runtime/code_audit_workbench.py
- asset_type: deterministic_validator_module
- public_safe: true
- purpose: Pure deterministic builder and Markdown renderer for caller-provided audit report material.
- verification_status: covered by tests.tracer_bullet.test_code_audit_workbench

## Verification Matrix
- acceptance: 156 tests, OK
- clean_tree_guard: passed
- git_diff_check: passed
- make_ci: passed
- schemas: 70 tests, OK
- tracer_bullet: 5543 tests, 4 skipped, OK

## Blocked Capabilities
- real provider execution remains blocked
- production autonomy remains blocked
- external actions remain blocked
- financial execution remains out of scope

## Safety Boundaries
- all listed assets are local-only
- no provider calls
- no network
- no production autonomy
- no real external execution
- no SQLite mutation and no SQLite introduction
- no environment-derived values or credential-bearing material are read
- no unredacted model inputs, provider outputs, or failure dumps are retained

## Public Release Notes
- This is the first production-output asset package rather than another abstract runtime subsystem.
- The current audit report is caller-input driven.
- The report generator does not discover hidden facts.
- The report generator does not execute tests.
- The report generator does not inspect GitHub over network.
- This asset is not a trading system.
- This asset is not an autonomous execution system.
