import inspect
import json
import unittest
from copy import deepcopy
from pathlib import Path

from kernel.lifecycle import service_method_authority_contract_validator as validator


SOURCE_BINDINGS = {
    "source_read_only_governance_layer_tag": "read-only-governance-layer-v1",
    "source_read_only_governance_layer_commit": (
        "4656e8f03404c6bb39e7976c6165e3d7dc0314fb"
    ),
    "source_write_side_precondition_checker_tag": (
        "write-side-precondition-checker-v1"
    ),
    "source_write_side_precondition_checker_commit": (
        "fd5788c7a4d3ed953fbc0295414ba7e6ad4f89f6"
    ),
    "source_write_side_precondition_ci_tag": "write-side-precondition-ci-v1",
    "source_write_side_precondition_ci_commit": (
        "05c81541ad3d7deee20023843142f702937f6c3f"
    ),
    "source_write_side_recovery_spec_only_tag": (
        "write-side-recovery-spec-only-v1"
    ),
    "source_write_side_recovery_spec_only_commit": (
        "ad560cc2dab135f2c1d56d948410ae47586d118e"
    ),
    "source_restore_dry_run_read_only_stack_tag": (
        "restore-dry-run-read-only-stack-v1"
    ),
    "source_restore_dry_run_read_only_stack_commit": (
        "e7c78e3ff0c5dc05806c293f01ab32cd33c9518b"
    ),
    "source_preflight_read_only_stack_tag": "preflight-read-only-stack-v1",
    "source_preflight_read_only_stack_commit": (
        "662b6161253c35204b437e88809c5bab21908c6d"
    ),
    "source_execution_authorization_read_only_stack_tag": (
        "execution-authorization-read-only-stack-v1"
    ),
    "source_execution_authorization_read_only_stack_commit": (
        "d586aeb60620010c900df7be1a88621ab2cb8dc1"
    ),
    "source_executor_precondition_read_only_stack_tag": (
        "executor-precondition-read-only-stack-v1"
    ),
    "source_executor_precondition_read_only_stack_commit": (
        "cb3948eb843866dcc961b6a074038c13db64d017"
    ),
    "source_write_path_read_only_stack_tag": "write-path-read-only-stack-v1",
    "source_write_path_read_only_stack_commit": (
        "8ffd4679aca8f593415089748df35df42af8f015"
    ),
    "source_repository_uow_allowlist_read_only_stack_tag": (
        "repository-uow-allowlist-read-only-stack-v1"
    ),
    "source_repository_uow_allowlist_read_only_stack_commit": (
        "bec2d04eab1922594dcbfbe35971f4efe0fe4849"
    ),
    "source_evidence_audit_append_read_only_stack_tag": (
        "evidence-audit-append-read-only-stack-v1"
    ),
    "source_evidence_audit_append_read_only_stack_commit": (
        "62db8a586efa9375d2c77cf7c6335ccf5ef11279"
    ),
    "source_append_runtime_authority_service_boundary_read_only_stack_tag": (
        "append-runtime-authority-service-boundary-read-only-stack-v1"
    ),
    "source_append_runtime_authority_service_boundary_read_only_stack_commit": (
        "bda430a6a8d1e1dbede2adb9594baa1ab5cf2039"
    ),
    "source_service_adapter_boundary_read_only_stack_tag": (
        "service-adapter-boundary-read-only-stack-v1"
    ),
    "source_service_adapter_boundary_read_only_stack_commit": (
        "8698ea42c78cbe79231698be8839b9d2c246cfdf"
    ),
    "source_service_method_authority_contract_spec_only_tag": (
        "service-method-authority-contract-spec-only-v1"
    ),
    "source_service_method_authority_contract_spec_only_commit": (
        "ffe284468215f3cfdc7c3de39b2708da1e653e42"
    ),
}

SERVICE_IDENTITIES = [
    "evidence_service",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "audit_service_future_adapter",
]

