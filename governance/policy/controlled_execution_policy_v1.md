# Controlled Execution Policy V1

## Purpose

This policy admits a narrow controlled-execution evidence program for SEOS.
The program exists to close a hard evidence blocker: SEOS cannot prove real
local creative execution when it has no controlled execution plane.

## Boundary

SEOS remains the control plane. It records task intent, approval state,
execution permits, evidence, replay context, failure bundles, and validation.
The controlled executor is a bounded local worker. It is not autonomous
authority, not RPA, not desktop control, not browser automation, not a host
sandbox, and not a secret manager.

## Permit Gate

Every execution requires an approved task reference and a valid execution
permit. The permit binds:

- permit ID and task ID
- operator approval receipt ID
- adapter and action
- input roots and output root
- write scope
- runtime, file-count, and byte budgets
- evidence requirements
- deterministic permit digest

Tampering with permit material must change the digest and fail validation.

## Default Denials

Network access defaults to false.

Destructive actions default to false.

Writes are restricted to one output directory.

Reads are restricted to declared input roots.

Long jobs require explicit runtime budget in the permit.

Every execution must return an execution result envelope with output hashes,
stdout/stderr digests, terminal status, and policy blocks when applicable.

## CI Boundary

Default CI must pass without Houdini, Blender, ComfyUI, After Effects, DaVinci
Resolve, Unreal Engine, ZBrush, Docker, cloud services, or paid assets.

The fake-DCC adapter is the CI-safe worker proof. Optional real DCC smoke tests
must skip or return a blocked result when local tools or licenses are missing.

## Observation-Mode Bridge

Observation mode remains a no-expansion posture by default. This policy is a
single narrow exception only because the missing controlled execution plane is
a hard evidence blocker for real local creative production evidence. The
exception does not reopen general product development, item continuation,
runtime expansion, cloud-first dependencies, or any RPA/computer-control
repositioning.

