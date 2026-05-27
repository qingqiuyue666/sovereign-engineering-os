# Worker Registry Admission Contract V1

This change adds a contract-only worker registry admission boundary. It proves
that a worker declaration and task request are eligible for queue admission while
keeping dispatch, execution, process supervision, provider calls, browser use,
DCC, MCP, schedulers, and persistence out of scope.

## Guarantees

- Worker declarations, admission requests, receipts, and registry manifests are
  deterministic and digest-only.
- `declared_at`, `requested_at`, `admitted_at`, and `created_at` are metadata and
  excluded from content hashes.
- Human invocation is required for admission requests.
- Live execution, provider calls, network, browser, DCC, and MCP flags must all
  be false.
- Raw command, argv, cwd, env, executable, timeout, stdout/stderr, prompt,
  payload, path, provider response, and secret-like fields are rejected.
- Human-review workers block until an approval receipt hash is present.
- Non-human-review workers reject unexpected approval receipt hashes.
- Registry manifests reject duplicate worker IDs and duplicate declaration
  hashes.

## Deferred Work

Queue integration, worker registry migration, WAL-backed admission append,
failure bundle linkage, artifact store linkage, watchdog receipts, and operator
console surfacing remain follow-on work behind the durable queue and real WAL
storage PRs.
