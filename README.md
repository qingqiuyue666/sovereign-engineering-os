# Sovereign Engineering OS

Sovereign Engineering OS is an AI execution control kernel and local-first governance kernel.

Current phase/state: post `single-file-lifecycle-controlled-demo-fixture-v1`.

Completed milestones:

- `repo-ci-canonical-health-gate-v1`
- `single-file-real-patch-lifecycle-foundation-v1`
- `single-file-lifecycle-hardening-smoke-v1`
- `single-file-lifecycle-current-phase-update-v1`
- `single-file-lifecycle-replay-verifier-v1`
- `single-file-lifecycle-controlled-demo-decision-audit-v1`
- `single-file-lifecycle-controlled-demo-fixture-v1`

Current capability:

- canonical `make ci`
- GitHub Actions CI
- single-file lifecycle
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
- acceptance smoke

Controlled demo proves:

- successful apply path
- validation-failure rollback path
- replay verifier success
- existing lifecycle and existing verifier operate together

Still not authorized:

- service runtime
- service calls
- DB/repository/UoW writes
- evidence/audit append
- executor dispatch
- restore service execution
- multi-file lifecycle
- broad physical I/O
- durable writes
- irreversible actions

Canonical health command:

```sh
make ci
```

The local reference interpreter for this phase is Python 3.14.4, and GitHub CI uses the hosted Python 3.14 line through `actions/setup-python`.

Next decision:

- demo hardening
- demo usage doc
- narrow adapter decision audit

Explicit stop rules:

- no service/DB/executor by default
- no multi-file expansion by default
- no new governance boundary family by default
- Business / Personal / Creative / Research OS remain later
