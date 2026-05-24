# Local-Fixture Runner Contract Draft v1

This decision records a contract draft only.

It is not a runner.
It does not create a runnable job.
It does not issue approval token material.
It does not issue execution token material.
It does not execute the adapter.
It does not execute Playwright.
It does not open a browser.
It does not access the network.
It does not authorize live websites.
It does not authorize arbitrary URLs.
It does not support account, login, cookie, session, or credential handling.
It does not support scraping, CAPTCHA, bypass, or stealth behavior.
It does not add npm/npx install paths.
It does not expose a freeform browser or Playwright invocation surface.
It does not accept candidate repository runtime paths.
It does not promote a production adapter.
It does not add a daemon, scheduler, or worker loop.
It does not grant autonomy.

The contract draft defines only what a later local-fixture-only runner would be
allowed to accept and emit. Future implementation requires a separate PR.
Future runner receipt artifacts require a separate PR.

Allowed future inputs are limited to verified human approval artifact path,
verified execution gate plan path, verified local fixture path, verified local
fixture sha256, output directory, runner invocation id, and reviewer/operator
metadata.

Forbidden future inputs include live URL, target URL, website, account,
credential, cookie, session, scraping target, CAPTCHA field, bypass flag,
stealth flag, arbitrary shell command, arbitrary argv, npm command, npx command,
browser launch command, Playwright freeform command, candidate repository
runtime path, and production adapter id.

Required future outputs are runner receipt JSON, runner receipt manifest, local
artifact index, local artifact index manifest, summary markdown, and checklist
markdown.

The only successful status is
local_fixture_runner_contract_draft_completed with decision
record_runner_contract_draft_only. The failure status is
local_fixture_runner_contract_draft_rejected with decision
reject_runner_contract_draft.

The next allowed action after success is
human_review_runner_contract_before_local_fixture_runner_stub_pr. The next
allowed action after failure is fix_runner_contract_draft_and_retry.
