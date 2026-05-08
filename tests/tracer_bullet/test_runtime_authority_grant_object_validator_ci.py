"""Tracer bullets for the runtime authority grant object validator CI."""

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

import kernel.lifecycle.runtime_authority_grant_object_validator_ci as ci_module
from kernel.lifecycle.runtime_authority_grant_object_validator_ci import (
    consume_runtime_authority_grant_object_validator_ci,
    runtime_authority_grant_object_validator_ci_manifest,
)


MANIFEST = runtime_authority_grant_object_validator_ci_manifest()
CONTRACT = MANIFEST["expected_contract_summary"]
GRANT_OBJECT = MANIFEST["expected_authority_grant_object_summary"]
AUTHORITY = MANIFEST["authority_summary"]
VALIDATOR_FAILURES = MANIFEST["validator_failure_taxonomy"]
CI_FAILURES = MANIFEST["ci_failure_taxonomy"]


class LeakyValue:
    def __repr__(self) -> str:
        return "LEAKY_RUNTIME_OBJECT"


def valid_payload() -> dict[str, object]:
    return {
        "runtime_authority_grant_object_ready": True,
        "reason_code": "ready",
        "failures": [],
        "contract": copy.deepcopy(CONTRACT),
        "authority_grant_object": copy.deepcopy(GRANT_OBJECT),
        "authority": copy.deepcopy(AUTHORITY),
        "json_safe": True,
        "validator_checkpoint_tag": "runtime-authority-grant-object-validator-v1",
        "validator_checkpoint_commit": (
            "ed31e3c92a7bd3d35e411dd4e559038023a2f8d9"
        ),
    }


def assert_json_safe_without_leak(
    testcase: unittest.TestCase,
    result: dict[str, object],
) -> None:
    encoded = json.dumps(result, sort_keys=True)
    testcase.assertNotIn("LEAKY_RUNTIME_OBJECT", encoded)


class PublicAPITests(unittest.TestCase):
    def test_public_api_exact(self) -> None:
        self.assertEqual(
            set(dir(ci_module)) & {
                "runtime_authority_grant_object_validator_ci_manifest",
                "consume_runtime_authority_grant_object_validator_ci",
            },
            {
                "runtime_authority_grant_object_validator_ci_manifest",
                "consume_runtime_authority_grant_object_validator_ci",
            },
        )

    def test_all_exact(self) -> None:
        self.assertEqual(
            ci_module.__all__,
            [
                "runtime_authority_grant_object_validator_ci_manifest",
                "consume_runtime_authority_grant_object_validator_ci",
            ],
        )

    def test_signatures_are_exact(self) -> None:
        self.assertEqual(
            list(
                inspect.signature(
                    runtime_authority_grant_object_validator_ci_manifest
                ).parameters
            ),
            [],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    consume_runtime_authority_grant_object_validator_ci
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
        manifest = runtime_authority_grant_object_validator_ci_manifest()
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(
            manifest["surface"],
            "runtime_authority_grant_object_validator_ci",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["validator_checkpoint_tag"],
            "runtime-authority-grant-object-validator-v1",
        )
        self.assertEqual(
            manifest["validator_checkpoint_commit"],
            "ed31e3c92a7bd3d35e411dd4e559038023a2f8d9",
        )
        self.assertEqual(
            manifest["expected_contract_name"],
            "RuntimeAuthorityGrantObjectV1",
        )
        self.assertEqual(
            manifest["expected_validator_package"],
            "runtime-authority-grant-object-validator-v1",
        )
        self.assertEqual(manifest["ci_failure_taxonomy"], CI_FAILURES)
        self.assertEqual(manifest["validator_failure_taxonomy"], VALIDATOR_FAILURES)
        self.assertEqual(
            manifest["public_api"],
            [
                "runtime_authority_grant_object_validator_ci_manifest",
                "consume_runtime_authority_grant_object_validator_ci",
            ],
        )
        self.assertEqual(
            manifest["import_boundary"],
            [
                "from collections.abc import Mapping",
                "from copy import deepcopy",
            ],
        )
        manifest["authority_summary"]["runtime_authority_runtime_authorized"] = True
        self.assertIs(
            runtime_authority_grant_object_validator_ci_manifest()[
                "authority_summary"
            ]["runtime_authority_runtime_authorized"],
            False,
        )


class HappyPathTests(unittest.TestCase):
    def test_happy_path_ready(self) -> None:
        result = consume_runtime_authority_grant_object_validator_ci(
            valid_payload()
        )

        self.assertEqual(
            set(result),
            {
                "ci_ok",
                "reason_code",
                "failures",
                "validator_checkpoint",
                "contract",
                "authority_grant_object",
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
                "tag": "runtime-authority-grant-object-validator-v1",
                "commit": "ed31e3c92a7bd3d35e411dd4e559038023a2f8d9",
            },
        )
        self.assertEqual(result["contract"], CONTRACT)
        self.assertEqual(result["authority_grant_object"], GRANT_OBJECT)
        self.assertEqual(result["authority"], AUTHORITY)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)

    def test_not_ready_valid_validator_output(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = [
            "source_refs_invalid",
            "json_safe_invalid",
        ]

        result = consume_runtime_authority_grant_object_validator_ci(payload)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"],
            ["source_refs_invalid", "json_safe_invalid"],
        )
        self.assert_json_ready(result)

    def test_input_immutability(self) -> None:
        payload = valid_payload()
        before = copy.deepcopy(payload)
        consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(payload, before)

    def test_non_authorizing_ci_ok(self) -> None:
        result = consume_runtime_authority_grant_object_validator_ci(
            valid_payload()
        )
        self.assertIs(result["ci_ok"], True)
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
        non_authority = result["non_authority"]
        self.assertEqual(
            non_authority["ci_ok_proves"],
            "already_rendered_validator_output_structurally_suitable_for_"
            "read_only_consolidation_only",
        )
        for key, value in non_authority.items():
            if key != "ci_ok_proves":
                self.assertIs(value, False)

    def assert_json_ready(self, result: dict[str, object]) -> None:
        self.assertIs(result["json_safe"], True)
        json.dumps(result, sort_keys=True)


