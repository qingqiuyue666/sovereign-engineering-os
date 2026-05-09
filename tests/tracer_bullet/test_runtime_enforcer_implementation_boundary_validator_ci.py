import ast
import copy
import inspect
import json
import unittest
from pathlib import Path

from kernel.lifecycle import (
    runtime_enforcer_implementation_boundary_validator_ci as module,
)
from kernel.lifecycle.runtime_enforcer_implementation_boundary_validator_ci import (
    consume_runtime_enforcer_implementation_boundary_validator_ci,
    runtime_enforcer_implementation_boundary_validator_ci_manifest,
)


MODULE_PATH = Path(module.__file__)


def manifest():
    return runtime_enforcer_implementation_boundary_validator_ci_manifest()


def valid_payload():
    details = manifest()
    return {
        "runtime_enforcer_implementation_boundary_ready": True,
        "reason_code": "ready",
        "failures": [],
        "boundary": copy.deepcopy(details["expected_boundary"]),
        "authority": copy.deepcopy(details["authority_summary"]),
        "non_authority": copy.deepcopy(
            details["expected_validator_non_authority_summary"]
        ),
        "json_safe": True,
        "validator_checkpoint_tag": (
            "runtime-enforcer-implementation-boundary-validator-v1"
        ),
        "validator_checkpoint_commit": (
            "84db914b906b6fb863407c0cc75350b6246f339a"
        ),
    }


def valid_not_ready_payload(*failures):
    payload = valid_payload()
    payload["runtime_enforcer_implementation_boundary_ready"] = False
    payload["reason_code"] = "not_ready"
    payload["failures"] = list(failures or ("source_ref_mismatch",))
    return payload


def source_text():
    return MODULE_PATH.read_text(encoding="utf-8")


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_defensive_copy(self):
        first = manifest()
        first["expected_boundary"]["source_refs"]["mutated"] = "bad"
        first["authority_summary"][
            "runtime_enforcer_runtime_authorized"
        ] = True

        fresh = manifest()

        self.assertNotIn("mutated", fresh["expected_boundary"]["source_refs"])
        self.assertIs(
            fresh["authority_summary"][
                "runtime_enforcer_runtime_authorized"
            ],
            False,
        )

    def test_manifest_is_json_safe(self):
        details = manifest()
        json.dumps(details, sort_keys=True)
        self.assertIs(details["json_safe"], True)

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            module.__all__,
            [
                "runtime_enforcer_implementation_boundary_validator_ci_manifest",
                "consume_runtime_enforcer_implementation_boundary_validator_ci",
            ],
        )
        details = manifest()
        self.assertEqual(details["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    consume_runtime_enforcer_implementation_boundary_validator_ci
                ).parameters
            ),
            ["payload"],
        )
        self.assertEqual(
            details["ci_failure_taxonomy"],
            [
                "ci_payload_not_mapping",
                "ci_payload_shape_mismatch",
                "validator_checkpoint_invalid",
                "readiness_invalid",
                "reason_code_invalid",
                "failure_list_invalid",
                "unknown_validator_failure",
                "boundary_summary_invalid",
                "authority_summary_invalid",
                "non_authority_summary_invalid",
                "json_safe_invalid",
            ],
        )
        self.assertEqual(
            details["validator_failure_taxonomy"],
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
            manifest()["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )


class HappyPathTests(unittest.TestCase):
    def test_valid_ready_validator_output_returns_ci_ok_true(self):
        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            valid_payload()
        )

        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["validator_checkpoint"],
            manifest()["expected_validator_checkpoint"],
        )
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

    def test_valid_not_ready_output_preserves_validator_failures(self):
        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            valid_not_ready_payload(
                "source_ref_mismatch",
                "authorization_flag_true",
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"],
            ["source_ref_mismatch", "authorization_flag_true"],
        )

    def test_ci_ok_authorizes_nothing(self):
        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            valid_payload()
        )

        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertTrue(
            all(
                value is False
                for value in result["non_authority"][
                    "ci_ok_authorizes"
                ].values()
            )
        )
        for key in (
            "ci_success_is_runtime_authority",
            "ci_success_is_enforcer_runtime_authority",
            "ci_success_is_enforcer_implementation_authority",
            "ci_success_is_service_call_authority",
            "ci_success_is_db_write_authority",
            "ci_success_is_append_authority",
            "ci_success_is_executor_authority",
            "ci_success_is_durable_write_authority",
            "ci_success_is_irreversible_action_authority",
        ):
            self.assertIs(result["non_authority"][key], False)

    def test_output_is_bounded_json_safe(self):
        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            valid_payload()
        )

        json.dumps(result, sort_keys=True)
        self.assertLess(len(json.dumps(result, sort_keys=True)), 60000)
        self.assertEqual(
            result["boundary"],
            manifest()["expected_boundary"],
        )


