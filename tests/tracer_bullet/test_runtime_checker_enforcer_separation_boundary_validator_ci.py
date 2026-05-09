import ast
import copy
import inspect
import json
import unittest
from pathlib import Path

from kernel.lifecycle import (
    runtime_checker_enforcer_separation_boundary_validator_ci as module,
)
from kernel.lifecycle.runtime_checker_enforcer_separation_boundary_validator_ci import (
    consume_runtime_checker_enforcer_separation_boundary_validator_ci,
    runtime_checker_enforcer_separation_boundary_validator_ci_manifest,
)


MODULE_PATH = Path(module.__file__)
READY_KEY = "runtime_checker_enforcer_separation_boundary_ready"


class LeakyValue:
    def __repr__(self):
        return "LEAKY_RUNTIME_OBJECT"


def manifest():
    return runtime_checker_enforcer_separation_boundary_validator_ci_manifest()


def valid_payload():
    data = manifest()
    return {
        READY_KEY: True,
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
    payload[READY_KEY] = False
    payload["reason_code"] = "not_ready"
    payload["failures"] = [failure]
    return payload


def invalid_validator_payload(failure="payload_not_mapping"):
    payload = not_ready_payload(failure)
    payload["reason_code"] = (
        "invalid_runtime_checker_enforcer_separation_boundary_payload"
    )
    return payload


def source_text():
    return MODULE_PATH.read_text(encoding="utf-8")


def assert_no_leak(testcase, result):
    rendered = json.dumps(result, sort_keys=True)
    testcase.assertNotIn("LEAKY_RUNTIME_OBJECT", rendered)
    testcase.assertNotIn("LEAKY_RUNTIME_OBJECT", repr(result))


class ManifestAndApiTests(unittest.TestCase):
    def test_manifest_defensive_copy(self):
        data = manifest()
        data["expected_boundary"]["source_refs"]["mutated"] = "bad"
        data["authority_summary"][
            "runtime_checker_runtime_authorized"
        ] = True
        data["non_authority_summary"]["ci_ok_authorizes"][
            "service_calls"
        ] = True

        fresh = manifest()

        self.assertNotIn("mutated", fresh["expected_boundary"]["source_refs"])
        self.assertIs(
            fresh["authority_summary"][
                "runtime_checker_runtime_authorized"
            ],
            False,
        )
        self.assertIs(
            fresh["non_authority_summary"]["ci_ok_authorizes"][
                "service_calls"
            ],
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
                (
                    "runtime_checker_enforcer_separation_boundary_"
                    "validator_ci_manifest"
                ),
                (
                    "consume_runtime_checker_enforcer_separation_boundary_"
                    "validator_ci"
                ),
            ),
        )
        self.assertEqual(manifest()["public_api"], list(module.__all__))
        self.assertEqual(
            list(
                inspect.signature(
                    runtime_checker_enforcer_separation_boundary_validator_ci_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    consume_runtime_checker_enforcer_separation_boundary_validator_ci
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

    def test_no_validator_import_or_call(self):
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

        self.assertEqual(imported_modules, {"collections.abc", "copy"})
        self.assertFalse(
            any(
                "runtime_checker_enforcer_separation_boundary_validator"
                in imported
                and not imported.endswith("_ci")
                for imported in imported_modules
            )
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
        self.assertFalse(
            any(
                name.startswith("validate_")
                or name.startswith("consume_runtime_")
                for name in calls
            )
        )


class HappyPathTests(unittest.TestCase):
    def test_valid_ready_validator_output_returns_ci_ok_true(self):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            valid_payload()
        )

        self.assertEqual(set(result), set(manifest()["expected_output_keys"]))
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["validator_checkpoint"],
            manifest()["expected_validator_checkpoint"],
        )
        json.dumps(result, sort_keys=True)

    def test_valid_not_ready_validator_output_returns_ci_ok_false(self):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            not_ready_payload("source_ref_mismatch")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        json.dumps(result, sort_keys=True)

    def test_valid_invalid_validator_payload_returns_not_ready(self):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            invalid_validator_payload("payload_not_mapping")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_output_is_bounded_json_safe(self):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            valid_payload()
        )
        encoded = json.dumps(result, sort_keys=True)

        self.assertIs(result["json_safe"], True)
        self.assertLess(len(encoded), 60000)

    def test_authority_summary_hard_false(self):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            valid_payload()
        )

        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        for flag in (
            "runtime_checker_enforcer_separation_authorized",
            "runtime_checker_runtime_authorized",
            "runtime_checker_implementation_authorized",
            "runtime_checker_decision_authorized",
            "runtime_enforcer_runtime_authorized",
            "runtime_enforcer_implementation_authorized",
            "runtime_enforcer_decision_authorized",
            "runtime_enforcer_action_authorized",
            "runtime_checker_to_enforcer_handoff_authorized",
            "runtime_authority_grant_usage_authorized",
            "authority_ref_runtime_usage_authorized",
            "service_call_admission_runtime_authorized",
            "admission_decision_runtime_authorized",
            "service_call_execution_authorized",
            "service_method_call_authorized",
            "service_side_effect_authorized",
            "evidence_service_authorized",
            "approval_service_authorized",
            "review_service_authorized",
            "revision_seal_service_authorized",
            "audit_service_authorized",
            "evidence_append_authorized",
            "audit_append_authorized",
            "repository_uow_writes_authorized",
            "direct_db_writes_authorized",
            "raw_sqlite_authorized",
            "ad_hoc_sql_authorized",
            "transaction_runtime_authorized",
            "idempotency_reservation_authorized",
            "rollback_runtime_authorized",
            "executor_service_dispatch_authorized",
            "restore_execution_authorized",
            "cli_execution_authorized",
            "schema_migration_authorized",
            "daemon_server_queue_authorized",
            "filesystem_side_effects_authorized",
            "external_network_authorized",
            "durable_writes_authorized",
            "irreversible_action_authorized",
            "db_repair_authorized",
        ):
            self.assertIn(flag, result["authority"])

    def test_ci_ok_authorizes_nothing(self):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            valid_payload()
        )
        non_authority = result["non_authority"]
        denies = non_authority["ci_ok_authorizes"]

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
            "service_method_call",
            "service_side_effect",
            "evidence_approval_review_revision_audit_services",
            "evidence_audit_append",
            "db_repository_uow_writes",
            "direct_db_writes",
            "raw_sqlite",
            "ad_hoc_sql",
            "transaction",
            "idempotency_reservation",
            "rollback",
            "executor_dispatch",
            "restore",
            "cli_schema_daemon",
            "filesystem_network_effects",
            "durable_writes",
            "irreversible_actions",
            "db_repair",
            "toctou_physical_enforcement",
            "capability_token_work",
            "forensic_audit_binding",
        ):
            self.assertIs(denies[denied], False)
        self.assertIs(non_authority["ci_success_is_runtime_authority"], False)
        self.assertIs(
            non_authority["validator_output_is_runtime_authority"],
            False,
        )
        self.assertIs(
            non_authority["checker_output_is_enforcer_authority"],
            False,
        )
        self.assertIs(non_authority["enforcer_output_is_execution"], False)