class PayloadShapeTests(unittest.TestCase):
    def test_payload_not_mapping(self) -> None:
        result = consume_runtime_authority_grant_object_validator_ci([])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["ci_payload_not_mapping"])
        assert_json_safe_without_leak(self, result)

    def test_top_level_shape_mismatch(self) -> None:
        payload = valid_payload()
        payload["extra"] = True
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["ci_payload_shape_mismatch"])

    def test_validator_checkpoint_tag_invalid(self) -> None:
        payload = valid_payload()
        payload["validator_checkpoint_tag"] = "wrong"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["validator_checkpoint_invalid"])

    def test_validator_checkpoint_commit_invalid(self) -> None:
        payload = valid_payload()
        payload["validator_checkpoint_commit"] = "0" * 40
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["validator_checkpoint_invalid"])


class ReadinessConsistencyTests(unittest.TestCase):
    def test_readiness_non_bool(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = "true"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_readiness_bool_as_int_rejected(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = 1
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_ready_with_wrong_reason_fails(self) -> None:
        payload = valid_payload()
        payload["reason_code"] = "not_ready"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["reason_code_invalid"])

    def test_ready_with_non_empty_failures_fails(self) -> None:
        payload = valid_payload()
        payload["failures"] = ["source_refs_invalid"]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_not_ready_with_empty_failures_fails(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = False
        payload["reason_code"] = "not_ready"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["readiness_invalid"])

    def test_not_ready_with_invalid_reason_fails(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = False
        payload["reason_code"] = "wrong"
        payload["failures"] = ["source_refs_invalid"]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["reason_code_invalid"])

    def test_failure_list_not_list_fails(self) -> None:
        payload = valid_payload()
        payload["failures"] = ("source_refs_invalid",)
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["failure_list_invalid"])

    def test_failure_list_non_string_fails(self) -> None:
        payload = valid_payload()
        payload["failures"] = ["source_refs_invalid", 1]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["failure_list_invalid"])

    def test_unknown_validator_failure_fails_closed(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = ["source_refs_invalid", "new_failure"]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["unknown_validator_failure"])

    def test_invalid_validator_reason_accepted_for_not_ready(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = False
        payload["reason_code"] = "invalid_runtime_authority_grant_payload"
        payload["failures"] = ["payload_not_mapping"]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["payload_not_mapping"])


