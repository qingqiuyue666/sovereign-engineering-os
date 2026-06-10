# GitHub Capability Intake Packet Lite v1

## Decision

Add a local-first GitHub capability intake packet builder as the first external
capability intake mainline.

The builder consumes a user-provided JSON manifest for an external GitHub
repository and emits a normalized, hash-bound intake packet for later human
review, bounded sandbox smoke selection, and adapter planning.

## Scope

This is intentionally Lite. It is an intake record only.

It may validate the user manifest, classify declared risks deterministically,
record bounded local evidence from an optional already-present repository
directory, and write packet artifacts into an existing output directory.

It must not search GitHub, use the network, clone repositories, run git,
install dependencies, execute third-party code, import candidate code, call
model APIs, generate adapters, register adapters, mutate candidate repository
files, add watcher behavior, or grant autonomy.

## Evidence Boundary

Optional local repository evidence is bounded to root allowlist files and
`.github/workflows/*.yml` / `.github/workflows/*.yaml`.

The builder does not recursively scan arbitrary repo files and does not follow
symlinks. It reads at most 20 evidence files, at most 262144 bytes per file,
and at most 1048576 evidence bytes total. Oversized and unreadable evidence
files are recorded as skipped. Evidence file symlinks block the packet.

## Outputs

The successful output set is:

- `github_capability_intake_packet.json`
- `github_capability_intake_packet_manifest.json`
- `github_capability_intake_packet_summary.md`
- `github_capability_intake_packet_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

All writes are exclusive and fail closed on existing output files or symlink
collisions. Preflight failures return structured payloads and write no
artifacts.

## Integrations

The capability is exposed through:

- launcher workflow `github_capability_intake_packet_workflow`
- CLI command `launch-github-capability-intake-packet`
- task graph adapter `github_capability_intake_packet`
- task graph capability `launch_github_capability_intake_packet`
- task graph artifact output binding
- product health structural checks
- adapter registry admission as local fixture metadata intake only

## Review Rule

License review is always required. A declared license does not imply legal
safety or approval. Unknown licenses and declared licenses both require human
review. Adapter generation and auto-adoption remain false.

## Next Milestone

After this intake foundation, the next milestone must evaluate real GitHub
repositories and produce either a bounded sandbox smoke result or the first
external worker adapter. No additional generic governance layer should be added
unless it directly enables real external capability execution under sandbox
constraints.
