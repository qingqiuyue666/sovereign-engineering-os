# Domain Adapter Foundation V1

## Scope

Domain Adapter Foundation V1 defines contract-only descriptors for future
ComfyUI, Houdini, Blender, Unreal, DaVinci Resolve, After Effects, and generic
local adapters.

## Descriptor Set

- State proxy descriptor: records digest-only state summaries and allowed
  observation classes.
- Operation plan descriptor: records planned operation class, input asset
  bindings, planned outputs, and non-runtime controls.
- Asset hash binding: binds source and output references to SHA-256 digests
  without copying raw asset payloads.
- Output manifest contract: requires hash-bound outputs in a new artifact
  directory and forbids source overwrite.
- Provenance policy: requires source asset hashes, operation plan hash, adapter
  version, human approval reference, and output manifest evidence.
- Replay policy: requires descriptor, command or operation match, asset digest
  match, environment digest, and output digest comparison.
- Adapter admission rules: keep every family in candidate state until a future
  explicit admission milestone.

## Boundary Statement

No live DCC execution is admitted by this milestone.

This foundation does not execute ComfyUI, Houdini, Blender, Unreal, DaVinci
Resolve, After Effects, or any other DCC software. It does not launch
subprocesses, access networks, call provider APIs, download assets, mutate
source assets, overwrite source files, store credentials, or enable production
autonomy.

## Future Admission

Future adapter milestones must bind to these descriptors and still pass their
own admission gates. A contract that enables live DCC execution, process launch,
network access, source overwrite, automatic replay execution, arbitrary command
control, or arbitrary Python control is invalid for this foundation.

## Review Notes

- Governance descriptor:
  `governance/domain/domain_adapter_foundation_v1.json`
- Python contract module:
  `kernel/domain/domain_adapter_foundation.py`
- Focused validation:
  `python3 -m unittest tests.tracer_bullet.test_domain_adapter_foundation_v1 -v`
