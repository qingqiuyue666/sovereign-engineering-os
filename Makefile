.PHONY: ci test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check health local-bootstrap local-smoke local-stop local-reset identity-check public-grade-check
.PHONY: test-runtime-execution-descriptor test-dry-run-orchestrator test-runtime-integration-trace test-completion-audit test-runtime-integration-hardening
.PHONY: test-security-classification test-secret-scanner test-environment-sanitizer test-anti-exfiltration-gate test-ai-context-firewall test-repository-hygiene test-leak-prevention-foundation
.PHONY: test-wal-integrity-guard test-taint-propagation test-artifact-provenance test-wal-integrity-contract test-capability-token-policy test-security-truth-substrate
.PHONY: test-task-manifest test-task-intake test-run-id test-run-ledger test-task-foundation test-operator-task-intake test-operator-task-ledger
.PHONY: test-cli-foundation test-cli-status test-cli-security-scan test-operator-cli
.PHONY: test-dry-run-runner test-runtime-runner test-event-journal test-runtime-state-machine test-idempotency test-runtime-runner-event-journal test-failure-bundle test-dry-run-runtime-foundation
.PHONY: test-failurebundle-replay-foundation test-replay-plan test-replay-manifest test-replay-verifier test-replay-diff test-replay-foundation
.PHONY: test-evidence-vault-boundary test-evidence-vault-receipt test-protected-storage-interface test-evidence-vault-boundary-foundation
.PHONY: test-audit-bundle test-audit-exporter test-audit-redaction test-audit-export-foundation
.PHONY: test-status-reporter-v12 test-health-plan test-module-registry test-local-status-foundation
.PHONY: test-provider-contract test-mock-provider test-provider-request-envelope test-provider-response-receipt test-provider-mock-foundation
.PHONY: test-provider-execution-plane test-provider-adapter-registry test-provider-execution-receipt test-provider-execution-plane-boundary
.PHONY: test-notification-contract test-telegram-mock test-notification-redaction test-notification-mock-foundation
.PHONY: test-vault-contract test-keyring-contract test-secret-ref test-vault-contract-foundation
.PHONY: test-daemon-contract test-scheduler-contract test-daemon-contract-foundation
.PHONY: test-source-reliability test-osint-task-contract test-macro-regime-contract test-asset-mapping-contract test-domain-pipeline-contracts
.PHONY: test-dashboard-model test-run-summary-model test-security-status-model test-dashboard-contracts
.PHONY: test-v12-foundation-progress-audit test-v12-foundation
.PHONY: installability-check test-installability package-build-smoke clean-clone-smoke install-smoke contract-check claim-to-evidence-check test-contracts test-claim-to-evidence failure-path-smoke adversarial-smoke test-failure-path-hardening test-adversarial security-control-check supply-chain-check secret-context-safety-check release-invariant-check test-security-control-matrix test-supply-chain-integrity test-secret-context-safety test-release-invariant ai-admission-check test-ai-provider-admission-safety dogfood-evidence-check test-dogfood-evidence reliability-benchmark schema-compatibility-check test-schema-compatibility-policy test-operational-stability smoke verify final-audit-check

PYTHON ?= python3

local-bootstrap:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/local_runtime_setup.py bootstrap . --apply

local-smoke:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/local_runtime_setup.py smoke . --apply

local-stop:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/local_runtime_setup.py stop . --apply

local-reset:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tools/local_runtime_setup.py reset . --apply

ci: health

health: test-root-integrity test-leak-prevention-foundation test-security-truth-substrate test-operator-task-ledger test-operator-cli test-runtime-runner-event-journal test-failurebundle-replay-foundation test-evidence-vault-boundary-foundation test-provider-execution-plane-boundary test-runtime-integration-hardening test-v12-foundation test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-real-runtime-provider-transport-execution test-production-autonomy-final-gate test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-protected-evidence-storage-implementation test-real-hmac-policy-realization test-real-merkle-proof-realization test-generic-payload-full-enforcement test-schemas test-tracer-bullet test-acceptance diff-check

identity-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/identity_boundary_check_v1.py

public-grade-check: identity-check

installability-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/installability_check_v1.py

test-installability:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_installability_v1 -v

package-build-smoke:
	bash scripts/package_build_smoke_v1.sh

clean-clone-smoke:
	bash scripts/clean_clone_observation_smoke_v1.sh

install-smoke:
	bash scripts/fresh_venv_install_smoke_v1.sh

contract-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/contract_check_v1.py

claim-to-evidence-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/claim_to_evidence_check_v1.py

test-contracts:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_contracts_v1 -v

