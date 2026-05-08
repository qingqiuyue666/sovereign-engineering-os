"""Tracer bullets for the runtime authority boundary validator."""

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

import kernel.lifecycle.runtime_authority_checker_enforcer_boundary_validator as validator_module
from kernel.lifecycle.runtime_authority_checker_enforcer_boundary_validator import (
    runtime_authority_checker_enforcer_boundary_validator_manifest,
    validate_runtime_authority_checker_enforcer_boundary,
)


MANIFEST = runtime_authority_checker_enforcer_boundary_validator_manifest()
SOURCE_REFS = MANIFEST["expected_source_refs"]
READINESS_SIGNALS = MANIFEST["expected_readiness_signals"]
BOUNDARY_GROUPS = MANIFEST["expected_boundary_model_groups"]
FALSE_AUTHORITY_FLAGS = tuple(MANIFEST["expected_false_authority_flags"])
TRUE_DECLARATIONS = tuple(MANIFEST["expected_true_declarations"])
FAILURE_ORDER = MANIFEST["failure_taxonomy"]
AUTHORITY_SUMMARY = MANIFEST["authority_summary"]
NON_AUTHORITY = MANIFEST["non_authority_statement"]
INPUT_KEY = "runtime_authority_checker_enforcer_boundary"


class LeakyValue:
    def __repr__(self) -> str:
        return "LEAKY_RUNTIME_OBJECT"


def valid_boundary() -> dict[str, object]:
    boundary: dict[str, object] = {
        "surface": "RuntimeAuthorityCheckerEnforcerBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(SOURCE_REFS),
        "readiness_signals": copy.deepcopy(READINESS_SIGNALS),
    }
    for group, fields in BOUNDARY_GROUPS.items():
        boundary[group] = {field: True for field in fields}
    boundary["required_false_authority_flags"] = {
        flag: False for flag in FALSE_AUTHORITY_FLAGS
    }
    boundary["required_true_declarations"] = {
        declaration: True for declaration in TRUE_DECLARATIONS
    }
    boundary["json_safe"] = True
    return boundary


