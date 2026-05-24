# Real GitHub Candidate Evaluation Pack v1

## Decision

#418 is now being used with real external GitHub candidates through the
GitHub Capability Intake Packet Lite pipeline.

This PR intentionally avoids another generic gate layer. It adds a deterministic
real-candidate metadata pack and tests that prove the existing #418 builder can
process those manifests.

## Candidate Selection

Playwright is selected as the first bounded sandbox smoke candidate.

This selection is only for a future local fixture sandbox smoke. It is not
approval for live website automation, account workflows, scraping, bypass
behavior, secrets, adapter generation, or production use.

`ahujasid/blender-mcp` is held for a later creative sandbox because Blender-side
socket/command behavior and possible Python execution require a separate
disposable-scene boundary.

`ultrafunkamsterdam/nodriver` is held as high-risk reference material only
because its anti-bot / detection-avoidance orientation and AGPL license require
policy, legal, and safety review before any runnable integration.

## Non-Actions

This PR does not perform the sandbox smoke yet.

It does not fetch, clone, install, import, or execute third-party candidate
code.

It does not approve any license.

It does not generate adapters.

It does not enable live website automation.

It does not enable Blender control.

## Next Milestone

The next milestone must be:

Playwright local fixture bounded sandbox smoke plan/result.

No additional generic governance layer may be added before a real sandbox smoke
unless it directly blocks unsafe execution.
