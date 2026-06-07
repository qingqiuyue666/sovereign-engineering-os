# SEOS Execution Plane V1

## Claim

SEOS now has a minimal controlled local execution-plane foundation.

## Risk

Adding process execution can be mistaken for autonomous authority, host
sandboxing, RPA, or desktop control.

## Control

Execution is separated from the SEOS control plane and allowed only through an
execution permit. The permit binds task ID, approval receipt, adapter, action,
output root, resource budgets, network denial, destructive-action denial, and
required evidence.

## Implementation

The V1 package is `execution_plane/`:

- `permits/` builds and validates digest-bound execution permits.
- `runner/` runs bounded subprocesses with timeouts, path checks, output
  collection, and result envelopes.
- `adapters/fake_dcc.py` materializes real CI-safe files.
- `adapters/houdini_hython.py` provides an optional local Houdini/hython
  contract that blocks or skips when the tool is unavailable.
- `evidence/` writes execution result envelopes and creative materialization
  records.

The execution plane is logically external to the SEOS control plane even though
it lives in the same repository for V1.

## Validation command

```bash
python3 scripts/execution_permit_check_v1.py
python3 scripts/controlled_executor_smoke_v1.py
python3 scripts/creative_real_execution_evidence_check_v1.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_execution_permit_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_controlled_process_runner_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_fake_dcc_adapter_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_execution_evidence_integration_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_houdini_adapter_contract_v1 -v
```

## Gate

Default CI uses the fake-DCC adapter only. Houdini/hython smoke is optional and
environment-gated.

## Evidence artifact

Execution evidence is represented by:

- `execution_plane/schemas/execution_permit_v1.json`
- `execution_plane/schemas/execution_result_v1.json`
- `creative/schemas/creative_materialization_v1.json`
- `reports/execution_plane/.gitkeep`
- `reports/creative/materializations/.gitkeep`

## Residual risk

Fake-DCC proves permit, runner, evidence, and materialization mechanics. It
does not prove artistic output quality or full cross-DCC production readiness.
Real DCC evidence remains optional and local-environment dependent.

