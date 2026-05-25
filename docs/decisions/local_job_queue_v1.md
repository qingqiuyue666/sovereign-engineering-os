# Local Job Queue V1

## Scope

Local Job Queue V1 adds a standalone queue contract and state machine for
controlled local tasks. It can enqueue descriptors, lease queued work,
record heartbeats, complete jobs, fail jobs with retry policy, cancel jobs,
classify expired leases for crash recovery, and render read-only summaries.

## Dependency Status

This milestone has semantic dependencies on the real local runner boundary and
capability token lifecycle. Real Local Runner Boundary V1 is merged, so queue
descriptors may carry inert references to `command_id`, `run_id`, approval
artifact references, and runner receipt references. Capability Token Lifecycle
V1 is not merged, so token ID and token receipt references remain inert metadata
with `WAITING_FOR_TOKEN_MERGE`; this branch does not import unmerged token code.
Execution and token integration remain deferred until those milestones are
merged.

## Queue States

- `queued`
- `leased`
- `completed`
- `failed`
- `canceled`

Terminal states are `completed`, `failed`, and `canceled`.

## Operations

- `enqueue` adds a descriptor and an append-only `enqueued` event.
- `lease_next` leases one queued job to a worker and records lease expiry.
- `heartbeat` refreshes the lease expiry.
- `complete` moves a leased job to `completed`.
- `fail` requeues before max attempts and moves to `failed` at max attempts.
- `cancel` moves a queued or leased job to `canceled`.
- `classify_expired_leases` reports expired leases without running recovery.
- `tools/local_job_queue_viewer.py` summarizes event records read-only.

## Descriptor Metadata

Job descriptors can carry semantic references for future integration:

- `command_id`
- `run_id`
- `approval_artifact_ref`
- `token_id`
- `token_receipt_ref`
- `runner_receipt_ref`

These fields are metadata only. The queue does not launch the runner, consume a
token, verify a token, re-execute a job, or interpret a runner receipt. Descriptor
mappings reject command lines, argv overrides, shell fields, browser fields,
network fields, provider fields, and URL fields.

## Boundary

This queue does not execute jobs. It starts no background daemon, owns no
unbounded scheduler, performs no network or browser work, calls no provider
API, stores no credentials, grants no arbitrary shell, and does not enable
production autonomy. It does not launch the runner and does not create daemon or
scheduler behavior from leases, heartbeats, retries, or expired lease
classification.

## Crash Recovery

Expired leases are classified as either `expired_lease_retryable` or
`expired_lease_terminal`. Classification is read-only; a human or separately
admitted controller must decide any recovery action.

## Merge Readiness

This branch can be reviewed independently as a state-machine contract. Any
integration with runner execution or token consumption must wait for those
prerequisite PRs to merge.
