# Local-Fixture Adapter Execution Gate Plan v1

This decision records only an execution-gate plan after the #430 dry-run
invocation plan.

It does not approve execution.
It does not issue approval token.
It does not create an execution runner.
It does not execute the adapter.
It does not execute Playwright.
It does not open a browser.
It does not execute #422/#424/#425/#426/#427/#428/#429/#430.
It does not enable production.
It does not enable live websites.
It does not enable general browser automation.
It does not enable arbitrary URLs.
It does not enable account/login/registration flows.
It does not enable scraping.
It does not enable bypass/captcha.
It does not access secrets/cookies.
It does not run npm/npx/install/browser download.
It does not execute candidate repository code.
It does not grant autonomy.

The capability only validates the #430 dry-run plan and local fixture file
path/hash, then writes a non-executable execution-gate plan plus human approval
request.

The only allowed state is execution_gate_plan_only / dry_run_plan_bound /
local_fixture_only / one_usage_receipt_bound / human_approval_request_only /
human_review_required / aggregation_bound / regression_bound / non_production.

Future execution remains blocked by a separate human approval artifact and a
separate execution runner PR.
