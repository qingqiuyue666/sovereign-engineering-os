# Replay Engine V1

## Scope

Replay Engine V1 adds a standalone descriptor verifier for local runner replay
evidence. It compares supplied receipts and replay descriptors; it does not
rerun the command.

## Dependency Status

This milestone has a semantic dependency on Real Local Runner Boundary V1
because future concrete replay manifests will come from that runner. This
branch does not import or depend on unmerged runner source. Concrete runner
receipt integration remains deferred until the runner boundary is merged.

## Comparisons

The verifier compares:

- source receipt digest to candidate receipt digest
- expected environment digest to actual environment digest
- expected command ID to actual command ID
- expected argv hash to actual argv hash
- expected output digest to actual output digest
- expected exit code to actual exit code

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
credential storage, and no production autonomy.

## Merge Readiness

This branch can be reviewed independently as a descriptor-verification
contract. Any replay path that actually invokes the runner must wait for a
separate admitted implementation after the runner boundary is merged.
