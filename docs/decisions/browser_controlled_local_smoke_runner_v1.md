# Browser Controlled Local Smoke Runner v1

## Verdict

`BROWSER_CONTROLLED_LOCAL_SMOKE_RUNNER_READY_FOR_LOCAL_TESTS`

This branch introduces a controlled local browser smoke runner.

It does not add Playwright, Selenium, external browser automation, external network access, login, payment, account creation, credential persistence, or browser profile access.

## Implemented

- Controlled local browser smoke runner.
- Loopback-only plan validation reuse.
- Explicit caller gate.
- Explicit environment gate: `SEOS_ENABLE_BROWSER_CONTROLLED_LOCAL_SMOKE=true`.
- Explicit injected browser transport requirement.
- Denial result artifacts.
- Failure quarantine for malformed plans.
- Tests for denial, fake transport success, unsafe transport response detection, and external URL / sensitive intent rejection.

## Required Gates Before Transport Call

All must be true:

1. Browser local smoke plan validates.
2. `allow_browser_smoke=True` is passed by the caller.
3. `SEOS_ENABLE_BROWSER_CONTROLLED_LOCAL_SMOKE=true` exists in the supplied environment.
4. Explicit `browser_transport` callable is supplied.

If any gate is missing, the runner writes a denial result and performs no browser transport call.

## Boundary Invariants

- loopback only
- no external network
- no login
- no payment
- no account creation
- no credential persistence
- no browser profile access
- no raw DOM persistence
- no screenshot payload persistence by default
- human review required

## Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_browser_controlled_local_smoke_runner -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Next Step

A later branch may add a disabled-by-default Playwright local adapter. It must remain loopback-only, profile-isolated, credential-free, excluded from normal external-network tests, and must not enable login/payment/account creation flows.
