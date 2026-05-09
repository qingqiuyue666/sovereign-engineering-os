import ast
import copy
import inspect
import json
import unittest
from pathlib import Path

from kernel.lifecycle import (
    runtime_checker_implementation_boundary_validator_ci as module,
)
from kernel.lifecycle.runtime_checker_implementation_boundary_validator_ci import (
    consume_runtime_checker_implementation_boundary_validator_ci,
    runtime_checker_implementation_boundary_validator_ci_manifest,
)


MODULE_PATH = Path(module.__file__)


def manifest():
    return runtime_checker_implementation_boundary_validator_ci_manifest()


def valid_payload():
    data = manifest()
    return {
        "runtime_checker_implementation_boundary_ready": True,
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
    payload["runtime_checker_implementation_boundary_ready"] = False
    payload["reason_code"] = "not_ready"
    payload["failures"] = [failure]
    return payload


def source_text():
    return MODULE_PATH.read_text(encoding="utf-8")


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_is_defensive_copy(self):
        data = manifest()
        data["expected_boundary"]["source_refs"]["mutated"] = "bad"
        data["authority_summary"]["runtime_checker_runtime_authorized"] = True

        fresh = manifest()

        self.assertNotIn("mutated", fresh["expected_boundary"]["source_refs"])
        self.assertIs(
            fresh["authority_summary"]["runtime_checker_runtime_authorized"],
            False,
        )

    def test_manifest_is_json_safe(self):
        data = manifest()

        json.dumps(data, sort_keys=True)

        self.assertIs(data["json_safe"], True)

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            module.__all__,
            [
                "runtime_checker_implementation_boundary_validator_ci_manifest",
                "consume_runtime_checker_implementation_boundary_validator_ci",
            ],
        )
        self.assertEqual(manifest()["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    consume_runtime_checker_implementation_boundary_validator_ci
                ).parameters
            ),
            ["payload"],
        )

    def test_only_mapping_deepcopy_imports(self):
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

    def test_ci_does_not_call_validator_or_adjacent_validators_ci(self):
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
            "kernel.lifecycle.runtime_checker_implementation_boundary_validator",
            "kernel.lifecycle.runtime_implementation_boundary_validator_ci",
            "kernel.lifecycle.runtime_implementation_boundary_validator",
            "kernel.lifecycle.runtime_final_eligibility_gate_validator_ci",
            "kernel.lifecycle.service_call_admission_gate_validator_ci",
            "kernel.lifecycle.runtime_authority_grant_object_validator_ci",
            "kernel.lifecycle.runtime_authority_checker_enforcer_boundary_validator_ci",
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
        forbidden_calls = {
            "validate_runtime_checker_implementation_boundary",
            "runtime_checker_implementation_boundary_validator_manifest",
            "consume_runtime_implementation_boundary_validator_ci",
            "consume_runtime_final_eligibility_gate_validator_ci",
            "consume_service_call_admission_gate_validator_ci",
            "consume_runtime_authority_grant_object_validator_ci",
            "consume_runtime_authority_checker_enforcer_boundary_validator_ci",
        }
        self.assertTrue(forbidden_calls.isdisjoint(calls))


