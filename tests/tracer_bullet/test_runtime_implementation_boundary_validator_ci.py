import ast
import copy
import inspect
import json
import unittest
from pathlib import Path

from kernel.lifecycle import (
    runtime_implementation_boundary_validator_ci as module,
)
from kernel.lifecycle.runtime_implementation_boundary_validator_ci import (
    consume_runtime_implementation_boundary_validator_ci,
    runtime_implementation_boundary_validator_ci_manifest,
)


MODULE_PATH = Path(module.__file__)


def manifest():
    return runtime_implementation_boundary_validator_ci_manifest()


def valid_payload():
    data = manifest()
    return {
        "runtime_implementation_boundary_ready": True,
        "reason_code": "ready",
        "failures": [],
        "boundary": copy.deepcopy(data["expected_boundary"]),
        "authority": copy.deepcopy(data["authority_summary"]),
        "non_authority": copy.deepcopy(
            data["expected_validator_non_authority_summary"]
        ),
        "json_safe": True,
        "validator_checkpoint_tag": data["validator_checkpoint_tag"],
        "validator_checkpoint_commit": data["validator_checkpoint_commit"],
    }


def not_ready_payload(failure="source_ref_mismatch"):
    payload = valid_payload()
    payload["runtime_implementation_boundary_ready"] = False
    payload["reason_code"] = "not_ready"
    payload["failures"] = [failure]
    return payload


def source_text():
    return MODULE_PATH.read_text(encoding="utf-8")


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_json_safe_and_defensive_copy(self):
        data = manifest()
        json.dumps(data, sort_keys=True)
        self.assertIs(data["json_safe"], True)

        data["expected_boundary"]["source_refs"]["mutated"] = "bad"
        fresh = manifest()
        self.assertNotIn("mutated", fresh["expected_boundary"]["source_refs"])

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            module.__all__,
            [
                "runtime_implementation_boundary_validator_ci_manifest",
                "consume_runtime_implementation_boundary_validator_ci",
            ],
        )
        data = manifest()
        self.assertEqual(data["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    consume_runtime_implementation_boundary_validator_ci
                ).parameters
            ),
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
            manifest()["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )

    def test_ci_does_not_import_or_call_validator(self):
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
        self.assertNotIn(
            "kernel.lifecycle.runtime_implementation_boundary_validator",
            imported_modules,
        )

        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        } | {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("validate_runtime_implementation_boundary", calls)
        self.assertNotIn("runtime_implementation_boundary_validator_manifest", calls)


class HappyPathTests(unittest.TestCase):
    def test_valid_ready_validator_output_returns_ci_ok_true(self):
        result = consume_runtime_implementation_boundary_validator_ci(
            valid_payload()
        )

        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(set(result), set(manifest()["expected_output_keys"]))
        json.dumps(result, sort_keys=True)

    def test_valid_not_ready_validator_output_returns_ci_ok_false(self):
        result = consume_runtime_implementation_boundary_validator_ci(
            not_ready_payload("source_ref_mismatch")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        json.dumps(result, sort_keys=True)

    def test_output_authority_hard_false(self):
        result = consume_runtime_implementation_boundary_validator_ci(
            valid_payload()
        )
        authority = result["authority"]

        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))
        self.assertIn("runtime_implementation_authorized", authority)
        self.assertIn("service_call_execution_authorized", authority)
        self.assertIn("repository_uow_writes_authorized", authority)
        self.assertIn("irreversible_action_authorized", authority)

    def test_ci_ok_non_authorizing(self):
        result = consume_runtime_implementation_boundary_validator_ci(
            valid_payload()
        )
        non_authority = result["non_authority"]

        self.assertEqual(
            non_authority["ci_ok_proves"],
            (
                "already_rendered_runtime_implementation_boundary_validator_"
                "output_structurally_valid_for_read_only_consolidation_only"
            ),
        )
        denies = non_authority["ci_ok_authorizes"]
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
        self.assertIs(non_authority["ci_success_is_runtime_authority"], False)