DECLARATION_GROUPS = {
    "method_authority_declarations": [
        "exact_service_identity_required",
        "exact_service_class_name_required",
        "exact_service_method_name_required",
        "exact_operation_kind_required",
        "exact_authority_scope_required",
        "exact_phase_required",
        "exact_input_contract_ref_required",
        "exact_output_contract_ref_required",
        "exact_idempotency_binding_ref_required",
        "exact_transaction_placement_ref_required",
        "exact_failure_incident_policy_ref_required",
        "exact_evidence_audit_ref_binding_required",
        "exact_authority_grant_ref_required",
        "exact_revocation_ref_required",
    ],
    "method_allowlist_declarations": [
        "service_method_allowlist_required",
        "wildcard_method_authority_forbidden",
        "class_level_authority_forbidden",
        "module_level_authority_forbidden",
        "dynamic_service_resolution_forbidden",
        "runtime_method_lookup_forbidden",
        "reflection_method_discovery_forbidden",
        "inferred_method_authority_forbidden",
        "service_object_passthrough_forbidden",
        "raw_callable_passthrough_forbidden",
    ],
    "result_contract_declarations": [
        "service_result_contract_required",
        "service_result_json_safe_required",
        "service_result_bounded_required",
        "service_result_deterministic_required",
        "explicit_success_failure_state_required",
        "explicit_reason_code_required",
        "explicit_failure_taxonomy_required",
        "service_result_no_runtime_handles_required",
        "service_result_no_raw_repr_required",
        "service_object_leakage_forbidden",
        "db_handle_leakage_forbidden",
        "repository_uow_handle_leakage_forbidden",
        "exception_object_leakage_forbidden",
        "filesystem_network_handle_leakage_forbidden",
        "raw_service_result_passthrough_forbidden",
        "implicit_append_success_forbidden",
        "implicit_audit_emission_forbidden",
        "fabricated_evidence_audit_refs_forbidden",
        "no_success_without_required_refs",
    ],
    "idempotency_replay_declarations": [
        "service_idempotency_binding_required",
        "service_idempotency_source_bound_required",
        "service_idempotency_operation_bound_required",
        "service_idempotency_service_identity_bound_required",
        "service_idempotency_method_bound_required",
        "service_idempotency_authority_ref_bound_required",
        "service_idempotency_evidence_audit_ref_bound_required",
        "service_replay_classification_required",
        "same_key_same_binding_safe_replay_only",
        "same_key_different_binding_fail_closed",
        "ambiguous_replay_incident_class",
        "idempotency_reservation_runtime_not_authorized",
    ],
    "transaction_placement_declarations": [
        "kernel_owned_transaction_required_for_future_runtime",
        "service_transaction_ownership_forbidden_by_default",
        "service_commit_forbidden",
        "service_rollback_forbidden",
        "uncontrolled_nested_transaction_forbidden",
        "in_transaction_service_call_requires_separate_authority",
        "out_of_band_service_call_policy_required",
        "commit_after_required_bookkeeping_only",
        "rollback_on_unexpected_exception_required",
        "rollback_failure_incident_class",
        "transaction_runtime_not_authorized",
    ],
    "failure_incident_declarations": [
        "expected_rejection_defined",
        "forbidden_service_call_fail_closed",
        "method_not_allowlisted_fail_closed",
        "malformed_service_result_fail_closed",
        "missing_ref_fail_closed",
        "mismatched_ref_fail_closed",
        "idempotency_mismatch_fail_closed",
        "ambiguous_replay_incident_class",
        "transaction_violation_incident_class",
        "post_mutation_service_failure_incident_class",
        "rollback_failure_incident_class",
        "failure_incident_separation_required",
        "partial_success_forbidden",
        "silent_success_forbidden",
        "incident_class_conditions_defined",
        "fail_closed_behavior_required",
    ],
    "evidence_audit_ref_declarations": [
        "evidence_audit_refs_source_bound_required",
        "evidence_audit_refs_operation_bound_required",
        "evidence_audit_refs_method_bound_required",
        "evidence_audit_refs_authority_bound_required",
        "evidence_audit_refs_json_safe_required",
        "fabricated_evidence_audit_refs_forbidden",
        "undeclared_ref_forbidden",
        "missing_ref_fail_closed",
        "mismatched_ref_fail_closed",
        "implicit_append_success_forbidden",
        "implicit_audit_emission_forbidden",
    ],
    "authority_grant_declarations": [
        "authority_source_bound_required",
        "authority_operation_bound_required",
        "authority_service_identity_bound_required",
        "authority_method_bound_required",
        "authority_phase_bound_required",
        "authority_result_contract_bound_required",
        "authority_idempotency_bound_required",
        "authority_transaction_placement_bound_required",
        "authority_failure_policy_bound_required",
        "authority_evidence_audit_ref_bound_required",
        "authority_human_approval_bound_required",
        "authority_operator_confirmation_bound_required",
        "authority_expiration_bound_required",
        "authority_issuer_bound_required",
        "authority_revocation_bound_required",
        "authority_narrow_required",
        "wildcard_authority_forbidden",
        "durable_authority_forbidden_by_default",
    ],
    "revocation_declarations": [
        "revocation_ref_required",
        "revoked_authority_fails_closed",
        "expired_authority_fails_closed",
        "mismatched_authority_fails_closed",
        "missing_authority_fails_closed",
        "read_only_validation_does_not_imply_authority",
        "ci_success_does_not_imply_authority",
        "tag_existence_does_not_imply_authority",
    ],
}

