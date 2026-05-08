"""Tracer bullets for the service call admission gate validator CI."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

import kernel.lifecycle.service_call_admission_gate_validator_ci as ci_module
from kernel.lifecycle.service_call_admission_gate_validator_ci import (
    consume_service_call_admission_gate_validator_ci,
    service_call_admission_gate_validator_ci_manifest,
)


MANIFEST = service_call_admission_gate_validator_ci_manifest()
GATE = MANIFEST["expected_gate_summary"]
AUTHORITY = MANIFEST["authority_summary"]
VALIDATOR_NON_AUTHORITY = MANIFEST["expected_validator_non_authority_summary"]
CI_NON_AUTHORITY = MANIFEST["non_authority_summary"]
VALIDATOR_FAILURES = MANIFEST["validator_failure_taxonomy"]
CI_FAILURES = MANIFEST["ci_failure_taxonomy"]


class LeakyValue:
    def __repr__(self) -> str:
        return "LEAKY_SERVICE_CALL_ADMISSION_OBJECT"


def valid_payload() -> dict[str, object]:
    return {
        "service_call_admission_gate_ready": True,
        "reason_code": "ready",
        "failures": [],
        "gate": copy.deepcopy(GATE),
        "authority": copy.deepcopy(AUTHORITY),
        "non_authority": copy.deepcopy(VALIDATOR_NON_AUTHORITY),
        "json_safe": True,
        "validator_checkpoint_tag": "service-call-admission-gate-validator-v1",
        "validator_checkpoint_commit": (
            "5499023b62617266cdcabc10996895cdbdd226f6"
        ),
    }


def assert_json_safe_without_leak(
    testcase: unittest.TestCase,
    result: dict[str, object],
) -> None:
    encoded = json.dumps(result, sort_keys=True)
    testcase.assertNotIn("LEAKY_SERVICE_CALL_ADMISSION_OBJECT", encoded)


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            set(dir(ci_module))
            & {
                "service_call_admission_gate_validator_ci_manifest",
                "consume_service_call_admission_gate_validator_ci",
            },
            {
                "service_call_admission_gate_validator_ci_manifest",
                "consume_service_call_admission_gate_validator_ci",
            },
        )

    def test_all_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "service_call_admission_gate_validator_ci_manifest",
                "consume_service_call_admission_gate_validator_ci",
            ],
        )

    def test_signatures_are_exact(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    service_call_admission_gate_validator_ci_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    consume_service_call_admission_gate_validator_ci
                ).parameters
            ),
            ["payload"],
        )

    def test_imports_limited_to_mapping_and_deepcopy(self) -> None:
        tree = ast.parse(inspect.getsource(ci_module))
        imports: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, ""))
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append((module, alias.name))

        self.assertEqual(
            imports,
            [
                ("collections.abc", "Mapping"),
                ("copy", "deepcopy"),
            ],
        )

    def test_manifest_defensive_copy_and_json_safe(self) -> None:
        manifest = service_call_admission_gate_validator_ci_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(
            manifest["surface"],
            "service_call_admission_gate_validator_ci",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["validator_checkpoint_tag"],
            "service-call-admission-gate-validator-v1",
        )
        self.assertEqual(
            manifest["validator_checkpoint_commit"],
            "5499023b62617266cdcabc10996895cdbdd226f6",
        )
        self.assertEqual(
            manifest["expected_contract_name"],
            "ServiceCallAdmissionGateV1",
        )
        self.assertEqual(
            manifest["expected_validator_package"],
            "service-call-admission-gate-validator-v1",
        )
        self.assertEqual(manifest["ci_failure_taxonomy"], CI_FAILURES)
        self.assertEqual(manifest["validator_failure_taxonomy"], VALIDATOR_FAILURES)
        self.assertEqual(
            manifest["expected_input_keys"],
            [
                "service_call_admission_gate_ready",
                "reason_code",
                "failures",
                "gate",
                "authority",
                "non_authority",
                "json_safe",
                "validator_checkpoint_tag",
                "validator_checkpoint_commit",
            ],
        )
        self.assertEqual(
            manifest["expected_gate_keys"],
            [
                "surface",
                "version",
                "source_refs",
                "admission_input",
                "required_false_authority_flags",
                "required_true_declarations",
                "json_safe",
            ],
        )
        self.assertEqual(
            manifest["public_api"],
            [
                "service_call_admission_gate_validator_ci_manifest",
                "consume_service_call_admission_gate_validator_ci",
            ],
        )
        self.assertEqual(
            manifest["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )
        manifest["authority_summary"]["service_call_execution_authorized"] = True
        manifest["expected_gate_summary"]["version"] = 2
        manifest["non_authority_summary"][
            "no_service_call_authorization"
        ] = False
        fresh = service_call_admission_gate_validator_ci_manifest()
        self.assertIs(
            fresh["authority_summary"]["service_call_execution_authorized"],
            False,
        )
        self.assertEqual(fresh["expected_gate_summary"]["version"], 1)
        self.assertIs(fresh["non_authority_summary"]["no_service_call_authorization"], True)


class HappyPathTests(unittest.TestCase):
    def test_happy_path_ready(self) -> None:
        result = consume_service_call_admission_gate_validator_ci(valid_payload())

        self.assertEqual(
            set(result),
            {
                "ci_ok",
                "reason_code",
                "failures",
                "validator_checkpoint",
                "gate",
                "authority",
                "non_authority",
                "json_safe",
            },
        )
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["validator_checkpoint"],
            {
                "tag": "service-call-admission-gate-validator-v1",
                "commit": "5499023b62617266cdcabc10996895cdbdd226f6",
            },
        )
        self.assertEqual(result["gate"], GATE)
        self.assertEqual(result["authority"], AUTHORITY)
        self.assertEqual(result["non_authority"], CI_NON_AUTHORITY)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertTrue(all(value is True for value in result["non_authority"].values()))
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

    def test_valid_not_ready_validator_output(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = [
            "source_ref_mismatch",
            "json_safe_invalid",
        ]

        result = consume_service_call_admission_gate_validator_ci(payload)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"],
            ["source_ref_mismatch", "json_safe_invalid"],
        )
        self.assert_json_ready(result)

    def test_valid_invalid_payload_reason_from_validator_is_not_ready(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = False
        payload["reason_code"] = "invalid_service_call_admission_payload"
        payload["failures"] = ["payload_not_mapping"]

        result = consume_service_call_admission_gate_validator_ci(payload)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["payload_not_mapping"])
        self.assert_json_ready(result)

    def test_input_immutability(self) -> None:
        payload = valid_payload()
        before = copy.deepcopy(payload)
        consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(payload, before)

    def test_output_hard_false_authority_flags_and_non_authorizing_ci_ok(self) -> None:
        result = consume_service_call_admission_gate_validator_ci(valid_payload())
        self.assertIs(result["ci_ok"], True)
        authority = result["authority"]
        for flag in (
            "service_call_admission_runtime_authorized",
            "service_call_admission_gate_authorized",
            "service_call_admission_decision_authorized",
            "runtime_authority_grant_runtime_authorized",
            "runtime_authority_ref_runtime_authorized",
            "runtime_authority_checker_authorized",
            "runtime_authority_enforcer_authorized",
            "runtime_authority_runtime_authorized",
            "service_call_execution_authorized",
            "service_adapter_runtime_authorized",
            "service_method_call_authorized",
            "evidence_append_authorized",
            "audit_append_authorized",
            "repository_uow_writes_authorized",
            "transaction_runtime_authorized",
            "idempotency_reservation_authorized",
            "rollback_runtime_authorized",
            "executor_service_dispatch_authorized",
            "durable_writes_authorized",
            "irreversible_action_authorized",
        ):
            self.assertIs(authority[flag], False)

        non_authority = result["non_authority"]
        self.assertIs(non_authority["structural_declaration_validity_only"], True)
        for key in (
            "no_service_call_admission_runtime_authorization",
            "no_admission_decision_runtime_authorization",
            "no_runtime_authority_grant_usage_authorization",
            "no_authority_ref_runtime_usage_authorization",
            "no_checker_enforcer_runtime_authorization",
            "no_service_call_authorization",
            "no_evidence_audit_append_authorization",
            "no_db_repository_uow_write_authorization",
            "no_transaction_runtime_authorization",
            "no_idempotency_reservation_runtime_authorization",
            "no_rollback_runtime_authorization",
            "no_executor_dispatch_authorization",
            "no_durable_write_authorization",
            "no_irreversible_action_authorization",
        ):
            self.assertIs(non_authority[key], True)

    def assert_json_ready(self, result: dict[str, object]) -> None:
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)


class PayloadShapeTests(unittest.TestCase):
    def test_ci_payload_not_mapping(self) -> None:
        result = consume_service_call_admission_gate_validator_ci([])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["ci_payload_not_mapping"])
        assert_json_safe_without_leak(self, result)

    def test_ci_payload_shape_mismatch_extra_key(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["ci_payload_shape_mismatch"])

    def test_ci_payload_shape_mismatch_missing_key(self) -> None:
        payload = valid_payload()
        del payload["gate"]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["ci_payload_shape_mismatch", "gate_summary_invalid"],
        )

    def test_validator_checkpoint_invalid(self) -> None:
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["validator_checkpoint_invalid"])

    def test_validator_checkpoint_commit_invalid(self) -> None:
        payload = valid_payload()
        payload["validator_checkpoint_commit"] = "0" * 40
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["validator_checkpoint_invalid"])


class ReadinessConsistencyTests(unittest.TestCase):
    def test_readiness_invalid_non_bool(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = "true"
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_bool_as_int_readiness_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = 1
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_ready_with_wrong_reason_fails(self) -> None:
        payload = valid_payload()
        payload["reason_code"] = "not_ready"
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["reason_code_invalid"])

    def test_ready_with_non_empty_failures_fails(self) -> None:
        payload = valid_payload()
        payload["failures"] = ["source_ref_mismatch"]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_not_ready_with_empty_failures_fails(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = False
        payload["reason_code"] = "not_ready"
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_not_ready_with_invalid_reason_fails(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = False
        payload["reason_code"] = "wrong"
        payload["failures"] = ["source_ref_mismatch"]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["reason_code_invalid"])

    def test_failure_list_invalid_not_list(self) -> None:
        payload = valid_payload()
        payload["failures"] = ("source_ref_mismatch",)
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["failure_list_invalid"])

    def test_failure_list_invalid_non_string(self) -> None:
        payload = valid_payload()
        payload["failures"] = ["source_ref_mismatch", 1]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["failure_list_invalid"])

    def test_unknown_validator_failure_fails_closed(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = ["source_ref_mismatch", "new_failure"]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["unknown_validator_failure"])


class SummaryValidationTests(unittest.TestCase):
    def test_gate_summary_invalid_surface(self) -> None:
        payload = valid_payload()
        payload["gate"]["surface"] = "Wrong"
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["gate_summary_invalid"])

    def test_gate_summary_invalid_bool_as_int_version(self) -> None:
        payload = valid_payload()
        payload["gate"]["version"] = True
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["gate_summary_invalid"])

    def test_gate_summary_invalid_source_refs_do_not_leak(self) -> None:
        payload = valid_payload()
        payload["gate"]["source_refs"] = {
            "service-call-admission-gate-validator-ci-v1": LeakyValue()
        }
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["gate_summary_invalid", "json_safe_invalid"],
        )
        assert_json_safe_without_leak(self, result)
        self.assertEqual(result["gate"], GATE)

    def test_gate_summary_invalid_required_true_declaration_type(self) -> None:
        payload = valid_payload()
        payload["gate"]["required_true_declarations"][
            "readiness_is_not_authority"
        ] = 1
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["gate_summary_invalid"])

    def test_authority_summary_invalid_missing_flag(self) -> None:
        payload = valid_payload()
        del payload["authority"]["service_call_execution_authorized"]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["authority_summary_invalid"])

    def test_authority_summary_invalid_non_bool_flag(self) -> None:
        payload = valid_payload()
        payload["authority"]["service_call_execution_authorized"] = 0
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["authority_summary_invalid"])

    def test_authority_flag_true_fails_closed(self) -> None:
        payload = valid_payload()
        payload["authority"]["service_call_execution_authorized"] = True
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["authority_summary_invalid"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_non_authority_summary_invalid(self) -> None:
        payload = valid_payload()
        payload["non_authority"][
            "service_call_admission_gate_ready_authorizes_service_calls"
        ] = True
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["non_authority_summary_invalid"])

    def test_json_safe_invalid_false(self) -> None:
        payload = valid_payload()
        payload["json_safe"] = False
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_json_safe_invalid_non_bool(self) -> None:
        payload = valid_payload()
        payload["json_safe"] = "true"
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_invalid_failures_with_object_remain_json_safe(self) -> None:
        payload = valid_payload()
        payload["failures"] = [LeakyValue()]
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["failure_list_invalid"])
        assert_json_safe_without_leak(self, result)

    def test_caller_controlled_invalid_authority_does_not_leak(self) -> None:
        payload = valid_payload()
        payload["authority"]["service_call_execution_authorized"] = LeakyValue()
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["authority_summary_invalid", "json_safe_invalid"],
        )
        assert_json_safe_without_leak(self, result)
        self.assertEqual(result["authority"], AUTHORITY)

    def test_caller_controlled_invalid_non_authority_does_not_leak(self) -> None:
        payload = valid_payload()
        payload["non_authority"][
            "service_call_admission_gate_ready_authorizes_service_calls"
        ] = LeakyValue()
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["non_authority_summary_invalid", "json_safe_invalid"],
        )
        assert_json_safe_without_leak(self, result)
        self.assertEqual(result["non_authority"], CI_NON_AUTHORITY)

    def test_bounded_output_on_failure_paths(self) -> None:
        cases = [
            [],
            {**valid_payload(), "validator_checkpoint_tag": "wrong"},
            {**valid_payload(), "service_call_admission_gate_ready": 1},
            {**valid_payload(), "json_safe": False},
        ]
        for payload in cases:
            with self.subTest(payload=type(payload).__name__):
                result = consume_service_call_admission_gate_validator_ci(payload)
                self.assertEqual(
                    set(result),
                    {
                        "ci_ok",
                        "reason_code",
                        "failures",
                        "validator_checkpoint",
                        "gate",
                        "authority",
                        "non_authority",
                        "json_safe",
                    },
                )
                json.dumps(result, sort_keys=True)


class DeterminismTests(unittest.TestCase):
    def test_deterministic_first_failure_order(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        payload["validator_checkpoint_tag"] = "wrong"
        payload["service_call_admission_gate_ready"] = 1
        payload["reason_code"] = "wrong"
        payload["failures"] = ["unknown"]
        payload["gate"] = []
        payload["authority"] = []
        payload["non_authority"] = []
        payload["json_safe"] = False
        result = consume_service_call_admission_gate_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            [
                "ci_payload_shape_mismatch",
                "validator_checkpoint_invalid",
                "readiness_invalid",
                "reason_code_invalid",
                "unknown_validator_failure",
                "gate_summary_invalid",
                "authority_summary_invalid",
                "non_authority_summary_invalid",
                "json_safe_invalid",
            ],
        )

    def test_every_validator_failure_is_known_for_not_ready(self) -> None:
        for failure in VALIDATOR_FAILURES:
            with self.subTest(failure=failure):
                payload = valid_payload()
                payload["service_call_admission_gate_ready"] = False
                payload["reason_code"] = "not_ready"
                payload["failures"] = [failure]
                result = consume_service_call_admission_gate_validator_ci(payload)
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertEqual(result["failures"], [failure])

    def test_ci_failure_taxonomy_exact_order(self) -> None:
        self.assertEqual(
            CI_FAILURES,
            [
                "ci_payload_not_mapping",
                "ci_payload_shape_mismatch",
                "validator_checkpoint_invalid",
                "readiness_invalid",
                "reason_code_invalid",
                "failure_list_invalid",
                "unknown_validator_failure",
                "gate_summary_invalid",
                "authority_summary_invalid",
                "non_authority_summary_invalid",
                "json_safe_invalid",
            ],
        )

    def test_validator_failure_taxonomy_exact_order(self) -> None:
        self.assertEqual(
            VALIDATOR_FAILURES,
            [
                "payload_not_mapping",
                "payload_shape_mismatch",
                "gate_not_mapping",
                "gate_shape_mismatch",
                "gate_surface_invalid",
                "gate_version_invalid",
                "source_ref_mismatch",
                "admission_input_invalid",
                "binding_group_invalid",
                "required_binding_invalid",
                "required_binding_false",
                "forbidden_implicit_authority_invalid",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "required_declaration_invalid",
                "required_declaration_false",
                "json_safe_invalid",
            ],
        )


class SourceBoundaryTests(unittest.TestCase):
    def source(self) -> str:
        return inspect.getsource(ci_module)

    def tree(self) -> ast.AST:
        return ast.parse(self.source())

    def test_validator_not_imported_or_called(self) -> None:
        source = self.source()
        self.assertNotIn(
            "validate_service_call_admission_gate",
            source,
        )
        self.assertNotIn(
            "service_call_admission_gate_validator import",
            source,
        )

    def test_no_git_shell_out(self) -> None:
        tree = self.tree()
        forbidden_calls = {"system", "popen", "run", "check_output", "git"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls)

    def test_no_service_db_repository_or_uow_imports(self) -> None:
        tree = self.tree()
        forbidden_modules = (
            "kernel.services",
            "kernel.stores",
            "sqlite3",
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                self.assertFalse(
                    any(module.startswith(name) for name in forbidden_modules),
                    module,
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(
                        any(alias.name.startswith(name) for name in forbidden_modules),
                        alias.name,
                    )

    def test_no_upstream_validator_checker_or_ci_imports(self) -> None:
        tree = self.tree()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("kernel.lifecycle."):
                    self.fail(f"unexpected lifecycle import: {module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("kernel.lifecycle."):
                        self.fail(f"unexpected lifecycle import: {alias.name}")

    def test_no_wall_clock_digest_runtime_introspection_or_subprocess(self) -> None:
        tree = self.tree()
        forbidden = {
            "datetime",
            "time",
            "hashlib",
            "hmac",
            "secrets",
            "inspect",
            "importlib",
            "subprocess",
            "os",
            "pathlib",
            "threading",
            "asyncio",
        }
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertEqual(imports, ["collections.abc", "copy"])
        self.assertFalse(forbidden & set(imports))

    def test_no_forbidden_runtime_service_db_repository_calls(self) -> None:
        tree = self.tree()
        forbidden_names = {
            "open",
            "connect",
            "execute",
            "executemany",
            "commit",
            "rollback",
            "dispatch",
            "restore",
            "append_evidence",
            "append_audit",
            "seal_revision",
            "approve",
            "review",
            "authorize",
            "import_module",
            "getattr",
            "eval",
            "exec",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_names)
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_names)

    def test_no_forbidden_executable_import_strings(self) -> None:
        tree = self.tree()
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertEqual(imports, ["collections.abc", "copy"])


if __name__ == "__main__":
    unittest.main()
