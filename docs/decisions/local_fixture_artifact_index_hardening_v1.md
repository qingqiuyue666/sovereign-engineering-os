# Local-Fixture Artifact Index Hardening v1

This decision hardens the artifact_index.json and artifact_index_manifest.json
contracts for local-fixture capability outputs.

The artifact index is metadata only.
It does not index candidate repository files.
It does not index external candidate artifacts.
It does not copy raw content.
It does not include source file content.
It does not create a runner.
It does not create a runnable job.
It does not issue approval token material.
It does not issue execution token material.
It does not execute an adapter.
It does not execute Playwright.
It does not open a browser.
It does not access the network.
It does not authorize live websites.
It does not promote production behavior.
It does not grant autonomy.

Each local-fixture output-producing capability must write an artifact index and
an artifact index manifest inside its output directory. The index records typed
metadata, adapter/capability identity, the output directory, deterministic
entries, and false boundary flags for candidate repository indexing, external
candidate artifact indexing, content indexing, and raw content copying.

Each indexed entry must identify the artifact role, full path, safe relative
path, existence state, and sha256 when a hash is available without
self-reference. Entry-level candidate repository, external artifact, content
indexing, and raw content copying flags remain false.

The manifest may hash artifact_index.json. artifact_index.json must not claim a
hash for artifact_index_manifest.json unless the entry explicitly marks the
hash as unavailable without self-reference. If artifact_index.json itself is an
indexed entry, its hash must be deferred to the manifest with an explicit
deferred-hash marker.

Ordering is deterministic by the capability's declared output order. Tests must
not depend on filesystem traversal order.
