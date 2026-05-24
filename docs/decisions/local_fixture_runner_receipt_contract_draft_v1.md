# Local-Fixture Runner Receipt Contract Draft v1

This decision records a contract draft only for a future local-fixture runner
receipt.

It is not a runner.
It does not create a runner stub.
It does not create a runnable job.
It does not issue approval material.
It does not issue execution material.
It does not execute the adapter.
It does not execute Playwright.
It does not open a browser.
It does not access the network.
It does not authorize live websites.
It does not support account, login, cookie, session, or credential handling.
It does not support scraping, CAPTCHA, bypass, or stealth behavior.
It does not accept arbitrary process invocation material.
It does not accept candidate repository runtime paths.
It does not promote production.
It does not add a daemon, scheduler, or worker loop.
It does not grant autonomy.

The contract draft defines only what a later local-fixture runner receipt must
contain. Future receipt implementation requires a separate PR. Future runner
stub implementation requires a separate PR.

Required future receipt inputs are verified runner stub admission gate result
path, verified human approval artifact result path, verified runner contract
draft result path, verified local fixture path, verified local fixture sha256,
output directory, runner invocation id, and reviewer/operator metadata.

Required future receipt outputs are local_fixture_runner_receipt.json,
local_fixture_runner_receipt_result.json,
local_fixture_runner_receipt_manifest.json,
local_fixture_runner_receipt_summary.md,
local_fixture_runner_receipt_checklist.md, artifact_index.json, and
artifact_index_manifest.json.

Required future receipt fields are receipt_type, runner_invocation_id, gate_id,
approval_artifact_id, runner_contract_id, local_fixture_path,
local_fixture_sha256, local_fixture_revalidated, local_fixture_exists,
local_fixture_regular_file, local_fixture_under_allowed_root,
adapter_execution_performed false, playwright_execution_performed false,
browser_open_performed false, network_access_performed false,
live_website_access_performed false, autonomous_execution_performed false,
production_promotion_granted false, runner_stub_metadata_recorded true,
receipt_recorded true, and metadata_only true.

Forbidden future receipt inputs include live URL, target URL, website, account,
credential, cookie, session, scraping target, CAPTCHA field, bypass flag,
stealth flag, arbitrary shell invocation material, arbitrary argument vector
material, Node package invocation material, browser startup invocation material,
Playwright freeform invocation material, candidate repository runtime path, and
production adapter id.

The only successful status is
local_fixture_runner_receipt_contract_draft_completed with decision
record_runner_receipt_contract_draft_only. The failure status is
local_fixture_runner_receipt_contract_draft_rejected with decision
reject_runner_receipt_contract_draft.

The next allowed action after success is
human_review_runner_receipt_contract_before_runner_stub_pr. The next allowed
action after failure is fix_runner_receipt_contract_draft_and_retry.