class PayloadValidationTests(unittest.TestCase):
    def assert_failure(self, payload, failure):
        result = consume_runtime_implementation_boundary_validator_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn(failure, result["failures"])
        return result

    def test_non_mapping_ci_payload_fails_closed(self):
        result = self.assert_failure([], "ci_payload_not_mapping")
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_wrong_ci_top_level_key_set_fails_closed(self):
        payload = valid_payload()
        payload["extra"] = True
        self.assert_failure(payload, "ci_payload_shape_mismatch")

    def test_wrong_validator_checkpoint_tag_fails_closed(self):
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        self.assert_failure(payload, "validator_checkpoint_invalid")

    def test_wrong_validator_checkpoint_commit_fails_closed(self):
        payload = valid_payload()
        payload["validator_checkpoint_commit"] = "bad"
        self.assert_failure(payload, "validator_checkpoint_invalid")

    def test_readiness_bool_as_int_rejected(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary_ready"] = 1
        self.assert_failure(payload, "readiness_invalid")

    def test_ready_with_non_empty_failures_fails_closed(self):
        payload = valid_payload()
        payload["failures"] = ["source_ref_mismatch"]
        self.assert_failure(payload, "readiness_invalid")

    def test_not_ready_with_empty_failures_fails_closed(self):
        payload = valid_payload()
        payload["runtime_implementation_boundary_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = []
        self.assert_failure(payload, "readiness_invalid")

    def test_unknown_validator_failure_fails_closed(self):
        payload = not_ready_payload("not_in_taxonomy")
        self.assert_failure(payload, "unknown_validator_failure")

    def test_invalid_boundary_summary_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["extra"] = True
        self.assert_failure(payload, "boundary_summary_invalid")

    def test_wrong_boundary_surface_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["surface"] = "Wrong"
        self.assert_failure(payload, "boundary_summary_invalid")

    def test_wrong_boundary_version_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["version"] = 2
        self.assert_failure(payload, "boundary_summary_invalid")

    def test_bool_as_int_boundary_version_rejected(self):
        payload = valid_payload()
        payload["boundary"]["version"] = True
        self.assert_failure(payload, "boundary_summary_invalid")

    def test_invalid_source_refs_fail_closed(self):
        payload = valid_payload()
        payload["boundary"]["source_refs"][
            "runtime-implementation-boundary-spec-only-v1"
        ] = "bad"
        self.assert_failure(payload, "boundary_summary_invalid")

    def test_invalid_runtime_boundary_items_fail_closed(self):
        payload = valid_payload()
        del payload["boundary"]["required_runtime_boundaries"][
            "runtime_checker_implementation_boundary"
        ]
        self.assert_failure(payload, "boundary_summary_invalid")

    def test_invalid_authority_summary_fails_closed(self):
        payload = valid_payload()
        del payload["authority"]["runtime_implementation_authorized"]
        self.assert_failure(payload, "authority_summary_invalid")

    def test_authority_flag_true_fails_closed(self):
        payload = valid_payload()
        payload["authority"]["service_call_execution_authorized"] = True
        self.assert_failure(payload, "authority_summary_invalid")

    def test_invalid_non_authority_summary_fails_closed(self):
        payload = valid_payload()
        payload["non_authority"]["validator_success_is_authority"] = True
        self.assert_failure(payload, "non_authority_summary_invalid")

    def test_json_safe_false_fails_closed(self):
        payload = valid_payload()
        payload["json_safe"] = False
        self.assert_failure(payload, "json_safe_invalid")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        payload["reason_code"] = "not_ready"
        payload["failures"] = ["not_in_taxonomy", "source_ref_mismatch"]
        payload["boundary"]["surface"] = "Wrong"
        payload["authority"]["service_call_execution_authorized"] = True
        payload["non_authority"]["validator_success_is_authority"] = True
        payload["json_safe"] = False

        result = consume_runtime_implementation_boundary_validator_ci(payload)

        self.assertEqual(
            result["failures"],
            [
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
    def test_input_immutability(self):
        payload = valid_payload()
        before = copy.deepcopy(payload)

        consume_runtime_implementation_boundary_validator_ci(payload)

        self.assertEqual(payload, before)

    def test_raw_object_leakage_prevented(self):
        class Secret:
            def __repr__(self):
                return "SECRET_CI_OBJECT"

        payload = valid_payload()
        payload["boundary"]["source_refs"] = {"attacker": Secret()}
        result = consume_runtime_implementation_boundary_validator_ci(payload)

        self.assertIn("boundary_summary_invalid", result["failures"])
        self.assertNotIn("SECRET_CI_OBJECT", repr(result))
        self.assertNotIn("attacker", result["boundary"]["source_refs"])
        json.dumps(result, sort_keys=True)

    def test_output_does_not_echo_malformed_mappings(self):
        payload = valid_payload()
        payload["boundary"] = {"attacker": "controlled"}
        result = consume_runtime_implementation_boundary_validator_ci(payload)

        self.assertIn("boundary_summary_invalid", result["failures"])
        self.assertNotIn("attacker", result["boundary"])
        self.assertEqual(result["boundary"], manifest()["expected_boundary"])

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
            "kernel.lifecycle.runtime_implementation_boundary_validator",
            "kernel.lifecycle.runtime_final_eligibility_gate_validator_ci",
            "kernel.lifecycle.service_call_admission_gate_validator_ci",
            "kernel.lifecycle.recovery_gate",
            "kernel.lifecycle.recovery_cli",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_modules))

        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        } | {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        for forbidden_call in (
            "execute",
            "commit",
            "rollback",
            "connect",
            "open",
            "run",
            "Popen",
            "validate_runtime_implementation_boundary",
            "consume_runtime_final_eligibility_gate_validator_ci",
            "restore_task_from_snapshot",
        ):
            self.assertNotIn(forbidden_call, calls)

    def test_no_time_digest_subprocess_filesystem_network_git_imports(self):
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
            "hmac",
            "secrets",
            "inspect",
            "importlib",
            "os",
            "pathlib",
            "sqlite3",
            "subprocess",
            "threading",
            "asyncio",
            "socket",
            "urllib",
            "requests",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_modules))


if __name__ == "__main__":
    unittest.main()
