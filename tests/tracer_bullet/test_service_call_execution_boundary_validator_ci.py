"""Tracer bullets for the service call boundary validator CI consumer."""

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

import kernel.lifecycle.service_call_execution_boundary_validator_ci as ci_module
from kernel.lifecycle.service_call_execution_boundary_validator_ci import (
    consume_service_call_execution_boundary_validator_ci,
    service_call_execution_boundary_validator_ci_manifest,
)


MANIFEST = service_call_execution_boundary_validator_ci_manifest()
CHECKPOINT = MANIFEST["expected_validator_checkpoint"]
SOURCE_REFS = MANIFEST["expected_source_refs"]
DECLARATION_GROUPS = tuple(MANIFEST["expected_declaration_groups"])
FALSE_AUTHORITY_FLAGS = tuple(MANIFEST["required_false_authority_flags"])
TRUE_DECLARATIONS = tuple(MANIFEST["required_true_declarations"])
AUTHORITY_FLAGS = tuple(MANIFEST["required_authority_summary_flags"])
VALIDATOR_FAILURES = tuple(MANIFEST["validator_failure_taxonomy"])
FAILURE_ORDER = tuple(MANIFEST["ci_failure_taxonomy"])


def valid_boundary() -> dict[str, object]:
    return {
        "surface": "service_call_execution_boundary_validator",
        "version": 1,
        "validator_checkpoint": copy.deepcopy(CHECKPOINT),
        "source_refs": copy.deepcopy(SOURCE_REFS),
        "declaration_groups": {
            group: {f"{group}_declared": True}
            for group in DECLARATION_GROUPS
        },
        "required_false_authority_flags": {
            flag: False for flag in FALSE_AUTHORITY_FLAGS
        },
        "required_true_declarations": {
            declaration: True for declaration in TRUE_DECLARATIONS
        },
        "json_safe": True,
        "authority": {flag: False for flag in AUTHORITY_FLAGS},
    }


def valid_payload(
    *,
    ready: bool = True,
    reason_code: str = "ready",
    failures: list[str] | None = None,
    boundary: object | None = None,
) -> dict[str, object]:
    if failures is None:
        failures = []
    if boundary is None:
        boundary = valid_boundary()
    return {
        "service_call_execution_boundary_ready": ready,
        "reason_code": reason_code,
        "failures": failures,
        "boundary": boundary,
    }


def contains_identity(value: object, target: object) -> bool:
    if value is target:
        return True
    if isinstance(value, dict):
        return any(
            contains_identity(key, target)
            or contains_identity(item, target)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_identity(item, target) for item in value)
    return False


def assert_rejected_with(
    test_case: unittest.TestCase,
    payload: object,
    failure: str,
) -> dict[str, object]:
    result = consume_service_call_execution_boundary_validator_ci(payload)
    test_case.assertIs(result["ci_ok"], False)
    test_case.assertIn(failure, result["failures"])
    json.dumps(result, sort_keys=True)
    return result


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "service_call_execution_boundary_validator_ci_manifest",
                "consume_service_call_execution_boundary_validator_ci",
            ],
        )

    def test_signatures(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    service_call_execution_boundary_validator_ci_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    consume_service_call_execution_boundary_validator_ci
                ).parameters
            ),
            ["payload"],
        )

    def test_manifest_exact_shape_json_safe_and_defensive_copy(self) -> None:
        manifest = service_call_execution_boundary_validator_ci_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(
            set(manifest),
            {
                "surface",
                "version",
                "input_shape",
                "expected_top_level_keys",
                "expected_boundary_keys",
                "expected_validator_checkpoint",
                "expected_source_refs",
                "expected_declaration_groups",
                "required_false_authority_flags",
                "required_true_declarations",
                "required_authority_summary_flags",
                "validator_failure_taxonomy",
                "ci_failure_taxonomy",
                "reason_codes",
                "non_authority",
                "json_safe",
            },
        )
        self.assertEqual(
            manifest["surface"],
            "service_call_execution_boundary_validator_ci",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["expected_top_level_keys"],
            [
                "service_call_execution_boundary_ready",
                "reason_code",
                "failures",
                "boundary",
            ],
        )
        self.assertEqual(
            manifest["expected_validator_checkpoint"],
            {
                "tag": "service-call-execution-boundary-validator-v1",
                "commit": "9712ad6ba5d7574e10e1008fa2001017c8da4493",
            },
        )
        self.assertIs(manifest["json_safe"], True)

        manifest["expected_validator_checkpoint"]["commit"] = "mutated"
        manifest["expected_source_refs"]["read-only-governance-layer-v1"] = (
            "mutated"
        )
        fresh = service_call_execution_boundary_validator_ci_manifest()
        self.assertEqual(
            fresh["expected_validator_checkpoint"]["commit"],
            "9712ad6ba5d7574e10e1008fa2001017c8da4493",
        )
        self.assertEqual(
            fresh["expected_source_refs"]["read-only-governance-layer-v1"],
            "4656e8f03404c6bb39e7976c6165e3d7dc0314fb",
        )


