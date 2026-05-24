# Local-Fixture Adapter Dry-Run Invocation Plan v1

This decision records only a dry-run invocation plan after a #429 one-use
local-fixture adapter usage receipt. It validates the #429 usage receipt result
and the bound local fixture file path/hash, then writes a non-executable plan.

This PR does not execute the adapter. It does not execute Playwright. It does
not open a browser. It does not execute #422/#424/#425/#426/#427/#428/#429. It
does not execute the promoted adapter, and it does not activate the
local-fixture usage receipt chain.

This PR does not enable production. It does not enable live websites. It does
not enable general browser automation. It does not enable arbitrary URLs. It
does not enable account/login/registration flows. It does not enable scraping.
It does not enable bypass/captcha. It does not access secrets/cookies. It does
not run npm/npx/install/browser download. It does not execute candidate
repository code. It does not grant autonomy.

The only allowed state is:

- dry_run_plan_only
- local_fixture_only
- one_usage_receipt_bound
- human_review_required
- aggregation_bound
- regression_bound
- non_production

The dry-run invocation plan is not executable. It does not contain argv, shell
commands, node commands, npm/npx commands, browser commands, Playwright
commands, file opener commands, or process invocation material. It records only
structured policy fields such as
`future_invocation_requires_separate_execution_gate = true`,
`future_execution_requires_human_approval = true`,
`executable_command_materialized = false`, and
`command_line_materialized = false`.

Future execution remains blocked by a separate execution gate and by policy,
legal, network, credential, and human-approval gates. This decision grants no
production promotion, no live website admission, no general browser automation
admission, and no autonomous execution authority.