class HappyPathTests(unittest.TestCase):
    def test_ready_validator_output_returns_ci_ok_true(self):
        result = consume_runtime_checker_implementation_boundary_validator_ci(
            valid_payload()
        )

        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(set(result), set(manifest()["expected_output_keys"]))
        json.dumps(result, sort_keys=True)

    def test_valid_not_ready_validator_output_returns_ci_ok_false(self):
        result = consume_runtime_checker_implementation_boundary_validator_ci(
            not_ready_payload("source_ref_mismatch")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        json.dumps(result, sort_keys=True)

    def test_output_is_bounded_json_safe(self):
        result = consume_runtime_checker_implementation_boundary_validator_ci(
            valid_payload()
        )

        json.dumps(result, sort_keys=True)
        self.assertIs(result["json_safe"], True)
        self.assertLess(len(json.dumps(result, sort_keys=True)), 50000)

    def test_authority_summary_hard_false_enforced(self):
        result = consume_runtime_checker_implementation_boundary_validator_ci(
            valid_payload()
        )

        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        for flag in (
            "runtime_checker_implementation_authorized",
            "runtime_checker_runtime_authorized",
            "runtime_checker_decision_authorized",
            "runtime_enforcer_runtime_authorized",
            "service_call_execution_authorized",
            "repository_uow_writes_authorized",
            "durable_writes_authorized",
            "irreversible_action_authorized",
        ):
            self.assertIn(flag, result["authority"])

    def test_ci_ok_does_not_authorize_runtime_or_side_effects(self):
        result = consume_runtime_checker_implementation_boundary_validator_ci(
            valid_payload()
        )
        denies = result["non_authority"]["ci_ok_authorizes"]

        for denied in (
            "runtime",
            "runtime_eligibility",
            "checker_runtime",
            "checker_implementation",
            "checker_decision",
            "enforcer_runtime",
            "enforcer_implementation",
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
        self.assertIs(
            result["non_authority"]["ci_success_is_runtime_authority"],
            False,
        )
        self.assertIs(
            result["non_authority"][
                "ci_success_is_checker_runtime_authority"
            ],
            False,
        )
        self.assertIs(
            result["non_authority"]["ci_success_is_service_call_authority"],
            False,
        )


class PayloadValidationTests(unittest.TestCase):
    def assert_failure(self, payload, failure):
        result = consume_runtime_checker_implementation_boundary_validator_ci(
            payload
        )
        self.assertIs(result["ci_ok"], False)
        self.assertIn(failure, result["failures"])
        return result

    def test_payload_must_be_mapping(self):
        result = self.assert_failure([], "ci_payload_not_mapping")
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

    def test_payload_shape_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["extra"] = True

        self.assert_failure(payload, "ci_payload_shape_mismatch")

    def test_checkpoint_tag_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"

        self.assert_failure(payload, "validator_checkpoint_invalid")

    def test_checkpoint_commit_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["validator_checkpoint_commit"] = "0" * 40

        self.assert_failure(payload, "validator_checkpoint_invalid")

    def test_readiness_must_be_bool_only(self):
        payload = valid_payload()
        payload["runtime_checker_implementation_boundary_ready"] = "true"

        self.assert_failure(payload, "readiness_invalid")

    def test_bool_as_int_readiness_rejected(self):
        payload = valid_payload()
        payload["runtime_checker_implementation_boundary_ready"] = 1

        self.assert_failure(payload, "readiness_invalid")

    def test_ready_with_non_ready_reason_fails_closed(self):
        payload = valid_payload()
        payload["reason_code"] = "not_ready"

        self.assert_failure(payload, "reason_code_invalid")

    def test_ready_with_failures_fails_closed(self):
        payload = valid_payload()
        payload["failures"] = ["source_ref_mismatch"]

        self.assert_failure(payload, "readiness_invalid")

    def test_not_ready_with_ready_reason_fails_closed(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["reason_code"] = "ready"

        self.assert_failure(payload, "reason_code_invalid")

    def test_not_ready_with_empty_failures_fails_closed(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["failures"] = []

        self.assert_failure(payload, "readiness_invalid")

    def test_unknown_validator_failure_fails_closed(self):
        payload = not_ready_payload("unknown")

        result = self.assert_failure(payload, "unknown_validator_failure")
        self.assertNotIn("unknown", result["failures"])

    def test_failure_list_must_be_list(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["failures"] = "source_ref_mismatch"

        self.assert_failure(payload, "failure_list_invalid")

    def test_failure_list_must_be_bounded_strings(self):
        class Secret:
            def __repr__(self):
                return "SECRET_FAILURE"

        payload = not_ready_payload("source_ref_mismatch")
        payload["failures"] = [Secret()]

        result = self.assert_failure(payload, "failure_list_invalid")
        self.assertNotIn("SECRET_FAILURE", repr(result))

    def test_json_safe_false_fails_closed(self):
        payload = valid_payload()
        payload["json_safe"] = False

        self.assert_failure(payload, "json_safe_invalid")

    def test_boundary_summary_must_be_mapping(self):
        payload = valid_payload()
        payload["boundary"] = []

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_boundary_surface_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["surface"] = "Wrong"

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_boundary_version_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["version"] = 2

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_bool_as_int_boundary_version_rejected(self):
        payload = valid_payload()
        payload["boundary"]["version"] = True

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_boundary_source_refs_mismatch_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["source_refs"][
            "runtime-checker-implementation-boundary-spec-only-v1"
        ] = "bad"

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_checker_boundary_model_invalid_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["runtime_checker_implementation_boundary_model"][
            "checker_runtime_forbidden"
        ] = False

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_checker_enforcer_separation_invalid_fails_closed(self):
        payload = valid_payload()
        payload["boundary"]["checker_enforcer_separation_model"][
            "checker_must_not_execute_service_calls"
        ] = False

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_forbidden_implicit_authority_invalid_fails_closed(self):
        payload = valid_payload()
        del payload["boundary"]["forbidden_implicit_authority_sources"][
            "future_ci_success"
        ]

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_authority_flag_true_fails_closed(self):
        payload = valid_payload()
        payload["authority"]["runtime_checker_runtime_authorized"] = True

        self.assert_failure(payload, "authority_summary_invalid")

    def test_authority_summary_missing_key_fails_closed(self):
        payload = valid_payload()
        del payload["authority"]["service_call_execution_authorized"]

        self.assert_failure(payload, "authority_summary_invalid")

    def test_non_authority_summary_invalid_fails_closed(self):
        payload = valid_payload()
        payload["non_authority"][
            "runtime_checker_implementation_boundary_ready_authorizes"
        ]["service_calls"] = True

        self.assert_failure(payload, "non_authority_summary_invalid")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        payload["runtime_checker_implementation_boundary_ready"] = 1
        payload["reason_code"] = "wrong"
        payload["failures"] = ["unknown"]
        payload["boundary"] = {}
        payload["authority"] = {}
        payload["non_authority"] = {}
        payload["json_safe"] = False

        result = consume_runtime_checker_implementation_boundary_validator_ci(
            payload
        )

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

    def test_invalid_caller_malformed_boundary_is_not_echoed(self):
        class Secret:
            def __repr__(self):
                return "SECRET_BOUNDARY"

        payload = valid_payload()
        payload["boundary"] = {"attacker": Secret()}

        result = self.assert_failure(payload, "boundary_summary_invalid")

        rendered = repr(result)
        self.assertNotIn("SECRET_BOUNDARY", rendered)
        self.assertNotIn("attacker", result["boundary"])
        self.assertEqual(result["boundary"], manifest()["expected_boundary"])

    def test_input_is_not_mutated(self):
        payload = valid_payload()
        before = copy.deepcopy(payload)

        consume_runtime_checker_implementation_boundary_validator_ci(payload)

        self.assertEqual(payload, before)


class SourceBoundaryTests(unittest.TestCase):
    def test_no_validator_service_repository_uow_db_runtime_executor_imports(self):
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
            "kernel.lifecycle.runtime_checker_implementation_boundary_validator",
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

        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        } | {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        forbidden_calls = {
            "validate_runtime_checker_implementation_boundary",
            "runtime_checker_implementation_boundary_validator_manifest",
            "execute",
            "commit",
            "rollback",
            "dispatch",
            "open_connection",
            "restore_task_from_snapshot",
        }
        self.assertTrue(forbidden_calls.isdisjoint(calls))

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
            "subprocess",
            "os",
            "pathlib",
            "socket",
            "urllib",
            "requests",
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
        forbidden_calls = {
            "now",
            "utcnow",
            "sha256",
            "run",
            "check_output",
            "Popen",
            "open",
            "Path",
            "request",
            "urlopen",
        }
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
