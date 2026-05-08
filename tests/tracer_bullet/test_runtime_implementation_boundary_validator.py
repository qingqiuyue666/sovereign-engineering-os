import ast
import copy
import inspect
import json
import unittest
from pathlib import Path

from kernel.lifecycle import runtime_implementation_boundary_validator as module
from kernel.lifecycle.runtime_implementation_boundary_validator import (
    runtime_implementation_boundary_validator_manifest,
    validate_runtime_implementation_boundary,
)


MODULE_PATH = Path(module.__file__)


def valid_boundary():
    manifest = runtime_implementation_boundary_validator_manifest()
    return {
        "surface": "RuntimeImplementationBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(manifest["expected_source_refs"]),
        "runtime_implementation_boundary_model": {
            item: True
            for item in manifest[
                "expected_runtime_implementation_boundary_model"
            ]
        },
        "required_runtime_boundaries": {
            item: True for item in manifest["required_runtime_boundaries"]
        },
        "false_authority_flags": {
            flag: False
            for flag in manifest["required_false_authority_flags"]
        },
        "true_declarations": {
            declaration: True
            for declaration in manifest["required_true_declarations"]
        },
        "json_safety": {
            requirement: True
            for requirement in manifest["json_safety_requirements"]
        },
        "future_validator_requirements": {
            requirement: True
            for requirement in manifest["future_validator_requirements"]
        },
        "future_ci_requirements": {
            requirement: True
            for requirement in manifest["future_ci_requirements"]
        },
        "json_safe": True,
    }


def valid_payload():
    return {"runtime_implementation_boundary": valid_boundary()}


