# Browser Controlled Local Smoke Runner

## Purpose

This runner introduces a controlled browser local-smoke path without launching a real browser by default.

It validates a loopback-only browser smoke plan and can call an explicitly injected local browser transport.

## Boundary

The runner must remain:

- loopback-only
- disabled by default
- no external network
- no login
- no account creation
- no payment
- no credential persistence
- no browser profile access
- no raw DOM persistence
- no screenshot payload persistence by default

## Required Gates

To call an injected browser transport, all of these must be true:

1. Browser local smoke plan validates.
2. `allow_browser_smoke=True` is passed by the caller.
3. `SEOS_ENABLE_BROWSER_CONTROLLED_LOCAL_SMOKE=true` exists in the supplied environment.
4. Explicit `browser_transport` callable is supplied.

If any gate is missing, the runner writes a denial result and performs no browser transport call.

## Normal Tests

Normal tests do not launch a browser.

They only exercise:

- default denial
- missing environment flag denial
- missing transport denial
- fake injected transport success
- unsafe transport response validation
- malformed plan failure quarantine
- external URL and sensitive intent rejection

## Future Live Browser Runner

A later branch may add a Playwright or Selenium adapter, but it must remain disabled by default, loopback-only, credential-free, profile-isolated, and excluded from normal external-network tests.
