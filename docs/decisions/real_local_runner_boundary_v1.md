# Real Local Runner Boundary V1

Status: accepted for candidate local validation only.

## Scope

This milestone introduces the first real local runner boundary for repository
validation commands. The runner accepts a `command_id`, resolves argv from an
immutable allowlist, requires a human approval artifact, runs with `shell`
disabled, captures stdout and stderr to files, records an exit code in a
receipt, writes a failure bundle for nonzero exit or timeout, and writes a
replay manifest plus artifact binding.

## Allowlist

- `focused_runner_chain_tests`
- `full_unittest_discover`
- `make_ci`
- `diff_check`

The command model is command-id only. User-supplied command lines, argv
overrides, shell commands, browser commands, Node/npm/npx commands, network
commands, provider API calls, and production-autonomy commands are invalid.

## Boundary

The adapter registry entry remains `candidate` and not production admitted.
This milestone does not add arbitrary shell execution, `shell=True`, arbitrary
argv, browser opening, Playwright live execution, network access, live website
access, scraping, bypass workflows, CAPTCHA workflows, credential storage,
provider API live calls, source asset overwrite, unbounded daemon behavior,
unbounded scheduler behavior, or production autonomy.

## Artifacts

- `real_local_runner_descriptor.json`
- `stdout.txt`
- `stderr.txt`
- `real_local_runner_receipt.json`
- `real_local_runner_failure_bundle.json` on nonzero exit or timeout
- `real_local_runner_replay_manifest.json`
- `real_local_runner_artifacts.json`
- `real_local_runner_summary.md`

## Integration

- Launcher workflow: `real_local_runner_boundary_workflow`
- CLI subcommand: `launch-real-local-runner-boundary`
- Adapter registry entry: `real_local_runner_boundary`
- Task graph node helper: `build_real_local_runner_task_graph_node`
- Task graph artifact binding roles: receipt, stdout, stderr, replay manifest,
  optional failure bundle, artifact binding, and summary
- Product health visibility: launcher workflow and CLI subcommand are statically
  visible
