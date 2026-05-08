"""Tracer bullets for the service call execution boundary validator."""

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

import kernel.lifecycle.service_call_execution_boundary_validator as validator_module
from kernel.lifecycle.service_call_execution_boundary_validator import (
    service_call_execution_boundary_validator_manifest,
    validate_service_call_execution_boundary,
)


MANIFEST = service_call_execution_boundary_validator_manifest()
SOURCE_REFS = MANIFEST["expected_source_refs"]
DECLARATION_GROUPS = MANIFEST["expected_declaration_groups"]
FALSE_AUTHORITY_FLAGS = tuple(MANIFEST["required_false_authority_flags"])
TRUE_DECLARATIONS = tuple(MANIFEST["required_true_declarations"])
FAILURE_ORDER = MANIFEST["failure_taxonomy"]
READY_FIELD = "service_call_execution_boundary_ready"


def valid_boundary() -> dict[str, object]:
    boundary: dict[str, object] = {
        "surface": "ServiceCallExecutionBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(SOURCE_REFS),
    }
    for group, declarations in DECLARATION_GROUPS.items():
        boundary[group] = {name: True for name in declarations}
    boundary["required_false_authority_flags"] = {
        flag: False for flag in FALSE_AUTHORITY_FLAGS
    }
    boundary["required_true_declarations"] = {
        declaration: True for declaration in TRUE_DECLARATIONS
    }
    boundary["json_safe"] = True
    return boundary


def valid_payload() -> dict[str, object]:
    return {"service_call_execution_boundary": valid_boundary()}


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            validator_module.__all__,
            [
                "service_call_execution_boundary_validator_manifest",
                "validate_service_call_execution_boundary",
            ],
        )

    def test_signatures(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    service_call_execution_boundary_validator_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    validate_service_call_execution_boundary
                ).parameters
            ),
            ["payload"],
        )

    def test_manifest_exact_shape_and_defensive_copy(self) -> None:
        manifest = service_call_execution_boundary_validator_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(
            set(manifest),
            {
                "surface",
                "version",
                "input_shape",
                "expected_top_level_keys",
                "expected_boundary_keys",
                "expected_source_refs",
                "expected_declaration_groups",
                "required_false_authority_flags",
                "required_true_declarations",
                "failure_taxonomy",
                "authority_summary_flags",
                "non_authority",
                "reason_codes",
                "json_safe",
            },
        )
        self.assertEqual(
            manifest["surface"], "service_call_execution_boundary_validator"
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["expected_top_level_keys"],
            ["service_call_execution_boundary"],
        )
        manifest["expected_source_refs"]["read-only-governance-layer-v1"] = (
            "mutated"
        )
        self.assertEqual(
            service_call_execution_boundary_validator_manifest()[
                "expected_source_refs"
            ]["read-only-governance-layer-v1"],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )


