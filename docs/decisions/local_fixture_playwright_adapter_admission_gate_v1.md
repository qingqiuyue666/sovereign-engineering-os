# Local-Fixture Playwright Adapter Admission Gate v1

Status: accepted

This PR adds a local-fixture-only admission / rejection gate based on #422
receipt evidence. The gate consumes the operator-provided Playwright execution
receipt directory, validates receipt, adapter draft, embedded smoke, artifact
index, and hash evidence, and emits a deterministic admission or rejection
decision.

This gate does not execute Playwright. It does not execute Node. It does not
create browser automation. It does not accept URLs. It does not access live
websites. It does not do accounts, login, or registration. It does not scrape.
It does not bypass or handle captcha. It does not read secrets or cookies. It
does not run npm, npx, install, or download logic. It does not access or execute
candidate repository code. It does not register a production adapter. It does
not grant production promotion.

Local-fixture-only admission is not production admission. The only admission
the gate may grant is for the bounded Playwright worker adapter draft in the
local-fixture-only lane under human review. Production admission, live website
admission, general browser automation admission, arbitrary URL navigation,
account workflows, scraping, bypass, captcha workflows, secrets, cookies,
external network, package installation, package runners, candidate repository
access, candidate code import/execution, arbitrary commands, production
promotion, and autonomous execution remain denied.

Live website automation remains blocked until separate policy, network,
credential, target allowlist, legal/ToS, abuse-prevention, and human approval
systems exist.

Next milestone may be:

1. stronger local fixture scenario suite
2. local-only browser-control regression pack
3. admission receipt aggregation across multiple local fixture runs
