# Tool Manifest Normalizer V1

Tool Manifest Normalizer V1 converts external or local tool candidate metadata
into a deterministic internal manifest for dry-run ingestion.

It supports MCP server and tool descriptors, CLI tool metadata, local script
metadata, API adapters, DCC applications and plugins, ComfyUI workflow
references, GitHub repository candidates, WASM plugins, browser automation
tools, model runtimes, render tools, and unknown source types. Unknown source
types normalize to `UNKNOWN` and are never admitted for runtime integration.

The normalizer is metadata-only. It does not fetch GitHub URLs, call MCP
servers, load ComfyUI workflows, launch DCC applications, call providers, open
browsers, spawn subprocesses, or execute CLI/plugin/script surfaces.

Forbidden payload fields include raw commands, command lines, argv/args,
shell/script/code fields, executable paths, cwd/workdir/env/path overrides,
timeouts, and credential material. The rejection check is recursive so those
fields cannot be hidden in input or output contract metadata.

The output `NormalizedToolManifest` always sets:

- `direct_execution_allowed: false`
- `runtime_integration_allowed: false`

`content_hash` is deterministic and excludes only `normalized_at`, allowing
multiple observations of the same candidate to produce the same manifest
content hash.