def source_text():
    return MODULE_PATH.read_text(encoding="utf-8")


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_json_safe_and_defensive_copy(self):
        manifest = runtime_implementation_boundary_validator_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertIs(manifest["json_safe"], True)

        manifest["expected_source_refs"]["mutated"] = "bad"
        fresh = runtime_implementation_boundary_validator_manifest()
        self.assertNotIn("mutated", fresh["expected_source_refs"])

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            module.__all__,
            [
                "runtime_implementation_boundary_validator_manifest",
                "validate_runtime_implementation_boundary",
            ],
        )
        manifest = runtime_implementation_boundary_validator_manifest()
        self.assertEqual(manifest["public_api"], list(module.__all__))
        self.assertEqual(
            list(inspect.signature(validate_runtime_implementation_boundary).parameters),
            ["payload"],
        )

    def test_production_imports_limited_to_mapping_and_deepcopy(self):
        tree = ast.parse(source_text())
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        self.assertEqual(len(imports), 2)
        self.assertEqual(imports[0].module, "collections.abc")
        self.assertEqual([alias.name for alias in imports[0].names], ["Mapping"])
        self.assertEqual(imports[1].module, "copy")
        self.assertEqual([alias.name for alias in imports[1].names], ["deepcopy"])
        self.assertEqual(
            runtime_implementation_boundary_validator_manifest()["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )

    def test_manifest_declares_expected_failure_taxonomy_and_reason_codes(self):
        manifest = runtime_implementation_boundary_validator_manifest()
        self.assertEqual(
            manifest["failure_taxonomy"],
            [
                "payload_not_mapping",
                "payload_shape_mismatch",
                "boundary_not_mapping",
                "boundary_shape_mismatch",
                "boundary_surface_invalid",
                "boundary_version_invalid",
                "source_ref_mismatch",
                "runtime_boundary_model_invalid",
                "required_runtime_boundary_invalid",
                "required_runtime_boundary_missing",
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
            manifest["allowed_reason_codes"],
            [
                "ready",
                "not_ready",
                "invalid_runtime_implementation_boundary_payload",
            ],
        )


class HappyPathTests(unittest.TestCase):
    def test_valid_rendered_declaration_returns_ready(self):
        result = validate_runtime_implementation_boundary(valid_payload())

        self.assertIs(result["runtime_implementation_boundary_ready"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

    def test_ready_output_hard_false_authority_summary(self):
        result = validate_runtime_implementation_boundary(valid_payload())
        authority = result["authority"]

        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))
        self.assertIn("runtime_implementation_authorized", authority)
        self.assertIn("service_call_execution_authorized", authority)
        self.assertIn("repository_uow_writes_authorized", authority)
        self.assertIn("irreversible_action_authorized", authority)

    def test_non_authority_summary_denies_runtime_service_write_append_executor(self):
        result = validate_runtime_implementation_boundary(valid_payload())
        non_authority = result["non_authority"]

        self.assertEqual(
            non_authority["runtime_implementation_boundary_ready_proves"],
            "structural_declaration_validity_only",
        )
        denies = non_authority[
            "runtime_implementation_boundary_ready_authorizes"
        ]
        for denied in (
            "runtime",
            "runtime_implementation",
            "checker_enforcer_runtime",
            "runtime_authority_grant_usage",
            "authority_ref_runtime_usage",
            "service_call_admission_runtime",
            "admission_decision_runtime",
            "service_calls",
            "db_repository_uow_writes",
            "evidence_audit_append",
            "transaction_idempotency_rollback",
            "executor_dispatch",
            "durable_writes",
            "irreversible_actions",
        ):
            self.assertIs(denies[denied], False)
        self.assertIs(non_authority["readiness_is_runtime_authority"], False)
        self.assertIs(non_authority["authorization_is_execution"], False)

    def test_output_boundary_summary_is_bounded_and_expected_only(self):
        result = validate_runtime_implementation_boundary(valid_payload())
        boundary = result["boundary"]
        manifest = runtime_implementation_boundary_validator_manifest()

        self.assertEqual(
            set(boundary["source_refs"]),
            set(manifest["expected_source_refs"]),
        )
        self.assertEqual(
            set(boundary["required_runtime_boundaries"]),
            set(manifest["required_runtime_boundaries"]),
        )
        self.assertEqual(
            set(boundary["false_authority_flags"]),
            set(manifest["required_false_authority_flags"]),
        )


class PayloadShapeTests(unittest.TestCase):
    def assert_failure(self, payload, failure):
        result = validate_runtime_implementation_boundary(payload)
        self.assertIs(result["runtime_implementation_boundary_ready"], False)
        self.assertIn(failure, result["failures"])
        return result

    def test_non_mapping_payload_fails_closed(self):
        result = self.assert_failure([], "payload_not_mapping")
        self.assertEqual(
            result["reason_code"],
            "invalid_runtime_implementation_boundary_payload",
        )

    def test_wrong_top_level_key_fails_closed(self):
        result = self.assert_failure({"wrong": valid_boundary()}, "payload_shape_mismatch")
        self.assertIn("boundary_not_mapping", result["failures"])

    def test_non_mapping_boundary_fails_closed(self):
        result = self.assert_failure(
            {"runtime_implementation_boundary": []},
            "boundary_not_mapping",
        )
        self.assertEqual(
            result["reason_code"],
            "invalid_runtime_implementation_boundary_payload",
        )

    def test_wrong_boundary_shape_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["extra"] = True
        self.assert_failure(payload, "boundary_shape_mismatch")

    def test_wrong_surface_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["surface"] = "Wrong"
        self.assert_failure(payload, "boundary_surface_invalid")

    def test_wrong_version_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["version"] = 2
        self.assert_failure(payload, "boundary_version_invalid")

    def test_bool_as_int_version_rejected(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["version"] = True
        self.assert_failure(payload, "boundary_version_invalid")

    def test_source_ref_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["source_refs"][
            "runtime-implementation-boundary-spec-only-v1"
        ] = "bad"
        self.assert_failure(payload, "source_ref_mismatch")

    def test_invalid_caller_source_refs_are_not_echoed(self):
        class Secret:
            def __repr__(self):
                return "SECRET_SOURCE_REF"

        payload = valid_payload()
        payload["runtime_implementation_boundary"]["source_refs"] = {
            "attacker": Secret()
        }
        result = self.assert_failure(payload, "source_ref_mismatch")

        rendered = repr(result)
        self.assertNotIn("SECRET_SOURCE_REF", rendered)
        self.assertNotIn("attacker", result["boundary"]["source_refs"])
        self.assertEqual(
            result["boundary"]["source_refs"],
            runtime_implementation_boundary_validator_manifest()[
                "expected_source_refs"
            ],
        )

    def test_missing_runtime_boundary_fails_closed(self):
        payload = valid_payload()
        del payload["runtime_implementation_boundary"][
            "required_runtime_boundaries"
        ]["runtime_checker_implementation_boundary"]
        self.assert_failure(payload, "required_runtime_boundary_missing")

    def test_invalid_runtime_boundary_model_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"][
            "runtime_implementation_boundary_model"
        ]["non_executable"] = 1
        self.assert_failure(payload, "runtime_boundary_model_invalid")

    def test_false_authority_flag_missing_fails_closed(self):
        payload = valid_payload()
        del payload["runtime_implementation_boundary"]["false_authority_flags"][
            "runtime_implementation_authorized"
        ]
        self.assert_failure(payload, "authorization_flag_invalid")

    def test_false_authority_flag_true_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        result = self.assert_failure(payload, "authorization_flag_true")
        self.assertIn("authorization_flag_true", result["failures"])

    def test_true_declaration_missing_fails_closed(self):
        payload = valid_payload()
        del payload["runtime_implementation_boundary"]["true_declarations"][
            "runtime_implementation_forbidden"
        ]
        self.assert_failure(payload, "required_declaration_invalid")

    def test_true_declaration_false_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["true_declarations"][
            "runtime_implementation_forbidden"
        ] = False
        self.assert_failure(payload, "required_declaration_false")

    def test_json_safety_invalid_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["json_safety"][
            "runtime_object_handles_forbidden"
        ] = False
        self.assert_failure(payload, "json_safety_invalid")

    def test_future_validator_requirement_invalid_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"][
            "future_validator_requirements"
        ]["read_only"] = False
        self.assert_failure(payload, "future_validator_requirement_invalid")

    def test_future_ci_requirement_invalid_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["future_ci_requirements"][
            "read_only"
        ] = False
        self.assert_failure(payload, "future_ci_requirement_invalid")

    def test_json_safe_false_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["json_safe"] = False
        self.assert_failure(payload, "json_safe_invalid")

    def test_bool_as_int_rejected_where_boolean_exactness_matters(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary"]["false_authority_flags"][
            "runtime_implementation_authorized"
        ] = 0
        self.assert_failure(payload, "authorization_flag_invalid")

        payload = valid_payload()
        payload["runtime_implementation_boundary"]["true_declarations"][
            "runtime_implementation_forbidden"
        ] = 1
        self.assert_failure(payload, "required_declaration_invalid")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        boundary = payload["runtime_implementation_boundary"]
        boundary["surface"] = "Wrong"
        boundary["version"] = True
        boundary["source_refs"] = {}
        boundary["runtime_implementation_boundary_model"] = {}
        boundary["required_runtime_boundaries"] = {}
        boundary["false_authority_flags"] = {}
        boundary["true_declarations"] = {}
        boundary["json_safety"] = {}
        boundary["future_validator_requirements"] = {}
        boundary["future_ci_requirements"] = {}
        boundary["json_safe"] = False

        result = validate_runtime_implementation_boundary(payload)

        self.assertEqual(
            result["failures"],
            [
                "boundary_surface_invalid",
                "boundary_version_invalid",
                "source_ref_mismatch",
                "runtime_boundary_model_invalid",
                "required_runtime_boundary_invalid",
                "required_runtime_boundary_missing",
                "authorization_flag_invalid",
                "required_declaration_invalid",
                "json_safety_invalid",
                "future_validator_requirement_invalid",
                "future_ci_requirement_invalid",
                "json_safe_invalid",
            ],
        )


class SafetyTests(unittest.TestCase):
    def test_input_immutability(self):
        payload = valid_payload()
        before = copy.deepcopy(payload)

        validate_runtime_implementation_boundary(payload)

        self.assertEqual(payload, before)

    def test_raw_object_leakage_prevented(self):
        class Secret:
            def __repr__(self):
                return "SECRET_RUNTIME_HANDLE"

        payload = valid_payload()
        payload["runtime_implementation_boundary"][
            "runtime_implementation_boundary_model"
        ]["non_executable"] = Secret()

        result = validate_runtime_implementation_boundary(payload)

        self.assertIn("runtime_boundary_model_invalid", result["failures"])
        self.assertNotIn("SECRET_RUNTIME_HANDLE", repr(result))
        json.dumps(result, sort_keys=True)

    def test_no_service_repository_uow_runtime_imports(self):
        tree = ast.parse(source_text())
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        forbidden_imports = {
            "kernel.services",
            "kernel.stores",
            "kernel.stores.sqlite.repositories",
            "kernel.stores.sqlite.unit_of_work",
            "sqlite3",
            "kernel.lifecycle.signable_path_orchestrator",
            "kernel.lifecycle.recovery_gate",
            "kernel.lifecycle.recovery_cli",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_modules))

        text = source_text()
        for marker in (
            "KernelUnitOfWork",
            "Repository",
            "audit.append(",
            "evidence.append(",
            "_audit.append(",
            "_repo.append(",
            "_journal_repo.append(",
            "_taint_repo.append(",
            ".execute(",
            ".commit(",
            ".rollback(",
            "open_connection",
            "restore_task_from_snapshot",
        ):
            self.assertNotIn(marker, text)

    def test_no_time_digest_subprocess_filesystem_network_imports(self):
        tree = ast.parse(source_text())
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        forbidden_imports = {
            "datetime",
            "time",
            "hashlib",
            "subprocess",
            "os",
            "pathlib",
            "socket",
            "urllib",
            "requests",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_modules))

        text = source_text()
        for marker in (
            "datetime.",
            "time.",
            "hashlib.",
            "subprocess.",
            "Path(",
            "open(",
            "socket.",
            "urllib.",
            "requests.",
        ):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
