# V12 Leak Prevention Threat Model v1

## Scope

This threat model covers V12-01 leak prevention only.

It excludes supply-chain analysis, WAL integrity, taint propagation, artifact provenance, provider runtime, encrypted vaults, daemon execution, OSINT ingestion, Telegram delivery, and production runtime orchestration.

## Primary risks

- committed credential material
- committed environment-value material
- private signing material in repository files
- AI context contamination with sensitive content
- provider request contamination with sensitive content
- run report or failure bundle leakage
- inherited process environment leakage
- fake test marker bypass outside approved test paths
- high-entropy false-positive livelock against legitimate hashes
- scanner resource exhaustion on large files or binaries

## Required controls

- CoreSecretScanner as a shared engine
- fake marker path enforcement
- max text and file size limits
- environment sanitizer with default-deny allowlist
- anti-exfiltration gate for outbound sinks
- AI context firewall with JSON-shape preservation
- repository hygiene gate
- read-only fail-closed gates

## Residual risks

- multi-turn split secret reconstruction is deferred
- semantic exfiltration of proprietary strategy is deferred
- supply-chain package provenance is deferred
- real keyring or KMS integration is deferred
- encrypted evidence vault is deferred

## Merge blockers

- no CoreSecretScanner
- fake marker allowed outside tests or security fixtures
- scanner lacks size caps
- gates mutate files instead of returning violations
- environment sanitizer missing
- anti-exfiltration gate does not share scanner engine
- AI context firewall does not share scanner engine
- credential patterns, private material blocks, sensitive field labels, and raw payload labels are not blocked