class HappyPathTests(unittest.TestCase):
    def test_happy_path_ci_ok(self) -> None:
        result = consume_service_call_execution_boundary_validator_ci(
            valid_payload()
        )

        self.assertEqual(
            set(result),
            {"ci_ok", "reason_code", "failures", "boundary"},
        )
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])

        boundary = result["boundary"]
        self.assertEqual(
            set(boundary),
            {
                "surface",
                "version",
                "validator_checkpoint",
                "source_refs",
                "declaration_groups",
                "required_false_authority_flags",
                "required_true_declarations",
                "json_safe",
                "authority",
            },
        )
        self.assertEqual(
            boundary["surface"],
            "service_call_execution_boundary_validator_ci",
        )
        self.assertEqual(boundary["version"], 1)
        self.assertEqual(boundary["validator_checkpoint"], CHECKPOINT)
        self.assertEqual(boundary["source_refs"], SOURCE_REFS)
        self.assertEqual(
            set(boundary["declaration_groups"]),
            set(DECLARATION_GROUPS),
        )
        self.assertEqual(
            boundary["required_false_authority_flags"],
            {flag: False for flag in FALSE_AUTHORITY_FLAGS},
        )
        self.assertEqual(
            boundary["required_true_declarations"],
            {declaration: True for declaration in TRUE_DECLARATIONS},
        )
        self.assertIs(boundary["json_safe"], True)

    def test_ci_ok_grants_no_authority(self) -> None:
        result = consume_service_call_execution_boundary_validator_ci(
            valid_payload()
        )
        boundary = result["boundary"]

        self.assertIs(result["ci_ok"], True)
        for flag in boundary["authority"].values():
            self.assertIs(flag, False)
        for flag in boundary["required_false_authority_flags"].values():
            self.assertIs(flag, False)

        self.assertIs(
            boundary["authority"]["service_call_execution_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["service_adapter_runtime_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["service_method_call_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["evidence_append_authorized"],
            False,
        )
        self.assertIs(boundary["authority"]["audit_append_authorized"], False)
        self.assertIs(
            boundary["authority"]["repository_uow_writes_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["transaction_runtime_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["idempotency_reservation_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["rollback_runtime_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["runtime_checker_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["runtime_enforcer_authorized"],
            False,
        )
        self.assertIs(
            boundary["authority"]["executor_implementation_authorized"],
            False,
        )
        self.assertIs(boundary["authority"]["durable_writes_authorized"], False)
        self.assertIs(
            boundary["authority"]["irreversible_action_authorized"],
            False,
        )

    def test_happy_not_ready_path(self) -> None:
        result = consume_service_call_execution_boundary_validator_ci(
            valid_payload(
                ready=False,
                reason_code="not_ready",
                failures=["source_ref_mismatch"],
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["source_ref_mismatch"])

    def test_invalid_validator_payload_reason_allowed_when_not_ready(
        self,
    ) -> None:
        result = consume_service_call_execution_boundary_validator_ci(
            valid_payload(
                ready=False,
                reason_code="invalid_service_call_execution_boundary_payload",
                failures=["payload_shape_mismatch"],
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])


class PayloadShapeTests(unittest.TestCase):
    def test_payload_not_mapping(self) -> None:
        result = assert_rejected_with(self, [], "payload_not_mapping")
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])

    def test_top_level_key_mismatch(self) -> None:
        payload = valid_payload()
        payload["extra"] = {}
        assert_rejected_with(self, payload, "payload_shape_mismatch")

        payload = valid_payload()
        del payload["reason_code"]
        assert_rejected_with(self, payload, "payload_shape_mismatch")

    def test_boundary_not_mapping(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(boundary=[]),
            "boundary_not_mapping",
        )

    def test_boundary_key_mismatch(self) -> None:
        boundary = valid_boundary()
        boundary["extra"] = True
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "boundary_shape_mismatch",
        )

        boundary = valid_boundary()
        del boundary["source_refs"]
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "boundary_shape_mismatch",
        )


class ValidatorIdentityTests(unittest.TestCase):
    def test_validator_surface_invalid(self) -> None:
        boundary = valid_boundary()
        boundary["surface"] = "wrong"
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "validator_surface_invalid",
        )

    def test_validator_version_invalid(self) -> None:
        boundary = valid_boundary()
        boundary["version"] = 2
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "validator_version_invalid",
        )

    def test_bool_as_int_version_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["version"] = True
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "validator_version_invalid",
        )

    def test_validator_checkpoint_missing_rejected(self) -> None:
        boundary = valid_boundary()
        del boundary["validator_checkpoint"]
        result = assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "validator_checkpoint_invalid",
        )
        self.assertIn("boundary_shape_mismatch", result["failures"])

    def test_validator_checkpoint_mismatch_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["validator_checkpoint"]["commit"] = "wrong"
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "validator_checkpoint_invalid",
        )