class PayloadValidationTests(unittest.TestCase):
    def assert_ci_failure(self, payload, failure):
        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            payload
        )
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn(failure, result["failures"])
        return result

    def test_payload_not_mapping_fails(self):
        result = self.assert_ci_failure([], "ci_payload_not_mapping")
        self.assertEqual(result["failures"], ["ci_payload_not_mapping"])

    def test_payload_shape_mismatch_fails(self):
        payload = valid_payload()
        payload["extra"] = True
        self.assert_ci_failure(payload, "ci_payload_shape_mismatch")

    def test_checkpoint_tag_mismatch_fails(self):
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        self.assert_ci_failure(payload, "validator_checkpoint_invalid")

    def test_checkpoint_commit_mismatch_fails(self):
        payload = valid_payload()
        payload["validator_checkpoint_commit"] = "wrong"
        self.assert_ci_failure(payload, "validator_checkpoint_invalid")

    def test_readiness_bool_as_int_rejected(self):
        payload = valid_payload()
        payload["runtime_enforcer_implementation_boundary_ready"] = 1
        self.assert_ci_failure(payload, "readiness_invalid")

    def test_readiness_reason_failures_inconsistency_fails(self):
        payload = valid_payload()
        payload["reason_code"] = "not_ready"
        self.assert_ci_failure(payload, "reason_code_invalid")

        payload = valid_payload()
        payload["failures"] = ["source_ref_mismatch"]
        self.assert_ci_failure(payload, "readiness_invalid")

        payload = valid_not_ready_payload()
        payload["failures"] = []
        self.assert_ci_failure(payload, "readiness_invalid")

    def test_unknown_validator_failure_fails(self):
        payload = valid_not_ready_payload("unknown")
        self.assert_ci_failure(payload, "unknown_validator_failure")

    def test_failure_list_invalid_fails(self):
        payload = valid_not_ready_payload()
        payload["failures"] = "source_ref_mismatch"
        self.assert_ci_failure(payload, "failure_list_invalid")

    def test_json_safe_false_fails(self):
        payload = valid_payload()
        payload["json_safe"] = False
        self.assert_ci_failure(payload, "json_safe_invalid")

    def test_boundary_surface_mismatch_fails(self):
        payload = valid_payload()
        payload["boundary"]["surface"] = "Wrong"
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_boundary_version_mismatch_fails(self):
        payload = valid_payload()
        payload["boundary"]["version"] = 2
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_bool_as_int_boundary_version_rejected(self):
        payload = valid_payload()
        payload["boundary"]["version"] = True
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_boundary_source_ref_mismatch_fails(self):
        payload = valid_payload()
        payload["boundary"]["source_refs"][
            "runtime-enforcer-implementation-boundary-spec-only-v1"
        ] = "bad"
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_invalid_caller_source_refs_not_echoed(self):
        class Secret:
            def __repr__(self):
                return "SECRET_SOURCE_REF"

        payload = valid_payload()
        payload["boundary"]["source_refs"] = {"attacker": Secret()}
        result = self.assert_ci_failure(payload, "boundary_summary_invalid")

        self.assertNotIn("SECRET_SOURCE_REF", repr(result))
        self.assertNotIn("attacker", result["boundary"]["source_refs"])
        self.assertEqual(
            result["boundary"]["source_refs"],
            manifest()["expected_boundary"]["source_refs"],
        )

    def test_enforcer_boundary_model_mismatch_fails(self):
        payload = valid_payload()
        payload["boundary"]["runtime_enforcer_implementation_boundary_model"][
            "runtime_enforcer_runtime_boundary"
        ] = False
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_checker_enforcer_separation_mismatch_fails(self):
        payload = valid_payload()
        payload["boundary"]["checker_enforcer_separation_model"][
            "checker_output_is_not_enforcer_authority"
        ] = False
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_forbidden_implicit_authority_source_mismatch_fails(self):
        payload = valid_payload()
        del payload["boundary"]["forbidden_implicit_authority_sources"][
            "enforcer_output"
        ]
        self.assert_ci_failure(payload, "boundary_summary_invalid")

    def test_authority_summary_missing_flag_fails(self):
        payload = valid_payload()
        del payload["authority"]["runtime_enforcer_runtime_authorized"]
        self.assert_ci_failure(payload, "authority_summary_invalid")

    def test_authority_summary_true_flag_fails(self):
        payload = valid_payload()
        payload["authority"]["service_call_execution_authorized"] = True
        self.assert_ci_failure(payload, "authority_summary_invalid")

    def test_non_authority_summary_missing_denial_fails(self):
        payload = valid_payload()
        del payload["non_authority"][
            "runtime_enforcer_implementation_boundary_ready_authorizes"
        ]["service_calls"]
        self.assert_ci_failure(payload, "non_authority_summary_invalid")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        payload["extra"] = True
        payload["validator_checkpoint_tag"] = "wrong"
        payload["runtime_enforcer_implementation_boundary_ready"] = 1
        payload["reason_code"] = "bad"
        payload["failures"] = ["unknown"]
        payload["boundary"] = {}
        payload["authority"] = {}
        payload["non_authority"] = {}
        payload["json_safe"] = False

        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            payload
        )

        self.assertEqual(
            result["failures"],
            [
                "ci_payload_shape_mismatch",
                "validator_checkpoint_invalid",
                "readiness_invalid",
                "reason_code_invalid",
                "unknown_validator_failure",
                "boundary_summary_invalid",
                "authority_summary_invalid",
                "non_authority_summary_invalid",
                "json_safe_invalid",
            ],
        )


