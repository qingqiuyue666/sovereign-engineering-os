import ast
import copy
import json
import unittest
from pathlib import Path

from kernel.lifecycle import runtime_final_eligibility_gate_validator_ci as ci
from kernel.lifecycle.runtime_final_eligibility_gate_validator_ci import (
    consume_runtime_final_eligibility_gate_validator_ci,
    runtime_final_eligibility_gate_validator_ci_manifest,
)


EXPECTED_CI_FAILURE_TAXONOMY = [
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
]

EXPECTED_VALIDATOR_FAILURE_TAXONOMY = [
    "payload_not_mapping",
    "payload_shape_mismatch",
    "gate_not_mapping",
    "gate_shape_mismatch",
    "gate_surface_invalid",
    "gate_version_invalid",
    "source_ref_mismatch",
    "completed_read_only_stack_invalid",
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
]

EXPECTED_REASON_CODES = ["ready", "not_ready", "invalid_ci_payload"]
PRODUCTION_PATH = Path(
    "kernel/lifecycle/runtime_final_eligibility_gate_validator_ci.py"
)


def _manifest():
    return runtime_final_eligibility_gate_validator_ci_manifest()


def _valid_payload():
    manifest = _manifest()
    return {
        "runtime_final_eligibility_gate_ready": True,
        "reason_code": "ready",
        "failures": [],
        "gate": copy.deepcopy(manifest["expected_validator_gate"]),
        "authority": copy.deepcopy(manifest["authority_summary"]),
        "non_authority": copy.deepcopy(
            manifest["expected_validator_non_authority_summary"]
        ),
        "json_safe": True,
        "validator_checkpoint_tag": manifest["validator_checkpoint_tag"],
        "validator_checkpoint_commit": manifest["validator_checkpoint_commit"],
    }


def _assert_json_safe(testcase, payload):
    json.dumps(payload, sort_keys=True)
    testcase.assertNotIn("object at 0x", str(payload))


class ManifestTests(unittest.TestCase):
    def test_manifest_returns_defensive_copy(self):
        first = _manifest()
        first["expected_source_refs"]["read-only-governance-layer-v1"] = "bad"
        second = _manifest()
        self.assertEqual(
            second["expected_source_refs"]["read-only-governance-layer-v1"],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )

    def test_manifest_is_json_safe(self):
        _assert_json_safe(self, _manifest())

    def test_public_api_and_all_exact(self):
        self.assertEqual(
            ci.__all__,
            [
                "runtime_final_eligibility_gate_validator_ci_manifest",
                "consume_runtime_final_eligibility_gate_validator_ci",
            ],
        )
        self.assertIs(
            ci.runtime_final_eligibility_gate_validator_ci_manifest,
            runtime_final_eligibility_gate_validator_ci_manifest,
        )
        self.assertIs(
            ci.consume_runtime_final_eligibility_gate_validator_ci,
            consume_runtime_final_eligibility_gate_validator_ci,
        )

    def test_ci_failure_taxonomy_is_exactly_expected(self):
        self.assertEqual(
            _manifest()["ci_failure_taxonomy"],
            EXPECTED_CI_FAILURE_TAXONOMY,
        )

    def test_validator_failure_taxonomy_is_exactly_expected(self):
        self.assertEqual(
            _manifest()["validator_failure_taxonomy"],
            EXPECTED_VALIDATOR_FAILURE_TAXONOMY,
        )

    def test_reason_codes_are_exactly_expected(self):
        self.assertEqual(_manifest()["allowed_reason_codes"], EXPECTED_REASON_CODES)