REQUIRED_DECLARATIONS = [
    "spec_only_non_executable",
    "service_adapter_implementation_forbidden",
    "service_calls_forbidden",
    "evidence_service_call_forbidden",
    "approval_service_call_forbidden",
    "review_service_call_forbidden",
    "revision_seal_service_call_forbidden",
    "audit_service_call_forbidden",
    "future_validator_required",
    "future_ci_required",
]

AUTHORITY_FLAGS = [
    "service_adapter_runtime_authorized",
    "service_adapter_implementation_authorized",
    "service_method_call_authorized",
    "service_side_effect_authorized",
    "evidence_service_authorized",
    "approval_service_authorized",
    "review_service_authorized",
    "revision_seal_service_authorized",
    "audit_service_authorized",
    "evidence_append_authorized",
    "audit_append_authorized",
    "append_runtime_authorized",
    "repository_uow_writes_authorized",
    "direct_db_writes_authorized",
    "raw_sqlite_authorized",
    "ad_hoc_sql_authorized",
    "transaction_runtime_authorized",
    "idempotency_reservation_authorized",
    "rollback_runtime_authorized",
    "runtime_allowlist_authorized",
    "runtime_checker_authorized",
    "runtime_enforcer_authorized",
    "executor_implementation_authorized",
    "restore_execution_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "filesystem_side_effects_authorized",
    "external_network_authorized",
    "durable_writes_authorized",
    "irreversible_action_authorized",
    "db_repair_authorized",
]

FAILURE_VALUES = [
    "payload_not_mapping",
    "payload_shape_mismatch",
    "contract_not_mapping",
    "contract_shape_mismatch",
    "contract_surface_invalid",
    "contract_version_invalid",
    "source_ref_mismatch",
    "service_identity_invalid",
    "method_authority_declaration_invalid",
    "method_allowlist_declaration_invalid",
    "result_contract_declaration_invalid",
    "idempotency_replay_declaration_invalid",
    "transaction_placement_declaration_invalid",
    "failure_incident_declaration_invalid",
    "evidence_audit_ref_declaration_invalid",
    "authority_grant_declaration_invalid",
    "revocation_declaration_invalid",
    "required_declaration_invalid",
    "required_declaration_false",
    "authorization_flag_invalid",
    "authorization_flag_true",
    "json_safe_invalid",
]

