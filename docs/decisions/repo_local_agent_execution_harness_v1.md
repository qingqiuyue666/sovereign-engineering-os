# Repo Local Agent Execution Harness v1

## Verdict

`REPO_LOCAL_AGENT_EXECUTION_HARNESS_READY_FOR_LOCAL_TESTS`

This branch introduces a repository-local execution harness for local agents such as Codex CLI, Aider, or Cline.

The harness reduces repeated manual command entry while preserving review gates for runtime authority.

## Implemented

- `policy/agent_execution_policy.yaml`
- `scripts/agent_run_checks.py`
- `tests/personal_ai/test_agent_execution_policy.py`
- `docs/usage/local_agent_execution_mode.md`

## Scope

The harness runs fixed repository verification commands and writes evidence. It does not merge, delete branches, tag releases, push to main, read secrets, or execute live runtimes.

## Policy Boundary

The policy defines:

- repository-only execution
- feature-branch-only work
- main write forbidden
- merge/delete/tag forbidden
- live runtime forbidden by default
- review-required kernel/runtime paths
- forbidden system/secret paths
- forbidden commands
- forbidden runtime activation classes

## Check Harness

Run:

```bash
python3 scripts/agent_run_checks.py
```

It runs:

- Personal AI tests
- `make ci`
- `git diff --check`
- `git status --short`
- forbidden marker scans

It writes:

```text
.agent_evidence/agent_run_checks_report.json
.agent_evidence/agent_run_checks_summary.md
```

## Non-Goals

This branch does not add:

- live model API execution
- browser automation
- ComfyUI endpoint calls
- Blender subprocess execution
- creative software control
- OS automation
- unrestricted network
- arbitrary subprocess
- auto-merge
- auto-delete-branch
- auto-release

## Human Review Boundary

Human review remains required for:

- kernel changes
- runtime activation changes
- admission gate changes
- approval logic changes
- live transport changes
- CLI activation commands
- secret handling changes

## Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_agent_execution_policy -v
python3 scripts/agent_run_checks.py --skip-tests --report-dir .agent_evidence/test_policy_only
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. Agent policy tests pass.
2. Harness policy-only mode writes evidence successfully.
3. Full Personal AI tests pass.
4. `make ci` passes.
5. No live runtime activation is introduced.
6. No secret-reading or credential persistence is introduced.
7. The harness remains repository-local.
