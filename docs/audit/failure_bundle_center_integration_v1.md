# Failure Bundle Center Integration V1

Status: implemented for #519.

This slice adds `kernel/runtime/failure_bundle_center_integration.py`, a local
file-backed integration layer over the existing failure bundle center contract.
It records digest-only failure bundles, appends `FAILURE_BUNDLE_EVENT` records
to the real WAL backend, writes `failure_bundle` artifacts through the artifact
store, and persists center manifests and receipts for replay/audit reads.

Covered critical failure kinds:

- WAL corruption
- artifact corruption
- queue invalid transition
- approval rejection
- replay reconstruction failure
- missing record
- hash mismatch
- worker timeout
- watchdog resource breach

Each bundle records task, job, run, WAL pointer, artifact, replay/snapshot,
approval, queue, corruption, watchdog, and worker context through sha256 digest
bindings. Missing required context fails closed before any WAL append. Bundle
write failures return a rejected minimal safe receipt that preserves the
sanitized original exception type without storing raw exception text.

Safety notes:

- Local-only file-backed persistence.
- No subprocess execution, provider calls, browser control, network access,
  daemon loop, credential access, or background autonomy.
- No raw stdout, stderr, traceback, command, environment, path, prompt, provider
  response, secret, or token material is accepted.
- Persisted bundles and manifests are hash-checked on read; tampering fails
  closed.
