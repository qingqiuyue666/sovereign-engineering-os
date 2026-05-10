# Sovereign Engineering OS

Sovereign Engineering OS is an AI execution control kernel and local-first governance kernel.

Current phase: `repo-ci-canonical-health-gate-v1`.

The repository is not runtime-ready. No service runtime is authorized, no service calls are authorized, no DB writes are authorized, no executor dispatch is authorized, and no physical I/O is authorized.

Canonical health command:

```sh
make ci
```

The local reference interpreter for this phase is Python 3.14.4, and GitHub CI uses the hosted Python 3.14 line through `actions/setup-python`.

The next strategic phase after this repository health gate is the single-file real patch lifecycle.

Governance rule: do not open a new governance boundary family unless the repo health gate or single-file lifecycle proves a concrete blocker.