class HappyPathTests(unittest.TestCase):
    def test_ready_valid_validator_output_returns_ci_ok(self):
        result = consume_runtime_final_eligibility_gate_validator_ci(
            _valid_payload()
        )
        self.assertEqual(
            set(result.keys()),
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
        self.assertIs(result["json_safe"], True)

    def test_valid_summarized_gate_output_returns_ci_ok(self):
        payload = _valid_payload()
        payload["gate"] = copy.deepcopy(_manifest()["expected_gate_summary"])
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["gate"], _manifest()["expected_gate_summary"])

    def test_input_payload_is_not_mutated(self):
        payload = _valid_payload()
        before = copy.deepcopy(payload)
        consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertEqual(payload, before)

    def test_output_is_bounded_and_json_safe(self):
        result = consume_runtime_final_eligibility_gate_validator_ci(
            _valid_payload()
        )
        _assert_json_safe(self, result)
        self.assertLess(len(str(result)), 50000)

    def test_output_authority_summary_is_hard_false(self):
        result = consume_runtime_final_eligibility_gate_validator_ci(
            _valid_payload()
        )
        self.assertTrue(result["authority"])
        self.assertTrue(
            all(value is False for value in result["authority"].values())
        )

    def test_non_authority_summary_denies_runtime_service_write_append_executor(
        self,
    ):
        result = consume_runtime_final_eligibility_gate_validator_ci(
            _valid_payload()
        )
        denials = result["non_authority"]["ci_ok_authorizes"]
        for key in [
            "runtime",
            "runtime_final_eligibility_runtime",
            "runtime_final_gate_runtime",
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
        ]:
            self.assertIs(denials[key], False)

    def test_ready_output_does_not_authorize_runtime_service_db_append_executor(
        self,
    ):
        result = consume_runtime_final_eligibility_gate_validator_ci(
            _valid_payload()
        )
        self.assertIs(result["ci_ok"], True)
        self.assertTrue(
            all(value is False for value in result["authority"].values())
        )
        self.assertTrue(
            all(
                value is False
                for value in result["non_authority"]["ci_ok_authorizes"].values()
            )
        )


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload_fails(self):
        result = consume_runtime_final_eligibility_gate_validator_ci([])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["ci_payload_not_mapping"])

    def test_wrong_top_level_key_fails(self):
        payload = _valid_payload()
        payload["extra"] = True
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("ci_payload_shape_mismatch", result["failures"])

    def test_wrong_checkpoint_tag_fails(self):
        payload = _valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["validator_checkpoint_invalid"])

    def test_wrong_checkpoint_commit_fails(self):
        payload = _valid_payload()
        payload["validator_checkpoint_commit"] = "0" * 40
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["validator_checkpoint_invalid"])

    def test_json_safe_false_fails(self):
        payload = _valid_payload()
        payload["json_safe"] = False
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])


class ReadinessConsistencyTests(unittest.TestCase):
    def test_bool_as_int_readiness_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate_ready"] = 1
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("readiness_invalid", result["failures"])

    def test_wrong_readiness_reason_consistency_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate_ready"] = False
        payload["reason_code"] = "ready"
        payload["failures"] = ["authorization_flag_true"]
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("reason_code_invalid", result["failures"])

    def test_ready_with_failures_fails(self):
        payload = _valid_payload()
        payload["failures"] = ["authorization_flag_true"]
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("readiness_invalid", result["failures"])

    def test_not_ready_with_empty_failures_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = []
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("readiness_invalid", result["failures"])

    def test_unknown_validator_failure_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = ["unknown_failure"]
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertEqual(result["failures"], ["unknown_validator_failure"])

    def test_valid_not_ready_output_returns_not_ready(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate_ready"] = False
        payload["reason_code"] = "invalid_runtime_final_eligibility_payload"
        payload["failures"] = ["gate_surface_invalid", "json_safe_invalid"]
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"],
            ["gate_surface_invalid", "json_safe_invalid"],
        )


