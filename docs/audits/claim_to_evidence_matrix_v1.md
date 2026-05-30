# Claim To Evidence Matrix V1

External review required: yes.
No global recognition claim is made by this matrix.

This matrix maps bounded public claims to repository evidence that can be
reviewed by a human. It is not a certification packet, analyst endorsement,
market validation, or external recognition statement.

| Claim ID | Bounded Claim | Evidence | Validation | Status | Limitations |
| --- | --- | --- | --- | --- | --- |
| CLAIM-SEOS-IDENTITY-001 | SEOS is documented as a local-first AI execution governance kernel. | `README.md`; `docs/identity/system_identity_v1.md`; `docs/identity/non_goals_v1.md` | `python3 scripts/identity_boundary_check_v1.py` | supported by repository evidence | Not an OS sandbox, RPA framework, computer-control tool, SaaS platform, or secret manager. |
| CLAIM-SEOS-OBSERVATION-002 | The repository records an observation-mode posture with no hard evidence blocker recorded. | `reports/observation/real_operation_observation_log_v1.json`; `scripts/observation_check_v1.py`; `docs/current_phase.md` | `python3 scripts/observation_check_v1.py` | bounded by repository evidence | Observation evidence is local repository evidence and still needs independent review. |
| CLAIM-SEOS-REPRO-003 | Clean-clone and fresh-venv smoke paths exist for reproducibility and installability evidence. | `scripts/clean_clone_observation_smoke_v1.sh`; `scripts/fresh_venv_install_smoke_v1.sh`; `scripts/package_build_smoke_v1.sh`; `scripts/installability_check_v1.py` | `python3 scripts/installability_check_v1.py`; `make verify` | supported by repository evidence | Smoke coverage is local and is not a public release artifact or platform matrix. |
| CLAIM-SEOS-CONTRACTS-004 | Core SEOS objects have documented V1 contract surfaces with examples and fail-closed behavior. | `docs/contracts/task_contract_v1.md`; `docs/contracts/execution_receipt_v1.md`; `docs/contracts/evidence_trace_v1.md`; `scripts/contract_check_v1.py` | `python3 scripts/contract_check_v1.py` | supported by repository evidence | Contract docs are documentation and validation evidence, not runtime expansion. |
| CLAIM-SEOS-TAG-005 | The `v0.1.0-rc3` release-candidate tag invariant is tracked as protected evidence. | `reports/observation/real_operation_observation_log_v1.json`; `docs/current_phase.md`; `CHANGELOG.md` | `git rev-parse 'v0.1.0-rc3^{}'` | bounded by repository evidence | The tag invariant can be checked, but this matrix does not publish or move a release. |
| CLAIM-SEOS-SECURITY-006 | The public boundary rejects unsupported security, autonomy, provider, and external-recognition claims. | `SECURITY.md`; `docs/identity/non_goals_v1.md`; `scripts/identity_boundary_check_v1.py`; `scripts/claim_to_evidence_check_v1.py` | `python3 scripts/identity_boundary_check_v1.py`; `python3 scripts/claim_to_evidence_check_v1.py` | requires external review | Repository checks reduce drift but do not replace independent security review. |
| CLAIM-SEOS-FAILCLOSED-007 | Failure-path and adversarial smoke coverage proves bad states do not produce fake success. | `scripts/failure_path_smoke_v1.sh`; `scripts/adversarial_smoke_v1.py`; `reports/failure_path/failure_path_baseline_v1.json`; `tests/adversarial/test_adversarial_inputs_v1.py` | `bash scripts/failure_path_smoke_v1.sh`; `python3 scripts/adversarial_smoke_v1.py` | supported by repository evidence | Coverage is local fail-closed evidence and not an external penetration test. |

Forbidden wording is carried in the JSON matrix for machine checks. The
markdown summary intentionally avoids printing final-recognition phrases as
claim text.
