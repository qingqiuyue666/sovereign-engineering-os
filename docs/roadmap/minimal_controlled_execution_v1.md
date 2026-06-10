# Minimal Controlled Execution Roadmap V1

The next target state is `MINIMAL_CONTROLLED_EXECUTION_READY`.

This roadmap defines the first execution closure as a minimal, allowlisted,
receipt-generating local execution boundary limited to repository self-check
commands. This PR does not implement execution, a runner, subprocess behavior,
MCP execution, CLI plugin execution, browser automation, provider calls, GUI
surfaces, or production autonomy.

## Contract-Only V1 Registry

The contract-only V1 registry contains exactly these command IDs:

- `git_status_short`: fixed argv `git status --short`
- `git_diff_check`: fixed argv `git diff --check`

Each registry entry is immutable metadata only: command ID, fixed argv,
command class, read-only expectation, allowed verifier, registry version, and
registry entry hash.

No other command ID is admitted by the contract-only V1 registry.

Deferred future-only command IDs, not V1 registry entries:

- `unittest_discover_tests`
- `make_ci`

## Explicitly Forbidden

- arbitrary shell
- arbitrary argv
- arbitrary cwd/env/path/executable/timeout
- `command_line`
- `command`
- payload-provided executable
- payload-provided cwd/env/path
- payload-provided timeout
- subprocess
- runner
- launcher
- CLI entrypoint
- daemon
- scheduler
- task graph execution
- auto re-execution
- network calls
- browser control
- provider API
- credentials
- DCC launch
- ComfyUI launch
- MCP execution
- CLI plugin execution
- package install
- file deletion
- asset mutation

## Required Execution Closure Components

- `TaskIntent`
- `PolicyDecision`
- `CommandEnvelope`
- `AdmissionDecision`
- `ApprovalToken if required`
- `AllowlistedRunner`
- `ExecutionReceipt`
- `Verifier`
- `JournalRecord`
- `FailureBundle`
- `OperatorTaskSnapshot`

These are roadmap admission criteria for the next phase, not implementation in
this PR. The contract-only slice may define request, policy decision, receipt,
failure bundle, snapshot ref, verifier input, and registry schemas only.

## Receipt Requirements

- `command_id`
- `allowlist_id`
- `started_at`
- `ended_at`
- `exit_code`
- `stdout_digest`
- `stderr_digest`
- `output_truncation_policy`
- `working_tree_before`
- `working_tree_after`
- `verifier_result`
- `journal_entry_id`
- `receipt_hash`
- `execution_performed=false`

## Failure Bundle Requirements

- `failure_id`
- `failed_step`
- `exit_code`
- `stderr_digest`
- `stdout_digest`
- `verifier_failure`
- `rollback_required`
- `human_review_required`
- `evidence_refs`
- `execution_performed=false`

## Non-Goals

- no general shell
- no DCC control
- no ComfyUI execution
- no provider API
- no browser automation
- no package install
- no GUI
- no autonomous production action
- no dry-run abstraction layer

The roadmap is intentionally narrow: it closes toward local repository
self-check contracts only. It does not implement subprocess execution, a
runner, a launcher, a CLI, a scheduler, a daemon, provider/browser/plugin/DCC/
ComfyUI/MCP execution, or another dry-run abstraction layer.
