# SEOS Examples

Examples in this repository are local, bounded demonstrations of existing SEOS
governance behavior. They are not authorization for OS automation, browser
control, RPA, live provider calls, autonomous AI execution, or secret access.
The controlled single-file lifecycle demonstration remains a bounded example,
not a runtime authority grant.

## Available Examples

- `examples/single_file_lifecycle_demo.py`: controlled single-file lifecycle
  demonstration using explicit approval mapping, validation callbacks, artifact
  persistence, rollback behavior, final seals, and replay verification.
- `examples/single_file_lifecycle_dry_run_manifest_fixture.py`: bounded
  non-executing dry-run manifest fixture.
- `examples/dry_run_manifest_fixture_usage.md`: documentation for reading the
  dry-run fixture safely.
- `examples/personal_ai_execution_os_v2_demo/`: historical local demo material;
  it must be interpreted through the current observation-mode boundary.

## Safe Interpretation

The examples show local evidence and governance behavior.

- This example does not prove service runtime readiness.
- This example does not prove DB/repository/UoW runtime readiness.
- This example does not prove executor runtime readiness.
- This example does not prove multi-file lifecycle readiness.
- This example does not prove broad physical I/O readiness.
- This example does not prove autonomous agent readiness.
- This example does not prove production automation readiness.
- This example does not prove commercial SaaS readiness.

## Run A Bounded Demo

```bash
PYTHONDONTWRITEBYTECODE=1 python3 examples/single_file_lifecycle_demo.py
```

## Validate Example Boundaries

```bash
python3 scripts/identity_boundary_check_v1.py
make ci
```

## Evidence Chain

| Claim | Risk | Control | Implementation | Validation command | Gate | Evidence artifact | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Examples are bounded | A demo may be mistaken for runtime authority | Safe interpretation rules | This README | `python3 scripts/identity_boundary_check_v1.py` | identity check | `examples/README.md` | Historical example names need context |
| Existing demo remains local | A reviewer may infer external service calls | Demo scope statement | Single-file lifecycle demo | `make ci` | tracer-bullet and acceptance tests | demo result artifacts | Demo proof is narrower than production operation |
