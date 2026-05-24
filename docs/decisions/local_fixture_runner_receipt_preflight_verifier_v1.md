# Local-Fixture Runner Receipt Preflight Verifier v1

This decision records a metadata-only preflight verifier for future
local-fixture runner receipt work.

It is a metadata-only preflight verifier.
It is not a runner.
It is not a runner stub.
It does not create a runnable job.
It does not issue approval material.
It does not issue execution material.
It does not execute the adapter.
It does not launch Playwright.
It does not open a browser.
It does not access the network.
It does not authorize live websites.
It does not authorize production.

The verifier reads only the existing local-fixture human approval artifact,
runner contract draft admission gate, and runner receipt contract draft JSON
metadata results. It checks that required metadata fields still agree and that
the upstream artifacts do not claim any runner, job, token, adapter execution,
browser, network, live website, autonomy, production, or executable command
materialization behavior.

Future runner receipt implementation requires a separate PR.
Future runner implementation requires a separate PR.

The artifact index is output-artifact-only. It indexes only the seven artifacts
written by this verifier. It performs no content indexing, no raw content
copying, no candidate repo indexing, and no external artifact indexing.
The artifact index performs no raw content copying.

The artifact_index.json entry has its hash deferred to
artifact_index_manifest.json. The artifact_index_manifest.json entry records
that its own hash is unavailable without self-reference. The
artifact_index_manifest.json artifact records the sha256 of artifact_index.json
after artifact_index.json has been written.
The artifact_index_manifest.json entry records that its own hash is unavailable.

The only successful status is
local_fixture_runner_receipt_preflight_verifier_completed with decision
record_runner_receipt_preflight_only. The failure status is
local_fixture_runner_receipt_preflight_verifier_rejected with decision
reject_runner_receipt_preflight.

The next allowed action after success is
human_review_runner_receipt_preflight_before_receipt_artifact_pr. The next
allowed action after failure is fix_runner_receipt_preflight_inputs_and_retry.
