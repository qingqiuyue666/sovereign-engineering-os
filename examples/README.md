# Controlled Single-File Lifecycle Demonstration

## Purpose

This example documents a controlled single-file lifecycle demonstration. It shows the existing single-file lifecycle and existing replay verifier operating together.

This is documentation for an existing demo.

This does not add runtime behavior.

This does not add CLI behavior.

This does not add service integration.

This does not add DB/repository/UoW integration.

This does not add executor behavior.

This does not add multi-file lifecycle behavior.

## What the demo uses

The controlled single-file lifecycle demonstration uses:

* `examples/single_file_lifecycle_demo.py`
* `run_controlled_single_file_lifecycle_demo`
* existing `run_single_file_patch_lifecycle`
* existing `verify_single_file_patch_lifecycle_replay`
* caller-provided `repo_root`
* caller-provided `artifact_root`
* repo-contained demo text files
* explicit approval mapping
* caller-provided validation callable behavior
* bounded JSON-safe output

## What the demo proves

The controlled single-file lifecycle demonstration proves, within its bounded example:

* successful apply path
* validation-failure rollback path
* artifact persistence
* final seal production
* replay verifier success
* existing lifecycle and existing verifier operate together

## What the demo does not prove

Readiness remains bounded by the existing lifecycle and replay verifier behavior shown in this controlled single-file lifecycle demonstration.

* The demo does not prove service runtime readiness.
* The demo does not prove DB/repository/UoW runtime readiness.
* The demo does not prove executor runtime readiness.
* The demo does not prove evidence/audit append readiness.
* The demo does not prove multi-file lifecycle readiness.
* The demo does not prove broad physical I/O readiness.
* The demo does not prove autonomous agent runtime readiness.
* The demo does not prove production automation platform readiness.

## How to run/read the demo safely

This documentation-only snippet imports and calls the existing `run_controlled_single_file_lifecycle_demo`. It does not require CLI behavior.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from examples.single_file_lifecycle_demo import run_controlled_single_file_lifecycle_demo


with TemporaryDirectory() as root:
    repo_root = Path(root)
    artifact_root = repo_root / "artifacts"
    result = run_controlled_single_file_lifecycle_demo(
        repo_root=repo_root,
        artifact_root=artifact_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
```

Expected result, at a high level:

* `ok` should be true.
* apply path should report `applied`.
* rollback path should report `rolled_back`.
* both verifier results should be ok.
* authority flags should remain false.

## Safe interpretation rules

* Treat the demo as a bounded proof of the existing single-file lifecycle.
* Do not treat it as approval for service calls.
* Do not treat it as approval for DB/repository/UoW writes.
* Do not treat it as approval for executor dispatch.
* Do not treat it as approval for evidence/audit append.
* Do not treat it as approval for multi-file lifecycle.
* Do not treat it as approval for broad physical I/O.
* Do not treat it as approval for durable writes or irreversible actions.

## Stop rules

* no service/DB/executor by default
* no multi-file expansion by default
* no new governance boundary family by default
* Business / Personal / Creative / Research OS remain later

## Validation

Existing canonical command remains `make ci`.

This docs-only package adds no tests.

The existing acceptance smoke covers the controlled demo fixture.
