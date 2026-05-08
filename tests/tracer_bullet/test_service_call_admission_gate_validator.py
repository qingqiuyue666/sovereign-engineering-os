"""Tracer bullets for the service call admission gate validator."""

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

import kernel.lifecycle.service_call_admission_gate_validator as validator_module
from kernel.lifecycle.service_call_admission_gate_validator import (
    service_call_admission_gate_validator_manifest,
    validate_service_call_admission_gate,
)


MANIFEST = service_call_admission_gate_validator_manifest()
SOURCE_REFS = MANIFEST["expected_source_refs"]
GATE_KEYS = tuple(MANIFEST["expected_gate_keys"])
BINDING_GROUPS = {
    group: tuple(fields)
    for group, fields in MANIFEST["expected_binding_groups"].items()
    if group != "forbidden_implicit_authority_sources"
}
FALSE_AUTHORITY_FLAGS = tuple(MANIFEST["required_false_authority_flags"])
TRUE_DECLARATIONS = tuple(MANIFEST["required_true_declarations"])
FAILURE_ORDER = tuple(MANIFEST["failure_taxonomy"])
READY_FIELD = "service_call_admission_gate_ready"


def valid_binding(group: str) -> dict[str, object]:
    return {"binding_group": group, "required": True}


def valid_gate() -> dict[str, object]:
    gate: dict[str, object] = {
        "surface": "ServiceCallAdmissionGateV1",
        "version": 1,
        "source_refs": copy.deepcopy(SOURCE_REFS),
    }
    for group, fields in BINDING_GROUPS.items():
        for field in fields:
            gate[field] = valid_binding(group)
    gate["false_authority_flags"] = {
        flag: False for flag in FALSE_AUTHORITY_FLAGS
    }
    gate["true_declarations"] = {
        declaration: True for declaration in TRUE_DECLARATIONS
    }
    gate["json_safe"] = True
    self_check_gate_keys = set(gate)
    if self_check_gate_keys != set(GATE_KEYS):
        raise AssertionError(sorted(set(GATE_KEYS) ^ self_check_gate_keys))
    return gate


def valid_payload() -> dict[str, object]:
    return {"service_call_admission_gate": valid_gate()}


def contains_identity(value: object, target: object) -> bool:
    if value is target:
        return True
    if isinstance(value, dict):
        return any(
            contains_identity(key, target) or contains_identity(item, target)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_identity(item, target) for item in value)
    return False


class PublicApiTests(unittest.TestCase):
    def test_all_exact(self) -> None:
        self.assertEqual(
            validator_module.__all__,
            [
                "service_call_admission_gate_validator_manifest",
                "validate_service_call_admission_gate",
            ],
        )

    def test_signatures_exact(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    service_call_admission_gate_validator_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    validate_service_call_admission_gate
                ).parameters
            ),
            ["payload"],
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = service_call_admission_gate_validator_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(
            set(manifest),
            {
                "surface",
                "version",
                "contract_name",
                "expected_top_level_keys",
                "expected_gate_keys",
                "expected_source_refs",
                "expected_binding_groups",
                "expected_binding_value_keys",
                "required_false_authority_flags",
                "required_true_declarations",
                "forbidden_implicit_authority_declarations",
                "failure_taxonomy",
                "allowed_reason_codes",
                "authority_summary",
                "non_authority_summary",
                "public_api",
                "import_boundary",
                "json_safe",
            },
        )
        self.assertEqual(
            manifest["surface"], "service_call_admission_gate_validator"
        )
        self.assertEqual(manifest["contract_name"], "ServiceCallAdmissionGateV1")
        self.assertEqual(
            manifest["expected_top_level_keys"],
            ["service_call_admission_gate"],
        )
        manifest["expected_source_refs"]["read-only-governance-layer-v1"] = (
            "mutated"
        )
        self.assertEqual(
            service_call_admission_gate_validator_manifest()[
                "expected_source_refs"
            ]["read-only-governance-layer-v1"],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )


