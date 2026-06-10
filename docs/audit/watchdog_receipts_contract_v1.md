# Watchdog Receipts Contract V1

This change adds a contract-only watchdog receipt boundary. It records watchdog
policy limits and observation receipts as deterministic, digest-only evidence
without launching work, killing work, persisting diagnostics, calling providers,
or starting background loops.

## Guarantees

- Policy receipts bind task/run IDs, queue job hash, worker admission receipt
  hash, runtime and memory limits, stream byte limits, and disabled kill/retry
  flags.
- Observation receipts bind policy hash, task/run IDs, sequence, previous
  receipt hash, observed state, numeric resource observations, digest-only
  stdout/stderr bindings, WAL record hash, artifact manifest hash, and optional
  failure bundle hash.
- `created_at` and `observed_at` are metadata and excluded from content hashes.
- Raw stdout, raw stderr, raw output, prompt, payload, path, env, command, argv,
  traceback, provider response, and secret-like fields are rejected.
- Terminal watchdog states require a failure bundle hash and quarantine.
- OK watchdog states reject failure bundle hashes and quarantine.
- Receipt chains fail closed on gaps, invalid receipt hashes, previous-hash
  mismatch, and task/run/policy identity mismatch.

## Deferred Work

Real watchdog integration, worker kill behavior, diagnostic artifact migration,
failure bundle linkage, durable queue interaction, and operator console surfacing
remain follow-on work behind the real WAL, durable queue, and failure bundle
center PRs.
