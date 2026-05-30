# Security Control Matrix V1

This matrix is the Wave 5 control index. Every control is local, bounded, and
subject to external review.

| Control ID | Risk | Control | Validation |
| --- | --- | --- | --- |
| SC-AI-APPROVAL-BYPASS | AI approval bypass | Human approval is required before dry-run receipts; rejected tasks cannot run. | `python3 scripts/adversarial_smoke_v1.py` |
| SC-FAKE-PASS | fake PASS | Shell smoke fails if PASSED appears after failure. | `bash scripts/failure_path_smoke_v1.sh` |
| SC-RECEIPT-FORGERY | receipt forgery | Corrupted receipt JSON is rejected. | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/adversarial` |
| SC-MISSING-EVIDENCE | missing evidence | Evidence trace reports incomplete. | `python3 scripts/adversarial_smoke_v1.py` |
| SC-REPLAY-FALSE-SUCCESS | replay false success | Replay cannot claim reconstructable when evidence is missing. | `python3 scripts/adversarial_smoke_v1.py` |
| SC-SECRET-LEAKAGE | secret leakage | Secrets are forbidden in tasks, context, receipts, and reports. | `python3 scripts/secret_context_safety_check_v1.py` |
| SC-CONTEXT-LEAKAGE | context leakage | Context bundles are digest-bound and redacted. | `python3 scripts/secret_context_safety_check_v1.py` |
| SC-PROVIDER-POISONING | provider response poisoning | Provider responses require digest-only receipts and human review. | `python3 scripts/contract_check_v1.py` |
| SC-MALICIOUS-PR | malicious PR/patch | CI, claim checks, and review notes must bound patch claims. | `make verify` |
| SC-CI-BYPASS | CI bypass | Canonical workflow runs invariant, static, smoke, and health gates. | `python3 scripts/supply_chain_check_v1.py` |
| SC-DEPENDENCY-RISK | dependency risk | Dependencies require review and bounded install policy. | `python3 scripts/supply_chain_check_v1.py` |
| SC-GITHUB-ACTIONS-RISK | GitHub Actions risk | Workflow permissions are minimal and actions require review/pinning policy. | `python3 scripts/supply_chain_check_v1.py` |
| SC-OPERATOR-MISAPPROVAL | operator misapproval | Operator checklist requires evidence and residual-risk review. | `docs/operator/operator_safety_checklist_v1.md` |
| SC-TAG-MUTATION | tag mutation | `v0.1.0-rc3` target is checked and must not move. | `python3 scripts/release_invariant_check_v1.py` |
| SC-LOCAL-PATH-LEAKAGE | local path leakage | Public docs and reports are scanned for local path markers. | `python3 scripts/security_control_check_v1.py` |

