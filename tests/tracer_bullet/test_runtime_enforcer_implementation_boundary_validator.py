import ast
import copy
import inspect
import json
import unittest
from pathlib import Path

from kernel.lifecycle import (
    runtime_enforcer_implementation_boundary_validator as module,
)
from kernel.lifecycle.runtime_enforcer_implementation_boundary_validator import (
    runtime_enforcer_implementation_boundary_validator_manifest,
    validate_runtime_enforcer_implementation_boundary,
)


MODULE_PATH = Path(module.__file__)


def valid_boundary():
    manifest = runtime_enforcer_implementation_boundary_validator_manifest()
    return {
        "surface": "RuntimeEnforcerImplementationBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(manifest["expected_source_refs"]),
        "runtime_enforcer_implementation_boundary_model": {
            item: True
            for item in manifest[
                "expected_runtime_enforcer_implementation_boundary_model"
            ]
        },
        "checker_enforcer_separation_model": {
            item: True
            for item in manifest[
                "expected_checker_enforcer_separation_model"
            ]
        },
        "forbidden_implicit_authority_sources": {
            item: True
            for item in manifest[
                "expected_forbidden_implicit_authority_sources"
            ]
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
    return {"runtime_enforcer_implementation_boundary": valid_boundary()}


def source_text():
    return MODULE_PATH.read_text(encoding="utf-8")


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_defensive_copy(self):
        manifest = runtime_enforcer_implementation_boundary_validator_manifest()
        manifest["expected_source_refs"]["mutated"] = "bad"
        manifest["authority_summary"][
            "runtime_enforcer_runtime_authorized"
        ] = True

        fresh = runtime_enforcer_implementation_boundary_validator_manifest()

        self.assertNotIn("mutated", fresh["expected_source_refs"])
        self.assertIs(
            fresh["authority_summary"][
                "runtime_enforcer_runtime_authorized"
            ],
            False,
        )

    def test_manifest_is_json_safe(self):
        manifest = runtime_enforcer_implementation_boundary_validator_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertIs(manifest["json_safe"], True)

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            module.__all__,
            [
                "runtime_enforcer_implementation_boundary_validator_manifest",
                "validate_runtime_enforcer_implementation_boundary",
            ],
        )
        manifest = runtime_enforcer_implementation_boundary_validator_manifest()
        self.assertEqual(manifest["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    validate_runtime_enforcer_implementation_boundary
                ).parameters
            ),
            ["payload"],
        )
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
                "enforcer_boundary_model_invalid",
                "checker_enforcer_separation_invalid",
                "forbidden_implicit_authority_invalid",
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
                "invalid_runtime_enforcer_implementation_boundary_payload",
            ],
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
            runtime_enforcer_implementation_boundary_validator_manifest()[
                "import_boundary"
            ],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )


class HappyPathTests(unittest.TestCase):
    def test_valid_declaration_returns_ready(self):
        result = validate_runtime_enforcer_implementation_boundary(
            valid_payload()
        )

        self.assertIs(
            result["runtime_enforcer_implementation_boundary_ready"],
            True,
        )
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

    def test_output_authority_summary_hard_false(self):
        result = validate_runtime_enforcer_implementation_boundary(
            valid_payload()
        )
        authority = result["authority"]

        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))
        for flag in (
            "runtime_enforcer_implementation_authorized",
            "runtime_enforcer_runtime_authorized",
            "runtime_enforcer_decision_authorized",
            "runtime_enforcer_action_authorized",
            "runtime_checker_runtime_authorized",
            "service_call_execution_authorized",
            "repository_uow_writes_authorized",
            "evidence_append_authorized",
            "audit_append_authorized",
            "durable_writes_authorized",
            "irreversible_action_authorized",
        ):
            self.assertIn(flag, authority)

    def test_output_non_authority_denies_required_paths(self):
        result = validate_runtime_enforcer_implementation_boundary(
            valid_payload()
        )
        non_authority = result["non_authority"]

        self.assertEqual(
            non_authority[
                "runtime_enforcer_implementation_boundary_ready_proves"
            ],
            "structural_declaration_validity_only",
        )
        denies = non_authority[
            "runtime_enforcer_implementation_boundary_ready_authorizes"
        ]
        for denied in (
            "runtime",
            "runtime_eligibility",
            "checker_runtime",
            "checker_implementation",
            "checker_decision",
            "enforcer_runtime",
            "enforcer_implementation",
            "enforcer_decision",
            "enforcer_action",
            "runtime_authority_grant_usage",
            "authority_ref_runtime_usage",
            "service_call_admission_runtime",
            "admission_decision_runtime",
            "service_calls",
            "db_repository_uow_writes",
            "evidence_audit_append",
            "transaction_idempotency_rollback",
            "executor_dispatch",
            "restore_execution",
            "durable_writes",
            "irreversible_actions",
        ):
            self.assertIs(denies[denied], False)
        self.assertIs(non_authority["readiness_is_runtime_authority"], False)
        self.assertIs(
            non_authority["validator_ready_is_enforcer_authority"],
            False,
        )
        self.assertIs(
            non_authority["enforcer_output_is_service_admission"],
            False,
        )
        self.assertIs(
            non_authority["enforcer_output_is_db_write_permission"],
            False,
        )
        self.assertIs(
            non_authority["enforcer_output_is_append_permission"],
            False,
        )
        self.assertIs(
            non_authority["enforcer_output_is_executor_dispatch_permission"],
            False,
        )

    def test_output_is_bounded_json_safe(self):
        result = validate_runtime_enforcer_implementation_boundary(
            valid_payload()
        )
        manifest = runtime_enforcer_implementation_boundary_validator_manifest()

        json.dumps(result, sort_keys=True)
        self.assertEqual(
            set(result["boundary"]["source_refs"]),
            set(manifest["expected_source_refs"]),
        )
        self.assertEqual(
            set(result["boundary"]["false_authority_flags"]),
            set(manifest["required_false_authority_flags"]),
        )
        self.assertLess(len(json.dumps(result, sort_keys=True)), 50000)


