# Post-529 Operator Closure V1 Runbook

## Scope

This runbook closes the post-#529 accelerated completion line after the
#514-#529 Final Landing V1 sequence is already complete. It links the #529
final signoff with P530 through P535, defines the exact operator command order,
and records the no-go boundary for release tagging.

This runbook is an operator procedure. It does not authorize hidden autonomy,
direct `main` mutation, tag creation, tag push, release publication, network
publishing, credential access, or branch deletion.

## Closure Chain

- #529: final release candidate signoff, PR #529.
- P530: independent final signoff verification, PR #530.
- P531: evidence transparency Merkle proof, PR #531.
- P532: declarative policy gate bundle, PR #532.
- P533: deterministic fault simulation harness, PR #533.
- P534: release ceremony tagging artifact gate, PR #534.
- P535: integrated hard audit acceptance, PR #535.
- P536: this operator closure runbook.

## Exact Command Order

Run the focused tests for the active priority first. For P536, the focused
tests are:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_post_529_operator_closure_runbook_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_post_529_operator_closure_runbook_v1 -v
```

After focused tests pass, run the mandatory local gate in this exact order:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests
make ci
git diff --check
git status --short
```

Only after the mandatory local gate is green, continue in this exact order:

```sh
git push -u origin codex/post-529-p536-docs-operator-runbook-closure-v1
gh pr create --base main --head codex/post-529-p536-docs-operator-runbook-closure-v1
gh pr checks 536 --watch --fail-fast --interval 10
gh pr view 536 --json state,isDraft,mergeStateStatus,headRefName,headRefOid,statusCheckRollup,url,body
gh pr merge 536 --squash --match-head-commit <P536_HEAD_SHA>
git fetch origin main
git switch main
git pull --ff-only origin main
```

