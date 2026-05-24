# Bounded Playwright Worker Adapter Draft V1

Status: draft adapter wrapper only.

## Decision

This change creates an adapter-draft wrapper around the already-merged
Playwright local fixture sandbox smoke from #420 only.

The draft proves that the worker-adapter-shaped contract can bind request
validation, output paths, manifests, task graph outputs, and human-review
metadata around the existing local fixture smoke. It does not create a general
browser automation adapter.

## Boundaries

This adapter draft:

- does not allow live websites
- does not accept arbitrary URLs
- does not allow account workflows
- does not allow login or registration workflows
- does not allow scraping
- does not allow bypass or captcha workflows
- does not use secrets or cookies
- does not install Playwright
- does not call `npm` or `npx`
- does not download browsers
- does not access or execute candidate repository code
- does not register a production adapter
- only proves the worker-adapter shape can wrap the local fixture smoke

All execution, when explicitly requested, remains delegated to the #420 bounded
local fixture smoke path. The wrapper adds no new subprocess path and accepts no
target URL.

## Registry

The registry entry is candidate-only and not production admitted. It is marked
local-fixture-only with explicit notes for no live websites, no arbitrary URLs,
human review required, and no production promotion.

## Next Allowed Directions

The next milestone may be an adapter review/admission gate for
local-fixture-only operation, or a real local execution receipt using installed
Playwright if an operator explicitly provides a local node/playwright
environment.

No live website automation is allowed until a separate policy, network,
credential, and target allowlist system exists.
