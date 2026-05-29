# Install Config Packaging Runnable Path V1 Audit

Priority: #525

## Scope

The #525 slice turns static packaging readiness into a local runnable path with
safe defaults:

- versioned config schema
- default disabled runtime
- dry-run bootstrap mode
- explicit apply mode for local layout creation
- local smoke-run receipt
- clean stop/reset path
- migration and rollback policy
- release artifact layout declaration
- path validation against traversal and symlink escape
- no network dependency for the core smoke path

## Implementation

Primary implementation:

- `kernel/install_config/local_runtime_path.py`
- `tools/local_runtime_setup.py`

The bootstrap command creates a marked `.seos-runtime/` layout only when
`--apply` is provided. The default command is dry-run. Reset refuses unmarked
runtime directories and refuses path escapes before removal.

## Evidence

Focused tests:

- `tests/tracer_bullet/test_install_config_packaging_runnable_path_v1.py`
- `validation/tests/acceptance/test_install_config_packaging_runnable_path_v1.py`

Required acceptance behavior:

- a fresh local clone can validate the config
- bootstrap creates only the marked local layout
- smoke writes a receipt without network/provider/subprocess execution
- stop records the disabled-daemon state
- reset removes only the marked runtime root

## Boundary

The runnable path does not:

- install the project
- install dependencies
- spawn subprocesses
- access the network
- execute provider code
- execute console entry points
- read environment credentials
- start a background daemon
- silently migrate config
- remove unmarked directories

## Verdict

READY_TO_REVIEW_AND_MERGE when focused validation, full local gates,
canonical-health, review checks, squash merge, and post-merge validation pass.