class ReadinessConsistencyTests(unittest.TestCase):
    def test_ready_with_non_ready_reason_rejected(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(reason_code="not_ready"),
            "validator_readiness_invalid",
        )

    def test_ready_with_failures_rejected(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(failures=["source_ref_mismatch"]),
            "validator_readiness_invalid",
        )

    def test_not_ready_with_ready_reason_rejected(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(
                ready=False,
                reason_code="ready",
                failures=["source_ref_mismatch"],
            ),
            "validator_readiness_invalid",
        )

    def test_not_ready_with_empty_failures_rejected(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(ready=False, reason_code="not_ready", failures=[]),
            "validator_readiness_invalid",
        )

    def test_ready_non_bool_rejected(self) -> None:
        payload = valid_payload()
        payload["service_call_execution_boundary_ready"] = 1
        assert_rejected_with(self, payload, "validator_readiness_invalid")

    def test_reason_code_invalid(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(reason_code="wrong"),
            "validator_reason_code_invalid",
        )

    def test_failures_non_list_rejected(self) -> None:
        payload = valid_payload()
        payload["failures"] = "source_ref_mismatch"
        assert_rejected_with(self, payload, "validator_failures_invalid")

    def test_failure_item_non_string_rejected(self) -> None:
        payload = valid_payload()
        payload["failures"] = [object()]
        assert_rejected_with(self, payload, "validator_failures_invalid")

    def test_unknown_validator_failure_rejected(self) -> None:
        assert_rejected_with(
            self,
            valid_payload(
                ready=False,
                reason_code="not_ready",
                failures=["unknown_failure"],
            ),
            "validator_failure_unknown",
        )

    def test_validator_failure_taxonomy_values_are_accepted(self) -> None:
        for failure in VALIDATOR_FAILURES:
            with self.subTest(failure=failure):
                result = consume_service_call_execution_boundary_validator_ci(
                    valid_payload(
                        ready=False,
                        reason_code="not_ready",
                        failures=[failure],
                    )
                )
                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertEqual(result["failures"], [failure])


class SourceRefTests(unittest.TestCase):
    def test_source_refs_mismatch(self) -> None:
        boundary = valid_boundary()
        boundary["source_refs"]["read-only-governance-layer-v1"] = "wrong"
        result = assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "source_ref_mismatch",
        )
        self.assertEqual(result["boundary"]["source_refs"], SOURCE_REFS)

    def test_source_refs_extra_missing_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["source_refs"]["extra"] = "value"
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "source_ref_mismatch",
        )

        boundary = valid_boundary()
        del boundary["source_refs"]["read-only-governance-layer-v1"]
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "source_ref_mismatch",
        )

    def test_source_refs_not_mapping_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["source_refs"] = []
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "source_ref_mismatch",
        )


