# Browser Playwright Real Package Admission

## Purpose

This admission package declares a future Playwright real transport candidate without installing Playwright, importing Playwright, launching a browser, or accessing the network.

It is a pre-admission artifact for human review before any real Playwright transport branch is allowed.

## Current Boundary

This branch must remain:

- candidate-only
- no dependency added
- no Playwright import
- no browser launch
- no external network
- loopback-only
- isolated temporary profile required for future transport
- no real user browser profile
- no persistent browser context
- no credential persistence
- no login
- no signup/account creation
- no payment
- no raw DOM persistence
- no screenshot payload persistence by default

## Admission Artifact

Build an admission package with:

```python
from pathlib import Path
from kernel.personal_ai.adapters.browser_playwright_real_package_admission import build_browser_playwright_real_package_admission

build_browser_playwright_real_package_admission(Path("outputs/playwright_admission"))
```

The package writes:

```text
browser_playwright_real_package_admission.json
browser_playwright_real_package_admission_verification.json
```

## Verification

The verification checks that the admission package remains candidate-only and that all dangerous runtime capabilities remain disabled.

## Not Allowed In This Branch

This branch must not:

- add Playwright to dependencies
- import Playwright
- call `sync_playwright` or `async_playwright`
- call `chromium.launch`, `firefox.launch`, or `webkit.launch`
- open external URLs
- use a real user profile
- persist credentials
- run login/signup/payment/account flows

## Future Branch

A future branch may add a real Playwright loopback transport. That branch must remain disabled by default, loopback-only, isolated-profile-only, credential-free, and excluded from normal external-network tests.
