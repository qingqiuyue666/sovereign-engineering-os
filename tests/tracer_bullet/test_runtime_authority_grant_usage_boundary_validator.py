import ast
import copy
import inspect
import json
import unittest

from kernel.lifecycle import (
    runtime_authority_grant_usage_boundary_validator as module,
)
from kernel.lifecycle.runtime_authority_grant_usage_boundary_validator import (
    runtime_authority_grant_usage_boundary_validator_manifest,
    validate_runtime_authority_grant_usage_boundary,
)


INPUT_KEY = "runtime_authority_grant_usage_boundary"
READY_KEY = "runtime_authority_grant_usage_boundary_ready"
INVALID_PAYLOAD = (
    "invalid_runtime_authority_grant_usage_boundary_payload"
)


class LeakyValue:
    def __repr__(self):
        return "LEAKY_GRANT_USAGE_RUNTIME_OBJECT"


def manifest():
    return runtime_authority_grant_usage_boundary_validator_manifest()


def valid_boundary():
    data = manifest()
    return {
        "surface": "RuntimeAuthorityGrantUsageBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(data["expected_source_refs"]),
        "runtime_authority_grant_usage_boundary_model": {
            item: True
            for item in data[
                "expected_runtime_authority_grant_usage_boundary_model"
            ]
        },
        "false_authority_flags": {
            flag: False for flag in data["required_false_authority_flags"]
        },
        "true_declarations": {
            declaration: True
            for declaration in data["required_true_declarations"]
        },
        "json_safety": {
            requirement: True
            for requirement in data["json_safety_requirements"]
        },
        "future_validator_requirements": {
            requirement: True
            for requirement in data["future_validator_requirements"]
        },
        "future_ci_requirements": {
            requirement: True
            for requirement in data["future_ci_requirements"]
        },
        "json_safe": True,
    }


def valid_payload():
    return {INPUT_KEY: valid_boundary()}


def source_tree():
    return ast.parse(inspect.getsource(module))


