# Browser Playwright Disabled Local Adapter

## Purpose

This adapter introduces a Playwright-like local adapter boundary without importing Playwright or launching a real browser by default.

It wraps the existing controlled local browser smoke runner and accepts only an explicit injected Playwright-like transport.

## Boundary

The adapter must remain:

- disabled by default
- loopback-only
- no external network
- no Playwright dependency added
- no Playwright import
- no real user browser profile
- no persistent context
- no credential persistence
- no login
- no signup/account creation
- no payment
- no raw DOM persistence
- no screenshot payload persistence by default

## Required Gates

To call an injected Playwright-like transport, all of these must be true:

1. Browser local smoke plan validates.
2. `allow_playwright_adapter=True` is passed by the caller.
3. `SEOS_ENABLE_BROWSER_PLAYWRIGHT_DISABLED_LOCAL_ADAPTER=true` exists in the supplied environment.
4. Explicit `playwright_transport` callable is supplied.

If any gate is missing, the adapter writes a denial result and performs no transport call.

## Normal Tests

Normal tests do not import Playwright and do not launch a browser.

They only exercise:

- default denial
- missing environment flag denial
- missing transport denial
- fake injected transport success
- unsafe response containment through controlled local runner validation
- malformed plan failure quarantine
- external URL and sensitive intent rejection

## Future Playwright Adapter

A later branch may add a real Playwright transport package. It must remain disabled by default, loopback-only, isolated-profile only, credential-free, excluded from normal external-network tests, and must not enable login/payment/account creation flows.