CONTRACT_KEYS = (
    ["surface", "version"]
    + list(SOURCE_BINDINGS)
    + ["service_identities"]
    + list(DECLARATION_GROUPS)
    + REQUIRED_DECLARATIONS
    + AUTHORITY_FLAGS
    + ["json_safe"]
)

OUTPUT_KEYS = [
    "surface",
    "version",
    *SOURCE_BINDINGS,
    "service_identities",
    *DECLARATION_GROUPS,
    *REQUIRED_DECLARATIONS,
    *AUTHORITY_FLAGS,
    "json_safe",
]

EXPECTED_MANIFEST = {
    "surface": "service_method_authority_contract_validator",
    "version": 1,
    "input_shape": "already_rendered_service_method_authority_contract_v1",
    "depends_on": {
        "service_method_authority_contract_spec_only": (
            "service-method-authority-contract-spec-only-v1"
        ),
        "service_adapter_boundary_read_only_stack": (
            "service-adapter-boundary-read-only-stack-v1"
        ),
        "append_runtime_authority_service_boundary_read_only_stack": (
            "append-runtime-authority-service-boundary-read-only-stack-v1"
        ),
        "evidence_audit_append_read_only_stack": (
            "evidence-audit-append-read-only-stack-v1"
        ),
        "repository_uow_allowlist_read_only_stack": (
            "repository-uow-allowlist-read-only-stack-v1"
        ),
        "write_path_read_only_stack": "write-path-read-only-stack-v1",
        "executor_precondition_read_only_stack": (
            "executor-precondition-read-only-stack-v1"
        ),
        "execution_authorization_read_only_stack": (
            "execution-authorization-read-only-stack-v1"
        ),
        "preflight_read_only_stack": "preflight-read-only-stack-v1",
        "restore_dry_run_read_only_stack": (
            "restore-dry-run-read-only-stack-v1"
        ),
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": (
            "write-side-precondition-checker-v1"
        ),
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "method_authority_ready_authorizes_service_calls": False,
    "method_authority_ready_authorizes_runtime": False,
    "method_authority_ready_authorizes_write": False,
    **{name: False for name in AUTHORITY_FLAGS},
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": [
        "invalid_method_authority_payload",
        "not_ready",
        "ready",
    ],
    "failure_values": FAILURE_VALUES,
}


def valid_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "surface": "ServiceMethodAuthorityContractV1",
        "version": 1,
        **SOURCE_BINDINGS,
        "service_identities": list(SERVICE_IDENTITIES),
    }
    for group_name, fields in DECLARATION_GROUPS.items():
        contract[group_name] = {field: True for field in fields}
    for field in REQUIRED_DECLARATIONS:
        contract[field] = True
    for field in AUTHORITY_FLAGS:
        contract[field] = False
    contract["json_safe"] = True
    return contract


def valid_payload() -> dict[str, object]:
    return {"service_method_authority_contract": valid_contract()}