def assert_json_safe_without_leak(testcase, result):
    encoded = json.dumps(result, sort_keys=True)
    testcase.assertNotIn("LEAKY_GRANT_USAGE_RUNTIME_OBJECT", encoded)


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_defensive_copy(self):
        data = manifest()
        data["expected_source_refs"][
            "runtime-authority-grant-usage-boundary-spec-only-v1"
        ] = "mutated"
        data["authority_summary"][
            "runtime_authority_grant_usage_authorized"
        ] = True
        data["non_authority_summary"][
            "runtime_authority_grant_usage_boundary_ready_authorizes"
        ]["service_calls"] = True

        fresh = manifest()

        self.assertEqual(
            fresh["expected_source_refs"][
                "runtime-authority-grant-usage-boundary-spec-only-v1"
            ],
            "01e51b3529011d1099c467186a62be903ce5d6a7",
        )
        self.assertIs(
            fresh["authority_summary"][
                "runtime_authority_grant_usage_authorized"
            ],
            False,
        )
        self.assertIs(
            fresh["non_authority_summary"][
                "runtime_authority_grant_usage_boundary_ready_authorizes"
            ]["service_calls"],
            False,
        )

    def test_manifest_is_json_safe(self):
        data = manifest()
        json.dumps(data, sort_keys=True)
        self.assertIs(data["json_safe"], True)

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            module.__all__,
            (
                "runtime_authority_grant_usage_boundary_validator_manifest",
                "validate_runtime_authority_grant_usage_boundary",
            ),
        )
        data = manifest()
        self.assertEqual(data["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    runtime_authority_grant_usage_boundary_validator_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    validate_runtime_authority_grant_usage_boundary
                ).parameters
            ),
            ["payload"],
        )
        self.assertEqual(
            data["failure_taxonomy"],
            [
                "payload_not_mapping",
                "payload_shape_mismatch",
                "boundary_not_mapping",
                "boundary_shape_mismatch",
                "boundary_surface_invalid",
                "boundary_version_invalid",
                "source_ref_mismatch",
                "grant_usage_boundary_model_invalid",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "required_declaration_invalid",
                "required_declaration_false",
                "json_safety_invalid",
                "future_validator_requirement_invalid",
                "future_ci_requirement_invalid",
                "json_safe_invalid",
            ],
        )
        self.assertEqual(
            data["allowed_reason_codes"],
            ["ready", "not_ready", INVALID_PAYLOAD],
        )

    def test_production_imports_limited_to_mapping_and_deepcopy(self):
        imports = [
            node
            for node in ast.walk(source_tree())
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        self.assertEqual(len(imports), 2)
        self.assertEqual(imports[0].module, "collections.abc")
        self.assertEqual(
            [alias.name for alias in imports[0].names],
            ["Mapping"],
        )
        self.assertEqual(imports[1].module, "copy")
        self.assertEqual(
            [alias.name for alias in imports[1].names],
            ["deepcopy"],
        )
        self.assertEqual(
            manifest()["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )


class HappyPathTests(unittest.TestCase):
    def test_ready_valid_declaration(self):
        result = validate_runtime_authority_grant_usage_boundary(
            valid_payload()
        )

        self.assertEqual(
            set(result),
            {
                READY_KEY,
                "reason_code",
                "failures",
                "boundary",
                "authority",
                "non_authority",
                "json_safe",
            },
        )
        self.assertIs(result[READY_KEY], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

    def test_output_bounded_expected_summary(self):
        result = validate_runtime_authority_grant_usage_boundary(
            valid_payload()
        )
        boundary = result["boundary"]
        data = manifest()

        self.assertEqual(set(boundary), set(data["expected_boundary_keys"]))
        self.assertEqual(
            boundary["source_refs"],
            data["expected_source_refs"],
        )
        self.assertEqual(
            set(boundary["runtime_authority_grant_usage_boundary_model"]),
            set(data["expected_runtime_authority_grant_usage_boundary_model"]),
        )
        self.assertTrue(
            all(
                value is True
                for value in boundary[
                    "runtime_authority_grant_usage_boundary_model"
                ].values()
            )
        )
        self.assertTrue(
            all(
                value is False
                for value in boundary["false_authority_flags"].values()
            )
        )
        self.assertTrue(
            all(
                value is True
                for value in boundary["true_declarations"].values()
            )
        )

    def test_authority_output_hard_false(self):
        result = validate_runtime_authority_grant_usage_boundary(
            valid_payload()
        )
        authority = result["authority"]

        self.assertEqual(authority, manifest()["authority_summary"])
        self.assertTrue(all(value is False for value in authority.values()))
        for flag in (
            "runtime_authority_grant_usage_authorized",
            "authority_ref_runtime_usage_authorized",
            "service_call_admission_runtime_authorized",
            "service_call_execution_authorized",
            "repository_uow_writes_authorized",
            "evidence_append_authorized",
            "audit_append_authorized",
            "transaction_runtime_authorized",
            "executor_service_dispatch_authorized",
            "durable_writes_authorized",
            "physical_io_authorized",
        ):
            self.assertIn(flag, authority)

    def test_ready_authorizes_no_runtime_grant_or_side_effects(self):
        result = validate_runtime_authority_grant_usage_boundary(
            valid_payload()
        )
        non_authority = result["non_authority"]

        self.assertEqual(
            non_authority[
                "runtime_authority_grant_usage_boundary_ready_proves"
            ],
            "structural_declaration_validity_only",
        )
        denies = non_authority[
            "runtime_authority_grant_usage_boundary_ready_authorizes"
        ]
        for denied in (
            "runtime_eligibility",
            "grant_usage",
            "grant_consumption",
            "grant_validation_runtime",
            "grant_revocation",
            "grant_expiry_enforcement",
            "grant_scope_enforcement",
            "grant_operation_enforcement",
            "grant_target_enforcement",
            "authority_ref_runtime_usage",
            "service_call_admission_runtime",
            "admission_decision_runtime",
            "service_calls",
            "db_repository_uow_writes",
            "evidence_audit_append",
            "transaction_idempotency_rollback",
            "executor_dispatch",
            "restore",
            "digest_sha_merkle_computation",
            "cryptographic_verification",
            "capability_token_work",
            "durable_writes",
            "irreversible_actions",
            "physical_io",
        ):
            self.assertIs(denies[denied], False)
        self.assertIs(non_authority["validator_success_is_runtime_authority"], False)
        self.assertIs(
            non_authority["validator_success_is_grant_usage_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_authority_ref_usage_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_service_call_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_db_write_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_append_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_executor_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_durable_write_authority"],
            False,
        )
        self.assertIs(
            non_authority["validator_success_is_physical_io_authority"],
            False,
        )

    def test_grant_object_and_downstream_boundaries_non_authority(self):
        result = validate_runtime_authority_grant_usage_boundary(
            valid_payload()
        )
        non_authority = result["non_authority"]

        self.assertIs(
            non_authority["grant_object_existence_is_usage_authority"],
            False,
        )
        self.assertIs(
            non_authority["grant_object_readiness_is_runtime_authority"],
            False,
        )
        self.assertIs(
            non_authority[
                "grant_object_validation_is_service_permission"
            ],
            False,
        )
        self.assertIs(
            non_authority["grant_presence_is_admission_permission"],
            False,
        )
        self.assertIs(
            non_authority[
                "grant_id_presence_is_authority_ref_runtime_usage"
            ],
            False,
        )
        self.assertIs(
            non_authority[
                "authority_ref_runtime_usage_remains_future_boundary"
            ],
            True,
        )
        self.assertIs(
            non_authority[
                "service_call_admission_runtime_remains_future_boundary"
            ],
            True,
        )
        self.assertIs(
            non_authority[
                "admission_decision_runtime_remains_future_boundary"
            ],
            True,
        )
        self.assertIs(
            non_authority[
                "transaction_idempotency_remains_future_boundary"
            ],
            True,
        )
        self.assertIs(
            non_authority[
                "evidence_audit_bookkeeping_remains_future_boundary"
            ],
            True,
        )
        self.assertIs(
            non_authority["executor_dispatch_remains_future_boundary"],
            True,
        )
        self.assertIs(
            non_authority[
                "durable_write_final_authorization_remains_future_boundary"
            ],
            True,
        )


class PayloadValidationTests(unittest.TestCase):
    def assert_failure(self, payload, failure, reason="not_ready"):
        result = validate_runtime_authority_grant_usage_boundary(payload)

        self.assertIn(failure, result["failures"])
        self.assertEqual(result["reason_code"], reason)
        self.assertIs(result[READY_KEY], False)
        assert_json_safe_without_leak(self, result)
        return result

    def test_payload_not_mapping(self):
        result = self.assert_failure(
            [],
            "payload_not_mapping",
            INVALID_PAYLOAD,
        )
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_payload_shape_mismatch(self):
        payload = valid_payload()
        payload["extra"] = valid_boundary()

        self.assert_failure(
            payload,
            "payload_shape_mismatch",
            INVALID_PAYLOAD,
        )

    def test_boundary_not_mapping(self):
        self.assert_failure(
            {INPUT_KEY: []},
            "boundary_not_mapping",
            INVALID_PAYLOAD,
        )

    def test_boundary_shape_mismatch(self):
        payload = valid_payload()
        payload[INPUT_KEY]["extra"] = True

        self.assert_failure(
            payload,
            "boundary_shape_mismatch",
            INVALID_PAYLOAD,
        )

    def test_invalid_surface(self):
        payload = valid_payload()
        payload[INPUT_KEY]["surface"] = "WrongSurface"

        self.assert_failure(payload, "boundary_surface_invalid")

    def test_invalid_version(self):
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = 2

        self.assert_failure(payload, "boundary_version_invalid")

    def test_bool_as_int_version_rejected(self):
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = True

        self.assert_failure(payload, "boundary_version_invalid")

    def test_source_ref_mismatch(self):
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"][
            "runtime-authority-grant-usage-boundary-spec-only-v1"
        ] = "bad"

        self.assert_failure(payload, "source_ref_mismatch")

    def test_invalid_source_refs_do_not_leak_into_output(self):
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"] = {
            "runtime-authority-grant-usage-boundary-spec-only-v1": (
                LeakyValue()
            )
        }

        result = self.assert_failure(payload, "source_ref_mismatch")
        self.assertEqual(
            result["boundary"]["source_refs"],
            manifest()["expected_source_refs"],
        )

    def test_boundary_model_invalid(self):
        payload = valid_payload()
        payload[INPUT_KEY][
            "runtime_authority_grant_usage_boundary_model"
        ].pop("grant_object_existence_boundary")

        self.assert_failure(payload, "grant_usage_boundary_model_invalid")

        payload = valid_payload()
        payload[INPUT_KEY][
            "runtime_authority_grant_usage_boundary_model"
        ]["grant_object_readiness_boundary"] = False

        self.assert_failure(payload, "grant_usage_boundary_model_invalid")

    def test_missing_false_authority_flag(self):
        payload = valid_payload()
        payload[INPUT_KEY]["false_authority_flags"].pop(
            "runtime_authority_grant_usage_authorized"
        )

        self.assert_failure(payload, "authorization_flag_invalid")

    def test_false_authority_flag_true_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["false_authority_flags"][
            "runtime_authority_grant_usage_authorized"
        ] = True

        self.assert_failure(payload, "authorization_flag_true")

    def test_false_authority_flag_non_bool_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["false_authority_flags"][
            "authority_ref_runtime_usage_authorized"
        ] = 0

        self.assert_failure(payload, "authorization_flag_invalid")

    def test_missing_true_declaration(self):
        payload = valid_payload()
        payload[INPUT_KEY]["true_declarations"].pop(
            "grant_object_is_not_usage_authority"
        )

        self.assert_failure(payload, "required_declaration_invalid")

    def test_true_declaration_false_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["true_declarations"][
            "grant_readiness_is_not_runtime_authority"
        ] = False

        self.assert_failure(payload, "required_declaration_false")

    def test_true_declaration_non_bool_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["true_declarations"][
            "grant_validation_is_not_service_permission"
        ] = 1

        self.assert_failure(payload, "required_declaration_invalid")

    def test_json_safety_invalid(self):
        payload = valid_payload()
        payload[INPUT_KEY]["json_safety"].pop(
            "runtime_object_handles_forbidden"
        )

        self.assert_failure(payload, "json_safety_invalid")

        payload = valid_payload()
        payload[INPUT_KEY]["json_safety"][
            "runtime_object_handles_forbidden"
        ] = False

        self.assert_failure(payload, "json_safety_invalid")

    def test_future_validator_requirement_invalid(self):
        payload = valid_payload()
        payload[INPUT_KEY]["future_validator_requirements"].pop(
            "validate_exact_source_refs"
        )

        self.assert_failure(
            payload,
            "future_validator_requirement_invalid",
        )

        payload = valid_payload()
        payload[INPUT_KEY]["future_validator_requirements"][
            "call_no_services"
        ] = False

        self.assert_failure(
            payload,
            "future_validator_requirement_invalid",
        )

    def test_future_ci_requirement_invalid(self):
        payload = valid_payload()
        payload[INPUT_KEY]["future_ci_requirements"].pop(
            "validate_readiness_consistency"
        )

        self.assert_failure(payload, "future_ci_requirement_invalid")

        payload = valid_payload()
        payload[INPUT_KEY]["future_ci_requirements"][
            "do_not_import_or_call_validator"
        ] = False

        self.assert_failure(payload, "future_ci_requirement_invalid")

    def test_json_safe_false(self):
        payload = valid_payload()
        payload[INPUT_KEY]["json_safe"] = False

        self.assert_failure(payload, "json_safe_invalid")

    def test_json_safe_rejects_raw_object_values(self):
        payload = valid_payload()
        payload[INPUT_KEY][
            "runtime_authority_grant_usage_boundary_model"
        ]["grant_object_existence_boundary"] = LeakyValue()

        result = self.assert_failure(
            payload,
            "grant_usage_boundary_model_invalid",
        )
        self.assertIn("json_safe_invalid", result["failures"])

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = True
        payload[INPUT_KEY]["source_refs"][
            "runtime-authority-grant-usage-boundary-spec-only-v1"
        ] = "bad"
        payload[INPUT_KEY]["false_authority_flags"][
            "runtime_authority_grant_usage_authorized"
        ] = True
        payload[INPUT_KEY]["true_declarations"][
            "grant_object_is_not_usage_authority"
        ] = False
        payload[INPUT_KEY]["json_safe"] = False

        result = validate_runtime_authority_grant_usage_boundary(payload)

        self.assertEqual(
            result["failures"],
            [
                "boundary_version_invalid",
                "source_ref_mismatch",
                "authorization_flag_true",
                "required_declaration_false",
                "json_safe_invalid",
            ],
        )


class SafetyTests(unittest.TestCase):
    def test_output_bounded(self):
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"] = {"bad": LeakyValue()}

        result = validate_runtime_authority_grant_usage_boundary(payload)
        json.dumps(result, sort_keys=True)
        self.assertEqual(
            set(result["boundary"]),
            set(manifest()["expected_boundary_keys"]),
        )
        self.assertEqual(result["authority"], manifest()["authority_summary"])
        self.assertEqual(
            result["non_authority"],
            manifest()["non_authority_summary"],
        )
        assert_json_safe_without_leak(self, result)

    def test_input_immutability(self):
        payload = valid_payload()
        original = copy.deepcopy(payload)

        validate_runtime_authority_grant_usage_boundary(payload)

        self.assertEqual(payload, original)

    def test_no_raw_object_leakage(self):
        payload = valid_payload()
        payload[INPUT_KEY]["false_authority_flags"][
            "runtime_authority_grant_usage_authorized"
        ] = LeakyValue()

        result = validate_runtime_authority_grant_usage_boundary(payload)

        assert_json_safe_without_leak(self, result)
        self.assertEqual(result["authority"], manifest()["authority_summary"])

    def test_no_service_db_runtime_imports_or_calls(self):
        tree = source_tree()
        source = inspect.getsource(module)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")

        self.assertEqual(imported_modules, {"collections.abc", "copy"})
        for forbidden in (
            "datetime.",
            "time.",
            "os.",
            "pathlib.",
            "sqlite3.",
            "subprocess.",
            "threading.",
            "asyncio.",
            "hashlib.",
            "hmac.",
            "secrets.",
            "inspect.",
            "importlib.",
            "requests.",
            "socket.",
            "open(",
            "git ",
            "service_call(",
            "append_evidence(",
            "append_audit(",
            "dispatch_executor(",
            "restore(",
        ):
            self.assertNotIn(forbidden, source)

    def test_no_upstream_validator_checker_or_ci_imports(self):
        source = inspect.getsource(module)

        for forbidden in (
            "validate_runtime_authority_grant_object(",
            "validate_runtime_authority_checker_enforcer_boundary(",
            "validate_runtime_checker_enforcer_separation_boundary(",
            "validate_service_call_admission_gate(",
            "validate_service_call_execution_boundary(",
            "validate_evidence_audit_append_contract(",
            "validate_repository_uow_allowlist(",
            "validate_executor_precondition(",
            "validate_execution_authorization(",
            "consume_runtime_",
            "consume_service_",
            "consume_evidence_",
            "consume_repository_",
            "consume_executor_",
            "consume_execution_",
        ):
            self.assertNotIn(forbidden, source)
