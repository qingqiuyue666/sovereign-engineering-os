# End-to-End Acceptance Matrix V1

## Scope Summary

This matrix defines system-level acceptance coverage for Sovereign Engineering
OS milestones. It is governance and validation planning only. It introduces no
runtime behavior, no production execution, no merge automation, and no release
automation.

## Global Validation Gates

- Focused milestone tests must pass.
- `python3 -m unittest discover tests` must pass.
- `make ci` must pass.
- `git diff --check` must pass.
- GitHub Actions must pass before a PR is review-ready.
- PR bodies must record scope, changed files, boundary statement, dependency
  status, local validation, GitHub Actions status, forbidden-surface
  confirmation, remaining blockers, and audit packet.

## Acceptance Coverage

| Area | Acceptance Evidence | Merge Readiness Signal |
| --- | --- | --- |
| Metadata chain | Runner-chain metadata receipts, preflight, artifact index, and task graph visibility remain non-runtime unless a later bounded runner PR is merged. | Metadata-only paths preserve no runner, no command materialization, no browser, no network, and no production promotion. |
| Real local runner | Command-id-only allowlist, human approval artifact, `shell=False`, timeout, stdout/stderr capture, receipt, failure bundle, replay manifest, and candidate adapter status. | Only allowlisted repo validation commands execute; no arbitrary command line or argv. |
| Token lifecycle | Issue, consume, revoke, expiry, single-use, scope binding, command-id binding, approval binding, revision binding, replay protection, and rejection tests. | Tokens cannot grant shell, network, browser, secrets, provider calls, or production autonomy. |
| Job queue | Descriptor, enqueue, lease, heartbeat, complete, fail, cancel, retry policy, timeout policy, append-only events, and crash recovery classification. | No background daemon by default and no autonomous production execution. |
| Replay | Receipt comparison, environment digest comparison, command-id match, argv hash match, output digest comparison, classification, and report. | Replay verification does not automatically re-execute unless separately admitted. |
| Worker registry | Bounded Codex, Claude, Gemini, GPT, DeepSeek, and deterministic local Python worker declarations with no-live-call defaults. | Provider execution disabled by default; no credentials or live provider calls. |
| PR audit | Changed-file scope checker, forbidden-surface scanner, required-test checklist, PR body contract, fixture-only CI reader, recommendation artifact, and audit packet generator. | Tooling produces recommendations only and never merges, deletes branches, or pushes main. |
| Artifact ledger | Read-only listing, filters, receipt view, failure bundle view, replay manifest view, summary output, and secret redaction. | Viewer never mutates, deletes, executes, or displays raw secrets. |
| Dashboard model | Read-only job, PR readiness, artifact, receipt, failure, approval, and milestone views. | Dashboard model never mutates, merges, deletes, executes, or calls networks. |
| Domain adapter foundation | State proxy, operation plan, asset hash binding, output manifest, provenance policy, replay policy, and admission rules. | No live DCC execution, external network, source overwrite, or process launch. |
| Forbidden surfaces | Static and behavioral checks for shell, arbitrary argv, command line, browser, network, provider API, credentials, daemons, schedulers, merge automation, branch deletion, and production autonomy. | Any forbidden surface makes the milestone blocked or not review-ready. |
| Mainline release readiness | Evidence list, CI green requirement, forbidden-surface scan, main validation command list, rollback/recovery evidence, and release recommendation artifact. | Recommendation only; no auto release, auto merge, branch deletion, or production promotion. |

## Waiting States

- `WAITING_FOR_PREVIOUS_PR_MERGE`: implementation requires code or artifacts
  from an unmerged earlier PR.
- `WAITING_FOR_DOMAIN_ADAPTER_FOUNDATION_MERGE`: adapter-specific contract
  would duplicate foundation types from an unmerged domain foundation PR.
- `BLOCKED`: proceeding would require forbidden behavior, architectural
  decisions, unsafe cleanup, non-fast-forward main, or unavailable GitHub auth.

## Forbidden Surface Rule

The matrix does not grant authority for arbitrary shell execution, `shell=True`,
arbitrary argv, arbitrary command lines, browser opening, Playwright live
execution, network access, live website access, account workflows, registration,
payment, scraping, bypass, CAPTCHA, credential storage, provider API live calls,
source asset overwrite, unbounded daemons, unbounded schedulers, direct push to
main, auto-merge, PR merge, branch deletion, release automation, or production
autonomy.

Explicitly forbidden review blockers include direct push to main, auto-merge,
branch deletion, production autonomy, provider API live calls, and credential
storage.

## Audit Packet Requirements

Every accepted PR audit packet must record milestone, branch, PR URL, head SHA,
changed files, focused tests, full unittest discovery result, `make ci` result,
`git diff --check` result, GitHub Actions run URL and status, dependency notes,
blockers, independent mergeability, and forbidden-surface confirmation.
