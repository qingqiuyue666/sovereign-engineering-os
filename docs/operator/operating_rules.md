# Operating Rules

## Default Mode

Default mode is local-first, deterministic, private operator support. The repository should produce reports, handoff packets, plans, and boundaries without enabling autonomous execution.

## Branch Discipline

- Start from latest `main`.
- Use a dedicated branch for each implementation window.
- Keep changes reviewable and tied to the requested priority.
- Do not rename public APIs.

## Test Discipline

- Add tracer-bullet coverage for every new Python module.
- Use `unittest`.
- Run the required tests before claiming success.
- Report exact failures if any command does not pass.

## Merge Discipline

- Merge only after verification passes.
- Preserve governance, security, classification, task manifest, CLI, audit, evidence, provider transport, local runtime, review gate, durable stores, code audit workbench, public asset manifest, health, and CI contracts.
- Do not modify the root README, Makefile, root integrity manifests, or health gate wiring in this slice.

## No-Kernel-Expansion Rule

Abstract kernel expansion is frozen. A new runtime module is allowed only when it directly supports an output asset, deterministic validator, private report, planning contract, or safety boundary requested by the operator.

## Output-Asset Priority

Private reports, manifests, workbench plans, handoff packets, and boundary documents come before new runtime behavior. Prefer docs plus deterministic validators over runtime abstractions.

## AI Worker Rules

- Read the private operator command center first.
- Use caller-provided material.
- Do not discover or transmit private state through external services.
- Do not persist raw prompts or raw model/provider responses.
- Do not weaken blocked capability language.

## Human Approval Rules

- Human review is required before merge.
- Human review is required before any future unblock of provider execution, production autonomy, external actions, financial execution, or trading automation.
- Operator preference alone does not enable a blocked capability.

## Failure Handling

- Every failure path fails closed.
- Invalid material raises a validation error.
- Missing required fields raise a validation error.
- Invalid digest fields raise a validation error.
- Forbidden fields raise a validation error.

## Recovery Handling

- Recovery remains operator-controlled and non-mutating for this private documentation layer.
- Rollbacks should revert the affected private docs and validators together.
- Durable stores must not be mutated by these private report contracts.
