# Sovereign Engineering OS

Sovereign Engineering OS is an AI execution control kernel and local-first governance kernel.

Current phase/state: post `single-file-lifecycle-narrow-adapter-design-v1`.

Completed milestones:

- `repo-ci-canonical-health-gate-v1`
- `single-file-real-patch-lifecycle-foundation-v1`
- `single-file-lifecycle-hardening-smoke-v1`
- `single-file-lifecycle-current-phase-update-v1`
- `single-file-lifecycle-replay-verifier-v1`
- `single-file-lifecycle-controlled-demo-decision-audit-v1`
- `single-file-lifecycle-controlled-demo-fixture-v1`
- `single-file-lifecycle-demo-current-phase-update-v1`
- `single-file-lifecycle-demo-usage-doc-decision-audit-v1`
- `single-file-lifecycle-demo-usage-doc-v1`
- `single-file-lifecycle-demo-hardening-decision-audit-v1`
- `single-file-lifecycle-demo-hardening-v1`
- `single-file-lifecycle-narrow-adapter-decision-audit-v1`
- `single-file-lifecycle-narrow-adapter-design-v1`

Current capability:

- canonical `make ci`
- GitHub Actions CI
- controlled single-file lifecycle
- explicit approval mapping
- preimage capture
- patch body persistence
- local artifacts
- validation callable
- rollback on validation failure or exception
- final seal
- bounded replay summary
- read-only replay verifier
- controlled demo fixture
- demo usage documentation
- demo hardening
- docs/design-only narrow adapter concept
- acceptance smoke

Controlled demo proves:

- successful apply path
- validation-failure rollback path
- replay verifier success
- existing lifecycle and existing verifier operate together

Narrow adapter design:

- docs/design-only
- dry-run/manifest-only concept
- non-executable
- non-authorizing
- not adapter implementation

Adapter implementation remains not authorized by default.

Still not authorized:

- service runtime
- service calls
- DB/repository/UoW writes
- evidence/audit append
- executor dispatch
- restore service execution
- adapter implementation
- CLI adapter
- tool execution
- shell/subprocess execution
- network execution
- multi-file lifecycle
- broad physical I/O
- durable writes
- irreversible actions
- Business Delivery OS
- Personal AI Execution OS
- Creative Production OS
- Research Decision OS

Canonical health command:

```sh
make ci
```

The local reference interpreter for this phase is Python 3.14.4, and GitHub CI uses the hosted Python 3.14 line through `actions/setup-python`.

Next decision:

- narrow adapter implementation decision audit
- dry-run manifest fixture decision audit
- stop/consolidation audit before adapter implementation

Explicit stop rules:

- no service/DB/executor by default
- no adapter implementation by default
- no CLI adapter by default
- no tool, shell/subprocess, or network execution by default
- no multi-file expansion by default
- no broad physical I/O by default
- no new governance boundary family by default
- Business / Personal / Creative / Research OS remain later
