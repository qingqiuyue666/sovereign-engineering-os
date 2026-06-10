# Worker Registry Capability Runtime V1

## Scope

Priority #521 adds a file-backed worker registry capability runtime that closes
the boundary between worker admission and durable queue leasing. The runtime is
human-invoked by callers, digest-bound, and local-only. It does not start worker
loops, execute commands, call providers, open browsers, read environment state,
or grant production autonomy.

## Runtime Boundary

`FileBackedWorkerRegistryCapabilityRuntime` coordinates these existing
contract surfaces:

- worker admission declarations, requests, receipts, and registry manifests
- approval runtime consumption when human approval is required
- durable queue state checks and authorized leasing
- watchdog policy receipt construction
- real WAL records of type `WORKER_REGISTRY_EVENT`
- artifact-store `worker_receipt` evidence
- file-backed capability issue, consume, revoke, and quarantine state

The runtime issues a single-use worker capability only after the target queue
job is already queued, the worker declaration admits the requested task class,
the approval gate has accepted where required, watchdog policy receipt evidence
exists, and worker state is bound to the real WAL.

## Fail-Closed Properties

The runtime rejects before queue leasing when:

- the queue job is missing or not queued
- the queue job identity does not match the requested task/run
- worker admission rejects the declaration/request pair
- the worker id does not match the issued capability
- the job id does not match the issued capability
- the capability is revoked, expired, already consumed, or scoped incorrectly
- the worker is quarantined
- the authorized job is not the next durable queued job selected by queue policy
- direct bypass material such as commands, paths, environment, shell, raw output,
  browser, provider, or network fields appears in the request

Rejected consume and revoke attempts are represented by deterministic receipts
and, where state is available, worker registry WAL rejection records. They do
not lease queue jobs.

## Evidence

Tracer and acceptance coverage exercise:

- successful authorization with approval, queue, admission, watchdog, WAL, and
  artifact evidence
- successful single consume that leases only the authorized queue job
- capability reuse rejection
- unauthorized worker rejection
- revoked capability rejection
- expired capability rejection
- quarantined worker rejection
- source guard coverage for direct process, network, browser, provider, and
  environment surfaces

The runtime stores worker receipt artifacts with digest-only material and avoids
raw command, output, path, environment, secret, and credential fields.
