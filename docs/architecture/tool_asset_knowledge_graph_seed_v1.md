# Tool / Asset Knowledge Graph Seed V1

## Purpose

Create the first minimal graph schema linking tools, assets, workflows,
capabilities, risks, candidate substrates, dependencies, models, MCP servers,
DCC apps, and the project itself.

## Architecture

The graph is an in-repository metadata seed. Candidate GitHub projects are
recorded as `CandidateSubstrateNode` entries with `direct_dependency_allowed_now`
and `runtime_integration_allowed_now` set to `false`.

## Safety boundaries

This does not install, vendor, import, or runtime-integrate any candidate. It
does not call network, browser, providers, credentials, ComfyUI, DCC apps, MCP
servers, agent frameworks, or production autonomy paths.

## Graph invariants

- All required node types are present.
- All required edge types are present.
- Executable tool nodes require a `RISK_OF` edge.
- Production approval requires an `APPROVED_FOR` edge.
- Candidate substrate links are metadata-only until a future approved PR changes
  that status.
