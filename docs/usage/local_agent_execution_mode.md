# Local Agent Execution Mode

## Purpose

This mode lets a local agent such as Codex CLI, Aider, or Cline run repeatable repository checks without turning the workstation into an unrestricted execution target.

The local agent may help write code on a feature branch, but it must not merge to `main`, delete branches, tag releases, read secrets, or activate live runtimes.

## Required Boundary

Run the local agent only inside the repository root:

```bash
cd /Users/qqy/Documents/GitHub/sovereign-engineering-os
```

The agent must not modify files outside this repository.

Forbidden workstation targets include:

- Desktop
- Downloads
- Documents outside this repository
- Pictures / Movies / Music
- Applications
- shell profiles
- SSH keys
- API key files
- browser profiles
- system directories

## Agent Policy

The policy file is:

```text
policy/agent_execution_policy.yaml
```

The policy separates:

- auto-allowed documentation/test/policy paths
- review-required kernel/runtime paths
- forbidden secret/system paths
- forbidden commands
- forbidden runtime activation classes

## Check Harness

Use:

```bash
python3 scripts/agent_run_checks.py
```

The harness runs a fixed check set:

- Personal AI tests
- `make ci`
- `git diff --check`
- `git status --short`
- forbidden marker scans
- evidence report generation

It writes evidence under:

```text
.agent_evidence/
```

The evidence report includes:

- repository root
- current branch
- git head
- policy hash
- command results
- forbidden scan results
- git status before and after
- completion timestamp

## What The Harness Does Not Do

The harness does not:

- merge branches
- delete branches
- tag releases
- push to `main`
- read `.env`
- read SSH keys
- read API key files
- execute live model calls
- launch browsers
- call ComfyUI endpoints
- launch Blender
- control creative software
- perform OS automation

## Safe Agent Operating Model

Recommended workflow:

1. Human creates a feature branch.
2. Local agent edits code only inside the repository.
3. Local agent runs `python3 scripts/agent_run_checks.py`.
4. Local agent commits only if checks pass.
5. Pull request is reviewed before merge.
6. Human performs merge and branch deletion.

## Auto-Approval Rule

Auto-commit may be acceptable for docs/tests/policy-only changes when the harness passes.

Human review remains required for:

- kernel changes
- runtime activation changes
- admission gate changes
- approval logic changes
- live model transport changes
- browser/ComfyUI/Blender/creative runtime changes
- secret handling changes
- CLI commands that can reach runtime activation

## Aider / Cline / Codex CLI Guidance

Use local agent tools only with repository-local constraints.

Do not enable global auto-approve for all terminal commands.

Do not allow agents to run dangerous commands such as:

- `sudo`
- `rm -rf`
- `chmod -R`
- `chown -R`
- `killall`
- `pkill`
- `launchctl`
- `osascript`
- `defaults write`
- `security`
- `curl | sh`
- `wget | sh`

The correct goal is not to remove human review. The correct goal is to stop wasting human time on repeatable low-risk checks while preserving hard review gates for runtime authority.
