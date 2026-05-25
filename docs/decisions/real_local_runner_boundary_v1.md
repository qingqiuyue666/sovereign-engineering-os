# Real Local Runner Boundary V1

Status: accepted for candidate local validation only.

## Scope

This milestone introduces the first real local runner boundary for repository
validation commands. The runner accepts a `command_id`, resolves argv from an
immutable allowlist, resolves the executable through a deterministic
system/brew/repo tool-root policy, requires a human approval artifact, runs with
`shell` disabled, captures stdout and stderr to files, records an exit code in
a receipt, writes a failure bundle for nonzero exit or timeout, and writes a
replay manifest plus artifact binding.

## Allowlist

- `focused_runner_chain_tests`
- `full_unittest_discover`
- `make_ci`
- `diff_check`

The command model is command-id only. User-supplied command lines, argv
overrides, shell commands, browser commands, Node/npm/npx commands, network
commands, provider API calls, and production-autonomy commands are invalid.

## Executable Resolution

The runner does not use arbitrary host `PATH` to resolve the allowlisted
executable. Each `command_id` is resolved before execution by
`real_local_runner_system_brew_repo_executable_resolution_v1` using deterministic
repo, system, and Homebrew tool roots. The executed argv begins with the
resolved absolute executable path, not the bare command name from the allowlist.

Resolution fails closed when the executable is missing, resolves outside the
allowed roots, or is a symlink whose link and realpath do not both remain in an
allowed root. The active Python interpreter is an explicit exception for
`python3` commands so unittest validation uses the already-running Python
runtime without host `PATH` lookup.

Receipts record `command_id`, `argv_hash`, resolved executable path, resolved
executable realpath, executable sha256 or an explicit unavailable reason,
environment path policy id, resolution policy id, and resolution policy digest.
Replay manifests record `command_id`, `argv_hash`, executable path, executable
sha256 or digest evidence, environment digest, resolution policy digest, and
`automatic_reexecution_allowed=false`.

## Boundary

The adapter registry entry remains `candidate` and not production admitted.
This milestone does not add arbitrary shell execution, `shell=True`, arbitrary
argv, browser opening, Playwright live execution, network access, live website
access, scraping, bypass workflows, CAPTCHA workflows, credential storage,
provider API live calls, source asset overwrite, unbounded daemon behavior,
unbounded scheduler behavior, or production autonomy.

network_allowed=false means runner policy does not authorize network use. It
does not claim OS-level network sandboxing, and this boundary does not claim
browser or network behavior is physically impossible unless a separate enforced
sandbox is added.

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