test-claim-to-evidence:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_claim_to_evidence_matrix_v1 -v

failure-path-smoke:
	bash scripts/failure_path_smoke_v1.sh

adversarial-smoke:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/adversarial_smoke_v1.py

test-failure-path-hardening:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_failure_path_hardening_v1 -v

test-adversarial:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/adversarial -v

security-control-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/security_control_check_v1.py

supply-chain-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/supply_chain_check_v1.py

secret-context-safety-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/secret_context_safety_check_v1.py

release-invariant-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/release_invariant_check_v1.py

test-security-control-matrix:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_security_control_matrix_v1 -v

test-supply-chain-integrity:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_supply_chain_integrity_v1 -v

test-secret-context-safety:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_secret_context_safety_v1 -v

test-release-invariant:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_release_invariant_v1 -v

ai-admission-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/ai_admission_check_v1.py

test-ai-provider-admission-safety:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_ai_provider_admission_safety_v1 -v

dogfood-evidence-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/dogfood_evidence_check_v1.py

test-dogfood-evidence:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_dogfood_evidence_v1 -v

reliability-benchmark:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/reliability_benchmark_v1.py

schema-compatibility-check:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/schema_compatibility_check_v1.py

test-schema-compatibility-policy:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_schema_compatibility_policy_v1 -v

test-operational-stability:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_operational_stability_v1 -v

smoke: public-grade-check installability-check package-build-smoke test-installability contract-check claim-to-evidence-check test-contracts test-claim-to-evidence failure-path-smoke adversarial-smoke test-failure-path-hardening test-adversarial security-control-check supply-chain-check secret-context-safety-check release-invariant-check test-security-control-matrix test-supply-chain-integrity test-secret-context-safety test-release-invariant ai-admission-check test-ai-provider-admission-safety dogfood-evidence-check test-dogfood-evidence reliability-benchmark schema-compatibility-check test-schema-compatibility-policy test-operational-stability

verify: smoke

final-audit-check: verify

test-root-integrity:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_root_integrity_verifier -v

test-sealed-evidence-coverage:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v

test-evidence-proof-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_proof_contract -v

test-evidence-proof-fixtures:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_proof_fixtures -v

test-final-runtime-contracts:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_final_runtime_contracts -v

test-gated-provider-transport:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_gated_provider_transport_contracts -v

test-real-runtime-provider-transport-execution:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_runtime_provider_transport_execution -v

test-production-autonomy-final-gate:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_production_autonomy_final_gate -v

test-runtime-sealed-receipt:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_sealed_receipt_contracts -v

test-generic-payload-shadow:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_generic_payload_shadow_contract -v

test-protected-evidence-storage:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_protected_evidence_storage_contract -v

test-protected-evidence-storage-implementation:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_protected_evidence_storage_implementation -v

test-real-hmac-policy-realization:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_hmac_policy_realization_contract -v

test-real-merkle-proof-realization:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_merkle_proof_realization_contract -v

test-generic-payload-full-enforcement:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_generic_audit_payload_full_enforcement_contract -v

test-security-classification:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_security_classification -v

test-secret-scanner:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_secret_scanner -v

test-environment-sanitizer:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_environment_sanitizer -v

test-anti-exfiltration-gate:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_anti_exfiltration_gate -v

test-ai-context-firewall:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_ai_context_firewall -v

test-repository-hygiene:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_repository_hygiene -v

test-leak-prevention-foundation: test-security-classification test-secret-scanner test-environment-sanitizer test-anti-exfiltration-gate test-ai-context-firewall test-repository-hygiene

test-wal-integrity-guard:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_wal_integrity_guard -v

test-taint-propagation:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_taint_propagation -v

test-artifact-provenance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_artifact_provenance -v

test-wal-integrity-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_wal_integrity_contract -v

test-capability-token-policy:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_capability_token_policy -v

test-security-truth-substrate: test-wal-integrity-guard test-taint-propagation test-artifact-provenance test-wal-integrity-contract test-capability-token-policy

test-task-manifest:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_task_manifest -v

test-task-intake:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_task_intake -v

test-run-id:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_run_id -v

test-run-ledger:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_run_ledger -v

test-task-foundation: test-task-manifest test-task-intake test-run-id test-run-ledger

test-operator-task-intake:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_operator_task_intake -v

test-operator-task-ledger: test-operator-task-intake test-run-ledger

test-cli-foundation:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_cli_foundation -v

test-cli-status:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_cli_status -v

test-cli-security-scan:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_cli_security_scan -v

test-operator-cli:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_operator_cli -v

test-dry-run-runner:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_dry_run_runner -v

