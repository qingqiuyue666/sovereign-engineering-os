# Controlled Execution Local Smoke V1

## Claim

An operator can run a local controlled execution smoke without installing a
paid DCC tool.

## Risk

Local smoke commands could be confused with uncontrolled computer control.

## Control

The smoke uses only the fake-DCC adapter. It requires a permit, writes inside a
temporary output root, records hashes, and returns an execution result envelope.

## Implementation

Run:

```bash
python3 scripts/execution_permit_check_v1.py
python3 scripts/controlled_executor_smoke_v1.py
python3 scripts/creative_real_execution_evidence_check_v1.py
```

Optional local Houdini/hython smoke:

```bash
python3 scripts/optional_houdini_hython_smoke_v1.py
```

If `hython` is unavailable, the optional smoke reports a skipped or blocked
state and exits successfully. It is not part of default CI.

## Validation command

```bash
make controlled-executor-smoke
make creative-real-execution-evidence-check
```

## Gate

The local smoke must not require network access, cloud services, Docker, paid
assets, or a real DCC installation.

## Evidence artifact

The smoke verifies an output file, output SHA256, execution result envelope,
and creative materialization record.

## Residual risk

The fake-DCC smoke is a production-mechanics proof. It is not a claim of full
DCC pipeline completion.

