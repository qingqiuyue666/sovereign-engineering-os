# Worker Registry Admission Implementation V1

## Scope

This change adds structured worker admission decisions to the existing
`kernel/os_engine` worker registry. It does not depend on the unmerged worker
registry admission contract PR #503.

## Behavior

Worker admission now produces a deterministic decision record containing:

- worker type
- adapter name
- accepted flag
- reason codes
- declared capabilities
- safety boundary
- large-artifact flag
- human-review-required flag
- content hash

`WorkerRegistry.register()` uses the admission decision before mutating the
registry. Rejected workers fail closed, and duplicate worker types keep the
existing `ValueError` behavior. Callers can also evaluate a candidate with
`evaluate_worker_admission()` without changing registry state.

The registry exposes deterministic `admission_report()` and
`admission_report_json()` read models for audit/replay inspection.

## Boundary

This implementation does not execute workers, start subprocesses, open network
connections, add retries, launch tools, mutate queues, or grant production
autonomy. It only admits or rejects registry metadata before registration.

Contract-specific conformance to PR #503 remains blocked until that draft PR is
merged. This implementation stays on the current `main` surface:
`kernel/os_engine/worker_registry.py`.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_os_engine_worker_registry -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_worker_registry_admission_implementation_v1 -v`
- `git diff --check`