def valid_payload() -> dict[str, object]:
    return {INPUT_KEY: valid_boundary()}


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
                (
                    "runtime_authority_checker_enforcer_boundary_"
                    "validator_manifest"
                ),
                "validate_runtime_authority_checker_enforcer_boundary",
            ],
        )

    def test_signatures(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    runtime_authority_checker_enforcer_boundary_validator_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    validate_runtime_authority_checker_enforcer_boundary
                ).parameters
            ),
            ["payload"],
        )

    def test_production_import_boundary(self) -> None:
        source = inspect.getsource(validator_module)
        tree = ast.parse(source)
        imports: list[tuple[str, str]] = []
        forbidden_modules = {
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
        for module, _name in imports:
            root = module.split(".")[0]
            self.assertNotIn(root, forbidden_modules)
            self.assertFalse(module.startswith("kernel.services"))
            self.assertFalse(module.startswith("kernel.stores"))
            self.assertFalse(module.startswith("kernel.recovery"))
            self.assertFalse(module.startswith("kernel.lifecycle"))
            self.assertNotIn("repositories", module)
            self.assertNotIn("unit_of_work", module)
            self.assertNotIn("validator", module)
            self.assertNotIn("checker", module)
            self.assertNotIn("ci", module)

    def test_manifest_defensive_copy_and_json_safe(self) -> None:
        manifest = (
            runtime_authority_checker_enforcer_boundary_validator_manifest()
        )
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(manifest["surface"], validator_module._SURFACE)
        self.assertEqual(manifest["version"], 1)
        manifest["expected_source_refs"]["read-only-governance-layer-v1"] = (
            "mutated"
        )
        self.assertEqual(
            runtime_authority_checker_enforcer_boundary_validator_manifest()[
                "expected_source_refs"
            ]["read-only-governance-layer-v1"],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )


class HappyPathTests(unittest.TestCase):
    def test_valid_payload_ready_and_bounded(self) -> None:
        result = validate_runtime_authority_checker_enforcer_boundary(
            valid_payload()
        )

        self.assertEqual(
            set(result),
            {
                "runtime_authority_boundary_ready",
                "reason_code",
                "failures",
                "boundary",
                "authority",
            },
        )
        self.assertIs(result["runtime_authority_boundary_ready"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["authority"], AUTHORITY_SUMMARY)
        self.assertTrue(all(value is False for value in AUTHORITY_SUMMARY.values()))

        boundary = result["boundary"]
        self.assertEqual(
            set(boundary),
            set(MANIFEST["expected_boundary_keys"]),
        )
        self.assertEqual(
            boundary["surface"], "RuntimeAuthorityCheckerEnforcerBoundaryV1"
        )
        self.assertEqual(boundary["version"], 1)
        self.assertEqual(boundary["source_refs"], SOURCE_REFS)
        self.assertEqual(boundary["readiness_signals"], READINESS_SIGNALS)
        self.assertEqual(
            boundary["required_false_authority_flags"],
            {flag: False for flag in FALSE_AUTHORITY_FLAGS},
        )
        self.assertEqual(
            boundary["required_true_declarations"],
            {declaration: True for declaration in TRUE_DECLARATIONS},
        )
        self.assertIs(boundary["json_safe"], True)
        json.dumps(result, sort_keys=True)


class PayloadShapeTests(unittest.TestCase):
    def test_non_mapping_payload(self) -> None:
        result = validate_runtime_authority_checker_enforcer_boundary([])
        self.assertEqual(result["reason_code"], "invalid_runtime_authority_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_wrong_top_level_key(self) -> None:
        result = validate_runtime_authority_checker_enforcer_boundary(
            {"wrong": valid_boundary()}
        )
        self.assertEqual(result["reason_code"], "invalid_runtime_authority_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_extra_top_level_key(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_boundary_not_mapping(self) -> None:
        result = validate_runtime_authority_checker_enforcer_boundary(
            {INPUT_KEY: []}
        )
        self.assertEqual(result["reason_code"], "invalid_runtime_authority_payload")
        self.assertEqual(result["failures"], ["boundary_not_mapping"])

    def test_boundary_missing_key(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["json_safe"]
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["reason_code"], "invalid_runtime_authority_payload")
        self.assertEqual(result["failures"], ["boundary_shape_mismatch"])

    def test_boundary_extra_key(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["extra"] = True
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["boundary_shape_mismatch"])


class SurfaceVersionTests(unittest.TestCase):
    def test_wrong_surface(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["surface"] = "WrongSurface"
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["boundary_surface_invalid"])

    def test_wrong_version(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = 2
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["boundary_version_invalid"])

    def test_bool_as_int_version_rejected(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["version"] = True
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["boundary_version_invalid"])


class SourceRefTests(unittest.TestCase):
    def test_exact_refs_required(self) -> None:
        result = validate_runtime_authority_checker_enforcer_boundary(
            valid_payload()
        )
        self.assertEqual(result["boundary"]["source_refs"], SOURCE_REFS)

    def test_missing_ref_fails(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["source_refs"]["read-only-governance-layer-v1"]
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["source_ref_mismatch"])

    def test_wrong_ref_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"]["read-only-governance-layer-v1"] = (
            "wrong"
        )
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["source_ref_mismatch"])

    def test_extra_ref_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"]["extra"] = "value"
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["source_ref_mismatch"])

    def test_object_valued_refs_do_not_leak(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["source_refs"]["read-only-governance-layer-v1"] = (
            LeakyValue()
        )
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        self.assertEqual(result["boundary"]["source_refs"], SOURCE_REFS)
        assert_json_safe_without_leak(self, result)


class ReadinessSignalTests(unittest.TestCase):
    def test_missing_signal_fails(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["readiness_signals"]["ci_ok"]
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["readiness_signal_invalid"])

    def test_extra_signal_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["readiness_signals"]["extra"] = False
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["readiness_signal_invalid"])

    def test_non_bool_signal_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["readiness_signals"]["ci_ok"] = 0
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["readiness_signal_invalid"])

    def test_true_signal_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["readiness_signals"]["ci_ok"] = True
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["readiness_signal_invalid"])


class BoundaryModelGroupTests(unittest.TestCase):
    def test_each_group_exact_set_required(self) -> None:
        for group, fields in BOUNDARY_GROUPS.items():
            payload = valid_payload()
            del payload[INPUT_KEY][group][fields[0]]
            result = validate_runtime_authority_checker_enforcer_boundary(
                payload
            )
            self.assertEqual(result["failures"], [f"{group}_invalid"])

            payload = valid_payload()
            payload[INPUT_KEY][group]["extra"] = True
            result = validate_runtime_authority_checker_enforcer_boundary(
                payload
            )
            self.assertEqual(result["failures"], [f"{group}_invalid"])

    def test_each_group_rejects_non_bool_and_false(self) -> None:
        for group, fields in BOUNDARY_GROUPS.items():
            payload = valid_payload()
            payload[INPUT_KEY][group][fields[0]] = "yes"
            result = validate_runtime_authority_checker_enforcer_boundary(
                payload
            )
            self.assertEqual(result["failures"], [f"{group}_invalid"])

            payload = valid_payload()
            payload[INPUT_KEY][group][fields[0]] = False
            result = validate_runtime_authority_checker_enforcer_boundary(
                payload
            )
            self.assertEqual(result["failures"], [f"{group}_invalid"])

    def test_object_valued_group_does_not_leak(self) -> None:
        payload = valid_payload()
        first_field = BOUNDARY_GROUPS["checker_boundary"][0]
        payload[INPUT_KEY]["checker_boundary"][first_field] = LeakyValue()
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["checker_boundary_invalid"])
        assert_json_safe_without_leak(self, result)


