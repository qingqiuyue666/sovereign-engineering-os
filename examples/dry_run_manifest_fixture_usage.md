# Dry-Run Manifest Fixture Usage

## What This Fixture Is

The dry-run manifest fixture is a bounded non-executing dry-run manifest fixture
for the controlled single-file lifecycle line.

It exposes a static manifest-shaped result for human inspection and repository
validation. It is not an adapter, runtime, executor, service integration, or
write path.

## Fixture File

The fixture is exposed by:

- `examples/single_file_lifecycle_dry_run_manifest_fixture.py`

## Public Function

Call:

- `run_single_file_lifecycle_dry_run_manifest_fixture()`

## Safe Import/Read Snippet

```python
from examples.single_file_lifecycle_dry_run_manifest_fixture import run_single_file_lifecycle_dry_run_manifest_fixture

result = run_single_file_lifecycle_dry_run_manifest_fixture()

assert result["ok"] is True
assert result["mode"] == "dry_run_manifest_only"
assert result["status"] == "non_executing"
assert result["bounded_summary"]["stop_rule"] == "STOP_BEFORE_ADAPTER_IMPLEMENTATION"
```

This snippet imports only the existing dry-run manifest fixture function and
inspects returned fields. It does not write files, read files, call shell, use
network, mutate repository files, run lifecycle, run replay verifier, or invoke
tools.

## What The Fixture Proves

The fixture proves only:

- bounded manifest shape
- hard-false authority posture
- non-execution claim
- JSON-safe fixture output
- dry-run manifest wording

## What The Fixture Does Not Prove

The fixture does not prove:

- adapter implementation readiness
- adapter runtime readiness
- general runtime readiness
- service runtime readiness
- DB/repository/UoW readiness
- executor runtime readiness
- evidence/audit append readiness
- multi-file lifecycle readiness
- broad physical I/O readiness
- autonomous agent runtime readiness
- production automation platform readiness
- Business Delivery OS readiness
- Personal AI Execution OS readiness
- Creative Production OS readiness
- Research Decision OS readiness

## Authority Posture

- all authority flags remain false
- adapter implementation remains not authorized by default
- direct adapter implementation remains rejected
- STOP_BEFORE_ADAPTER_IMPLEMENTATION remains preserved
- APPROVE_DRY_RUN_MANIFEST_FIXTURE_NEXT remains preserved

## Forbidden Interpretation

The fixture must not be interpreted as:

- adapter implementation
- adapter runtime
- general runtime
- agent runtime
- service runtime
- autonomous executor
- production automation platform
- full AI execution OS
- multi-file patch system

## Forbidden Operations

The fixture does not authorize:

- adapter code
- CLI
- service calls
- DB/repository/UoW
- evidence/audit append
- executor dispatch
- restore service
- subprocess
- network
- tool execution
- multi-file lifecycle
- broad physical I/O
- durable writes
- irreversible actions
- new governance boundary family

## Validation

Canonical repository validation remains:

`make ci`

This usage document does not add new validation commands requiring new tools. It
does not suggest direct adapter execution.

## Next-Step Boundary

After this usage document, future work remains limited to:

- current phase alignment
- usage doc hardening only if concrete defects exist
- adapter implementation decision audit with expected rejection unless concrete
  hard blockers are proven

Do not proceed directly to adapter implementation.
