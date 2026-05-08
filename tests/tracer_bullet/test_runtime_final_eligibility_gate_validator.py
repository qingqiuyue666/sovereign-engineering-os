import ast
import copy
import json
import unittest
from pathlib import Path

from kernel.lifecycle import runtime_final_eligibility_gate_validator as validator
from kernel.lifecycle.runtime_final_eligibility_gate_validator import (
    runtime_final_eligibility_gate_validator_manifest,
    validate_runtime_final_eligibility_gate,
)


EXPECTED_FAILURE_TAXONOMY = [
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

EXPECTED_REASON_CODES = [
    "ready",
    "not_ready",
    "invalid_runtime_final_eligibility_payload",
]

PRODUCTION_PATH = Path(
    "kernel/lifecycle/runtime_final_eligibility_gate_validator.py"
)


def _manifest():
    return runtime_final_eligibility_gate_validator_manifest()


def _valid_gate():
    manifest = _manifest()
    return {
        "surface": manifest["contract_name"],
        "version": 1,
        "source_refs": copy.deepcopy(manifest["expected_source_refs"]),
        "completed_read_only_stacks": copy.deepcopy(
            manifest["expected_completed_read_only_stacks"]
        ),
        "required_runtime_boundaries": {
            boundary: True
            for boundary in manifest["required_runtime_boundaries"]
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


def _valid_payload():
    return {"runtime_final_eligibility_gate": _valid_gate()}


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
            validator.__all__,
            [
                "runtime_final_eligibility_gate_validator_manifest",
                "validate_runtime_final_eligibility_gate",
            ],
        )
        self.assertIs(
            validator.runtime_final_eligibility_gate_validator_manifest,
            runtime_final_eligibility_gate_validator_manifest,
        )
        self.assertIs(
            validator.validate_runtime_final_eligibility_gate,
            validate_runtime_final_eligibility_gate,
        )

    def test_failure_taxonomy_is_exactly_expected(self):
        self.assertEqual(
            _manifest()["failure_taxonomy"],
            EXPECTED_FAILURE_TAXONOMY,
        )

    def test_reason_codes_are_exactly_expected(self):
        self.assertEqual(
            _manifest()["allowed_reason_codes"],
            EXPECTED_REASON_CODES,
        )


class HappyPathTests(unittest.TestCase):
    def test_ready_valid_payload_returns_ready(self):
        result = validate_runtime_final_eligibility_gate(_valid_payload())
        self.assertEqual(
            set(result.keys()),
            {
                "runtime_final_eligibility_gate_ready",
                "reason_code",
                "failures",
                "gate",
                "authority",
                "non_authority",
                "json_safe",
            },
        )
        self.assertIs(result["runtime_final_eligibility_gate_ready"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["json_safe"], True)

    def test_input_payload_is_not_mutated(self):
        payload = _valid_payload()
        before = copy.deepcopy(payload)
        validate_runtime_final_eligibility_gate(payload)
        self.assertEqual(payload, before)

    def test_output_is_bounded_and_json_safe(self):
        result = validate_runtime_final_eligibility_gate(_valid_payload())
        _assert_json_safe(self, result)
        self.assertLess(len(str(result)), 50000)

    def test_output_authority_summary_is_hard_false(self):
        result = validate_runtime_final_eligibility_gate(_valid_payload())
        self.assertTrue(result["authority"])
        self.assertTrue(
            all(value is False for value in result["authority"].values())
        )

    def test_non_authority_summary_denies_runtime_service_write_append_executor(
        self,
    ):
        result = validate_runtime_final_eligibility_gate(_valid_payload())
        denials = result["non_authority"][
            "runtime_final_eligibility_gate_ready_authorizes"
        ]
        for key in [
            "runtime",
            "service_calls",
            "db_repository_uow_writes",
            "evidence_audit_append",
            "executor_dispatch",
            "transaction_idempotency_rollback",
        ]:
            self.assertIs(denials[key], False)

    def test_ready_output_does_not_authorize_runtime_service_db_append_executor(
        self,
    ):
        result = validate_runtime_final_eligibility_gate(_valid_payload())
        self.assertIs(result["runtime_final_eligibility_gate_ready"], True)
        self.assertTrue(
            all(value is False for value in result["authority"].values())
        )
        self.assertTrue(
            all(
                value is False
                for value in result["non_authority"][
                    "runtime_final_eligibility_gate_ready_authorizes"
                ].values()
            )
        )


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload_fails(self):
        result = validate_runtime_final_eligibility_gate([])
        self.assertEqual(result["reason_code"], "invalid_runtime_final_eligibility_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_wrong_top_level_key_fails(self):
        result = validate_runtime_final_eligibility_gate({"bad": _valid_gate()})
        self.assertIn("payload_shape_mismatch", result["failures"])

    def test_missing_gate_fails(self):
        result = validate_runtime_final_eligibility_gate({})
        self.assertEqual(
            result["failures"],
            ["payload_shape_mismatch", "gate_not_mapping"],
        )

    def test_non_mapping_gate_fails(self):
        result = validate_runtime_final_eligibility_gate(
            {"runtime_final_eligibility_gate": object()}
        )
        self.assertEqual(result["reason_code"], "invalid_runtime_final_eligibility_payload")
        self.assertIn("gate_not_mapping", result["failures"])

    def test_wrong_gate_key_set_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["extra"] = True
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("gate_shape_mismatch", result["failures"])

    def test_wrong_surface_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["surface"] = "bad"
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("gate_surface_invalid", result["failures"])

    def test_wrong_version_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["version"] = 2
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("gate_version_invalid", result["failures"])

    def test_bool_as_int_version_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["version"] = True
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("gate_version_invalid", result["failures"])

    def test_json_safe_false_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["json_safe"] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("json_safe_invalid", result["failures"])


class SourceAndDeclarationTests(unittest.TestCase):
    def test_wrong_source_refs_fail(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["source_refs"][
            "runtime-final-eligibility-gate-spec-only-v1"
        ] = "bad"
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("source_ref_mismatch", result["failures"])

    def test_invalid_caller_source_refs_are_not_echoed(self):
        marker = object()
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["source_refs"][
            "read-only-governance-layer-v1"
        ] = marker
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("source_ref_mismatch", result["failures"])
        self.assertNotIn("object at 0x", str(result))
        self.assertEqual(
            result["gate"]["source_refs"],
            _manifest()["expected_source_refs"],
        )

    def test_wrong_completed_read_only_stacks_fail(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["completed_read_only_stacks"][
            "read-only-governance-layer-v1"
        ] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("completed_read_only_stack_invalid", result["failures"])

    def test_missing_required_runtime_boundary_fails(self):
        payload = _valid_payload()
        del payload["runtime_final_eligibility_gate"][
            "required_runtime_boundaries"
        ]["runtime_final_eligibility_gate"]
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("required_runtime_boundary_missing", result["failures"])

    def test_malformed_required_runtime_boundary_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"][
            "required_runtime_boundaries"
        ]["runtime_final_eligibility_gate"] = "yes"
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("required_runtime_boundary_invalid", result["failures"])

    def test_wrong_false_authority_flag_set_fails(self):
        payload = _valid_payload()
        del payload["runtime_final_eligibility_gate"]["false_authority_flags"][
            "runtime_final_gate_authorized"
        ]
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("authorization_flag_invalid", result["failures"])

    def test_true_authority_flag_fails_closed(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("authorization_flag_true", result["failures"])
        self.assertIs(result["runtime_final_eligibility_gate_ready"], False)

    def test_wrong_true_declaration_set_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["true_declarations"][
            "extra"
        ] = True
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("required_declaration_invalid", result["failures"])

    def test_false_required_declaration_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["true_declarations"][
            "future_validator_required"
        ] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("required_declaration_false", result["failures"])

    def test_wrong_json_safety_fails(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["json_safety"][
            "raw_repr_leakage_forbidden"
        ] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("json_safety_invalid", result["failures"])

    def test_wrong_future_validator_requirements_fail(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"][
            "future_validator_requirements"
        ]["read_only"] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn(
            "future_validator_requirement_invalid",
            result["failures"],
        )

    def test_wrong_future_ci_requirements_fail(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"]["future_ci_requirements"][
            "read_only"
        ] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertIn("future_ci_requirement_invalid", result["failures"])

    def test_no_raw_object_leakage_through_invalid_object_values(self):
        payload = _valid_payload()
        payload["runtime_final_eligibility_gate"][
            "required_runtime_boundaries"
        ]["runtime_final_eligibility_gate"] = object()
        result = validate_runtime_final_eligibility_gate(payload)
        _assert_json_safe(self, result)
        self.assertNotIn("object at 0x", str(result))


class DeterminismTests(unittest.TestCase):
    def test_deterministic_failure_ordering(self):
        payload = _valid_payload()
        gate = payload["runtime_final_eligibility_gate"]
        gate["surface"] = "bad"
        gate["version"] = True
        gate["source_refs"] = {}
        gate["false_authority_flags"]["audit_append_authorized"] = True
        gate["true_declarations"]["future_ci_required"] = False
        result = validate_runtime_final_eligibility_gate(payload)
        self.assertEqual(
            result["failures"],
            [
                "gate_surface_invalid",
                "gate_version_invalid",
                "source_ref_mismatch",
                "authorization_flag_true",
                "required_declaration_false",
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
                imports.append(
                    (None, tuple(alias.name for alias in node.names))
                )
        self.assertEqual(
            imports,
            [
                ("collections.abc", ("Mapping",)),
                ("copy", ("deepcopy",)),
            ],
        )

    def test_no_service_repository_uow_db_executor_restore_runtime_imports(self):
        forbidden = {
            "kernel.services",
            "kernel.stores",
            "sqlite3",
            "kernel.lifecycle.recovery_gate",
            "kernel.lifecycle.recovery_cli",
            "kernel.lifecycle.recovery_session_host",
            "kernel.lifecycle.signable_path_orchestrator",
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

    def test_validator_does_not_import_or_call_adjacent_validators_or_ci(self):
        forbidden_names = {
            "validate_service_call_admission_gate",
            "consume_service_call_admission_gate_validator_ci",
            "validate_runtime_authority_grant_object",
            "consume_runtime_authority_grant_object_validator_ci",
            "validate_runtime_authority_checker_enforcer_boundary",
            "consume_runtime_authority_checker_enforcer_boundary_validator_ci",
        }
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, forbidden_names)
            elif isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_names)


if __name__ == "__main__":
    unittest.main()
