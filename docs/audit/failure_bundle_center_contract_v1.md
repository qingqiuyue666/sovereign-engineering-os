# Failure Bundle Center Contract V1

This change adds a contract-only center for failure bundle evidence. The center
binds sanitized failure bundle digests to WAL record hashes, artifact manifest
hashes, snapshot/replay reconstruction hashes, recovery plan hashes, digest-only
output evidence, retry decisions, and quarantine requirements.

The module does not persist bundles, execute recovery, start workers, schedule
background activity, call providers, launch browsers, or read environment state.

## Guarantees

- Failure references are digest-only and deterministic.
- `observed_at` and `created_at` are metadata and excluded from hashes.
- Raw stdout, raw stderr, traceback, prompt, payload, path, env, command, and
  secret-like fields are rejected fail-closed.
- Digest-only stdout/stderr bindings are allowed with explicit truncation flags.
- Terminal, policy-blocked, and operator-blocked failures require quarantine and
  cannot request retry-after-backoff.
- Retryable failures must explicitly select retry-after-backoff.
- The center manifest rejects duplicate bundle IDs, duplicate reference hashes,
  task/run mismatch, and recovery plan hash mismatch.

## Deferred Work

Real failure bundle persistence, artifact-root storage, WAL-backed append,
watchdog integration, operator console surfacing, and recovery execution remain
follow-on work behind the real WAL and artifact storage PRs.
