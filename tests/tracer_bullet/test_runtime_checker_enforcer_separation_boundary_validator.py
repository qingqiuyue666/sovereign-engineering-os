import ast
import copy
import inspect
import json
import unittest

from kernel.lifecycle import (
    runtime_checker_enforcer_separation_boundary_validator as module,
)
from kernel.lifecycle.runtime_checker_enforcer_separation_boundary_validator import (
    runtime_checker_enforcer_separation_boundary_validator_manifest,
    validate_runtime_checker_enforcer_separation_boundary,
)


INPUT_KEY = "runtime_checker_enforcer_separation_boundary"
READY_KEY = "runtime_checker_enforcer_separation_boundary_ready"


class LeakyValue:
    def __repr__(self):
        return "LEAKY_RUNTIME_OBJECT"


def manifest():
    return runtime_checker_enforcer_separation_boundary_validator_manifest()


def valid_boundary():
    data = manifest()
    return {
        "surface": "RuntimeCheckerEnforcerSeparationBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(data["expected_source_refs"]),
        "checker_enforcer_separation_boundary_model": {
            item: True
            for item in data[
                "expected_checker_enforcer_separation_boundary_model"
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
    testcase.assertNotIn("LEAKY_RUNTIME_OBJECT", encoded)


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_defensive_copy(self):
        data = manifest()
        data["expected_source_refs"]["mutated"] = "bad"
        data["authority_summary"][
            "runtime_checker_enforcer_separation_authorized"
        ] = True
        data["non_authority_summary"][
            "runtime_checker_enforcer_separation_boundary_ready_authorizes"
        ]["runtime"] = True

        fresh = manifest()

        self.assertNotIn("mutated", fresh["expected_source_refs"])
        self.assertIs(
            fresh["authority_summary"][
                "runtime_checker_enforcer_separation_authorized"
            ],
            False,
        )
        self.assertIs(
            fresh["non_authority_summary"][
                "runtime_checker_enforcer_separation_boundary_ready_authorizes"
            ]["runtime"],
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
                "runtime_checker_enforcer_separation_boundary_validator_manifest",
                "validate_runtime_checker_enforcer_separation_boundary",
            ),
        )
        data = manifest()
        self.assertEqual(data["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    runtime_checker_enforcer_separation_boundary_validator_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    validate_runtime_checker_enforcer_separation_boundary
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
                "checker_enforcer_separation_boundary_model_invalid",
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
            [
                "ready",
                "not_ready",
                (
                    "invalid_runtime_checker_enforcer_separation_boundary_"
                    "payload"
                ),
            ],
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
    def test_valid_ready_payload(self):
        result = validate_runtime_checker_enforcer_separation_boundary(
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

    def test_output_is_bounded_expected_summary(self):
        result = validate_runtime_checker_enforcer_separation_boundary(
            valid_payload()
        )
        boundary = result["boundary"]
        data = manifest()

        self.assertEqual(
            set(boundary),
            set(data["expected_boundary_keys"]),
        )
        self.assertEqual(
            boundary["source_refs"],
            data["expected_source_refs"],
        )
        self.assertEqual(
            set(boundary["checker_enforcer_separation_boundary_model"]),
            set(data["expected_checker_enforcer_separation_boundary_model"]),
        )
        self.assertTrue(
            all(
                value is True
                for value in boundary[
                    "checker_enforcer_separation_boundary_model"
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

    def test_authority_summary_hard_false(self):
        result = validate_runtime_checker_enforcer_separation_boundary(
            valid_payload()
        )
        authority = result["authority"]

        self.assertTrue(authority)
        self.assertEqual(authority, manifest()["authority_summary"])
        self.assertTrue(all(value is False for value in authority.values()))
        for flag in (
            "runtime_checker_enforcer_separation_authorized",
            "runtime_checker_to_enforcer_handoff_authorized",
            "runtime_checker_output_as_enforcer_authority_authorized",
            "runtime_enforcer_output_as_execution_authorized",
            "service_call_execution_authorized",
            "repository_uow_writes_authorized",
            "evidence_append_authorized",
            "audit_append_authorized",
            "transaction_runtime_authorized",
            "executor_service_dispatch_authorized",
            "durable_writes_authorized",
            "irreversible_action_authorized",
        ):
            self.assertIn(flag, authority)

    def test_ready_authorizes_nothing(self):
        result = validate_runtime_checker_enforcer_separation_boundary(
            valid_payload()
        )
        non_authority = result["non_authority"]

        self.assertEqual(
            non_authority[
                "runtime_checker_enforcer_separation_boundary_ready_proves"
            ],
            "structural_declaration_validity_only",
        )
        denies = non_authority[
            "runtime_checker_enforcer_separation_boundary_ready_authorizes"
        ]
        for denied in (
            "runtime",
            "checker_runtime",
            "checker_implementation",
            "checker_decision",
            "enforcer_runtime",
            "enforcer_implementation",
            "enforcer_decision",
            "enforcer_action",
            "checker_to_enforcer_handoff",
            "runtime_authority_grant_usage",
            "authority_ref_runtime_usage",
            "service_call_admission",
            "admission_decision",
            "service_calls",
            "service_adapter_runtime",
            "evidence_approval_review_revision_audit_services",
            "evidence_audit_append",
            "db_repository_uow_writes",
            "transaction_idempotency_rollback",
            "executor_dispatch",
            "restore",
            "cli_schema_daemon",
            "durable_writes",
            "irreversible_actions",
            "toctou_physical_enforcement",
            "capability_token_work",
            "forensic_audit_binding",
        ):
            self.assertIs(denies[denied], False)
        self.assertIs(non_authority["validator_success_is_authority"], False)
        self.assertIs(
            non_authority["checker_output_is_enforcer_authority"],
            False,
        )
        self.assertIs(
            non_authority["checker_to_enforcer_handoff_is_authorized"],
            False,
        )
        self.assertIs(non_authority["enforcer_output_is_execution"], False)
        self.assertIs(
            non_authority["enforcer_output_is_service_call_permission"],
            False,
        )
        self.assertIs(
            non_authority["enforcer_output_is_db_write_permission"],
            False,
        )


class PayloadValidationTests(unittest.TestCase):
    def assert_failure(self, payload, failure, reason="not_ready"):
        result = validate_runtime_checker_enforcer_separation_boundary(payload)

        self.assertIn(failure, result["failures"])
        self.assertEqual(result["reason_code"], reason)
        self.assertIs(result[READY_KEY], False)
        assert_json_safe_without_leak(self, result)
        return result

    def test_invalid_payload_not_mapping(self):
        result = self.assert_failure(
            [],
            "payload_not_mapping",
            "invalid_runtime_checker_enforcer_separation_boundary_payload",
        )
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_payload_shape_mismatch(self):
        payload = valid_payload()
        payload["extra"] = valid_boundary()

        self.assert_failure(
            payload,
            "payload_shape_mismatch",
            "invalid_runtime_checker_enforcer_separation_boundary_payload",
        )

    def test_boundary_not_mapping(self):
        self.assert_failure(
            {INPUT_KEY: []},
            "boundary_not_mapping",
            "invalid_runtime_checker_enforcer_separation_boundary_payload",
        )

    def test_boundary_shape_mismatch(self):
        payload = valid_payload()
        payload[INPUT_KEY]["extra"] = True

        self.assert_failure(
            payload,
            "boundary_shape_mismatch",
            "invalid_runtime_checker_enforcer_separation_boundary_payload",
        )

    def test_surface_invalid(self):
        payload = valid_payload()
        payload[INPUT_KEY]["surface"] = "WrongSurface"

        self.assert_failure(payload, "boundary_surface_invalid")

    def test_version_invalid(self):
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
            "runtime-checker-enforcer-separation-boundary-spec-only-v1"
        ] = "bad"

        self.assert_failure(payload, "source_ref_mismatch")

    def test_invalid_source_refs_not_echoed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"] = {
            "runtime-checker-enforcer-separation-boundary-spec-only-v1": (
                LeakyValue()
            )
        }

        result = self.assert_failure(payload, "source_ref_mismatch")
        self.assertEqual(
            result["boundary"]["source_refs"],
            manifest()["expected_source_refs"],
        )

    def test_boundary_model_missing_or_false_fails(self):
        payload = valid_payload()
        payload[INPUT_KEY]["checker_enforcer_separation_boundary_model"].pop(
            "checker_output_boundary"
        )

        self.assert_failure(
            payload,
            "checker_enforcer_separation_boundary_model_invalid",
        )

        payload = valid_payload()
        payload[INPUT_KEY]["checker_enforcer_separation_boundary_model"][
            "checker_output_boundary"
        ] = False

        self.assert_failure(
            payload,
            "checker_enforcer_separation_boundary_model_invalid",
        )

    def test_each_false_flag_required(self):
        for flag in manifest()["required_false_authority_flags"]:
            payload = valid_payload()
            payload[INPUT_KEY]["false_authority_flags"].pop(flag)

            with self.subTest(flag=flag):
                self.assert_failure(payload, "authorization_flag_invalid")

    def test_true_authority_flag_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["false_authority_flags"][
            "runtime_checker_to_enforcer_handoff_authorized"
        ] = True

        self.assert_failure(payload, "authorization_flag_true")

    def test_authority_flag_non_bool_fails(self):
        payload = valid_payload()
        payload[INPUT_KEY]["false_authority_flags"][
            "runtime_checker_runtime_authorized"
        ] = 0

        self.assert_failure(payload, "authorization_flag_invalid")

    def test_each_true_declaration_required(self):
        for declaration in manifest()["required_true_declarations"]:
            payload = valid_payload()
            payload[INPUT_KEY]["true_declarations"].pop(declaration)

            with self.subTest(declaration=declaration):
                self.assert_failure(payload, "required_declaration_invalid")

    def test_required_declaration_false_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["true_declarations"][
            "checker_output_is_not_enforcer_authority"
        ] = False

        self.assert_failure(payload, "required_declaration_false")

    def test_json_safety_missing_or_false_fails(self):
        payload = valid_payload()
        payload[INPUT_KEY]["json_safety"].pop("runtime_object_handles")

        self.assert_failure(payload, "json_safety_invalid")

        payload = valid_payload()
        payload[INPUT_KEY]["json_safety"]["runtime_object_handles"] = False

        self.assert_failure(payload, "json_safety_invalid")

    def test_future_validator_requirement_missing_or_false_fails(self):
        payload = valid_payload()
        payload[INPUT_KEY]["future_validator_requirements"].pop(
            "future_execution_context_binding_boundary_required"
        )

        self.assert_failure(payload, "future_validator_requirement_invalid")

        payload = valid_payload()
        payload[INPUT_KEY]["future_validator_requirements"][
            "ghost_authority_forbidden"
        ] = False

        self.assert_failure(payload, "future_validator_requirement_invalid")

    def test_future_ci_requirement_missing_or_false_fails(self):
        payload = valid_payload()
        payload[INPUT_KEY]["future_ci_requirements"].pop(
            "validates_validator_checkpoint_binding"
        )

        self.assert_failure(payload, "future_ci_requirement_invalid")

        payload = valid_payload()
        payload[INPUT_KEY]["future_ci_requirements"][
            "must_not_import_or_call_validator"
        ] = False

        self.assert_failure(payload, "future_ci_requirement_invalid")

    def test_json_safe_false_or_missing_fails_closed(self):
        payload = valid_payload()
        payload[INPUT_KEY]["json_safe"] = False

        self.assert_failure(payload, "json_safe_invalid")

        payload = valid_payload()
        payload[INPUT_KEY].pop("json_safe")

        self.assert_failure(
            payload,
            "json_safe_invalid",
            "invalid_runtime_checker_enforcer_separation_boundary_payload",
        )

    def test_json_safety_rejects_unbounded_or_non_json_values(self):
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"] = copy.deepcopy(
            manifest()["expected_source_refs"]
        )
        payload[INPUT_KEY]["source_refs"][
            "runtime-checker-enforcer-separation-boundary-spec-only-v1"
        ] = "x" * 4097

        self.assert_failure(payload, "source_ref_mismatch")

        payload = valid_payload()
        payload[INPUT_KEY]["json_safety"]["runtime_object_handles"] = (
            LeakyValue()
        )

        self.assert_failure(payload, "json_safety_invalid")

    def test_reason_code_mapping(self):
        invalid = validate_runtime_checker_enforcer_separation_boundary(
            {INPUT_KEY: valid_boundary(), "extra": True}
        )
        not_ready_payload = valid_payload()
        not_ready_payload[INPUT_KEY]["source_refs"] = {}
        not_ready = validate_runtime_checker_enforcer_separation_boundary(
            not_ready_payload
        )
        ready = validate_runtime_checker_enforcer_separation_boundary(
            valid_payload()
        )

        self.assertEqual(
            invalid["reason_code"],
            "invalid_runtime_checker_enforcer_separation_boundary_payload",
        )
        self.assertEqual(not_ready["reason_code"], "not_ready")
        self.assertEqual(ready["reason_code"], "ready")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = True
        payload[INPUT_KEY]["source_refs"] = {}
        payload[INPUT_KEY]["false_authority_flags"][
            "runtime_checker_runtime_authorized"
        ] = True
        payload[INPUT_KEY]["true_declarations"][
            "checker_output_is_not_enforcer_authority"
        ] = False
        payload[INPUT_KEY]["future_ci_requirements"] = {}
        payload[INPUT_KEY]["json_safe"] = False

        result = validate_runtime_checker_enforcer_separation_boundary(payload)

        self.assertEqual(
            result["failures"],
            [
                "boundary_version_invalid",
                "source_ref_mismatch",
                "authorization_flag_true",
                "required_declaration_false",
                "future_ci_requirement_invalid",
                "json_safe_invalid",
            ],
        )


class SafetyTests(unittest.TestCase):
    def test_input_is_not_mutated(self):
        payload = valid_payload()
        original = copy.deepcopy(payload)

        validate_runtime_checker_enforcer_separation_boundary(payload)

        self.assertEqual(payload, original)

    def test_raw_object_leakage_prevention(self):
        payload = valid_payload()
        payload[INPUT_KEY]["future_validator_requirements"][
            "ghost_authority_forbidden"
        ] = LeakyValue()

        result = validate_runtime_checker_enforcer_separation_boundary(payload)

        assert_json_safe_without_leak(self, result)
        self.assertNotIn("LEAKY_RUNTIME_OBJECT", repr(result))

    def test_gemini_risk_future_declarations_represented(self):
        data = manifest()
        requirements = set(data["future_validator_requirements"])

        for expected in (
            "checker_output_not_enough_for_enforcer_action",
            "checker_to_enforcer_handoff_remains_future_boundary",
            "future_execution_context_binding_boundary_required",
            "context_drift_must_fail_closed",
            "final_pre_dispatch_context_validation_future_boundary",
            "payload_environment_filesystem_state_binding_not_implemented_here",
            "bool_tag_readiness_ci_ok_checker_output_enforcer_output_not_authority",
            "stale_dead_intent_authority_must_fail_closed",
            "ghost_authority_forbidden",
            "single_use_capability_consumption_remains_future_boundary",
            "forensic_binding_boundary_required",
            "evidence_audit_bookkeeping_boundary_required",
            "transaction_idempotency_boundary_required",
            "executor_dispatch_boundary_required",
            "durable_write_final_authorization_boundary_required",
            "physical_enforcement_not_implemented",
        ):
            self.assertIn(expected, requirements)

    def test_no_forbidden_runtime_imports_or_calls(self):
        tree = source_tree()
        forbidden_import_roots = {
            "datetime",
            "time",
            "os",
            "pathlib",
            "sqlite3",
            "subprocess",
            "hashlib",
            "hmac",
            "secrets",
            "socket",
            "requests",
            "urllib",
            "importlib",
        }
        forbidden_calls = {
            "open",
            "connect",
            "execute",
            "commit",
            "rollback",
            "run",
            "Popen",
            "sha256",
            "getenv",
            "listdir",
            "walk",
            "scandir",
            "time",
            "now",
            "utcnow",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(
                        alias.name.split(".")[0],
                        forbidden_import_roots,
                    )
                    self.assertFalse(alias.name.startswith("kernel.services"))
                    self.assertFalse(alias.name.startswith("kernel.stores"))
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                self.assertNotIn(root, forbidden_import_roots)
                self.assertFalse((node.module or "").startswith("kernel."))
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    self.assertNotIn(func.id, forbidden_calls)
                elif isinstance(func, ast.Attribute):
                    self.assertNotIn(func.attr, forbidden_calls)

    def test_no_upstream_validator_checker_ci_calls(self):
        tree = source_tree()
        imported_modules = []
        called_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module or "")
            elif isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called_names.add(func.id)
                elif isinstance(func, ast.Attribute):
                    called_names.add(func.attr)

        self.assertEqual(imported_modules, ["collections.abc", "copy"])
        self.assertFalse(
            any(
                name.startswith("validate_runtime_")
                or name.startswith("consume_runtime_")
                for name in called_names
            )
        )

    def test_bounded_output_for_invalid_payload(self):
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"] = {"bad": LeakyValue()}
        payload[INPUT_KEY]["false_authority_flags"] = {
            "runtime_checker_runtime_authorized": LeakyValue()
        }
        result = validate_runtime_checker_enforcer_separation_boundary(payload)

        json.dumps(result, sort_keys=True)
        assert_json_safe_without_leak(self, result)
        self.assertEqual(
            result["boundary"]["source_refs"],
            manifest()["expected_source_refs"],
        )


if __name__ == "__main__":
    unittest.main()
