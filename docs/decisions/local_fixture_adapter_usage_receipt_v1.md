# Local-Fixture Adapter Usage Receipt v1

This decision records only one local-fixture-only usage receipt after the #428
admission-gated local adapter registry promotion. It is evidence binding, not
execution.

The receipt validates the #428 promotion result, validates a local fixture file
path and hash under the operator-provided output directory, and writes a receipt
for human review. It does not execute the adapter, does not execute Playwright,
and does not open the fixture in a browser.

It does not execute #422. It does not execute #424. It does not execute #425.
It does not execute #426. It does not execute #427. It does not execute #428.
It only reads existing evidence artifacts and supplied local fixture metadata.

It does not enable production. It does not enable live websites. It does not
enable general browser automation. It does not enable arbitrary URLs. It does
not enable account/login/registration flows. It does not enable scraping. It
does not enable bypass/captcha. It does not access secrets/cookies.

It does not run npm/npx/install/browser download. It does not execute candidate repository code.
It does not import candidate repository code. It does not grant autonomy.

Boundary statements:

- does not enable production
- does not enable live websites
- does not enable general browser automation
- does not enable arbitrary URLs
- does not enable account/login/registration flows
- does not enable scraping
- does not enable bypass/captcha
- does not access secrets/cookies
- does not run npm/npx/install/browser download
- does not grant autonomy

The only allowed state is:

- local_fixture_only
- one_usage_receipt_only
- human_review_required
- aggregation_bound
- regression_bound
- non_production

Future live website work remains blocked by separate policy, legal, network, credential, and human-approval gates.