class DeclarationGroupTests(unittest.TestCase):
    def test_declaration_groups_missing_extra_rejected(self) -> None:
        boundary = valid_boundary()
        del boundary["declaration_groups"]["service_call_attempt_boundary"]
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "declaration_group_invalid",
        )

        boundary = valid_boundary()
        boundary["declaration_groups"]["extra_group"] = {}
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "declaration_group_invalid",
        )

    def test_declaration_group_non_mapping_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["declaration_groups"][
            "service_call_attempt_boundary"
        ] = []
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "declaration_group_invalid",
        )

    def test_declaration_group_raw_object_rejected_and_not_leaked(self) -> None:
        sentinel = object()
        boundary = valid_boundary()
        boundary["declaration_groups"][
            "service_call_attempt_boundary"
        ]["raw"] = sentinel

        result = assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "declaration_group_invalid",
        )

        self.assertFalse(contains_identity(result, sentinel))
        json.dumps(result, sort_keys=True)


class RequiredFalseAuthorityFlagTests(unittest.TestCase):
    def test_required_false_authority_flags_missing_rejected(self) -> None:
        for flag in FALSE_AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                boundary = valid_boundary()
                del boundary["required_false_authority_flags"][flag]
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "authorization_flag_invalid",
                )

    def test_required_false_authority_flags_non_bool_rejected(self) -> None:
        for flag in FALSE_AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                boundary = valid_boundary()
                boundary["required_false_authority_flags"][flag] = "false"
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "authorization_flag_invalid",
                )

    def test_required_false_authority_flag_true_rejected(self) -> None:
        for flag in FALSE_AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                boundary = valid_boundary()
                boundary["required_false_authority_flags"][flag] = True
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "authorization_flag_true",
                )


class RequiredTrueDeclarationTests(unittest.TestCase):
    def test_required_true_declaration_missing_rejected(self) -> None:
        for declaration in TRUE_DECLARATIONS:
            with self.subTest(declaration=declaration):
                boundary = valid_boundary()
                del boundary["required_true_declarations"][declaration]
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "required_declaration_invalid",
                )

    def test_required_true_declaration_non_bool_rejected(self) -> None:
        for declaration in TRUE_DECLARATIONS:
            with self.subTest(declaration=declaration):
                boundary = valid_boundary()
                boundary["required_true_declarations"][declaration] = "true"
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "required_declaration_invalid",
                )

    def test_required_true_declaration_false_rejected(self) -> None:
        for declaration in TRUE_DECLARATIONS:
            with self.subTest(declaration=declaration):
                boundary = valid_boundary()
                boundary["required_true_declarations"][declaration] = False
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "required_declaration_false",
                )


class AuthoritySummaryTests(unittest.TestCase):
    def test_authority_summary_missing_rejected(self) -> None:
        for flag in AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                boundary = valid_boundary()
                del boundary["authority"][flag]
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "authorization_flag_invalid",
                )

    def test_authority_summary_non_bool_rejected(self) -> None:
        for flag in AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                boundary = valid_boundary()
                boundary["authority"][flag] = "false"
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "authorization_flag_invalid",
                )

    def test_authority_summary_true_rejected(self) -> None:
        for flag in AUTHORITY_FLAGS:
            with self.subTest(flag=flag):
                boundary = valid_boundary()
                boundary["authority"][flag] = True
                assert_rejected_with(
                    self,
                    valid_payload(boundary=boundary),
                    "authorization_flag_true",
                )

    def test_output_authority_summary_hard_false(self) -> None:
        result = consume_service_call_execution_boundary_validator_ci(
            valid_payload()
        )
        self.assertEqual(
            result["boundary"]["authority"],
            {flag: False for flag in AUTHORITY_FLAGS},
        )