class HappyPathTests(unittest.TestCase):
    def test_happy_ready_path(self) -> None:
        result = validator.validate_service_method_authority_contract(
            valid_payload()
        )

        self.assertTrue(result["method_authority_ready"])
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(list(result), [
            "method_authority_ready",
            "reason_code",
            "failures",
            "contract",
        ])

    def test_exact_output_shape(self) -> None:
        result = validator.validate_service_method_authority_contract(
            valid_payload()
        )

        self.assertEqual(list(result["contract"]), OUTPUT_KEYS)
        self.assertEqual(
            result["contract"]["surface"],
            "service_method_authority_contract_validator",
        )
        self.assertEqual(result["contract"]["version"], 1)
        self.assertEqual(
            result["contract"]["service_identities"], SERVICE_IDENTITIES
        )
        self.assertTrue(result["contract"]["json_safe"])

    def test_exact_input_shape(self) -> None:
        payload = valid_payload()
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(list(payload), ["service_method_authority_contract"])
        self.assertTrue(result["method_authority_ready"])


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        result = validator.validate_service_method_authority_contract([])

        self.assertEqual(result["reason_code"], "invalid_method_authority_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])
        self.assertFalse(result["method_authority_ready"])

    def test_missing_top_level_key(self) -> None:
        result = validator.validate_service_method_authority_contract({})

        self.assertEqual(result["reason_code"], "invalid_method_authority_payload")
        self.assertIn("payload_shape_mismatch", result["failures"])
        self.assertIn("contract_not_mapping", result["failures"])

    def test_extra_top_level_key(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["reason_code"], "invalid_method_authority_payload")
        self.assertIn("payload_shape_mismatch", result["failures"])


class ContractStructureTests(unittest.TestCase):
    def test_contract_non_mapping(self) -> None:
        result = validator.validate_service_method_authority_contract(
            {"service_method_authority_contract": []}
        )

        self.assertEqual(result["reason_code"], "invalid_method_authority_payload")
        self.assertEqual(result["failures"], ["contract_not_mapping"])

    def test_contract_missing_key(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"].pop("json_safe")
        result = validator.validate_service_method_authority_contract(payload)

        self.assertIn("contract_shape_mismatch", result["failures"])

    def test_contract_extra_key(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["raw_contract"] = object()
        result = validator.validate_service_method_authority_contract(payload)

        self.assertIn("contract_shape_mismatch", result["failures"])
        self.assertNotIn("raw_contract", result["contract"])

    def test_wrong_surface(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["surface"] = "wrong"
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["reason_code"], "invalid_method_authority_payload")
        self.assertIn("contract_surface_invalid", result["failures"])

    def test_wrong_version(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["version"] = 2
        result = validator.validate_service_method_authority_contract(payload)

        self.assertIn("contract_version_invalid", result["failures"])

    def test_bool_as_int_version(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["version"] = True
        result = validator.validate_service_method_authority_contract(payload)

        self.assertIn("contract_version_invalid", result["failures"])


class SourceAndIdentityTests(unittest.TestCase):
    def test_source_ref_mismatch(self) -> None:
        payload = valid_payload()
        contract = payload["service_method_authority_contract"]
        contract["source_service_method_authority_contract_spec_only_commit"] = (
            "bad"
        )
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])

    def test_invalid_service_identities(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["service_identities"] = [
            "evidence_service"
        ]
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["service_identity_invalid"])
        self.assertEqual(result["contract"]["service_identities"], [])


class DeclarationGroupTests(unittest.TestCase):
    def test_each_declaration_group_false(self) -> None:
        expected_failures = {
            "method_authority_declarations": (
                "method_authority_declaration_invalid"
            ),
            "method_allowlist_declarations": (
                "method_allowlist_declaration_invalid"
            ),
            "result_contract_declarations": (
                "result_contract_declaration_invalid"
            ),
            "idempotency_replay_declarations": (
                "idempotency_replay_declaration_invalid"
            ),
            "transaction_placement_declarations": (
                "transaction_placement_declaration_invalid"
            ),
            "failure_incident_declarations": (
                "failure_incident_declaration_invalid"
            ),
            "evidence_audit_ref_declarations": (
                "evidence_audit_ref_declaration_invalid"
            ),
            "authority_grant_declarations": (
                "authority_grant_declaration_invalid"
            ),
            "revocation_declarations": "revocation_declaration_invalid",
        }
        for group_name, failure in expected_failures.items():
            with self.subTest(group_name=group_name):
                payload = valid_payload()
                contract = payload["service_method_authority_contract"]
                first_field = next(iter(contract[group_name]))
                contract[group_name][first_field] = False

                result = validator.validate_service_method_authority_contract(
                    payload
                )

                self.assertEqual(result["failures"], [failure])

    def test_group_non_mapping(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"][
            "method_authority_declarations"
        ] = []
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(
            result["failures"], ["method_authority_declaration_invalid"]
        )

    def test_group_extra_key(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"][
            "method_allowlist_declarations"
        ]["extra"] = True
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(
            result["failures"], ["method_allowlist_declaration_invalid"]
        )


class RequiredDeclarationTests(unittest.TestCase):
    def test_required_declaration_false(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"][
            "spec_only_non_executable"
        ] = False
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["required_declaration_false"])

    def test_required_declaration_non_bool(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"][
            "future_validator_required"
        ] = "yes"
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["required_declaration_invalid"])


class AuthorizationFlagTests(unittest.TestCase):
    def test_authorization_flag_true(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"][
            "service_method_call_authorized"
        ] = True
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertFalse(result["contract"]["service_method_call_authorized"])

    def test_authorization_flag_non_bool(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"][
            "transaction_runtime_authorized"
        ] = "false"
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["authorization_flag_invalid"])
        self.assertFalse(result["contract"]["transaction_runtime_authorized"])

    def test_output_hard_false_authority_flags(self) -> None:
        result = validator.validate_service_method_authority_contract(
            valid_payload()
        )

        for field in AUTHORITY_FLAGS:
            self.assertIs(result["contract"][field], False)


