# Security Policy

## Supported scope

This repository is local-first and governance-first. Production runtime, provider execution, encrypted vault, supply-chain scanning, WAL integrity, and taint propagation are not part of V12-01 leak prevention.

## Reporting

Do not place credential material, environment values, private signing material, provider responses, raw prompts, cookies, or local credential paths in issues, pull requests, logs, screenshots, reports, or AI context.

Report security issues by describing the affected file path, policy surface, and sanitized symptom only.

## V12-01 leak prevention rules

- CoreSecretScanner is the shared scanner engine.
- AI context and anti-exfiltration gates must reuse the shared scanner.
- Fake test markers are valid only under approved test or security fixture paths.
- Security gates are read-only and fail-closed.
- Environment access must use sanitized copies.
- Large files and binaries must not be loaded into memory for scanning.
- Redaction must preserve structured data shape where practical.

## Credential rotation

If credential material may have entered repository history, logs, AI context, reports, or exported artifacts, rotate it outside this repository and record only a sanitized rotation receipt.