class JsonSafetyTests(unittest.TestCase):
    def test_json_safe_missing_rejected(self) -> None:
        boundary = valid_boundary()
        del boundary["json_safe"]
        result = assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "json_safe_invalid",
        )
        self.assertIn("boundary_shape_mismatch", result["failures"])

    def test_json_safe_false_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["json_safe"] = False
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "json_safe_invalid",
        )

    def test_json_safe_non_bool_rejected(self) -> None:
        boundary = valid_boundary()
        boundary["json_safe"] = "true"
        assert_rejected_with(
            self,
            valid_payload(boundary=boundary),
            "json_safe_invalid",
        )

    def test_output_is_json_safe(self) -> None:
        result = consume_service_call_execution_boundary_validator_ci(
            valid_payload()
        )
        json.dumps(result, sort_keys=True)


class SafetyAndDeterminismTests(unittest.TestCase):
    def test_deterministic_failure_ordering(self) -> None:
        payload = valid_payload(
            ready=True,
            reason_code="not_ready",
            failures=["unknown_failure"],
        )
        payload["extra"] = {}
        boundary = payload["boundary"]
        boundary["extra"] = True
        boundary["surface"] = "wrong"
        boundary["version"] = True
        boundary["validator_checkpoint"]["commit"] = "wrong"
        boundary["source_refs"]["read-only-governance-layer-v1"] = "wrong"
        boundary["declaration_groups"][
            "service_call_attempt_boundary"
        ] = []
        boundary["required_true_declarations"][
            "spec_only_non_executable"
        ] = False
        boundary["required_false_authority_flags"][
            "service_call_execution_authorized"
        ] = True
        boundary["authority"]["service_call_execution_authorized"] = True
        boundary["json_safe"] = False

        result = consume_service_call_execution_boundary_validator_ci(payload)

        expected = {
            "payload_shape_mismatch",
            "boundary_shape_mismatch",
            "validator_surface_invalid",
            "validator_version_invalid",
            "validator_checkpoint_invalid",
            "validator_readiness_invalid",
            "validator_failure_unknown",
            "source_ref_mismatch",
            "declaration_group_invalid",
            "required_declaration_false",
            "authorization_flag_true",
            "json_safe_invalid",
        }
        self.assertEqual(
            result["failures"],
            [failure for failure in FAILURE_ORDER if failure in expected],
        )

    def test_input_not_mutated(self) -> None:
        payload = valid_payload()
        original = copy.deepcopy(payload)
        consume_service_call_execution_boundary_validator_ci(payload)
        self.assertEqual(payload, original)

    def test_output_does_not_leak_raw_object_values_from_invalid_input(
        self,
    ) -> None:
        sentinel = object()
        payload = valid_payload()
        boundary = payload["boundary"]
        boundary["validator_checkpoint"]["commit"] = sentinel
        boundary["source_refs"]["read-only-governance-layer-v1"] = sentinel
        boundary["declaration_groups"][
            "service_call_attempt_boundary"
        ]["raw"] = sentinel
        boundary["required_false_authority_flags"][
            "service_call_execution_authorized"
        ] = sentinel
        boundary["required_true_declarations"][
            "spec_only_non_executable"
        ] = sentinel
        boundary["authority"]["service_call_execution_authorized"] = sentinel

        result = consume_service_call_execution_boundary_validator_ci(payload)

        self.assertIs(result["ci_ok"], False)
        self.assertFalse(contains_identity(result, sentinel))
        json.dumps(result, sort_keys=True)


class SourceBoundaryTests(unittest.TestCase):
    def source(self) -> str:
        return inspect.getsource(ci_module)

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

    def test_no_validator_imports_or_calls(self) -> None:
        for module, names in self.module_imports():
            joined = ".".join((module, *names))
            self.assertNotIn(
                "service_call_execution_boundary_validator.",
                joined,
            )

        tree = ast.parse(self.source())
        forbidden_calls = {
            "validate_service_call_execution_boundary",
            "service_call_execution_boundary_validator_manifest",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    self.assertNotIn(func.id, forbidden_calls)
                elif isinstance(func, ast.Attribute):
                    self.assertNotIn(func.attr, forbidden_calls)

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

    def test_no_recovery_cli_or_upstream_imports(self) -> None:
        forbidden = (
            "recovery",
            "cli",
            "validator_ci",
            "checker",
            "consumer",
        )
        for module, names in self.module_imports():
            joined = ".".join((module, *names)).lower()
            for item in forbidden:
                self.assertNotIn(item, joined)

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
