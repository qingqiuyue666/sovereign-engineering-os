"""Tracer bullets for the runtime authority grant object validator."""

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

import kernel.lifecycle.runtime_authority_grant_object_validator as validator_module
from kernel.lifecycle.runtime_authority_grant_object_validator import (
    runtime_authority_grant_object_validator_manifest,
    validate_runtime_authority_grant_object,
)


MANIFEST = runtime_authority_grant_object_validator_manifest()
SOURCE_REFS = MANIFEST["expected_source_refs"]
GRANT_OBJECT_KEYS = tuple(MANIFEST["expected_grant_object_keys"])
AUTHORITY_REF_FIELDS = tuple(MANIFEST["expected_authority_ref_fields"])
OBJECT_MODEL_FIELDS = tuple(MANIFEST["expected_object_model_fields"])
BINDING_MODEL_FIELDS = tuple(MANIFEST["expected_binding_model_fields"])
FALSE_AUTHORITY_FLAGS = tuple(MANIFEST["required_false_authority_flags"])
TRUE_DECLARATIONS = tuple(MANIFEST["required_true_declarations"])
FAILURE_ORDER = MANIFEST["failure_taxonomy"]
AUTHORITY_SUMMARY = MANIFEST["authority_summary"]
INPUT_KEY = "runtime_authority_grant_object"


class LeakyValue:
    def __repr__(self) -> str:
        return "LEAKY_RUNTIME_OBJECT"


def safe_ref(name: str) -> str:
    return f"ref:{name}"


def safe_model(name: str) -> dict[str, object]:
    return {
        "binding_id": safe_ref(name),
        "source_bound": True,
        "operation_bound": True,
        "notes": [name, "declaration_only"],
    }


def valid_authority_ref() -> dict[str, object]:
    return {
        field: safe_ref(field)
        for field in AUTHORITY_REF_FIELDS
    }


def valid_grant_object() -> dict[str, object]:
    grant: dict[str, object] = {
        "surface": "RuntimeAuthorityGrantObjectV1",
        "version": 1,
        "source_refs": copy.deepcopy(SOURCE_REFS),
        "authority_grant_id": "grant:runtime-authority-grant-object-v1",
        "authority_ref": valid_authority_ref(),
        "required_false_authority_flags": {
            flag: False for flag in FALSE_AUTHORITY_FLAGS
        },
        "required_true_declarations": {
            declaration: True for declaration in TRUE_DECLARATIONS
        },
        "json_safe": True,
    }
    for field in OBJECT_MODEL_FIELDS:
        grant[field] = safe_model(field)
    for field in BINDING_MODEL_FIELDS:
        grant[field] = safe_model(field)
    return grant


def valid_payload() -> dict[str, object]:
    return {INPUT_KEY: valid_grant_object()}