test-runtime-runner:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_runner -v

test-event-journal:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_event_journal -v

test-runtime-state-machine:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_state_machine -v

test-idempotency:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_idempotency -v

test-runtime-runner-event-journal: test-runtime-runner test-event-journal test-runtime-state-machine test-idempotency

test-failure-bundle:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_failure_bundle -v

test-dry-run-runtime-foundation: test-dry-run-runner test-event-journal test-failure-bundle

test-replay-plan:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_replay_plan -v

test-replay-manifest:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_replay_manifest -v

test-replay-verifier:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_replay_verifier -v

test-replay-diff:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_replay_diff -v

test-replay-foundation: test-replay-manifest test-replay-verifier test-replay-diff

test-failurebundle-replay-foundation: test-failure-bundle test-replay-plan test-replay-diff

test-audit-bundle:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_audit_bundle -v

test-audit-exporter:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_audit_exporter -v

test-audit-redaction:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_audit_redaction -v

test-audit-export-foundation: test-audit-bundle test-audit-exporter test-audit-redaction

test-status-reporter-v12:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_status_reporter_v12 -v

test-health-plan:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_health_plan -v

test-module-registry:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_module_registry -v

test-local-status-foundation: test-status-reporter-v12 test-health-plan test-module-registry

test-provider-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_provider_contract -v

test-mock-provider:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_mock_provider -v

test-provider-request-envelope:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_provider_request_envelope -v

test-provider-response-receipt:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_provider_response_receipt -v

test-provider-mock-foundation: test-provider-contract test-mock-provider test-provider-request-envelope test-provider-response-receipt

test-provider-execution-plane:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_provider_execution_plane -v

test-provider-adapter-registry:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_provider_adapter_registry -v

test-provider-execution-receipt:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_provider_execution_receipt -v

test-provider-execution-plane-boundary: test-provider-execution-plane test-provider-adapter-registry test-provider-execution-receipt

test-runtime-execution-descriptor:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_execution_descriptor -v

test-dry-run-orchestrator:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_dry_run_orchestrator -v

test-runtime-integration-trace:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_integration_trace -v

test-completion-audit:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_completion_audit -v

test-runtime-integration-hardening: test-runtime-execution-descriptor test-dry-run-orchestrator test-runtime-integration-trace test-completion-audit

test-notification-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_notification_contract -v

test-telegram-mock:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_telegram_mock -v

test-notification-redaction:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_notification_redaction -v

test-notification-mock-foundation: test-notification-contract test-telegram-mock test-notification-redaction

test-vault-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_vault_contract -v

test-evidence-vault-boundary:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_vault_boundary -v

test-evidence-vault-receipt:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_vault_receipt -v

test-protected-storage-interface:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_protected_storage_interface -v

test-evidence-vault-boundary-foundation: test-evidence-vault-boundary test-evidence-vault-receipt test-protected-storage-interface

test-keyring-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_keyring_contract -v

test-secret-ref:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_secret_ref -v

test-vault-contract-foundation: test-vault-contract test-keyring-contract test-secret-ref

test-daemon-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_daemon_contract -v

test-scheduler-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_scheduler_contract -v

test-daemon-contract-foundation: test-daemon-contract test-scheduler-contract

test-source-reliability:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_source_reliability -v

test-osint-task-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_osint_task_contract -v

test-macro-regime-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_macro_regime_contract -v

test-asset-mapping-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_asset_mapping_contract -v

test-domain-pipeline-contracts: test-source-reliability test-osint-task-contract test-macro-regime-contract test-asset-mapping-contract

test-dashboard-model:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_dashboard_model -v

test-run-summary-model:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_run_summary_model -v

test-security-status-model:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_security_status_model -v

test-dashboard-contracts: test-dashboard-model test-run-summary-model test-security-status-model

test-v12-foundation-progress-audit:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_v12_foundation_progress_audit -v

test-v12-foundation: test-leak-prevention-foundation test-security-truth-substrate test-task-foundation test-cli-foundation test-cli-status test-cli-security-scan test-dry-run-runtime-foundation test-runtime-runner-event-journal test-replay-foundation test-audit-export-foundation test-local-status-foundation test-provider-mock-foundation test-notification-mock-foundation test-vault-contract-foundation test-daemon-contract-foundation test-domain-pipeline-contracts test-dashboard-contracts test-v12-foundation-progress-audit

test-schemas:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/schemas

test-tracer-bullet:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/tracer_bullet

test-acceptance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s validation/tests/acceptance

diff-check:
	git diff --check
	test -z "$$(git status --short)"
