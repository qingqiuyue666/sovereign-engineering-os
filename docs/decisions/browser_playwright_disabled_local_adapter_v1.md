# Browser Playwright Disabled Local Adapter v1

## Verdict

`BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER_READY_FOR_LOCAL_TESTS`

This branch introduces a disabled Playwright-like local adapter boundary for browser smoke execution.

It does not add a Playwright dependency, does not import Playwright, does not launch a real browser, does not access external network, does not use a real user profile, and does not allow login/payment/account creation flows.

## Implemented

- Disabled Playwright-like local adapter.
- Reuse of controlled local browser smoke runner.
- Explicit callsite gate.
- Explicit environment gate: `SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER=true`.
- Explicit injected Playwright-like transport requirement.
- Denial result artifacts.
- Failure quarantine for malformed plans.
- Tests for denial, fake transport success, unsafe response containment, and external URL / sensitive intent rejection.

## Required Gates Before Transport Call

All must be true:

1. Browser local smoke plan validates.
2. `allow_playwright_adapter=True` is passed by the caller.
3. `SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER=true` exists in the supplied environment.
4. Explicit `playwright_transport` callable is supplied.

If any gate is missing, the adapter writes a denial result and performs no transport call.

## Boundary Invariants

- no Playwright dependency added
- no Playwright import
- no real browser launch by default
- loopback only
- no external network
- no real user browser profile
- no persistent context
- no credential persistence
- no login
- no signup/account creation
- no payment
- no raw DOM persistence
- no screenshot payload persistence by default
- human review required

## Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_browser_playwright_disabled_local_adapter -v
python3 -m unittest tests.personal_ai.test_browser_controlled_local_smoke_runner -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Next Step

A later branch may add a real Playwright transport package. It must remain disabled by default, loopback-only, isolated-profile only, credential-free, excluded from normal external-network tests, and must not enable login/payment/account creation flows.