class SummaryValidationTests(unittest.TestCase):
    def test_contract_summary_invalid(self) -> None:
        payload = valid_payload()
        payload["contract"]["contract_name"] = "Wrong"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["contract_summary_invalid"])

    def test_authority_grant_object_summary_invalid(self) -> None:
        payload = valid_payload()
        payload["authority_grant_object"]["surface"] = "Wrong"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["authority_grant_object_summary_invalid"],
        )

    def test_authority_summary_invalid(self) -> None:
        payload = valid_payload()
        del payload["authority"]["runtime_authority_runtime_authorized"]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["authority_summary_invalid"])

    def test_authority_summary_flag_true_fails_closed(self) -> None:
        payload = valid_payload()
        payload["authority"]["runtime_authority_runtime_authorized"] = True
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["authority_summary_invalid"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_non_authority_summary_invalid(self) -> None:
        payload = valid_payload()
        payload["contract"]["non_authority_summary"][
            "runtime_authority_grant_object_ready_authorizes_runtime"
        ] = True
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["non_authority_summary_invalid"])

    def test_json_safe_missing(self) -> None:
        payload = valid_payload()
        del payload["json_safe"]
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["ci_payload_shape_mismatch", "json_safe_invalid"],
        )

    def test_json_safe_false(self) -> None:
        payload = valid_payload()
        payload["json_safe"] = False
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_json_safe_non_bool(self) -> None:
        payload = valid_payload()
        payload["json_safe"] = "true"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(result["failures"], ["json_safe_invalid"])

    def test_invalid_nested_object_does_not_leak_and_output_serializes(self) -> None:
        payload = valid_payload()
        payload["contract"]["expected_source_refs"] = {
            "runtime-authority-grant-object-spec-only-v1": LeakyValue()
        }
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            ["contract_summary_invalid", "json_safe_invalid"],
        )
        assert_json_safe_without_leak(self, result)

    def test_bounded_output_on_failure_paths(self) -> None:
        cases = [
            [],
            {**valid_payload(), "validator_checkpoint_tag": "wrong"},
            {**valid_payload(), "runtime_authority_grant_object_ready": 1},
            {**valid_payload(), "json_safe": False},
        ]
        for payload in cases:
            with self.subTest(payload=type(payload).__name__):
                result = consume_runtime_authority_grant_object_validator_ci(
                    payload
                )
                self.assertEqual(
                    set(result),
                    {
                        "ci_ok",
                        "reason_code",
                        "failures",
                        "validator_checkpoint",
                        "contract",
                        "authority_grant_object",
                        "authority",
                        "non_authority",
                        "json_safe",
                    },
                )
                json.dumps(result, sort_keys=True)


class DeterminismTests(unittest.TestCase):
    def test_deterministic_failure_ordering(self) -> None:
        payload = valid_payload()
        payload["runtime_authority_grant_object_ready"] = 1
        payload["reason_code"] = "wrong"
        payload["failures"] = ["unknown"]
        payload["contract"] = []
        payload["authority_grant_object"] = []
        payload["authority"] = []
        payload["json_safe"] = False
        payload["validator_checkpoint_tag"] = "wrong"
        result = consume_runtime_authority_grant_object_validator_ci(payload)
        self.assertEqual(
            result["failures"],
            [
                "validator_checkpoint_invalid",
                "readiness_invalid",
                "reason_code_invalid",
                "unknown_validator_failure",
                "contract_summary_invalid",
                "authority_grant_object_summary_invalid",
                "authority_summary_invalid",
                "json_safe_invalid",
            ],
        )

    def test_every_validator_failure_is_known_for_not_ready(self) -> None:
        for failure in VALIDATOR_FAILURES:
            with self.subTest(failure=failure):
                payload = valid_payload()
                payload["runtime_authority_grant_object_ready"] = False
                payload["reason_code"] = "not_ready"
                payload["failures"] = [failure]
                result = consume_runtime_authority_grant_object_validator_ci(
                    payload
                )
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertEqual(result["failures"], [failure])


class SourceBoundaryTests(unittest.TestCase):
    def source(self) -> str:
        return inspect.getsource(ci_module)

    def test_no_validator_import_or_call(self) -> None:
        source = self.source()
        self.assertNotIn(
            "validate_runtime_authority_grant_object",
            source,
        )
        self.assertNotIn(
            "runtime_authority_grant_object_validator import",
            source,
        )

    def test_no_service_imports_or_calls(self) -> None:
        tree = ast.parse(self.source())
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
                    self.assertNotIn(alias.name, forbidden_modules)

    def test_no_db_repository_uow_imports(self) -> None:
        tree = ast.parse(self.source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                self.assertFalse(module.startswith("kernel.stores"), module)
                self.assertNotEqual(module, "sqlite3")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(
                        alias.name.startswith("kernel.stores"),
                        alias.name,
                    )
                    self.assertNotEqual(alias.name, "sqlite3")

    def test_no_upstream_validator_checker_or_ci_imports(self) -> None:
        tree = ast.parse(self.source())
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
        tree = ast.parse(self.source())
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
        self.assertEqual(
            imports,
            [
                "collections.abc",
                "copy",
            ],
        )
        self.assertFalse(forbidden & set(imports))

    def test_no_git_shell_out_or_filesystem_side_effect(self) -> None:
        tree = ast.parse(self.source())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    self.assertNotEqual(node.func.attr, "system")
                    self.assertNotEqual(node.func.attr, "popen")
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"open", "exec", "eval"})


if __name__ == "__main__":
    unittest.main()
