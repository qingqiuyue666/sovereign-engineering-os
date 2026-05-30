# Abuse Case Catalog V1

## Purpose

This catalog maps expected abuse cases to fail-closed outcomes. It is evidence
for external review input, not a claim of complete security coverage.

| Abuse Case | Required Outcome | Evidence |
| --- | --- | --- |
| AI approval bypass | Execution requires human approval and rejected tasks cannot run. | `scripts/adversarial_smoke_v1.py` |
| fake PASS | Failed commands cannot print PASS or leave success markers. | `scripts/failure_path_smoke_v1.sh` |
| receipt forgery | Corrupted receipts fail closed. | `tests/adversarial/test_adversarial_inputs_v1.py` |
| missing evidence | Evidence trace and replay report incomplete, not success. | `reports/failure_path/failure_path_baseline_v1.json` |
| replay false success | Replay cannot claim reconstructable when required receipts are missing. | `scripts/adversarial_smoke_v1.py` |
| secret leakage | Secret-like content is rejected or redacted; secrets must not be read. | `SECURITY.md` |
| context leakage | AI context bundles must be sanitized and digest-bound. | `docs/security/ai_context_safety_policy_v1.md` |
| provider response poisoning | Provider response receipts must be digest-only and review-bound. | `docs/contracts/provider_response_receipt_v1.md` |
| malicious PR/patch | CI and human review must validate claim boundaries before merge. | `.github/workflows/ci.yml` |
| CI bypass | Required checks are run in canonical-health and `make ci`. | `Makefile` |
| dependency risk | Dependencies require review and bounded installation. | `docs/supply_chain/dependency_policy_v1.md` |
| GitHub Actions risk | Workflow permissions are read-only by default. | `docs/supply_chain/github_actions_policy_v1.md` |
| operator misapproval | Operator checklists require evidence, scope, and residual risk review. | `docs/operator/operator_safety_checklist_v1.md` |
| tag mutation | `v0.1.0-rc3` must remain immutable. | `scripts/release_invariant_check_v1.py` |
| local path leakage | Public docs and reports must not leak private local paths. | `scripts/security_control_check_v1.py` |

