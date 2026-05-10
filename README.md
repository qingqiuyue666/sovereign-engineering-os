# Sovereign Engineering OS

Sovereign Engineering OS is an AI execution control kernel and local-first governance kernel.

Current phase/state: post `single-file-lifecycle-hardening-smoke-v1`.

Completed milestones:

- `repo-ci-canonical-health-gate-v1`
- `single-file-real-patch-lifecycle-foundation-v1`
- `single-file-lifecycle-hardening-smoke-v1`

Current capability:

- one repo-contained text file lifecycle
- explicit approval mapping
- proposal id / patch id / target path binding
- expected preimage identity binding
- preimage capture
- patch body persistence
- proposal, preimage, validation, and final seal artifacts
- caller-provided validation callable
- rollback on validation failure or exception
- bounded replay summary
- acceptance smoke

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

Next decision: controlled demo fixture, replay verifier design, or narrow adapter design.

Explicit stop rules:

- no multi-file expansion by default
- no service/DB/executor by default
- no new governance boundary family by default
- Business Delivery OS, Personal AI Execution OS, Creative Production OS, and Research Decision OS remain later
