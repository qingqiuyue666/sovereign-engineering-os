# Playwright Local Fixture Bounded Sandbox Smoke v1

## Decision

Add the first execution-facing step for the #419 selected candidate,
`microsoft/playwright`, as a bounded local fixture sandbox smoke.

Plan-only mode is default. The smoke executes only local fixture pages when
explicitly requested with `--execute-local-fixture-smoke`, `--node-command`, and
`--runner-script`.

## Scope

The Python harness validates the #419 selection matrix and Playwright candidate
manifest, generates deterministic fixture files under the requested existing
`output_dir`, and writes hash-bound plan, manifest, summary, checklist, fixture,
result, and artifact-index outputs.

The fixture contains the marker
`SOVEREIGN_PLAYWRIGHT_LOCAL_FIXTURE_SMOKE_MARKER`, a `#smoke-button`, and a
`#smoke-status` element that becomes `clicked` after the button is clicked.
The target URL is generated internally as `file://` from the fixture path.

## Non-Actions

This PR does not access live websites.

It does not do account workflows.

It does not scrape.

It does not bypass.

It does not use secrets.

It does not install dependencies.

It does not use `npx` or `npm`.

It does not download browsers.

It does not approve Playwright for production.

It does not generate adapters.

It does not register adapters.

It does not access, import, execute, or mutate candidate repository code.

## Runner Boundary

The JS runner is an owned local smoke runner at
`tools/playwright/local_fixture_smoke_runner.js`. It accepts only
`--fixture-url`, `--output-json`, and `--screenshot-path`, rejects non-`file://`
fixture URLs, and records any non-local request as a failure.

If Playwright is missing, the runner fails clearly with
`playwright_dependency_missing`.

The Python tests do not require Playwright to be installed and use a
deterministic fake executable/runner for execution-path coverage.

## Interpretation

A successful smoke only proves local fixture browser-control viability. It does
not prove live website safety, account workflow safety, scraping safety,
bypass safety, credential safety, dependency-install safety, license approval,
adapter readiness, or production readiness.

## Next Milestone

After a passing smoke, the next milestone may be a bounded Playwright worker
adapter draft, but only for local fixture pages first.
