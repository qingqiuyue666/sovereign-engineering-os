# Install Config Packaging Runnable Path V1

Status: implemented for #525.

## Purpose

This runbook defines the safe local path from a fresh clone to a runnable,
receipt-backed smoke check. The runtime is disabled by default and no command
installs dependencies, opens network connections, calls providers, reads
secrets, starts daemons, or executes console entry points.

## One-Command Bootstrap

Dry-run preview:

```bash
python3 tools/local_runtime_setup.py bootstrap .
```

Apply the local layout:

```bash
python3 tools/local_runtime_setup.py bootstrap . --apply
```

The apply command creates only `.seos-runtime/` under the repository root after
path validation and writes:

- `.seos-runtime/config/local-runtime-config-v1.json`
- `.seos-runtime/runtime-root-marker-v1.json`
- `.seos-runtime/receipts/bootstrap-receipt-v1.json`

## Config Schema

Schema version: `1`.

Required fields:

- `schema_version`
- `runtime_root`
- `runtime_enabled`
- `default_mode`
- `network_access`
- `provider_execution`
- `background_daemon`
- `layout_version`
- `migration_policy`
- `rollback_policy`
- `release_artifact_layout`

Safe defaults:

- `runtime_enabled = false`
- `default_mode = "dry_run"`
- `network_access = false`
- `provider_execution = false`
- `background_daemon = false`
- `runtime_root = ".seos-runtime"`

Any unknown schema version, unknown config key, path escape, symlink runtime
root, enabled network/provider/daemon flag, or secret-like config material fails
closed.

## Runtime Layout

The default local layout is:

- `config/`
- `wal/`
- `queues/`
- `artifacts/`
- `snapshots/`
- `receipts/`
- `failure_bundles/`
- `watchdog/`
- `workers/`
- `quarantine/`
- `backups/`
- `logs/`
- `release/`

All paths must resolve inside the repository root. Absolute paths, `..`
segments, secret-like path names, and symlink roots are rejected.

## Smoke Run

```bash
python3 tools/local_runtime_setup.py smoke . --apply
```

The smoke run verifies the marked layout and writes
`.seos-runtime/receipts/smoke-run-receipt-v1.json`. It does not run providers,
package managers, subprocesses, entry points, or network calls.

## Stop And Reset

```bash
python3 tools/local_runtime_setup.py stop . --apply
python3 tools/local_runtime_setup.py reset . --apply
```

Stop records that no background daemon is enabled or running. Reset removes the
runtime root only when the marker exists and its layout hash matches the current
validated config.

## Migration Policy

- Automatic migration is disabled.
- A backup is required before any future migration.
- Operator receipt evidence is required.
- Unknown config schema versions fail closed.

## Rollback Policy

- Rollback/reset requires the runtime marker.
- Operator receipt evidence is required.
- Quarantine is preserved by policy for future backup/restore flows.
- Unmarked directories are never removed.

## Release Artifact Layout

Release artifacts are declared as:

- `dist/sovereign-engineering-os-{version}.tar.gz`
- `dist/sovereign-engineering-os-{version}-runtime-receipts.json`
- `reports/release/install_config_packaging_runnable_path_v1.json`
- `docs/runbooks/install_config_packaging_runnable_path_v1.md`

## Verification

Focused:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_install_config_packaging_runnable_path_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_install_config_packaging_runnable_path_v1 -v
```

Full gates:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests
make ci
git diff --check
git status --short
```