class SafetyTests(unittest.TestCase):
    def test_input_is_not_mutated(self):
        payload = valid_payload()
        before = copy.deepcopy(payload)

        consume_runtime_enforcer_implementation_boundary_validator_ci(payload)

        self.assertEqual(payload, before)

    def test_raw_object_leakage_prevention(self):
        class Secret:
            def __repr__(self):
                return "SECRET_RUNTIME_HANDLE"

        payload = valid_payload()
        payload["boundary"][
            "runtime_enforcer_implementation_boundary_model"
        ]["runtime_enforcer_runtime_boundary"] = Secret()

        result = consume_runtime_enforcer_implementation_boundary_validator_ci(
            payload
        )

        self.assertIn("boundary_summary_invalid", result["failures"])
        self.assertIn("json_safe_invalid", result["failures"])
        self.assertNotIn("SECRET_RUNTIME_HANDLE", repr(result))
        json.dumps(result, sort_keys=True)

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
            "kernel.lifecycle.runtime_enforcer_implementation_boundary_validator",
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

    def test_ci_does_not_import_or_call_validator(self):
        text = source_text()
        for marker in (
            "from kernel.lifecycle.runtime_enforcer_implementation_boundary_validator",
            "import runtime_enforcer_implementation_boundary_validator",
            "validate_runtime_enforcer_implementation_boundary(",
        ):
            self.assertNotIn(marker, text)

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


if __name__ == "__main__":
    unittest.main()
