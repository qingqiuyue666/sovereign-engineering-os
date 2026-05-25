# Minimal Controlled Execution Contract-Only V1

Status: contract-only.

This slice defines schema contracts for a future Minimal Controlled Execution
Kernel. It does not implement subprocess execution, a runner, a launcher, a
CLI entrypoint, a scheduler, a daemon, task graph execution, auto
re-execution, provider/browser/plugin/DCC/ComfyUI/MCP execution, network
access, credential use, package installation, file deletion, asset mutation, or
another dry-run abstraction layer.

## Registry

The V1 registry contains exactly:

- `git_status_short`: fixed argv `git status --short`
- `git_diff_check`: fixed argv `git diff --check`

Each entry carries immutable metadata: command ID, fixed argv, command class,
read-only expectation, allowed verifier, registry version, and registry entry
hash.

Deferred future-only command IDs, not V1 entries:

- `unittest_discover_tests`
- `make_ci`

## Contracts

The contract-only surface is limited to:

- `ExecutionRequest`
- `ExecutionPolicyDecision`
- `ExecutionReceipt`
- `ExecutionFailureBundle`
- `ExecutionSnapshotRef`
- `ExecutionVerifierInput`

`ExecutionRequest` is command-id-only metadata. Payload-supplied argv, cwd,
env, path, executable, timeout, command, command line, shell, network,
provider, browser, plugin, DCC, ComfyUI, and MCP fields are rejected.

Policy decisions include policy version, registry version/hash, rejection
reasons, and forbidden-surface flags set false.

Receipts, failures, snapshots, and verifier inputs are contract records only in
this slice and must carry `execution_performed=false`. A receipt status that
claims execution success is invalid before a separately admitted subprocess
implementation exists.