def assert_json_safe_without_leak(
    testcase: unittest.TestCase,
    result: dict[str, object],
) -> None:
    encoded = json.dumps(result, sort_keys=True)
    testcase.assertNotIn("LEAKY_RUNTIME_OBJECT", encoded)


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            validator_module.__all__,
            [
                "runtime_authority_grant_object_validator_manifest",
                "validate_runtime_authority_grant_object",
            ],
        )

    def test_signatures_are_exact(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    runtime_authority_grant_object_validator_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    validate_runtime_authority_grant_object
                ).parameters
            ),
            ["payload"],
        )

    def test_imports_limited_to_mapping_and_deepcopy(self) -> None:
        tree = ast.parse(inspect.getsource(validator_module))
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
        manifest = runtime_authority_grant_object_validator_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(manifest["surface"], "runtime_authority_grant_object_validator")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["contract_name"], "RuntimeAuthorityGrantObjectV1")
        self.assertEqual(
            manifest["public_api"],
            [
                "runtime_authority_grant_object_validator_manifest",
                "validate_runtime_authority_grant_object",
            ],
        )
        self.assertEqual(
            manifest["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )
        manifest["expected_source_refs"]["read-only-governance-layer-v1"] = (
            "mutated"
        )
        self.assertEqual(
            runtime_authority_grant_object_validator_manifest()[
                "expected_source_refs"
            ]["read-only-governance-layer-v1"],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )


class HappyPathTests(unittest.TestCase):
    def test_happy_path_ready(self) -> None:
        result = validate_runtime_authority_grant_object(valid_payload())

        self.assertEqual(
            set(result),
            {
                "runtime_authority_grant_object_ready",
                "reason_code",
                "failures",
                "contract",
                "authority_grant_object",
                "authority",
                "json_safe",
            },
        )
        self.assertIs(result["runtime_authority_grant_object_ready"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["json_safe"], True)
        self.assertEqual(result["authority"], AUTHORITY_SUMMARY)
        self.assertTrue(all(value is False for value in result["authority"].values()))

        summary = result["authority_grant_object"]
        self.assertEqual(summary["surface"], "RuntimeAuthorityGrantObjectV1")
        self.assertEqual(summary["version"], 1)
        self.assertEqual(summary["source_refs"], SOURCE_REFS)
        self.assertEqual(summary["object_fields"], list(GRANT_OBJECT_KEYS))
        self.assertEqual(
            summary["authority_ref_fields"],
            list(AUTHORITY_REF_FIELDS),
        )
        self.assertTrue(
            all(
                value is False
                for value in summary["required_false_authority_flags"].values()
            )
        )
        self.assertTrue(
            all(
                value is True
                for value in summary["required_true_declarations"].values()
            )
        )
        json.dumps(result, sort_keys=True)

    def test_input_immutability(self) -> None:
        payload = valid_payload()
        before = copy.deepcopy(payload)
        validate_runtime_authority_grant_object(payload)
        self.assertEqual(payload, before)

    def test_ready_authorizes_no_runtime_or_side_effects(self) -> None:
        result = validate_runtime_authority_grant_object(valid_payload())
        self.assertIs(result["runtime_authority_grant_object_ready"], True)
        authority = result["authority"]
        for flag in (
            "runtime_authority_grant_runtime_authorized",
            "runtime_authority_ref_runtime_authorized",
            "runtime_authority_checker_authorized",
            "runtime_authority_enforcer_authorized",
            "runtime_authority_runtime_authorized",
            "service_call_execution_authorized",
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
        non_authority = result["contract"]["non_authority_summary"]
        self.assertEqual(
            non_authority["runtime_authority_grant_object_ready_proves"],
            "structural_declaration_validity_only",
        )
        self.assertIs(
            non_authority[
                "runtime_authority_grant_object_ready_authorizes_runtime"
            ],
            False,
        )


class PayloadShapeTests(unittest.TestCase):
    def test_payload_not_mapping(self) -> None:
        result = validate_runtime_authority_grant_object([])
        self.assertEqual(result["reason_code"], "invalid_runtime_authority_grant_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_top_level_shape_mismatch(self) -> None:
        result = validate_runtime_authority_grant_object(
            {"wrong": valid_grant_object()}
        )
        self.assertEqual(result["reason_code"], "invalid_runtime_authority_grant_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_grant_object_not_mapping(self) -> None:
        result = validate_runtime_authority_grant_object({INPUT_KEY: []})
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["grant_object_not_mapping"])

    def test_grant_object_shape_mismatch(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["authority_ref"]
        result = validate_runtime_authority_grant_object(payload)
        self.assertIn("grant_object_shape_mismatch", result["failures"])
        self.assertIn("authority_ref_invalid", result["failures"])


class SurfaceVersionSourceTests(unittest.TestCase):
    def test_surface_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["surface"] = "WrongSurface"
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["surface_invalid"])

    def test_version_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = 2
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["version_invalid"])

    def test_bool_as_int_version_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = True
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["version_invalid"])

    def test_source_refs_exact(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"][
            "runtime-authority-grant-object-spec-only-v1"
        ] = "wrong"
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["source_refs_invalid"])

    def test_invalid_source_refs_object_does_not_leak(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"] = {
            "read-only-governance-layer-v1": LeakyValue()
        }
        result = validate_runtime_authority_grant_object(payload)
        self.assertIn("source_refs_invalid", result["failures"])
        self.assertIn("json_safe_invalid", result["failures"])
        assert_json_safe_without_leak(self, result)


class AuthorityRefTests(unittest.TestCase):
    def test_authority_ref_not_mapping(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["authority_ref"] = []
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["authority_ref_invalid"])

    def test_authority_ref_shape_mismatch(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["authority_ref"]["authority_ref_id"]
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["authority_ref_invalid"])

    def test_authority_ref_invalid_nested_object_does_not_leak(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["authority_ref"]["source_ref"] = LeakyValue()
        result = validate_runtime_authority_grant_object(payload)
        self.assertIn("authority_ref_invalid", result["failures"])
        self.assertIn("json_safe_invalid", result["failures"])
        assert_json_safe_without_leak(self, result)


class ModelDeclarationTests(unittest.TestCase):
    def test_object_model_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["authority_subject"] = []
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["object_model_invalid"])

    def test_binding_model_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["operation_binding"] = []
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["binding_model_invalid"])

    def test_non_authority_model_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"][
            "readiness_is_not_authority"
        ] = False
        result = validate_runtime_authority_grant_object(payload)
        self.assertIn("non_authority_model_invalid", result["failures"])
        self.assertIn("required_true_declarations_invalid", result["failures"])

    def test_forbidden_implicit_authority_invalid(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"][
            "implicit_authority_escalation_forbidden"
        ] = False
        result = validate_runtime_authority_grant_object(payload)
        self.assertIn(
            "forbidden_implicit_authority_invalid",
            result["failures"],
        )
        self.assertIn("required_true_declarations_invalid", result["failures"])


