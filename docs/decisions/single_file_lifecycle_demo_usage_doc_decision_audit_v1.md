# Single-File Lifecycle Demo Usage Doc Decision Audit V1

## Scope

This is a decision audit only.

This decision audit decides whether the next implementation package should be
`single-file-lifecycle-demo-usage-doc-v1`.

This does not implement the usage doc. This does not add
`examples/README.md`. This does not change production code. This does not
change tests. This does not change acceptance tests. This does not change
examples. This does not change the controlled demo file. This does not change
lifecycle implementation. This does not change replay verifier.

This does not add adapter. This does not add CLI. This does not add service
calls. This does not add DB/repository/UoW. This does not add evidence/audit
append. This does not add executor dispatch. This does not add restore service.
This does not add subprocess. This does not add network. This does not add
daemon/server/queue. This does not add multi-file lifecycle. This does not add
broad physical I/O. This does not add a new governance boundary family.

This is not Business Delivery OS. This is not Personal AI Execution OS. This
is not Creative Production OS. This is not Research Decision OS.

## Checkpoint Basis

Current required checkpoint:

- `single-file-lifecycle-demo-current-phase-update-v1`
  - target: `ca02abdf9de9442ba1edef1480cddc8366f9c601`

Previous checkpoints:

- `single-file-lifecycle-controlled-demo-fixture-v1`
  - target: `d852e3f6e7f07d8414433101bcd822e7f2c8f583`
- `single-file-lifecycle-controlled-demo-decision-audit-v1`
  - target: `cc5ab348b42754c591ba1872b070578e6081fc46`
- `single-file-lifecycle-replay-verifier-v1`
  - target: `22a1a6f512dfc999df0399bef4b4f2dd7c170b10`
- `single-file-lifecycle-current-phase-update-v1`
  - target: `5efc8eaa68a3ea57a23282dfa61c523fb7cde9e5`
- `single-file-lifecycle-hardening-smoke-v1`
  - target: `2f0c8f91f53a1bee0a9dd5fd40e3e3872a0b7cf2`
- `single-file-real-patch-lifecycle-foundation-v1`
  - target: `7edcbc69534845a6bb3c870b370daedf38db9662`
- `repo-ci-canonical-health-gate-v1`
  - target: `11c5613637ad47a7e3493fda5377394fc604f2d2`

The decision below assumes those checkpoint tags resolve exactly to the listed
targets before any future usage document package begins.

## Decision Questions

1. Whether the next implementation package should be
   `single-file-lifecycle-demo-usage-doc-v1`?

Yes. The controlled demo fixture exists, the lifecycle and replay verifier are
already wired together, and the next safest package is a human-readable usage
boundary before demo hardening or adapter decisions.

2. Whether the usage doc package must be limited to `examples/README.md`?

Yes. The future usage doc package must be limited to `examples/README.md`.
It must not change production code, tests, acceptance tests, examples code,
the controlled demo file, lifecycle implementation, replay verifier, README,
`docs/current_phase.md`, CI workflow, Makefile, pyproject, or governance specs.

3. Whether the usage doc must describe the demo only as
   `a controlled single-file lifecycle demonstration`?

Yes. The future usage doc must describe the demo only as
`a controlled single-file lifecycle demonstration`.

The future usage doc must forbid describing the demo as:

- general runtime
- agent runtime
- service runtime
- autonomous executor
- full AI execution OS
- multi-file patch system
- production automation platform

4. Whether the usage doc must explain how to run/read the demo safely without
   adding CLI/runtime behavior?

Yes. The future usage doc must explain how to run and read the existing
controlled demo safely without adding CLI behavior, runtime behavior, service
behavior, DB behavior, executor behavior, subprocess behavior, network behavior,
daemon/server/queue behavior, multi-file behavior, or broad physical I/O.

5. Whether the usage doc must explain what the demo proves?

Yes. The future usage doc must explain that the demo proves:

- successful apply path
- validation-failure rollback path
- artifact persistence
- final seal production
- replay verifier success
- existing lifecycle and existing verifier operate together

6. Whether the usage doc must explain what the demo does not prove?

Yes. The future usage doc must explain that the demo does not prove:

- not service runtime
- not DB/repository/UoW runtime
- not executor runtime
- not evidence/audit append
- not multi-file lifecycle
- not broad physical I/O
- not autonomous agent runtime
- not production automation platform

7. Whether the usage doc must preserve stop rules?

Yes. The future usage doc must preserve these stop rules:

- no service/DB/executor by default
- no multi-file expansion by default
- no new governance boundary family by default
- Business / Personal / Creative / Research OS remain later

8. Whether the usage doc should be covered only by existing `make ci` and diff
   checks, without adding new tests?

Yes. The future usage doc should be covered only by existing `make ci`,
`git diff --check`, and scope inspection. It should not add new tests or
acceptance tests.

## Future Package Boundary

The approved next implementation package, if taken, is:

- `single-file-lifecycle-demo-usage-doc-v1`

The only allowed implementation file for that package is:

- `examples/README.md`

That package must remain documentation-only. It must not implement demo
hardening, adapter decisions, production lifecycle changes, replay verifier
changes, service calls, DB/repository/UoW behavior, evidence/audit append,
executor dispatch, restore service execution, subprocess use, network use,
daemon/server/queue behavior, multi-file lifecycle, broad physical I/O, or a
new governance boundary family.

## Strategic Boundary

The controlled demo fixture is complete enough to justify a human-readable
usage boundary. The usage boundary should be frozen before demo hardening,
adapter decision work, or any later runtime-facing package.

This decision keeps service runtime, DB/repository/UoW runtime, executor
runtime, evidence/audit append, multi-file lifecycle, broad physical I/O,
autonomous agent runtime, and production automation platform claims out of
scope.

## Verdict

APPROVE_DEMO_USAGE_DOC_NEXT
