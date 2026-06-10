# Resource Watchdog Receipts V1

## Scope

This change adds an implementation receipt path to the existing
`kernel/os_engine` process watchdog. It does not depend on the unmerged
watchdog receipt contract PR #504.

## Behavior

`ProcessSupervisor` now accepts an optional `receipt_dir`. When configured, it
writes one receipt for every supervised process outcome, including success,
nonzero exit, stream overflow, timeout, and quarantine paths.

Receipts include:

- receipt type and receipt id
- command hash, not raw command output
- configured resource limits
- return code
- duration and max RSS
- timeout, memory, stdout, stderr, and quarantine flags
- diagnostic path when a failure bundle exists
- retry attempt policy
- deterministic content hash

The generic `CommandWorker` configures watchdog receipts under
`artifact_root/watchdog_receipts` and carries the receipt path through
`WorkerRunResult.metadata` and `artifact_paths`.

## Boundary

Receipts intentionally do not store raw stdout or raw stderr. This change does
not add retries, shell execution, network calls, browser control, provider calls,
or production autonomy.

Contract-specific conformance to PR #504 remains blocked until that draft PR is
merged. This implementation stays on current `main` surfaces:
`kernel/os_engine/memory_watchdog.py` and `kernel/os_engine/worker_registry.py`.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_os_engine_memory_watchdog -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_os_engine_worker_registry -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_resource_watchdog_receipts_v1 -v`
- `git diff --check`