class PayloadValidationTests(unittest.TestCase):
    def assert_failure(self, payload, failure):
        result = validate_runtime_enforcer_implementation_boundary(payload)
        self.assertIs(
            result["runtime_enforcer_implementation_boundary_ready"],
            False,
        )
        self.assertIn(failure, result["failures"])
        return result

    def test_payload_not_mapping_fails_with_invalid_payload_reason(self):
        result = self.assert_failure([], "payload_not_mapping")
        self.assertEqual(
            result["reason_code"],
            "invalid_runtime_enforcer_implementation_boundary_payload",
        )

    def test_payload_shape_mismatch_fails(self):
        result = self.assert_failure(
            {"wrong": valid_boundary()},
            "payload_shape_mismatch",
        )
        self.assertIn("boundary_not_mapping", result["failures"])
        self.assertEqual(result["reason_code"], "not_ready")

    def test_boundary_not_mapping_fails(self):
        result = self.assert_failure(
            {"runtime_enforcer_implementation_boundary": []},
            "boundary_not_mapping",
        )
        self.assertEqual(result["reason_code"], "not_ready")

    def test_boundary_shape_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["extra"] = True
        self.assert_failure(payload, "boundary_shape_mismatch")

    def test_surface_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["surface"] = "Wrong"
        self.assert_failure(payload, "boundary_surface_invalid")

    def test_version_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["version"] = 2
        self.assert_failure(payload, "boundary_version_invalid")

    def test_bool_as_int_version_rejected(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["version"] = True
        self.assert_failure(payload, "boundary_version_invalid")

    def test_source_ref_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["source_refs"][
            "runtime-enforcer-implementation-boundary-spec-only-v1"
        ] = "bad"
        self.assert_failure(payload, "source_ref_mismatch")

    def test_invalid_caller_source_refs_not_echoed_in_output(self):
        class Secret:
            def __repr__(self):
                return "SECRET_SOURCE_REF"

        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["source_refs"] = {
            "attacker": Secret()
        }
        result = self.assert_failure(payload, "source_ref_mismatch")

        rendered = repr(result)
        self.assertNotIn("SECRET_SOURCE_REF", rendered)
        self.assertNotIn("attacker", result["boundary"]["source_refs"])
        self.assertEqual(
            result["boundary"]["source_refs"],
            runtime_enforcer_implementation_boundary_validator_manifest()[
                "expected_source_refs"
            ],
        )

    def test_enforcer_boundary_model_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "runtime_enforcer_implementation_boundary_model"
        ]["runtime_enforcer_runtime_boundary"] = 1
        self.assert_failure(payload, "enforcer_boundary_model_invalid")

    def test_checker_enforcer_separation_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "checker_enforcer_separation_model"
        ]["checker_output_is_not_enforcer_authority"] = False
        self.assert_failure(payload, "checker_enforcer_separation_invalid")

    def test_forbidden_implicit_authority_source_mismatch_fails(self):
        payload = valid_payload()
        del payload["runtime_enforcer_implementation_boundary"][
            "forbidden_implicit_authority_sources"
        ]["enforcer_output"]
        self.assert_failure(payload, "forbidden_implicit_authority_invalid")

    def test_missing_false_flag_fails(self):
        payload = valid_payload()
        del payload["runtime_enforcer_implementation_boundary"][
            "false_authority_flags"
        ]["runtime_enforcer_runtime_authorized"]
        self.assert_failure(payload, "authorization_flag_invalid")

    def test_false_flag_set_true_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "false_authority_flags"
        ]["service_call_execution_authorized"] = True
        result = self.assert_failure(payload, "authorization_flag_true")
        self.assertIn("authorization_flag_true", result["failures"])

    def test_missing_true_declaration_fails(self):
        payload = valid_payload()
        del payload["runtime_enforcer_implementation_boundary"][
            "true_declarations"
        ]["runtime_enforcer_implementation_forbidden"]
        self.assert_failure(payload, "required_declaration_invalid")

    def test_true_declaration_set_false_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "true_declarations"
        ]["runtime_enforcer_implementation_forbidden"] = False
        self.assert_failure(payload, "required_declaration_false")

    def test_json_safety_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["json_safety"][
            "runtime_object_handles"
        ] = False
        self.assert_failure(payload, "json_safety_invalid")

    def test_future_validator_requirement_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "future_validator_requirements"
        ]["remain_read_only"] = False
        self.assert_failure(payload, "future_validator_requirement_invalid")

    def test_future_ci_requirement_mismatch_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "future_ci_requirements"
        ]["remain_read_only"] = False
        self.assert_failure(payload, "future_ci_requirement_invalid")

    def test_json_safe_false_fails(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"]["json_safe"] = False
        self.assert_failure(payload, "json_safe_invalid")

    def test_bool_as_int_rejected_for_boolean_fields(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "false_authority_flags"
        ]["runtime_enforcer_runtime_authorized"] = 0
        self.assert_failure(payload, "authorization_flag_invalid")

        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "true_declarations"
        ]["runtime_enforcer_implementation_forbidden"] = 1
        self.assert_failure(payload, "required_declaration_invalid")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        boundary = payload["runtime_enforcer_implementation_boundary"]
        boundary["surface"] = "Wrong"
        boundary["version"] = True
        boundary["source_refs"] = {}
        boundary["runtime_enforcer_implementation_boundary_model"] = {}
        boundary["checker_enforcer_separation_model"] = {}
        boundary["forbidden_implicit_authority_sources"] = {}
        boundary["false_authority_flags"] = {}
        boundary["true_declarations"] = {}
        boundary["json_safety"] = {}
        boundary["future_validator_requirements"] = {}
        boundary["future_ci_requirements"] = {}
        boundary["json_safe"] = False

        result = validate_runtime_enforcer_implementation_boundary(payload)

        self.assertEqual(
            result["failures"],
            [
                "boundary_surface_invalid",
                "boundary_version_invalid",
                "source_ref_mismatch",
                "enforcer_boundary_model_invalid",
                "checker_enforcer_separation_invalid",
                "forbidden_implicit_authority_invalid",
                "authorization_flag_invalid",
                "required_declaration_invalid",
                "json_safety_invalid",
                "future_validator_requirement_invalid",
                "future_ci_requirement_invalid",
                "json_safe_invalid",
            ],
        )


