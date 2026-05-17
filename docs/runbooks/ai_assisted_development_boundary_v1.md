# AI-Assisted Development Boundary v1

## Purpose

This runbook defines the local-first operating boundary for AI-assisted development.

The system treats cloud AI tools as draft workers only. They are not authority over repository truth, protected architecture assets, secrets, production execution, git history, merge decisions, or deployment.

## Authority Model

- Local terminal is the authority for git, CI, commit, merge, push, branch deletion, and release state.

- Git file content and local CI are the source of truth.

- Cloud AI may produce drafts, patches, review comments, or localized suggestions.

- Cloud AI may not decide final correctness.

- Human review is required before any patch enters the authority repository.

## Asset Classes

### A Layer: Cloud Assist Allowed

A-layer work may use cloud AI with sanitized context.

Examples:

- ordinary documentation

- non-core test drafts

- policy JSON formatting

- runbook drafts

- mock boundary language

- schema examples without real data

- non-core Makefile suggestions

### B Layer: Patch-Only

B-layer work may use cloud AI only with minimal snippets and patch output.

Rules:

- no full repository mount

- no production context

- no secrets

- no complete architecture context

- output should be a unified diff patch or localized suggestion

- local terminal applies and tests the patch

Examples:

- localized validator patch

- single-file refactor

- limited test patch

- sanitized failure log analysis

- contract shape review

### C Layer: Local-Only

C-layer work must not be sent to cloud AI.

Examples:

- system architecture core

- runtime spine design

- provider architecture

- replay architecture

- evidence vault architecture

- OSINT / asset mapping architecture

- decision engine

- real provider implementation

- real strategy parameters

- real execution logic

- real deployment scripts

- real evidence vault

- real KMS/keyring

- secrets, tokens, cookies, sessions, `.env`

## Repository Rules

The authority repository must not be mounted into cloud AI tools for core work.

Cloud AI may not perform:

- `git push`

- `git merge`

- branch deletion

- main branch modification

- secret reads

- `.env` reads

- production execution

- provider live execution

- vault live write

- autonomous deployment

## Patch-Only Workflow

1. Open a local branch in the authority repository.

2. Extract only the necessary snippets.

3. Send snippets to cloud AI only if the task is A or B layer.

4. Require patch-only output.

5. Apply with `git apply --check`.

6. Run local tests and `make ci`.

7. Commit locally.

8. Push only after local authority verification.

## Required Task Intake

Every new task must be classified before execution:

- task name

- asset class: A / B / C

- whether cloud AI is allowed

- repository access mode

- secret exposure check

- expected outputs

- human review requirement

## Non-Overclaim Rule

This policy does not claim cloud AI is private, offline, or safe for protected architecture assets. It only defines boundaries for controlled use.

