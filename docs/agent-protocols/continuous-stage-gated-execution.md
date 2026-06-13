# Continuous Stage-Gated Execution Protocol

## MISSION

Institutionalize how AI agents work in this repository: execute safe requested
repository work continuously, gate risk explicitly, preserve evidence, avoid
fake completion, and stop at human approval boundaries.

## CURRENT STATE

The repository contains the SEIS strategic operating layer, 16-stage gates, and
real-world validation execution package. The current repository status is
review-ready for these layers, while real-world status remains human-action and
evidence gated. This protocol layer is institutionalization only. It is not a
new SEIS strategy layer and does not expand business scope.

## TARGET STATE

Agents have a default operating protocol with:

- concise root instructions in `AGENTS.md`
- Claude-compatible memory in `CLAUDE.md`
- detailed protocols under `docs/agent-protocols/`
- reusable playbooks under `playbooks/`
- final reporting checks under `checklists/`
- checkpoint reporting under `reports/checkpoints/`

## AUTO-EXECUTE ALLOWED

Agents may auto-execute low-risk work when it stays inside the requested
repository scope:

- inspect branch, remote, status, diffs, and PR state
- create a requested feature branch from the correct base
- add or update documentation, checklists, playbooks, and checkpoint reports
- add narrow references to new protocol files
- run local validation commands
- apply narrow safe fixes for local validation failures
- commit scoped changes
- push the working branch and open a draft PR when explicitly requested

## HARD PROHIBITIONS

Agents must not:

- push directly to `main`
- merge a final PR unless explicitly authorized
- delete branches, assets, or preserved local artifacts
- perform production deployment
- perform real-world outreach
- handle secrets, tokens, accounts, or credentials
- claim paid, customer, revenue, delivery, acceptance, or validation evidence
  without source records
- change architecture authority boundaries without approval
- introduce new dependencies, services, or permissions without approval
- perform irreversible destructive actions

## SCOPE BOUNDARY

This protocol governs agent operation. It does not create new SEIS strategy
stages, expand the market thesis, perform validation, contact users, deploy
software, or claim commercial progress. Repository documentation can be ready
while external evidence remains pending.

## STAGE GATES

### Gate 1: Intake

- Read the user request fully.
- Identify required files, branch, checks, and final output.
- Identify explicit prohibitions.

Exit evidence: extracted scope and stop conditions.

### Gate 2: Current State

- Verify repository root and remote.
- Fetch current remote state when publishing is requested.
- Confirm branch, worktree status, and known preserved artifacts.
- Inspect relevant PR state when the task depends on PR topology.

Exit evidence: status, remote, base branch, branch conflict check.

### Gate 3: Scope Confirmation by Action

- Proceed automatically only when the task is low risk and scoped.
- Stop if unrelated dirty changes make staging ambiguous.
- Stop if the requested repository does not match the checkout.

Exit evidence: intended file list or blocker report.

### Gate 4: Implementation

- Make the smallest change set that satisfies the request.
- Preserve project language and evidence boundaries.
- Do not rewrite unrelated systems.

Exit evidence: diff and changed files.

### Gate 5: Checks

- Run required local checks.
- Apply only narrow safe fixes.
- Rerun once after a fix.
- Stop if still failing.

Exit evidence: command names and pass/fail output.

### Gate 6: Commit and Publish

- Stage only intended files.
- Commit with a scoped message.
- Push the working branch.
- Open a draft PR when requested.

Exit evidence: branch, commit hash, PR URL.

### Gate 7: Human Review

- Stop after the draft PR unless explicitly authorized to continue.
- Do not merge.

Exit evidence: final report and next human gate.

## AUTO-FIX POLICY

Auto-fixes are allowed only for narrow, reversible repository issues such as
formatting, broken links introduced by the branch, missing required references,
or validation wording failures caused by the current change. Do not auto-fix
unrelated historical issues. Retry the failing check once after the narrow fix.

## CHECKS

Required checks for this protocol layer:

```bash
python3 scripts/identity_boundary_check_v1.py
python3 scripts/observation_check_v1.py
python3 scripts/creative_total_check_v3.py
python3 scripts/secret_context_safety_check_v1.py
git diff --check
git diff --cached --check
```

CI or GitHub checks should be reported when available. If CI is unavailable,
unknown, pending, or failing, state that directly.

## EVIDENCE OUTPUT

Final reports must include:

- branch name
- PR number and URL when published
- files created
- files modified
- commit hash
- checks run and outcomes
- CI status when available
- risks
- blockers
- remaining human approval gate

## ROLLBACK / RECOVERY POLICY

Prefer reversible corrections. Do not delete user work to recover. If a pushed
branch needs rollback, use a new corrective commit unless the human explicitly
authorizes history rewriting. Preserve logs, diffs, check output, and the
reason for recovery.

## STOP CONDITIONS

Stop and report blockers when:

- repository root or remote does not match the request
- branch or PR topology is unsafe or ambiguous
- unrelated worktree changes make staging unsafe
- a required check fails after one narrow retry
- auth is unavailable for required publish actions
- CI fails or remains unknown where CI completion is required
- the next step is a high-risk human approval gate

## FINAL REPORT

Every final report must state what changed, how it was verified, what evidence
exists, what evidence is still missing, and exactly where the human gate now
stands.