class HappyPathTests(unittest.TestCase):
    def test_happy_path_ready(self) -> None:
        result = validate_service_call_execution_boundary(valid_payload())

        self.assertEqual(
            set(result),
            {
                READY_FIELD,
                "reason_code",
                "failures",
                "boundary",
            },
        )
        self.assertIs(result[READY_FIELD], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])

        boundary = result["boundary"]
        self.assertEqual(
            set(boundary),
            {
                "surface",
                "version",
                "source_refs",
                "declaration_groups",
                "required_false_authority_flags",
                "required_true_declarations",
                "json_safe",
                "authority",
            },
        )
        self.assertEqual(
            boundary["surface"], "service_call_execution_boundary_validator"
        )
        self.assertEqual(boundary["version"], 1)
        self.assertEqual(boundary["source_refs"], SOURCE_REFS)
        self.assertEqual(
            boundary["declaration_groups"],
            {
                group: {name: True for name in declarations}
                for group, declarations in DECLARATION_GROUPS.items()
            },
        )
        self.assertEqual(
            boundary["required_false_authority_flags"],
            {flag: False for flag in FALSE_AUTHORITY_FLAGS},
        )
        self.assertEqual(
            boundary["required_true_declarations"],
            {name: True for name in TRUE_DECLARATIONS},
        )
        self.assertIs(boundary["json_safe"], True)

    def test_ready_grants_no_authority(self) -> None:
        result = validate_service_call_execution_boundary(valid_payload())
        boundary = result["boundary"]

        for flag in boundary["authority"].values():
            self.assertIs(flag, False)
        for flag in boundary["required_false_authority_flags"].values():
            self.assertIs(flag, False)

        self.assertIs(
            boundary["authority"]["service_call_execution_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["service_adapter_runtime_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["service_method_call_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["evidence_append_authorized"], False
        )
        self.assertIs(boundary["authority"]["audit_append_authorized"], False)
        self.assertIs(
            boundary["authority"]["repository_uow_writes_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["transaction_runtime_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["idempotency_reservation_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["rollback_runtime_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["runtime_checker_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["runtime_enforcer_authorized"], False
        )
        self.assertIs(
            boundary["authority"]["executor_implementation_authorized"], False
        )
        self.assertIs(boundary["authority"]["durable_writes_authorized"], False)
        self.assertIs(
            boundary["authority"]["irreversible_action_authorized"], False
        )


class PayloadAndBoundaryShapeTests(unittest.TestCase):
    def assert_failure(
        self,
        payload: object,
        failure: str,
        reason: str | None = None,
    ) -> dict[str, object]:
        result = validate_service_call_execution_boundary(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn(failure, result["failures"])
        if reason is not None:
            self.assertEqual(result["reason_code"], reason)
        return result

    def test_payload_not_mapping(self) -> None:
        result = self.assert_failure(
            [],
            "payload_not_mapping",
            "invalid_service_call_execution_boundary_payload",
        )
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_top_level_key_mismatch(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        self.assert_failure(
            payload,
            "payload_shape_mismatch",
            "invalid_service_call_execution_boundary_payload",
        )

        self.assert_failure(
            {},
            "payload_shape_mismatch",
            "invalid_service_call_execution_boundary_payload",
        )

    def test_boundary_not_mapping(self) -> None:
        self.assert_failure(
            {"service_call_execution_boundary": []},
            "boundary_not_mapping",
            "invalid_service_call_execution_boundary_payload",
        )

    def test_boundary_key_mismatch(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["extra"] = True
        self.assert_failure(
            payload,
            "boundary_shape_mismatch",
            "invalid_service_call_execution_boundary_payload",
        )

    def test_invalid_surface(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["surface"] = (
            "WrongSurface"
        )
        self.assert_failure(
            payload,
            "boundary_surface_invalid",
            "invalid_service_call_execution_boundary_payload",
        )

    def test_invalid_version(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["version"] = 2
        self.assert_failure(
            payload,
            "boundary_version_invalid",
            "invalid_service_call_execution_boundary_payload",
        )

    def test_bool_as_int_version_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["version"] = True
        self.assert_failure(
            payload,
            "boundary_version_invalid",
            "invalid_service_call_execution_boundary_payload",
        )


class SourceRefTests(unittest.TestCase):
    def contains_identity(self, value: object, target: object) -> bool:
        if value is target:
            return True
        if isinstance(value, dict):
            return any(
                self.contains_identity(key, target)
                or self.contains_identity(item, target)
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple)):
            return any(self.contains_identity(item, target) for item in value)
        return False

    def assert_source_failure(self, source_refs: object) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["source_refs"] = source_refs
        result = validate_service_call_execution_boundary(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        self.assertEqual(result["boundary"]["source_refs"], SOURCE_REFS)
        json.dumps(result, sort_keys=True)

    def test_source_ref_mismatch(self) -> None:
        source_refs = copy.deepcopy(SOURCE_REFS)
        source_refs["read-only-governance-layer-v1"] = "wrong"
        self.assert_source_failure(source_refs)

    def test_source_refs_extra_missing_rejected(self) -> None:
        source_refs = copy.deepcopy(SOURCE_REFS)
        source_refs["extra"] = "value"
        self.assert_source_failure(source_refs)

        source_refs = copy.deepcopy(SOURCE_REFS)
        del source_refs["read-only-governance-layer-v1"]
        self.assert_source_failure(source_refs)

    def test_source_refs_non_mapping_rejected(self) -> None:
        self.assert_source_failure([])

    def test_source_refs_object_value_is_not_echoed(self) -> None:
        sentinel = object()
        payload = valid_payload()
        payload["service_call_execution_boundary"]["source_refs"][
            "read-only-governance-layer-v1"
        ] = sentinel

        result = validate_service_call_execution_boundary(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])
        self.assertEqual(result["boundary"]["source_refs"], SOURCE_REFS)
        self.assertFalse(self.contains_identity(result, sentinel))
        self.assertIs(
            payload["service_call_execution_boundary"]["source_refs"][
                "read-only-governance-layer-v1"
            ],
            sentinel,
        )
        json.dumps(result, sort_keys=True)


class DeclarationGroupTests(unittest.TestCase):
    def assert_declaration_failure(
        self,
        payload: dict[str, object],
        failure: str,
    ) -> dict[str, object]:
        result = validate_service_call_execution_boundary(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn(failure, result["failures"])
        return result

    def test_every_declaration_group_missing_or_extra_rejected(self) -> None:
        for group in DECLARATION_GROUPS:
            with self.subTest(group=group, case="missing group"):
                payload = valid_payload()
                del payload["service_call_execution_boundary"][group]
                self.assert_declaration_failure(
                    payload, "declaration_group_invalid"
                )

            with self.subTest(group=group, case="extra declaration"):
                payload = valid_payload()
                payload["service_call_execution_boundary"][group][
                    "extra_declaration"
                ] = True
                self.assert_declaration_failure(
                    payload, "declaration_group_invalid"
                )

    def test_declaration_group_non_mapping_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"][
            "service_call_attempt_boundary"
        ] = []
        self.assert_declaration_failure(payload, "declaration_group_invalid")

    def test_required_declaration_missing_rejected(self) -> None:
        payload = valid_payload()
        del payload["service_call_execution_boundary"][
            "service_call_attempt_boundary"
        ]["exact_service_identity_required"]
        result = self.assert_declaration_failure(
            payload, "required_declaration_invalid"
        )
        self.assertIn("declaration_group_invalid", result["failures"])

    def test_required_declaration_non_bool_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"][
            "service_call_attempt_boundary"
        ]["exact_service_identity_required"] = "true"
        self.assert_declaration_failure(
            payload, "required_declaration_invalid"
        )

    def test_required_declaration_false_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"][
            "service_call_attempt_boundary"
        ]["exact_service_identity_required"] = False
        self.assert_declaration_failure(payload, "required_declaration_false")


class AuthorityFlagTests(unittest.TestCase):
    def assert_authority_failure(
        self,
        payload: dict[str, object],
        failure: str,
    ) -> None:
        result = validate_service_call_execution_boundary(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn(failure, result["failures"])
        for flag in result["boundary"]["authority"].values():
            self.assertIs(flag, False)
        for flag in result["boundary"][
            "required_false_authority_flags"
        ].values():
            self.assertIs(flag, False)

    def test_required_false_authority_flags_missing_rejected(self) -> None:
        for flag in FALSE_AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                payload = valid_payload()
                del payload["service_call_execution_boundary"][
                    "required_false_authority_flags"
                ][flag]
                self.assert_authority_failure(
                    payload, "authorization_flag_invalid"
                )

    def test_required_false_authority_flags_non_bool_rejected(self) -> None:
        for flag in FALSE_AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                payload = valid_payload()
                payload["service_call_execution_boundary"][
                    "required_false_authority_flags"
                ][flag] = "false"
                self.assert_authority_failure(
                    payload, "authorization_flag_invalid"
                )

    def test_required_false_authority_flag_true_rejected(self) -> None:
        for flag in FALSE_AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                payload = valid_payload()
                payload["service_call_execution_boundary"][
                    "required_false_authority_flags"
                ][flag] = True
                self.assert_authority_failure(
                    payload, "authorization_flag_true"
                )

    def test_required_false_authority_map_shape_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"][
            "required_false_authority_flags"
        ]["extra"] = False
        self.assert_authority_failure(payload, "authorization_flag_invalid")


class RequiredTrueDeclarationTests(unittest.TestCase):
    def assert_required_true_failure(
        self,
        payload: dict[str, object],
        failure: str,
    ) -> None:
        result = validate_service_call_execution_boundary(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn(failure, result["failures"])

    def test_required_true_declaration_missing_rejected(self) -> None:
        for declaration in TRUE_DECLARATIONS:
            with self.subTest(declaration=declaration):
                payload = valid_payload()
                del payload["service_call_execution_boundary"][
                    "required_true_declarations"
                ][declaration]
                self.assert_required_true_failure(
                    payload, "required_declaration_invalid"
                )

    def test_required_true_declaration_non_bool_rejected(self) -> None:
        for declaration in TRUE_DECLARATIONS:
            with self.subTest(declaration=declaration):
                payload = valid_payload()
                payload["service_call_execution_boundary"][
                    "required_true_declarations"
                ][declaration] = "true"
                self.assert_required_true_failure(
                    payload, "required_declaration_invalid"
                )

    def test_required_true_declaration_false_rejected(self) -> None:
        for declaration in TRUE_DECLARATIONS:
            with self.subTest(declaration=declaration):
                payload = valid_payload()
                payload["service_call_execution_boundary"][
                    "required_true_declarations"
                ][declaration] = False
                self.assert_required_true_failure(
                    payload, "required_declaration_false"
                )

    def test_required_true_declaration_map_shape_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"][
            "required_true_declarations"
        ]["extra"] = True
        self.assert_required_true_failure(
            payload, "required_declaration_invalid"
        )


class JsonSafetyTests(unittest.TestCase):
    def assert_json_safe_failure(self, payload: dict[str, object]) -> None:
        result = validate_service_call_execution_boundary(payload)
        self.assertIs(result[READY_FIELD], False)
        self.assertIn("json_safe_invalid", result["failures"])

    def test_json_safe_missing_rejected(self) -> None:
        payload = valid_payload()
        del payload["service_call_execution_boundary"]["json_safe"]
        self.assert_json_safe_failure(payload)

    def test_json_safe_false_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["json_safe"] = False
        self.assert_json_safe_failure(payload)

    def test_json_safe_non_bool_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary"]["json_safe"] = "true"
        self.assert_json_safe_failure(payload)

    def test_output_is_json_safe(self) -> None:
        result = validate_service_call_execution_boundary(valid_payload())
        json.dumps(result, sort_keys=True)


class SafetyAndDeterminismTests(unittest.TestCase):
    def contains_identity(self, value: object, target: object) -> bool:
        if value is target:
            return True
        if isinstance(value, dict):
            return any(
                self.contains_identity(key, target)
                or self.contains_identity(item, target)
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple)):
            return any(self.contains_identity(item, target) for item in value)
        return False

    def test_deterministic_failure_ordering(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        boundary = payload["service_call_execution_boundary"]
        boundary["surface"] = "WrongSurface"
        boundary["version"] = True
        boundary["source_refs"]["read-only-governance-layer-v1"] = "wrong"
        boundary["service_call_attempt_boundary"][
            "exact_service_identity_required"
        ] = False
        boundary["required_false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        boundary["json_safe"] = False

        result = validate_service_call_execution_boundary(payload)

        self.assertEqual(
            result["failures"],
            [
                failure
                for failure in FAILURE_ORDER
                if failure
                in {
                    "payload_shape_mismatch",
                    "boundary_surface_invalid",
                    "boundary_version_invalid",
                    "source_ref_mismatch",
                    "required_declaration_false",
                    "authorization_flag_true",
                    "json_safe_invalid",
                }
            ],
        )

    def test_input_not_mutated(self) -> None:
        payload = valid_payload()
        original = copy.deepcopy(payload)
        validate_service_call_execution_boundary(payload)
        self.assertEqual(payload, original)

    def test_output_does_not_leak_raw_input_objects(self) -> None:
        payload = valid_payload()
        result = validate_service_call_execution_boundary(payload)
        payload["service_call_execution_boundary"]["source_refs"][
            "read-only-governance-layer-v1"
        ] = "mutated"
        payload["service_call_execution_boundary"][
            "service_call_attempt_boundary"
        ]["exact_service_identity_required"] = False

        self.assertEqual(
            result["boundary"]["source_refs"][
                "read-only-governance-layer-v1"
            ],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )
        self.assertIs(
            result["boundary"]["declaration_groups"][
                "service_call_attempt_boundary"
            ]["exact_service_identity_required"],
            True,
        )

    def test_invalid_adjacent_mapping_values_do_not_leak(self) -> None:
        declaration_object = object()
        false_authority_object = object()
        true_declaration_object = object()
        extra_object = object()
        payload = valid_payload()
        boundary = payload["service_call_execution_boundary"]
        boundary["service_call_attempt_boundary"][
            "exact_service_identity_required"
        ] = declaration_object
        boundary["service_call_attempt_boundary"]["extra"] = extra_object
        boundary["required_false_authority_flags"][
            "service_call_execution_authorized"
        ] = false_authority_object
        boundary["required_false_authority_flags"]["extra"] = extra_object
        boundary["required_true_declarations"][
            "spec_only_non_executable"
        ] = true_declaration_object
        boundary["required_true_declarations"]["extra"] = extra_object

        result = validate_service_call_execution_boundary(payload)

        self.assertIs(result[READY_FIELD], False)
        self.assertIn("declaration_group_invalid", result["failures"])
        self.assertIn("required_declaration_invalid", result["failures"])
        self.assertIn("authorization_flag_invalid", result["failures"])
        for sentinel in (
            declaration_object,
            false_authority_object,
            true_declaration_object,
            extra_object,
        ):
            self.assertFalse(self.contains_identity(result, sentinel))
        self.assertIs(
            payload["service_call_execution_boundary"][
                "service_call_attempt_boundary"
            ]["exact_service_identity_required"],
            declaration_object,
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

    def test_production_import_boundary(self) -> None:
        self.assertEqual(
            self.module_imports(),
            [
                ("collections.abc", ("Mapping",)),
                ("copy", ("deepcopy",)),
            ],
        )

    def test_no_services_imports(self) -> None:
        for module, names in self.module_imports():
            joined = ".".join((module, *names))
            self.assertNotIn("kernel.services", joined)
            self.assertNotIn(".services", joined)

    def test_no_db_sqlite_repository_uow_imports(self) -> None:
        forbidden = (
            "sqlite3",
            "kernel.stores.sqlite",
            "repositories",
            "unit_of_work",
        )
        for module, names in self.module_imports():
            joined = ".".join((module, *names))
            for item in forbidden:
                self.assertNotIn(item, joined)

    def test_no_recovery_cli_or_upstream_validator_imports(self) -> None:
        forbidden = (
            "recovery",
            "cli",
            "validator_ci",
            "validator",
            "checker",
            "consumer",
        )
        for module, names in self.module_imports():
            joined = ".".join((module, *names))
            for item in forbidden:
                self.assertNotIn(item, joined.lower())

    def test_no_runtime_utility_imports(self) -> None:
        forbidden = {
            "datetime",
            "time",
            "os",
            "pathlib",
            "subprocess",
            "threading",
            "asyncio",
            "hashlib",
            "hmac",
            "secrets",
            "inspect",
            "importlib",
        }
        for module, names in self.module_imports():
            self.assertNotIn(module, forbidden)
            for name in names:
                self.assertNotIn(name, forbidden)


if __name__ == "__main__":
    unittest.main()