After merge, rerun the mandatory local gate on `main` in the same exact order:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests
make ci
git diff --check
git status --short
```

Then verify the branch was retained:

```sh
git ls-remote --heads origin codex/post-529-p536-docs-operator-runbook-closure-v1
```

## Failure Interpretation

- Focused test failure: the active priority is incomplete. Fix only the active
  priority scope, rerun focused tests, then rerun the full mandatory gate.
- Tracer discovery failure: a runtime, evidence, WAL, or fail-closed behavior
  regressed. Do not open or update a ready-to-merge PR until it is fixed.
- Acceptance discovery failure: the operator-facing contract regressed. Treat
  it as release-blocking.
- Full `unittest discover tests` failure: a cross-module contract regressed.
  Do not merge.
- `make ci` failure: the canonical local CI surface is not green. Do not merge.
- `git diff --check` failure: whitespace or patch hygiene is invalid. Fix and
  rerun all gates.
- Non-empty `git status --short`: local state is dirty. Identify whether the
  change belongs to the active priority before proceeding.
- `canonical-health` pending: wait. Pending is not a pass.
- `canonical-health` failure: inspect logs, fix on the priority branch, rerun
  focused and mandatory gates, push, and wait for a new green check.
- PR `mergeStateStatus` not clean, head SHA mismatch, draft state, or missing
  check: do not squash merge.

## Evidence Artifact Paths

- #529 final signoff report:
  `release-candidate-final-signoff/reports/final-signoff-report.json`
- #529 final system status report:
  `release-candidate-final-signoff/reports/final-system-status-report.json`
- #529 signoff receipt:
  `release-candidate-final-signoff/receipts/<receipt_hash>.json`
- #529 WAL:
  `release-candidate-final-signoff/signoff.real-wal.jsonl`
- P530 independent verification report:
  `independent-final-signoff-verification/reports/independent-verification-report.json`
- P530 verification receipt:
  `independent-final-signoff-verification/receipts/<receipt_hash>.json`
- P530 WAL:
  `independent-final-signoff-verification/verification.real-wal.jsonl`
- P531 transparency report:
  `evidence-transparency-merkle/reports/transparency-report.json`
- P531 transparency receipt:
  `evidence-transparency-merkle/receipts/<receipt_hash>.json`
- P531 inclusion proofs:
  `evidence-transparency-merkle/proofs/<item_id>-<proof_hash>.json`
- P531 WAL:
  `evidence-transparency-merkle/transparency.real-wal.jsonl`
- P532 policy decision report:
  `declarative-policy-gate-bundle/reports/policy-decision-report.json`
- P532 policy decision receipt:
  `declarative-policy-gate-bundle/receipts/<receipt_hash>.json`
- P532 WAL:
  `declarative-policy-gate-bundle/policy.real-wal.jsonl`
- P533 fault simulation report:
  `deterministic-fault-simulation/reports/fault-simulation-report.json`
- P533 scenario receipts:
  `deterministic-fault-simulation/scenario-receipts/<receipt_hash>.json`
- P533 report receipts:
  `deterministic-fault-simulation/report-receipts/<report_hash>.json`
- P533 WAL:
  `deterministic-fault-simulation/simulation.real-wal.jsonl`
- P534 release ceremony report:
  `release-ceremony-tagging/reports/release-ceremony-report.json`
- P534 release notes draft:
  `release-ceremony-tagging/release-notes/release-notes-draft.md`
- P534 tag command proposal:
  `release-ceremony-tagging/tag-command/tag-command-proposal.json`
- P534 release ceremony receipt:
  `release-ceremony-tagging/receipts/<receipt_hash>.json`
- P534 WAL:
  `release-ceremony-tagging/release-ceremony.real-wal.jsonl`
- P535 integrated hard audit report:
  `integrated-hard-audit/reports/integrated-hard-audit-report.md`
- P535 integrated hard audit JSON report:
  `integrated-hard-audit/reports/integrated-hard-audit-report.json`
- P535 integrated hard audit receipt:
  `integrated-hard-audit/receipts/<receipt_hash>.json`
- P535 WAL:
  `integrated-hard-audit/hard-audit.real-wal.jsonl`

## Release And Tagging Approval Boundary

P534 may generate a tag command proposal only. Do not create a tag. Do not push
a tag. Do not publish a release. Do not upload release artifacts. Do not treat
the release notes draft as a published release note.

The only acceptable P534 output before separate human release approval is local
evidence under `release-ceremony-tagging/`, including the release notes draft,
the tag command proposal JSON, the release ceremony report, the release
ceremony receipt, and the release ceremony WAL.

## Rollback And Recovery

If a priority branch fails before merge:

1. Keep the branch.
2. Inspect the failing focused test, mandatory gate, or CI log.
3. Fix only the active priority scope.
4. Rerun focused tests.
5. Rerun the mandatory local gate.
6. Push the amended branch.
7. Wait for `canonical-health`.

If a priority has already been squash merged:

1. Do not rewrite `main`.
2. Do not delete the retained branch.
3. Open a new corrective priority branch from current `main`.
4. Link the failed merge commit and the corrective PR in the operator report.
5. Rerun the mandatory local gate before and after the corrective merge.

For recovery procedures that involve runtime state, follow
`docs/runbooks/recovery_rollback_disaster_procedure_v1.md`.

## Clean Reset Instructions

Use these commands only to return to the verified remote `main` state after all
local work is committed, merged, or intentionally abandoned:

```sh
git fetch origin main
git switch main
git pull --ff-only origin main
git status --short
```

If `git status --short` is non-empty, stop and classify each path before
removing or overwriting anything. Do not use destructive reset commands unless
the operator explicitly authorizes that operation for the listed paths.

## No-Go Conditions

Do not proceed when any of these conditions is true:

- a focused test failed
- any mandatory validation command failed
- `canonical-health` is pending, missing, cancelled, or failed
- PR head SHA differs from the local head SHA
- PR is draft
- PR merge state is not clean
- `git status --short` is non-empty after validation
- branch retention cannot be verified
- an upstream receipt is missing, rejected, stale, or contradictory
- transparency proof verification fails
- policy decision denies the release ceremony
- fault simulation reports unsafe recovery
- release ceremony says a tag was created or pushed
- release ceremony says external artifacts were published
- release notes or tag command proposal are missing
- any runbook link required by #529 or P535 is missing
- credentials, `.env` files, or secret-bearing material would need to be read

## Do-Not-Proceed Conditions

Do not proceed from P536 to any follow-up priority unless every P530-P536 PR is
merged, every priority branch is retained, every post-merge validation gate has
passed on `main`, and the operator report names no blockers.

If a later priority asks to create a release tag, treat that as a new approval
boundary. This runbook closes the evidence line; it does not approve release
publication.