class SafetyTests(unittest.TestCase):
    def test_input_is_not_mutated(self):
        payload = valid_payload()
        before = copy.deepcopy(payload)

        validate_runtime_enforcer_implementation_boundary(payload)

        self.assertEqual(payload, before)

    def test_no_raw_object_leakage_in_output(self):
        class Secret:
            def __repr__(self):
                return "SECRET_RUNTIME_HANDLE"

        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary"][
            "runtime_enforcer_implementation_boundary_model"
        ]["runtime_enforcer_runtime_boundary"] = Secret()

        result = validate_runtime_enforcer_implementation_boundary(payload)

        self.assertIn("enforcer_boundary_model_invalid", result["failures"])
        self.assertNotIn("SECRET_RUNTIME_HANDLE", repr(result))
        json.dumps(result, sort_keys=True)

    def test_validator_ready_authorizes_nothing(self):
        result = validate_runtime_enforcer_implementation_boundary(
            valid_payload()
        )

        self.assertIs(
            result["runtime_enforcer_implementation_boundary_ready"],
            True,
        )
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertTrue(
            all(
                value is False
                for value in result["non_authority"][
                    "runtime_enforcer_implementation_boundary_ready_authorizes"
                ].values()
            )
        )

    def test_no_forbidden_imports_in_production_module(self):
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

    def test_no_service_db_append_runtime_executor_markers(self):
        text = source_text()
        for marker in (
            "KernelUnitOfWork",
            "Repository",
            "EvidenceService",
            "ApprovalService",
            "ReviewService",
            "RevisionSealService",
            "audit.append(",
            "evidence.append(",
            "_audit.append(",
            "_repo.append(",
            "_journal_repo.append(",
            ".execute(",
            ".commit(",
            ".rollback(",
            "open_connection",
            "restore_task_from_snapshot",
            "executor.dispatch",
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

    def test_validator_does_not_call_upstream_validators_checkers_or_ci(self):
        text = source_text()
        for marker in (
            "validate_runtime_checker",
            "validate_runtime_implementation",
            "validate_runtime_final_eligibility",
            "validate_service_call_admission",
            "validate_runtime_authority_grant",
            "validate_runtime_authority_checker_enforcer",
            "_validator_ci",
        ):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
