# Operator Console Read Model Projection V1

## Scope

This change adds an implementation projection for the existing Sovereign Console
read models. It derives an operator-facing status report from
`RuntimeSnapshot` without requiring the unmerged readonly operator-console
contract PR.

## Behavior

The projection records:

- runtime and database availability
- WAL status
- queue depth and active job count
- failed and quarantined job counts
- human-review-required job count
- warning count
- bounded recent job ids
- bounded recent event types
- next required operator action
- deterministic content hash

## Boundary

The projection is read-only. It does not submit jobs, create approvals, mutate
SQLite state, launch the GUI, start workers, call external tools, open network
connections, or expose raw event payloads.

Contract-specific conformance to PR #505 remains blocked until that draft PR is
merged. This implementation intentionally stays on current `main` surfaces:
`apps/ui/read_models.py` and the existing bounded SQLite projection tests.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_sovereign_console_read_models -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_operator_console_read_model_projection_v1 -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_os_engine_gui_execution_split tests.tracer_bullet.test_desktop_local_smoke -v`
- `git diff --check`
