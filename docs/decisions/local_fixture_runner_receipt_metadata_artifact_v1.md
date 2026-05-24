# Local-Fixture Runner Receipt Metadata Artifact v1

This is a metadata-only runner receipt artifact.

This is not a runner.
This is not a runner stub.
This does not create a runnable job.
This does not issue approval material.
This does not issue execution material.
This does not execute the adapter.
This does not launch Playwright.
This does not open a browser.
This does not access the network.
This does not authorize live websites.
This does not authorize production.

The artifact writer reads only a verified local-fixture runner receipt
preflight JSON metadata result. It records receipt metadata and carries the
upstream source artifact paths, hashes, and identity metadata where present.
It does not authorize implementation, invocation, live website access,
production promotion, or any execution.

Future runner stub implementation requires a separate PR.
Future runner implementation requires a separate PR.

The artifact index is output-artifact-only. It indexes only the seven artifacts
written by this receipt metadata writer. It performs no content indexing, no
raw content copying, no candidate repo indexing, and no external artifact
indexing. The artifact index performs no raw content copying.
The artifact index performs no external artifact indexing.

Self-reference hash handling for artifact_index and artifact_index_manifest is
explicit. The artifact_index.json entry has its hash deferred to
artifact_index_manifest.json. The artifact_index_manifest.json entry records
that its own hash is unavailable without self-reference. The
artifact_index_manifest.json artifact records the sha256 of artifact_index.json
after artifact_index.json has been written.
The artifact_index_manifest.json entry records that its own hash is unavailable.

The only successful status is
local_fixture_runner_receipt_metadata_artifact_completed with decision
record_runner_receipt_metadata_only. The failure status is
local_fixture_runner_receipt_metadata_artifact_rejected with decision
reject_runner_receipt_metadata.

The next allowed action after success is
human_review_runner_receipt_metadata_before_runner_stub_pr. The next allowed
action after failure is fix_runner_receipt_metadata_inputs_and_retry.