class PayloadValidationTests(unittest.TestCase):
    def assert_failure(self, payload, failure):
        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            payload
        )
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn(failure, result["failures"])
        assert_no_leak(self, result)
        return result

    def test_payload_not_mapping(self):
        result = self.assert_failure([], "ci_payload_not_mapping")
        self.assertEqual(result["failures"], ["ci_payload_not_mapping"])

    def test_payload_shape_mismatch(self):
        payload = valid_payload()
        payload["extra"] = True

        self.assert_failure(payload, "ci_payload_shape_mismatch")

    def test_checkpoint_tag_mismatch(self):
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"

        self.assert_failure(payload, "validator_checkpoint_invalid")

    def test_checkpoint_commit_mismatch(self):
        payload = valid_payload()
        payload["validator_checkpoint_commit"] = "0" * 40

        self.assert_failure(payload, "validator_checkpoint_invalid")

    def test_readiness_must_be_bool(self):
        payload = valid_payload()
        payload[READY_KEY] = "true"

        self.assert_failure(payload, "readiness_invalid")

    def test_readiness_bool_as_int_rejected(self):
        payload = valid_payload()
        payload[READY_KEY] = 1

        self.assert_failure(payload, "readiness_invalid")

    def test_ready_consistency_reason_violation(self):
        payload = valid_payload()
        payload["reason_code"] = "not_ready"

        self.assert_failure(payload, "reason_code_invalid")

    def test_ready_consistency_failures_violation(self):
        payload = valid_payload()
        payload["failures"] = ["source_ref_mismatch"]

        self.assert_failure(payload, "readiness_invalid")

    def test_not_ready_consistency_reason_violation(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["reason_code"] = "ready"

        self.assert_failure(payload, "reason_code_invalid")

    def test_not_ready_consistency_empty_failures_violation(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["failures"] = []

        self.assert_failure(payload, "readiness_invalid")

    def test_reason_code_unknown_rejected(self):
        payload = valid_payload()
        payload["reason_code"] = "unknown"

        self.assert_failure(payload, "reason_code_invalid")

    def test_failure_list_invalid(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["failures"] = "source_ref_mismatch"

        self.assert_failure(payload, "failure_list_invalid")

    def test_failure_list_rejects_non_string_without_echo(self):
        payload = not_ready_payload("source_ref_mismatch")
        payload["failures"] = [LeakyValue()]

        result = self.assert_failure(payload, "failure_list_invalid")
        self.assertNotIn("LEAKY_RUNTIME_OBJECT", repr(result))

    def test_unknown_validator_failure_rejected(self):
        payload = not_ready_payload("unknown_failure")

        result = self.assert_failure(payload, "unknown_validator_failure")
        self.assertNotIn("unknown_failure", result["failures"])

    def test_json_safe_false_invalid(self):
        payload = valid_payload()
        payload["json_safe"] = False

        self.assert_failure(payload, "json_safe_invalid")

    def test_json_safe_missing_invalid(self):
        payload = valid_payload()
        del payload["json_safe"]

        result = self.assert_failure(payload, "json_safe_invalid")
        self.assertIn("ci_payload_shape_mismatch", result["failures"])

    def test_boundary_summary_invalid(self):
        payload = valid_payload()
        payload["boundary"] = []

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_source_refs_mismatch(self):
        payload = valid_payload()
        payload["boundary"]["source_refs"][
            "runtime-checker-enforcer-separation-boundary-spec-only-v1"
        ] = "bad"

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_boundary_model_mismatch(self):
        payload = valid_payload()
        payload["boundary"][
            "checker_enforcer_separation_boundary_model"
        ]["checker_output_boundary"] = False

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_future_boundary_declaration_missing_invalid(self):
        payload = valid_payload()
        del payload["boundary"]["future_validator_requirements"][
            "future_execution_context_binding_boundary_required"
        ]

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_gemini_risk_containment_missing_invalid(self):
        payload = valid_payload()
        payload["boundary"]["future_validator_requirements"][
            "physical_enforcement_not_implemented"
        ] = False

        self.assert_failure(payload, "boundary_summary_invalid")

    def test_authority_summary_invalid(self):
        payload = valid_payload()
        payload["authority"] = {}

        self.assert_failure(payload, "authority_summary_invalid")

    def test_true_authority_fails_closed(self):
        payload = valid_payload()
        payload["authority"][
            "runtime_checker_to_enforcer_handoff_authorized"
        ] = True

        self.assert_failure(payload, "authority_summary_invalid")

    def test_non_authority_summary_invalid(self):
        payload = valid_payload()
        payload["non_authority"][
            "runtime_checker_enforcer_separation_boundary_ready_authorizes"
        ]["service_calls"] = True

        self.assert_failure(payload, "non_authority_summary_invalid")

    def test_non_authority_gemini_risk_missing_invalid(self):
        payload = valid_payload()
        del payload["non_authority"][
            "runtime_checker_enforcer_separation_boundary_ready_authorizes"
        ]["toctou_physical_enforcement"]

        self.assert_failure(payload, "non_authority_summary_invalid")

    def test_raw_object_leakage_prevention(self):
        payload = valid_payload()
        payload["boundary"] = {"attacker": LeakyValue()}
        payload["authority"] = {"attacker": LeakyValue()}
        payload["non_authority"] = {"attacker": LeakyValue()}

        result = self.assert_failure(payload, "boundary_summary_invalid")

        self.assertIn("authority_summary_invalid", result["failures"])
        self.assertIn("non_authority_summary_invalid", result["failures"])
        self.assertEqual(result["boundary"], manifest()["expected_boundary"])
        self.assertEqual(result["authority"], manifest()["authority_summary"])
        self.assertNotIn("attacker", result["boundary"])
        assert_no_leak(self, result)

    def test_reason_code_mapping(self):
        ready = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            valid_payload()
        )
        not_ready = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            not_ready_payload("source_ref_mismatch")
        )
        invalid = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
            []
        )

        self.assertEqual(ready["reason_code"], "ready")
        self.assertEqual(not_ready["reason_code"], "not_ready")
        self.assertEqual(invalid["reason_code"], "invalid_ci_payload")

    def test_deterministic_failure_ordering(self):
        payload = valid_payload()
        payload["extra"] = True
        payload["validator_checkpoint_tag"] = "wrong"
        payload[READY_KEY] = 1
        payload["reason_code"] = "wrong"
        payload["failures"] = ["unknown_failure"]
        payload["boundary"] = {}
        payload["authority"] = {}
        payload["non_authority"] = {}
        payload["json_safe"] = False

        result = consume_runtime_checker_enforcer_separation_boundary_validator_ci(
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

    def test_input_immutability(self):
        payload = valid_payload()
        before = copy.deepcopy(payload)

        consume_runtime_checker_enforcer_separation_boundary_validator_ci(payload)

        self.assertEqual(payload, before)


class SourceBoundaryTests(unittest.TestCase):
    def test_no_forbidden_runtime_imports_or_calls(self):
        tree = ast.parse(source_text())
        forbidden_import_roots = {
            "datetime",
            "time",
            "os",
            "pathlib",
            "sqlite3",
            "subprocess",
            "threading",
            "asyncio",
            "hashlib",
            "hmac",
            "secrets",
            "inspect",
            "importlib",
            "socket",
            "requests",
            "urllib",
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
            "stat",
            "read_text",
            "write_text",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    self.assertNotIn(root, forbidden_import_roots)
                    self.assertFalse(alias.name.startswith("kernel.services"))
                    self.assertFalse(alias.name.startswith("kernel.stores"))
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                root = module_name.split(".")[0]
                self.assertNotIn(root, forbidden_import_roots)
                self.assertFalse(module_name.startswith("kernel.services"))
                self.assertFalse(module_name.startswith("kernel.stores"))
                self.assertFalse(
                    module_name.startswith(
                        "kernel.lifecycle.runtime_checker_enforcer_"
                        "separation_boundary_validator"
                    )
                )
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    self.assertNotIn(func.id, forbidden_calls)
                elif isinstance(func, ast.Attribute):
                    self.assertNotIn(func.attr, forbidden_calls)

    def test_no_digest_hash_merkle_env_filesystem_token_crypto_pid_time_uow_subprocess_behavior(self):
        tree = ast.parse(source_text())
        forbidden_imports = {
            "hashlib",
            "hmac",
            "secrets",
            "os",
            "pathlib",
            "sqlite3",
            "subprocess",
            "datetime",
            "time",
            "threading",
            "asyncio",
        }
        forbidden_calls = {
            "sha256",
            "digest",
            "hexdigest",
            "getenv",
            "environ",
            "listdir",
            "walk",
            "scandir",
            "stat",
            "open",
            "connect",
            "execute",
            "commit",
            "rollback",
            "run",
            "Popen",
            "now",
            "utcnow",
            "time",
            "pid",
            "getpid",
        }

        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(
            forbidden_imports.isdisjoint(
                {name.split(".")[0] for name in imported if name}
            )
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
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_no_service_db_repository_uow_audit_evidence_executor_calls(self):
        tree = ast.parse(source_text())
        imported = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

        for module_name in imported:
            self.assertFalse(module_name.startswith("kernel.services"))
            self.assertFalse(module_name.startswith("kernel.stores"))
            self.assertFalse(module_name.startswith("kernel.repositories"))
            self.assertNotIn("unit_of_work", module_name)
            self.assertNotIn("repository", module_name)

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
            "append_evidence",
            "append_audit",
            "call_service",
            "execute",
            "dispatch",
            "restore",
            "reserve",
            "rollback",
            "commit",
            "connect",
        }
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
