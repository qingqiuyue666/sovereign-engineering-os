# Real Execution Evidence Program V1

## Claim

Dry-run plans cannot prove real local creative production. SEOS therefore
needs a narrow evidence program that materializes files under governance.

## Risk

The evidence program could weaken the existing creative boundary if it implied
full DCC automation, paid-asset handling, or uncontrolled local execution.

## Control

The first proof is intentionally small:

1. Approved task metadata exists.
2. A digest-bound execution permit is issued.
3. A bounded local adapter runs.
4. A real output file is written only inside the permitted output root.
5. Output hashes are recorded.
6. A result envelope and creative materialization record are produced.

## Implementation

V1 includes:

- fake-DCC CI adapter for deterministic real file materialization
- optional Houdini/hython adapter contract
- execution permit schema and validation
- execution result schema
- creative materialization schema
- evidence collector writing result and materialization JSON

## Validation command

```bash
python3 scripts/creative_real_execution_evidence_check_v1.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_execution_evidence_integration_v1 -v
```

## Gate

CI must pass with no paid DCC installed. Optional Houdini/hython smoke is not a
default CI requirement.

## Evidence artifact

The evidence collector writes execution results under an execution evidence
root and materialization records under a creative materialization root. Public
result fields use relative paths, output-root labels, and hashes rather than
private absolute machine paths.

## Residual risk

The fake-DCC adapter proves the execution evidence chain, not production art
quality. Real Houdini, ComfyUI, Blender, After Effects, DaVinci, Unreal, and
cross-DCC shot loops remain later phases.

