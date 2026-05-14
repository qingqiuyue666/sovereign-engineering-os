# OSS Integration Plan v1

Status: selected safe integrations plan

Branch: `oss-top-repo-integration-autonomous-sprint`

## Scope

This plan implements safe local-first capabilities for Personal AI Local v1 using standard-library code shaped by the intake audit. No external dependency is added. No vendored code is added. No kernel/adapters files are changed.

## Selected repositories and fit

### `python-jsonschema/jsonschema`

- why useful: proven contract-first validation pattern
- exact local capability: deterministic validation reports for job packages and approved output packages
- architecture fit: `kernel/personal_ai/package_validator.py` and `kernel/personal_ai/output_validator.py`
- integration type: design inspiration only
- expected outputs: `job_package_validation.json`, `approved_output_validation.json`
- tests required: required artifacts, malformed manifests, hash checks, boundary checks, raw sentinel leakage checks
- boundary risks: validators must not fetch remote references or read input contents
- rollback strategy: remove validator modules, CLI subcommands, and tests

### `frictionlessdata/frictionless-py`

- why useful: package-level validation reports for data artifacts
- exact local capability: package completeness, artifact presence, and no-leakage reporting
- architecture fit: validator report payloads under `kernel/personal_ai`
- integration type: design inspiration only
- expected outputs: same validator report outputs
- tests required: deterministic output, missing artifact ordering, no raw sentinel leakage
- boundary risks: avoid raw tabular validation and raw cell capture
- rollback strategy: keep existing package builders unchanged and remove validation report generation

### `simonw/sqlite-utils`

- why useful: local artifact indexing and metadata-centric search posture
- exact local capability: deterministic JSON artifact index over generated job package files
- architecture fit: `kernel/personal_ai/artifact_index.py`
- integration type: design inspiration only
- expected outputs: `artifact_index.json`, `artifact_index_manifest.json`
- tests required: metadata-only entries, hashes, deterministic ordering, path escape rejection, no raw content copying
- boundary risks: SQLite dependency and search query execution are unnecessary now
- rollback strategy: remove artifact index generation and CLI subcommand

### `syrupy-project/syrupy`

- why useful: snapshot/golden testing discipline
- exact local capability: path-normalized deterministic snapshot payloads
- architecture fit: `kernel/personal_ai/snapshot_utils.py`
- integration type: design inspiration only
- expected outputs: reusable normalized payloads for tests; no runtime artifact required
- tests required: temp path normalization, stable canonical JSON, no absolute path brittleness
- boundary risks: snapshots must not capture raw input contents
- rollback strategy: remove snapshot helper and tests

### `Textualize/rich`

- why useful: readable CLI result design and explicit machine-safe summaries
- exact local capability: safer JSON CLI outputs with explicit result paths
- architecture fit: `kernel/personal_ai/local_mvp_cli.py`
- integration type: design inspiration only
- expected outputs: CLI JSON with validation/index paths when relevant
- tests required: existing CLI still works, new subcommands produce JSON and write only requested outputs
- boundary risks: no colored terminal dependency, no interactive terminal state
- rollback strategy: remove added subcommands and keep legacy parser

### `pallets/click`

- why useful: command grouping and focused command responsibilities
- exact local capability: safe subcommands: `run-local`, `write-approval-request`, `create-approved-output`, `validate-job`, `validate-output`, `index-artifacts`
- architecture fit: `kernel/personal_ai/local_mvp_cli.py`
- integration type: design inspiration only
- expected outputs: same local package, approval, validation, and index artifacts
- tests required: legacy invocation, subcommand invocation, failure JSON, no hidden tool control
- boundary risks: keep standard-library argparse; do not introduce command execution
- rollback strategy: return CLI to single-command legacy mode

### `CycloneDX/cyclonedx-python-lib`

- why useful: explicit registry and manifest discipline for integration provenance
- exact local capability: static OSS integration registry with selected, optional, design-only, and rejected records
- architecture fit: `kernel/personal_ai/oss_integration_registry.py`
- integration type: design inspiration only
- expected outputs: optional `oss_integration_registry.json`
- tests required: no dynamic loading, no code execution, deterministic records, rejected candidates visible
- boundary risks: do not create SBOM generation, remote package inspection, or dependency scanning
- rollback strategy: remove registry module and tests

## Files to add

- `kernel/personal_ai/artifact_index.py`
- `kernel/personal_ai/package_validator.py`
- `kernel/personal_ai/output_validator.py`
- `kernel/personal_ai/oss_integration_registry.py`
- `kernel/personal_ai/snapshot_utils.py`
- `tests/personal_ai/test_artifact_index.py`
- `tests/personal_ai/test_package_validator.py`
- `tests/personal_ai/test_output_validator.py`
- `tests/personal_ai/test_oss_integration_registry.py`
- `tests/personal_ai/test_snapshot_utils.py`
- `tests/personal_ai/test_local_mvp_cli_integrations.py`

## Files to modify

- `kernel/personal_ai/__init__.py`
- `kernel/personal_ai/local_mvp_cli.py`
- `kernel/personal_ai/job_package.py`
- `kernel/personal_ai/job_manifest.py`
- `kernel/personal_ai/output_package.py`
- `docs/usage/personal_ai_local_v1_usage.md`
- `README.md`
- `docs/current_phase.md`

## Implementation order

1. Add artifact index, validator, output validator, snapshot utils, and registry modules.
2. Wire artifact index generation into the local job package builder.
3. Wire approved output validation into the approved output package builder.
4. Add safe CLI subcommands while preserving the existing invocation.
5. Add focused tests under `tests/personal_ai`.
6. Update usage docs, README, and current phase.
7. Run focused tests, repo CI, diff checks, forbidden import scan, and destructive operation scan.

## Expected outputs

Job package supplemental artifacts:

- `artifact_index.json`
- `artifact_index_manifest.json`
- `job_package_validation.json`

Approved output package supplemental artifact:

- `approved_output_validation.json`

Optional registry output:

- `oss_integration_registry.json`

## Boundary risks and controls

- input mutation: validators and indexes read generated package artifacts only
- raw cell values: validators scan generated outputs for sentinel leakage but do not read source spreadsheets
- spreadsheet output writing: no `.xlsx`, `.xlsm`, or `.xls` outputs are generated
- network/API: no imports or runtime calls
- external tool control: no subprocess, browser, OS automation, or app control
- kernel/adapters: unchanged
- license: design inspiration only, no external source copy

## Rollback strategy

The rollback is file-scoped:

- remove the five new production modules
- remove tests for those modules
- remove CLI subcommand wiring
- remove supplemental generated artifact references from docs
- keep existing local MVP job package, approval gate, approved output package, and provenance chain intact