class HappyPathTests(unittest.TestCase):
    def test_happy_path_ready(self) -> None:
        result = validate_service_call_admission_gate(valid_payload())

        self.assertEqual(
            set(result),
            {
                READY_FIELD,
                "reason_code",
                "failures",
                "gate",
                "authority",
                "non_authority",
                "json_safe",
            },
        )
        self.assertIs(result[READY_FIELD], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

        gate = result["gate"]
        self.assertEqual(gate["surface"], "ServiceCallAdmissionGateV1")
        self.assertEqual(gate["version"], 1)
        self.assertEqual(gate["source_refs"], SOURCE_REFS)
        self.assertEqual(gate["admission_input"], MANIFEST["expected_binding_groups"])
        self.assertEqual(
            gate["required_false_authority_flags"],
            {flag: False for flag in FALSE_AUTHORITY_FLAGS},
        )
        self.assertEqual(
            gate["required_true_declarations"],
            {declaration: True for declaration in TRUE_DECLARATIONS},
        )

    def test_input_immutability(self) -> None:
        payload = valid_payload()
        original = copy.deepcopy(payload)
        validate_service_call_admission_gate(payload)
        self.assertEqual(payload, original)

    def test_output_hard_false_authority_flags(self) -> None:
        result = validate_service_call_admission_gate(valid_payload())
        self.assertEqual(
            set(result["authority"]), set(FALSE_AUTHORITY_FLAGS)
        )
        for value in result["authority"].values():
            self.assertIs(value, False)
        for value in result["gate"]["required_false_authority_flags"].values():
            self.assertIs(value, False)

    def test_non_authority_summary_forbids_runtime_service_db_append_executor(
        self,
    ) -> None:
        result = validate_service_call_admission_gate(valid_payload())
        non_authority = result["non_authority"]
        self.assertEqual(
            non_authority["service_call_admission_gate_ready_proves"],
            "structural_declaration_validity_only",
        )
        for key in (
            "service_call_admission_gate_ready_authorizes_service_call_admission_runtime",
            "service_call_admission_gate_ready_authorizes_admission_decision_runtime",
            "service_call_admission_gate_ready_authorizes_runtime_authority_grant_usage",
            "service_call_admission_gate_ready_authorizes_authority_ref_runtime_usage",
            "service_call_admission_gate_ready_authorizes_checker_enforcer_runtime",
            "service_call_admission_gate_ready_authorizes_service_calls",
            "service_call_admission_gate_ready_authorizes_evidence_audit_append",
            "service_call_admission_gate_ready_authorizes_db_repository_uow_writes",
            "service_call_admission_gate_ready_authorizes_transaction_runtime",
            "service_call_admission_gate_ready_authorizes_idempotency_reservation",
            "service_call_admission_gate_ready_authorizes_rollback_runtime",
            "service_call_admission_gate_ready_authorizes_executor_dispatch",
            "service_call_admission_gate_ready_authorizes_durable_writes",
            "service_call_admission_gate_ready_authorizes_irreversible_actions",
        ):
            self.assertIs(non_authority[key], False)


class PayloadShapeTests(unittest.TestCase):
    def assert_failure(
        self,
        payload: object,
        failure: str,
        reason: str | None = None,
    ) -> dict[str, object]:
        result = validate_service_call_admission_gate(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn(failure, result["failures"])
        if reason is not None:
            self.assertEqual(result["reason_code"], reason)
        json.dumps(result, sort_keys=True)
        return result

    def test_payload_not_mapping(self) -> None:
        result = self.assert_failure(
            [],
            "payload_not_mapping",
            "invalid_service_call_admission_payload",
        )
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_payload_shape_mismatch(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        self.assert_failure(
            payload,
            "payload_shape_mismatch",
            "invalid_service_call_admission_payload",
        )

    def test_gate_not_mapping(self) -> None:
        self.assert_failure(
            {"service_call_admission_gate": []},
            "gate_not_mapping",
            "invalid_service_call_admission_payload",
        )

    def test_gate_shape_mismatch(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["extra"] = True
        self.assert_failure(
            payload,
            "gate_shape_mismatch",
            "invalid_service_call_admission_payload",
        )

    def test_gate_surface_invalid(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["surface"] = "WrongSurface"
        self.assert_failure(payload, "gate_surface_invalid", "not_ready")

    def test_gate_version_invalid(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["version"] = 2
        self.assert_failure(payload, "gate_version_invalid", "not_ready")

    def test_bool_as_int_version_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["version"] = True
        self.assert_failure(payload, "gate_version_invalid", "not_ready")


class SourceRefTests(unittest.TestCase):
    def test_source_ref_mismatch(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["source_refs"][
            "read-only-governance-layer-v1"
        ] = "wrong"

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        self.assertEqual(result["gate"]["source_refs"], SOURCE_REFS)
        json.dumps(result, sort_keys=True)

    def test_invalid_source_refs_object_remains_json_safe_and_not_echoed(
        self,
    ) -> None:
        sentinel = object()
        payload = valid_payload()
        payload["service_call_admission_gate"]["source_refs"][
            "read-only-governance-layer-v1"
        ] = sentinel

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        self.assertEqual(result["gate"]["source_refs"], SOURCE_REFS)
        self.assertFalse(contains_identity(result, sentinel))
        self.assertIs(
            payload["service_call_admission_gate"]["source_refs"][
                "read-only-governance-layer-v1"
            ],
            sentinel,
        )
        json.dumps(result, sort_keys=True)


class AdmissionInputTests(unittest.TestCase):
    def assert_gate_failure(
        self,
        field: str,
        value: object,
        failure: str,
    ) -> dict[str, object]:
        payload = valid_payload()
        payload["service_call_admission_gate"][field] = value
        result = validate_service_call_admission_gate(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn(failure, result["failures"])
        json.dumps(result, sort_keys=True)
        return result

    def test_admission_input_invalid(self) -> None:
        self.assert_gate_failure(
            "service_identity",
            {"binding_group": "service_identity_binding", "required": object()},
            "admission_input_invalid",
        )

    def test_binding_group_invalid(self) -> None:
        self.assert_gate_failure(
            "service_identity",
            {"binding_group": "wrong_group", "required": True},
            "binding_group_invalid",
        )

    def test_required_binding_invalid(self) -> None:
        self.assert_gate_failure(
            "service_identity",
            {"binding_group": "service_identity_binding", "required": "true"},
            "required_binding_invalid",
        )

    def test_required_binding_false(self) -> None:
        self.assert_gate_failure(
            "service_identity",
            {"binding_group": "service_identity_binding", "required": False},
            "required_binding_false",
        )

    def test_no_caller_controlled_invalid_binding_values_leak(self) -> None:
        sentinel = object()
        payload = valid_payload()
        payload["service_call_admission_gate"]["service_identity"] = {
            "binding_group": "service_identity_binding",
            "required": sentinel,
        }

        result = validate_service_call_admission_gate(payload)

        self.assertFalse(contains_identity(result, sentinel))
        self.assertEqual(
            result["gate"]["admission_input"],
            MANIFEST["expected_binding_groups"],
        )
        json.dumps(result, sort_keys=True)


class AuthorityAndDeclarationTests(unittest.TestCase):
    def test_forbidden_implicit_authority_invalid(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["true_declarations"][
            "tag_existence_is_not_authority"
        ] = False

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("forbidden_implicit_authority_invalid", result["failures"])
        self.assertIn("required_declaration_false", result["failures"])

    def test_authorization_flag_invalid(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["false_authority_flags"][
            "service_call_execution_authorized"
        ] = "false"

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("authorization_flag_invalid", result["failures"])
        self.assertEqual(
            result["authority"],
            {flag: False for flag in FALSE_AUTHORITY_FLAGS},
        )

    def test_authorization_flag_true(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["false_authority_flags"][
            "service_call_execution_authorized"
        ] = True

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("authorization_flag_true", result["failures"])
        self.assertIs(result["authority"]["service_call_execution_authorized"], False)

    def test_required_declaration_invalid(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["true_declarations"][
            "spec_only_non_executable"
        ] = "true"

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("required_declaration_invalid", result["failures"])

    def test_required_declaration_false(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["true_declarations"][
            "spec_only_non_executable"
        ] = False

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("required_declaration_false", result["failures"])

    def test_json_safe_invalid(self) -> None:
        payload = valid_payload()
        payload["service_call_admission_gate"]["json_safe"] = False

        result = validate_service_call_admission_gate(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("json_safe_invalid", result["failures"])

    def test_ready_requires_no_failures(self) -> None:
        result = validate_service_call_admission_gate(valid_payload())
        self.assertIs(result[READY_FIELD], result["failures"] == [])
        self.assertEqual(result["reason_code"], "ready")


class DeterminismTests(unittest.TestCase):
    def test_deterministic_first_failure_order(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        gate = payload["service_call_admission_gate"]
        gate["surface"] = "WrongSurface"
        gate["version"] = True
        gate["source_refs"]["read-only-governance-layer-v1"] = "wrong"
        gate["service_identity"] = {
            "binding_group": "wrong_group",
            "required": False,
        }
        gate["false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        gate["true_declarations"]["spec_only_non_executable"] = False
        gate["json_safe"] = False

        result = validate_service_call_admission_gate(payload)

        expected_failures = {
            "payload_shape_mismatch",
            "gate_surface_invalid",
            "gate_version_invalid",
            "source_ref_mismatch",
            "binding_group_invalid",
            "required_binding_false",
            "authorization_flag_true",
            "required_declaration_false",
            "json_safe_invalid",
        }
        self.assertEqual(
            result["failures"],
            [
                failure
                for failure in FAILURE_ORDER
                if failure in expected_failures
            ],
        )
        self.assertEqual(
            result["failures"][0],
            "payload_shape_mismatch",
        )

    def test_no_caller_controlled_invalid_authority_or_declaration_leak(
        self,
    ) -> None:
        auth_sentinel = object()
        declaration_sentinel = object()
        payload = valid_payload()
        payload["service_call_admission_gate"]["false_authority_flags"][
            "service_call_execution_authorized"
        ] = auth_sentinel
        payload["service_call_admission_gate"]["true_declarations"][
            "spec_only_non_executable"
        ] = declaration_sentinel

        result = validate_service_call_admission_gate(payload)

        self.assertFalse(contains_identity(result, auth_sentinel))
        self.assertFalse(contains_identity(result, declaration_sentinel))
        self.assertEqual(
            result["gate"]["required_false_authority_flags"],
            {flag: False for flag in FALSE_AUTHORITY_FLAGS},
        )
        self.assertEqual(
            result["gate"]["required_true_declarations"],
            {declaration: True for declaration in TRUE_DECLARATIONS},
        )
        json.dumps(result, sort_keys=True)


class SourceBoundaryTests(unittest.TestCase):
    def source(self) -> str:
        return inspect.getsource(validator_module)

    def module_imports(self) -> list[tuple[str, tuple[str, ...]]]:
        tree = ast.parse(self.source())
        imports: list[tuple[str, tuple[str, ...]]] = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                imports.append(
                    (
                        node.module or "",
                        tuple(alias.name for alias in node.names),
                    )
                )
            elif isinstance(node, ast.Import):
                imports.append(("", tuple(alias.name for alias in node.names)))
        return imports

    def test_imports_limited_to_mapping_and_deepcopy(self) -> None:
        self.assertEqual(
            self.module_imports(),
            [
                ("collections.abc", ("Mapping",)),
                ("copy", ("deepcopy",)),
            ],
        )

    def test_no_forbidden_runtime_service_db_repository_imports(self) -> None:
        forbidden = {
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
            "kernel.services",
            "services",
            "repositories",
            "unit_of_work",
            "recovery",
            "cli",
        }
        for module, names in self.module_imports():
            joined = ".".join((module, *names)).lower()
            for item in forbidden:
                self.assertNotIn(item.lower(), joined)

    def test_no_forbidden_runtime_calls(self) -> None:
        tree = ast.parse(self.source())
        forbidden_calls = {
            "open",
            "execute",
            "append",
            "commit",
            "rollback",
            "dispatch",
            "seal_revision",
            "close_evidence",
            "render_review",
            "evaluate_barrier",
            "reverify_for_seal",
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in forbidden_calls:
                self.fail(f"forbidden executable call found: {name}")


if __name__ == "__main__":
    unittest.main()
