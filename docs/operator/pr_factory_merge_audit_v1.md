# PR Factory And Merge Audit V1

## Scope

This document records the A3 merge-audit tooling boundary. The tooling evaluates
caller-provided PR evidence, fixture-only CI status, changed-file scope,
forbidden-surface text, required validation results, and PR body sections.

## Recommendation Values

- `MERGE_ALLOWED`: all supplied evidence is passing, CI fixture status is pass,
  and no blockers are present.
- `DO_NOT_MERGE`: supplied evidence is failing, missing, out of scope, or
  forbidden-surface violations are present.
- `WAITING_FOR_CI`: all local supplied evidence is acceptable, but CI fixture
  status is pending.
- `BLOCKED`: an explicit blocker is present.

## Non-Authority Boundary

The tool is not a merge executor. It does not call GitHub, merge pull requests,
delete branches, push to main, enable auto-merge, execute tests, launch
browsers, access the network, call providers, store credentials, or grant
production autonomy.

## Evidence Inputs

- milestone id/name
- branch
- PR URL
- base and head SHAs
- changed files
- allowed file prefixes
- file text snippets supplied by the caller
- required test result map
- PR body text
- CI status fixture payload
- blockers and dependency notes

## Artifact Output

The generated artifact is JSON and records:

- recommendation
- changed-file scope result
- forbidden-surface scan result
- required test checklist result
- PR body contract result
- fixture-only CI status
- dependency notes and blockers
- false authority flags for merge, branch deletion, direct main push, and
  auto-merge

The output writer refuses to overwrite an existing artifact path.
