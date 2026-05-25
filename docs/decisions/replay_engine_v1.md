# Replay Engine V1

## Scope

Replay Engine V1 adds a standalone descriptor verifier for local runner replay
evidence. It compares supplied receipts and replay descriptors; it does not
rerun the command.

## Dependency Status

This milestone is aligned with the merged Real Local Runner Boundary V1,
Capability Token Lifecycle V1, and Local Job Queue V1 chain. It remains a
verification-only surface: it reads caller-supplied evidence descriptors and
emits a report, but it does not call the runner, consume tokens, or mutate queue
state.

## Comparisons

The verifier verifies Real Local Runner Boundary evidence:

- expected command ID to actual command ID
- expected argv hash to actual argv hash
- expected resolved argv hash to actual resolved argv hash
- expected executable path and realpath to actual executable path and realpath
- expected executable sha256, or the explicit sha256 unavailable reason, to the
  actual executable sha256 evidence
- expected environment digest to actual environment digest
- expected environment path policy ID to actual environment path policy ID
- expected executable resolution policy ID to actual executable resolution
  policy ID
- expected resolution policy digest to actual resolution policy digest
- expected stdout and stderr sha256 values to actual stdout and stderr sha256
  values
- expected receipt sha256 to actual receipt sha256
- expected exit code to actual exit code

The verifier treats Capability Token Lifecycle state as evidence. When token
metadata is represented, token ID or reference, command ID binding, scope
binding, repo revision binding, approval artifact binding, receipt reference,
and consumed, revoked, or expired state are compared as inert metadata only.
Those fields never authorize replay execution.

The verifier treats Local Job Queue state as evidence. When queue metadata is
represented, job ID or reference, job state evidence, append-only event
reference, runner receipt reference, and token receipt or reference are compared
as inert metadata only. Queue replay does not enqueue, lease, complete, fail, or
cancel jobs.

## Report

The verifier emits a deterministic replay report containing:

- replay ID
- accepted flag
- replay match flag
- failure classification
- failure list
- receipt comparison hash
- content hash
- observation timestamp

Observation time is excluded from deterministic report hashes.

## Boundary

This milestone authorizes no automatic re-execution. It performs no command
execution, no arbitrary shell, no `shell=True`, no arbitrary argv or
command-line input, no network, no browser, no provider API calls, no
credential storage, and no production autonomy. It does not consume, revoke, or
issue tokens. It does not enqueue, lease, complete, fail, or cancel jobs. It
starts no daemon or scheduler and opens no browser.

## Merge Readiness

This branch can be reviewed independently as a descriptor-verification
contract. Any replay path that actually invokes the runner, token lifecycle, or
queue state machine must be a separate admitted implementation and is outside
Replay Engine V1.