class SummaryValidationTests(unittest.TestCase):
    def test_wrong_gate_surface_fails(self):
        payload = _valid_payload()
        payload["gate"]["surface"] = "bad"
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_gate_version_fails(self):
        payload = _valid_payload()
        payload["gate"]["version"] = 2
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_bool_as_int_gate_version_fails(self):
        payload = _valid_payload()
        payload["gate"]["version"] = True
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_source_refs_fail(self):
        payload = _valid_payload()
        payload["gate"]["source_refs"]["read-only-governance-layer-v1"] = "bad"
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_completed_read_only_stacks_fail(self):
        payload = _valid_payload()
        payload["gate"]["completed_read_only_stacks"][
            "read-only-governance-layer-v1"
        ] = False
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_required_runtime_boundaries_fail(self):
        payload = _valid_payload()
        payload["gate"]["required_runtime_boundaries"][
            "runtime_final_eligibility_gate"
        ] = False
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_false_authority_flags_fail(self):
        payload = _valid_payload()
        del payload["gate"]["false_authority_flags"][
            "runtime_final_gate_authorized"
        ]
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_true_authority_flag_fails_closed(self):
        payload = _valid_payload()
        payload["gate"]["false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_true_declarations_fail(self):
        payload = _valid_payload()
        payload["gate"]["true_declarations"]["extra"] = True
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_false_required_declaration_fails(self):
        payload = _valid_payload()
        payload["gate"]["true_declarations"]["future_ci_required"] = False
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])

    def test_wrong_authority_summary_fails(self):
        payload = _valid_payload()
        del payload["authority"]["durable_writes_authorized"]
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("authority_summary_invalid", result["failures"])

    def test_true_authority_summary_fails_closed(self):
        payload = _valid_payload()
        payload["authority"]["durable_writes_authorized"] = True
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn("authority_summary_invalid", result["failures"])

    def test_wrong_non_authority_summary_fails(self):
        payload = _valid_payload()
        payload["non_authority"]["readiness_is_runtime_authority"] = True
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("non_authority_summary_invalid", result["failures"])

    def test_no_raw_object_leakage_through_invalid_object_values(self):
        marker = object()
        payload = _valid_payload()
        payload["gate"]["source_refs"]["read-only-governance-layer-v1"] = marker
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertIn("gate_summary_invalid", result["failures"])
        _assert_json_safe(self, result)
        self.assertNotIn("object at 0x", str(result))
        self.assertEqual(
            result["gate"]["source_refs"],
            _manifest()["expected_source_refs"],
        )


class DeterminismTests(unittest.TestCase):
    def test_deterministic_failure_ordering(self):
        payload = _valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        payload["runtime_final_eligibility_gate_ready"] = 1
        payload["reason_code"] = "bad"
        payload["failures"] = [object()]
        payload["gate"]["surface"] = "bad"
        payload["authority"]["durable_writes_authorized"] = True
        payload["non_authority"]["validator_success_is_authority"] = True
        payload["json_safe"] = False
        result = consume_runtime_final_eligibility_gate_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            [
                "validator_checkpoint_invalid",
                "readiness_invalid",
                "reason_code_invalid",
                "failure_list_invalid",
                "gate_summary_invalid",
                "authority_summary_invalid",
                "non_authority_summary_invalid",
                "json_safe_invalid",
            ],
        )


class SourceBoundaryTests(unittest.TestCase):
    def _tree(self):
        return ast.parse(PRODUCTION_PATH.read_text())

    def test_production_imports_limited_to_mapping_and_deepcopy(self):
        imports = []
        for node in self._tree().body:
            if isinstance(node, ast.ImportFrom):
                imports.append(
                    (
                        node.module,
                        tuple(alias.name for alias in node.names),
                    )
                )
            elif isinstance(node, ast.Import):
                imports.append((None, tuple(alias.name for alias in node.names)))
        self.assertEqual(
            imports,
            [
                ("collections.abc", ("Mapping",)),
                ("copy", ("deepcopy",)),
            ],
        )

    def test_no_validator_import_or_call(self):
        forbidden_names = {
            "validate_runtime_final_eligibility_gate",
            "runtime_final_eligibility_gate_validator_manifest",
            "runtime_final_eligibility_gate_validator",
        }
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("runtime_final_eligibility_gate_validator", node.module or "")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(
                        "runtime_final_eligibility_gate_validator",
                        alias.name,
                    )
            elif isinstance(node, ast.Name):
                self.assertNotIn(node.id, forbidden_names)
            elif isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_names)

    def test_no_service_repository_uow_db_executor_restore_runtime_imports(self):
        forbidden = {
            "kernel.services",
            "kernel.stores",
            "sqlite3",
            "kernel.lifecycle.recovery_gate",
            "kernel.lifecycle.recovery_cli",
            "kernel.lifecycle.recovery_session_host",
            "kernel.lifecycle.signable_path_orchestrator",
            "kernel.lifecycle.runtime_authority_checker_enforcer_boundary_validator",
            "kernel.lifecycle.runtime_authority_grant_object_validator",
            "kernel.lifecycle.service_call_admission_gate_validator",
        }
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)

    def test_no_forbidden_standard_library_imports(self):
        forbidden = {
            "time",
            "datetime",
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
        }
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)

    def test_no_git_shell_out_dependency(self):
        source = PRODUCTION_PATH.read_text()
        forbidden = ("git ", "rev-parse", "ls-remote", "subprocess.", "system(")
        for marker in forbidden:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
