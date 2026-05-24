# Local-Only Playwright Fixture Scenario Suite v1

This PR adds a local-only Playwright fixture scenario suite.

The suite relies on the existing #422 operator-provided receipt path for
execution evidence. Each runtime scenario delegates to that receipt path and
then evaluates the generated receipt, bounded adapter draft, embedded smoke,
artifact index, and hash evidence.

This does not create live website automation. It does not create general
browser automation. It does not accept URLs. It does not access live websites.
It does not do accounts, login, or registration. It does not scrape. It does
not bypass or support captcha workflows. It does not read secrets or cookies.
It does not run package-manager commands, install dependencies, or download
browsers. It does not access or execute candidate repository code. It does not
register a production adapter. It does not grant production promotion.

The suite produces local-fixture-only regression evidence. Local fixture
scenario suite success is not production admission.

Live website automation remains blocked until separate policy, network,
credential, target allowlist, legal/ToS, abuse-prevention, and human approval
systems exist.

Next milestone may be:

1. Admission receipt aggregation across multiple local fixture suite runs.
2. Local-only browser-control regression pack.
3. Stricter scenario content injection after #420 fixture generator is safely
   parameterized.