class JsonSafetyTests(unittest.TestCase):
    def test_json_safe_false(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["json_safe"] = False
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_json_safe_non_bool(self) -> None:
        payload = valid_payload()
        payload["service_method_authority_contract"]["json_safe"] = "true"
        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_output_json_safe(self) -> None:
        result = validator.validate_service_method_authority_contract(
            valid_payload()
        )

        json.dumps(result, sort_keys=True)


class SemanticsAndSafetyTests(unittest.TestCase):
    def test_method_authority_ready_grants_no_authority(self) -> None:
        result = validator.validate_service_method_authority_contract(
            valid_payload()
        )
        manifest = validator.service_method_authority_contract_validator_manifest()

        self.assertTrue(result["method_authority_ready"])
        self.assertFalse(
            manifest["method_authority_ready_authorizes_service_calls"]
        )
        self.assertFalse(manifest["method_authority_ready_authorizes_runtime"])
        self.assertFalse(manifest["method_authority_ready_authorizes_write"])
        for field in AUTHORITY_FLAGS:
            self.assertFalse(result["contract"][field])
            self.assertFalse(manifest[field])

    def test_input_not_mutated(self) -> None:
        payload = valid_payload()
        before = deepcopy(payload)

        validator.validate_service_method_authority_contract(payload)

        self.assertEqual(payload, before)

    def test_combined_failures_deterministic_order(self) -> None:
        payload = valid_payload()
        contract = payload["service_method_authority_contract"]
        contract["surface"] = "wrong"
        contract["source_read_only_governance_layer_tag"] = "wrong"
        contract["service_identities"] = []
        contract["method_authority_declarations"][
            "exact_service_identity_required"
        ] = False
        contract["future_ci_required"] = False
        contract["service_side_effect_authorized"] = True
        contract["json_safe"] = False

        result = validator.validate_service_method_authority_contract(payload)

        self.assertEqual(
            result["failures"],
            [
                "contract_surface_invalid",
                "source_ref_mismatch",
                "service_identity_invalid",
                "method_authority_declaration_invalid",
                "required_declaration_false",
                "authorization_flag_true",
                "json_safe_invalid",
            ],
        )

    def test_no_raw_contract_object_leakage(self) -> None:
        payload = valid_payload()
        marker = {"runtime_handle_repr": object()}
        payload["service_method_authority_contract"]["unexpected"] = marker

        result = validator.validate_service_method_authority_contract(payload)

        self.assertNotIn("unexpected", result["contract"])
        with self.assertRaises(TypeError):
            json.dumps(marker)
        json.dumps(result)


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            validator.service_method_authority_contract_validator_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = validator.service_method_authority_contract_validator_manifest()
        manifest["depends_on"]["read_only_governance_layer"] = "mutated"
        manifest["runtime_dependencies"].append("mutated")
        manifest["failure_values"].append("mutated")

        self.assertEqual(
            validator.service_method_authority_contract_validator_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(name for name in dir(validator) if not name.startswith("_")),
            [
                "Mapping",
                "deepcopy",
                "service_method_authority_contract_validator_manifest",
                "validate_service_method_authority_contract",
            ],
        )

    def test_signatures(self) -> None:
        self.assertEqual(
            str(
                inspect.signature(
                    validator.service_method_authority_contract_validator_manifest
                )
            ),
            "() -> dict[str, object]",
        )
        self.assertEqual(
            str(
                inspect.signature(
                    validator.validate_service_method_authority_contract
                )
            ),
            "(payload: object) -> dict[str, object]",
        )


class SourceBoundaryTests(unittest.TestCase):
    def source_text(self) -> str:
        source_path = Path(validator.__file__)
        return source_path.read_text()

    def sanitized_source_text(self) -> str:
        source = self.source_text()
        allowed_strings = [
            "service_method_authority_contract_validator",
            "service_method_authority_contract_validator_manifest",
            "validate_service_method_authority_contract",
            "service-method-authority-contract-spec-only-v1",
            "service_adapter_runtime_authorized",
            "service_method_call_authorized",
            "service_side_effect_authorized",
            "evidence_service_authorized",
            "approval_service_authorized",
            "review_service_authorized",
            "revision_seal_service_authorized",
            "audit_service_authorized",
        ]
        for allowed in allowed_strings:
            source = source.replace(allowed, "")
        return source

    def test_only_allowed_production_imports(self) -> None:
        source = self.source_text()

        self.assertIn("from collections.abc import Mapping", source)
        self.assertIn("from copy import deepcopy", source)
        import_lines = [
            line for line in source.splitlines() if line.startswith("import ")
            or line.startswith("from ")
        ]
        self.assertEqual(
            import_lines,
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )

    def test_no_service_db_repository_uow_recovery_cli_import(self) -> None:
        source = self.source_text()
        forbidden = [
            "kernel.services",
            "kernel.stores.sqlite",
            "repositories",
            "unit_of_work",
            "recovery_gate",
            "recovery_session_host",
            "signable_path_orchestrator",
            "recovery_cli",
        ]

        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_upstream_validator_checker_ci_import(self) -> None:
        source = self.source_text()
        forbidden = [
            "service_adapter_boundary_validator",
            "append_runtime_authority_service_boundary_validator",
            "evidence_audit_append_contract_validator",
            "repository_uow_allowlist_validator",
            "write_path_contract_validator",
            "executor_precondition_validator",
            "execution_authorization_validator",
            "validator_ci",
            "write_side_recovery_precondition_checker",
            "recovery_precondition_checker",
        ]

        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_forbidden_runtime_markers(self) -> None:
        source = self.sanitized_source_text()
        forbidden = [
            "datetime.now",
            "time.time",
            "time.monotonic",
            "hashlib",
            "hmac",
            "secrets",
            "sha256",
            "blake2",
            "open(",
            "Path(",
            "os.environ",
            "subprocess",
            "threading",
            "asyncio",
            "socket",
            "argparse",
            "click",
            "inspect.",
            "getattr(",
            "callable(",
            "dir(",
            "hasattr(",
            "importlib",
            "open_connection",
            "UnitOfWork",
            "KernelUnitOfWork",
            "approval_service.",
            "review_service.",
            "revision_seal_service.",
            "evidence_service.",
            "close_evidence",
            "evaluate_barrier",
            "reverify_for_seal",
            "render_review",
            "seal_revision",
            "append_audit",
            "append_evidence",
            "restore_task",
            "restore_if_allowed",
            "restore_task_from_snapshot",
            "recovery_session_host",
            "signable_path_orchestrator",
            "apply_migrations",
            "begin_transaction",
            "commit(",
            "rollback(",
            "reserve_idempotency",
            "service_adapter_runtime",
            "call_service",
            "service_method_call",
        ]

        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
