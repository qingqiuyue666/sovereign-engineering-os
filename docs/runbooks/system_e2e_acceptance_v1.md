# System E2E Acceptance V1 Runbook

## Scope

System E2E Acceptance V1 proves the local runtime path from task creation
through worker admission, approval-gated controlled execution, queue evidence,
WAL evidence, artifact persistence, snapshot/replay reconstruction, operator
console readout, failure bundle evidence, watchdog evidence, corruption
fail-closed probes, and a signable final acceptance report.

## Procedure

1. Create a fresh local runtime root.
2. Run `FileBackedSystemE2EAcceptance(runtime_root=...).run(...)`.
3. Confirm the returned receipt is accepted and every gate in `gate_results` is
   accepted.
4. Confirm `system-e2e/reports/final-acceptance-report.json` and
   `system-e2e/receipts/final-acceptance-receipt.json` exist.
5. Confirm the final snapshot receipt verifies the final state and the operator
   console snapshot is read-only and `ok`.

## Required Gates

- task created
- worker admission
- approval gate
- queue submit
- WAL append
- lease/heartbeat
- controlled execution boundary
- artifact write
- snapshot create
- replay reconstruct
- operator console read
- failure bundle path
- watchdog path
- corrupted WAL fail-closed
- corrupted artifact fail-closed
- missing approval fail-closed
- replay final state verified
- final acceptance report signable

## Failure Handling

Any rejected gate makes the final receipt rejected. Corruption probes are kept
under `system-e2e/probes` and are not repaired. Missing approval is tested in an
isolated probe runtime and must fail before execution is performed.
