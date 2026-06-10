# Operator-Provided Playwright Execution Receipt V1

Status: receipt layer only.

## Decision

This change adds a receipt layer around the already-merged bounded Playwright
worker adapter draft from #421 only.

The receipt records operator-provided local execution evidence: the supplied
local executable path, runner script path, generated receipt artifacts, bounded
adapter draft wrapper artifacts, embedded local fixture smoke artifacts, success
or failure evidence, and relevant SHA-256 hashes. It only proves local
`file://` fixture execution using an operator-supplied local runtime.

## Boundaries

This receipt:

- does not create a browser automation system
- does not install Playwright
- does not download browsers
- does not run `npm` or `npx`
- does not accept URLs
- does not access live websites
- does not do accounts, login, or registration
- does not scrape
- does not bypass or handle captcha workflows
- does not read secrets or cookies
- does not access or execute candidate repository code
- does not register a production adapter
- records operator-provided local execution evidence only
- proves local `file://` fixture execution only through the #421 wrapper

The receipt delegates to
`run_bounded_playwright_worker_adapter_draft` with the embedded local fixture
smoke enabled. It adds no new browser execution path and no general browser
automation surface.

## Next Allowed Directions

The next milestone may be one of:

- local-fixture-only adapter admission or rejection gate based on this receipt
- stronger local fixture scenario suite
- local-only browser-control regression pack

Live website automation remains blocked until separate policy, network,
credential, target allowlist, legal/ToS, abuse-prevention, and human approval
systems exist.
