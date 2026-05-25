# Minimal Controlled Execution Roadmap V1

The next target state is `MINIMAL_CONTROLLED_EXECUTION_READY`.

This roadmap defines the first execution closure as a minimal, allowlisted,
receipt-generating local execution boundary limited to repository self-check
commands. This PR does not implement execution, a runner, subprocess behavior,
MCP execution, CLI plugin execution, browser automation, provider calls, GUI
surfaces, or production autonomy.

## First Allowed Command Set

- `git status --short`
- `git diff --check`
- `python3 -m unittest discover tests`
- `make ci`

No other command is admitted by this roadmap.

## Explicitly Forbidden

- arbitrary shell
- arbitrary argv
- `command_line`
- payload-provided executable
- payload-provided cwd/env/path
- payload-provided timeout
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
this PR.

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

## Non-Goals

- no general shell
- no DCC control
- no ComfyUI execution
- no provider API
- no browser automation
- no package install
- no GUI
- no autonomous production action

The roadmap is intentionally narrow: it closes toward local repository
self-check receipts only.
