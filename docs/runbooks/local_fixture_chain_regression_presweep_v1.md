# Local-Fixture Chain Regression Pre-Sweep v1

Use this runbook to review the merged local-fixture chain through #431 without
adding runtime capability behavior.

## Scope

This runbook is local-only evidence review. It does not implement #432, #433,
or #434. It does not create a runner, does not create a token, does not create
a runnable job, does not create a browser session, does not create a network
path, does not create an adapter execution path, does not create a Playwright
execution path, does not create a daemon, does not create a scheduler, does
not create a worker loop, and does not create a production promotion path.

## Review Checklist

- Confirm the relevant capability modules still exist.
- Confirm the latest decision docs exist where available.
- Confirm #431 contains no runner, token, browser, or network execution
  affordance.
- Confirm #431 tests retain usage receipt hash and root binding regressions.
- Confirm #430 and #431 retain output directory mismatch protection.
- Confirm the future gate strings remain present:
  `future_execution_requires_separate_human_approval_artifact` and
  `future_execution_requires_separate_execution_runner_pr`.
- Confirm local-fixture chain source files contain no forbidden live-target,
  account, credential, cookie, scraping, bypass, CAPTCHA, execution, approval,
  browser-open, or Playwright CLI flags.
- Confirm artifact index / manifest files remain part of capability output
  patterns.
- Confirm deterministic rejection reasons remain present for critical boundary
  failures.

## Validation

Run these local checks from the repository root:

```bash
python3 -m unittest tests.tracer_bullet.test_local_fixture_chain_health_presweep
python3 -m unittest tests.tracer_bullet.test_local_fixture_adapter_execution_gate_plan
python3 -m unittest tests.tracer_bullet.test_local_fixture_adapter_dry_run_invocation_plan
python3 -m unittest tests.tracer_bullet.test_local_fixture_adapter_usage_receipt
python3 -m unittest discover tests
make ci
git diff --check
git status --short --branch
```

Stop if any command attempts network access, opens a browser, executes
Playwright, executes an adapter, issues a token, or creates a runner.

## Future Work Boundary

Human review is required before future execution. Future runner requires
separate PR. Future runner receipt required. This runbook is not the runner PR
and is not an approval artifact.