class AuthorityFlagTests(unittest.TestCase):
    def test_required_false_flag_missing(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["required_false_authority_flags"][
            "runtime_authority_grant_runtime_authorized"
        ]
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(
            result["failures"],
            ["required_false_authority_flags_invalid"],
        )

    def test_required_false_flag_non_bool(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_false_authority_flags"][
            "runtime_authority_grant_runtime_authorized"
        ] = "false"
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(
            result["failures"],
            ["required_false_authority_flags_invalid"],
        )

    def test_required_false_flag_true_fails_closed(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_false_authority_flags"][
            "runtime_authority_grant_runtime_authorized"
        ] = True
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertIs(
            result["authority"]["runtime_authority_grant_runtime_authorized"],
            False,
        )


class TrueDeclarationTests(unittest.TestCase):
    def test_required_true_declaration_missing(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["required_true_declarations"][
            "spec_only_non_executable"
        ]
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(
            result["failures"],
            ["required_true_declarations_invalid"],
        )

    def test_required_true_declaration_non_bool(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"][
            "spec_only_non_executable"
        ] = "true"
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(
            result["failures"],
            ["required_true_declarations_invalid"],
        )

    def test_required_true_declaration_false(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"][
            "spec_only_non_executable"
        ] = False
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(
            result["failures"],
            ["required_true_declarations_invalid"],
        )


class JsonSafetyTests(unittest.TestCase):
    def test_json_safe_missing(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["json_safe"]
        result = validate_runtime_authority_grant_object(payload)
        self.assertIn("grant_object_shape_mismatch", result["failures"])
        self.assertIn("json_safe_invalid", result["failures"])

    def test_json_safe_false(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["json_safe"] = False
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_json_safe_non_bool(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["json_safe"] = "true"
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_bounded_output_on_failure_paths(self) -> None:
        invalid_payloads = [
            [],
            {"wrong": valid_grant_object()},
            {INPUT_KEY: []},
            {INPUT_KEY: {**valid_grant_object(), "source_refs": LeakyValue()}},
        ]
        for payload in invalid_payloads:
            result = validate_runtime_authority_grant_object(payload)
            self.assertEqual(
                set(result),
                {
                    "runtime_authority_grant_object_ready",
                    "reason_code",
                    "failures",
                    "contract",
                    "authority_grant_object",
                    "authority",
                    "json_safe",
                },
            )
            self.assertIs(result["runtime_authority_grant_object_ready"], False)
            self.assertIs(result["json_safe"], True)
            assert_json_safe_without_leak(self, result)


class DeterminismTests(unittest.TestCase):
    def test_deterministic_failure_ordering(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["surface"] = "WrongSurface"
        payload[INPUT_KEY]["version"] = True
        payload[INPUT_KEY]["source_refs"] = {}
        payload[INPUT_KEY]["authority_ref"] = []
        payload[INPUT_KEY]["required_false_authority_flags"][
            "runtime_authority_grant_runtime_authorized"
        ] = True
        payload[INPUT_KEY]["json_safe"] = False
        result = validate_runtime_authority_grant_object(payload)
        self.assertEqual(
            result["failures"],
            [
                failure
                for failure in FAILURE_ORDER
                if failure
                in {
                    "surface_invalid",
                    "version_invalid",
                    "source_refs_invalid",
                    "authority_ref_invalid",
                    "authorization_flag_true",
                    "json_safe_invalid",
                }
            ],
        )


class SourceBoundaryTests(unittest.TestCase):
    def test_no_forbidden_production_imports_or_coupling(self) -> None:
        tree = ast.parse(inspect.getsource(validator_module))
        forbidden_roots = {
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
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    self.assertNotIn(root, forbidden_roots)
                    self.assertNotIn("services", alias.name)
                    self.assertNotIn("repositories", alias.name)
                    self.assertNotIn("unit_of_work", alias.name)
                    self.assertNotIn("validator", alias.name)
                    self.assertNotIn("checker", alias.name)
                    self.assertNotIn("ci", alias.name)
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".")[0]
                self.assertNotIn(root, forbidden_roots)
                self.assertFalse(module.startswith("kernel.services"))
                self.assertFalse(module.startswith("kernel.stores"))
                self.assertFalse(module.startswith("kernel.recovery"))
                self.assertFalse(module.startswith("kernel.lifecycle"))
                self.assertNotIn("repositories", module)
                self.assertNotIn("unit_of_work", module)
                self.assertNotIn("validator", module)
                self.assertNotIn("checker", module)
                self.assertNotIn("ci", module)

    def test_no_wall_clock_digest_or_runtime_introspection_imports(self) -> None:
        imports = []
        tree = ast.parse(inspect.getsource(validator_module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        imported_text = " ".join(imports)
        for forbidden in (
            "datetime",
            "time",
            "hashlib",
            "hmac",
            "secrets",
            "inspect",
            "importlib",
            "subprocess",
            "sqlite3",
        ):
            self.assertNotIn(forbidden, imported_text)


if __name__ == "__main__":
    unittest.main()
