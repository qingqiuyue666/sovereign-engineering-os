# Local-Fixture Human Approval Artifact v1

This decision records a metadata-only human approval artifact after the #431
local-fixture adapter execution-gate plan.

It is not an execution token.
It does not issue approval token.
It does not issue execution token.
It does not create a runner.
It does not create a runnable job.
It does not execute the adapter.
It does not execute Playwright.
It does not open a browser.
It does not access network.
It does not authorize live websites.
It does not authorize production.
It does not grant autonomy.
It does not support arbitrary URLs.
It does not support account/login/cookie/credential handling.
It does not support scraping/CAPTCHA/bypass/stealth.
It does not add package installation paths.
It does not promote a production adapter.
It does not add daemon/scheduler/worker loop.

The capability validates the #431 execution-gate plan result and records that a
human reviewer approved moving to a future separate runner-contract PR.

The only allowed state is human_review_metadata_record_only / metadata_only /
human_review_recorded / non_production / local_fixture_only /
execution_gate_plan_only.

Future execution remains blocked by a separate runner-contract PR, a separate
local-fixture runner gate before invocation, and a separate runner receipt after
any future runner invocation.