class FalseAuthorityFlagTests(unittest.TestCase):
    def test_missing_and_extra_flags_fail(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["required_false_authority_flags"][
            FALSE_AUTHORITY_FLAGS[0]
        ]
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["authorization_flag_invalid"])

        payload = valid_payload()
        payload[INPUT_KEY]["required_false_authority_flags"]["extra"] = False
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["authorization_flag_invalid"])

    def test_non_bool_flag_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_false_authority_flags"][
            FALSE_AUTHORITY_FLAGS[0]
        ] = 0
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["authorization_flag_invalid"])

    def test_true_flag_fails_closed_and_output_remains_false(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertTrue(
            all(
                value is False
                for value in result["boundary"][
                    "required_false_authority_flags"
                ].values()
            )
        )


class RequiredTrueDeclarationTests(unittest.TestCase):
    def test_missing_and_extra_declarations_fail(self) -> None:
        payload = valid_payload()
        del payload[INPUT_KEY]["required_true_declarations"][
            TRUE_DECLARATIONS[0]
        ]
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["required_declaration_invalid"])

        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"]["extra"] = True
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["required_declaration_invalid"])

    def test_non_bool_declaration_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"][
            TRUE_DECLARATIONS[0]
        ] = 1
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["required_declaration_invalid"])

    def test_false_declaration_fails(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["required_true_declarations"][
            "service_calls_forbidden"
        ] = False
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(result["failures"], ["required_declaration_false"])


class JsonSafetyTests(unittest.TestCase):
    def test_json_safe_must_be_exactly_true(self) -> None:
        for value in (False, "true", 1, None):
            payload = valid_payload()
            payload[INPUT_KEY]["json_safe"] = value
            result = validate_runtime_authority_checker_enforcer_boundary(
                payload
            )
            self.assertEqual(result["failures"], ["json_safe_invalid"])


class DeterminismAndSafetyTests(unittest.TestCase):
    def test_deterministic_failure_ordering(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["json_safe"] = False
        payload[INPUT_KEY]["surface"] = "WrongSurface"
        payload[INPUT_KEY]["source_refs"]["read-only-governance-layer-v1"] = (
            "wrong"
        )
        payload[INPUT_KEY]["required_false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(
            result["failures"],
            [
                "boundary_surface_invalid",
                "source_ref_mismatch",
                "authorization_flag_true",
                "json_safe_invalid",
            ],
        )
        self.assertEqual(
            result["failures"],
            [
                failure
                for failure in FAILURE_ORDER
                if failure in result["failures"]
            ],
        )

    def test_input_not_mutated(self) -> None:
        payload = valid_payload()
        original = copy.deepcopy(payload)
        validate_runtime_authority_checker_enforcer_boundary(payload)
        self.assertEqual(payload, original)

    def test_result_does_not_leak_raw_object_identity(self) -> None:
        payload = valid_payload()
        payload[INPUT_KEY]["authority_input_model"]["source_bound"] = (
            LeakyValue()
        )
        result = validate_runtime_authority_checker_enforcer_boundary(payload)
        assert_json_safe_without_leak(self, result)


class NonAuthoritySemanticsTests(unittest.TestCase):
    def test_ready_authorizes_nothing_runtime_or_side_effecting(self) -> None:
        result = validate_runtime_authority_checker_enforcer_boundary(
            valid_payload()
        )
        self.assertIs(result["runtime_authority_boundary_ready"], True)

        authority = result["authority"]
        for flag, value in authority.items():
            with self.subTest(flag=flag):
                self.assertIs(value, False)

        self.assertIs(
            authority["runtime_authority_checker_authorized"], False
        )
        self.assertIs(
            authority["runtime_authority_enforcer_authorized"], False
        )
        self.assertIs(
            authority["runtime_authority_runtime_authorized"], False
        )
        self.assertIs(authority["service_call_execution_authorized"], False)
        self.assertIs(authority["evidence_append_authorized"], False)
        self.assertIs(authority["audit_append_authorized"], False)
        self.assertIs(authority["repository_uow_writes_authorized"], False)
        self.assertIs(authority["transaction_runtime_authorized"], False)
        self.assertIs(
            authority["idempotency_reservation_authorized"], False
        )
        self.assertIs(authority["rollback_runtime_authorized"], False)
        self.assertIs(
            authority["executor_service_dispatch_authorized"], False
        )
        self.assertIs(authority["durable_writes_authorized"], False)
        self.assertIs(authority["irreversible_action_authorized"], False)

    def test_manifest_non_authority_statement(self) -> None:
        self.assertEqual(
            NON_AUTHORITY[
                "runtime_authority_boundary_ready_proves"
            ],
            "structural_declaration_validity_only",
        )
        for key, value in NON_AUTHORITY.items():
            if key.endswith("_authorizes_runtime"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_service_calls"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_evidence_append"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_audit_append"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_repository_uow_writes"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_transaction_runtime"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_idempotency"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_rollback"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_executor_dispatch"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_durable_writes"):
                self.assertIs(value, False)
            if key.endswith("_authorizes_irreversible_actions"):
                self.assertIs(value, False)


if __name__ == "__main__":
    unittest.main()
