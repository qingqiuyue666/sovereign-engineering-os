import ast
import copy
import inspect
import json
import unittest

from kernel.lifecycle import runtime_authority_checker_enforcer_boundary_validator_ci as ci_module
from kernel.lifecycle.runtime_authority_checker_enforcer_boundary_validator_ci import (
    consume_runtime_authority_checker_enforcer_boundary_validator_ci,
    runtime_authority_checker_enforcer_boundary_validator_ci_manifest,
)


EXPECTED_PUBLIC_API = [
    "runtime_authority_checker_enforcer_boundary_validator_ci_manifest",
    "consume_runtime_authority_checker_enforcer_boundary_validator_ci",
]


class RuntimeLeak:
    def __repr__(self):
        return "RUNTIME_LEAK_OBJECT"


def _manifest():
    return runtime_authority_checker_enforcer_boundary_validator_ci_manifest()


def _valid_boundary():
    manifest = _manifest()
    return {
        "surface": "RuntimeAuthorityCheckerEnforcerBoundaryV1",
        "version": 1,
        "source_refs": copy.deepcopy(manifest["expected_source_refs"]),
        "readiness_signals": copy.deepcopy(manifest["expected_readiness_signals"]),
        **copy.deepcopy(manifest["expected_boundary_model_groups"]),
        "required_false_authority_flags": copy.deepcopy(
            manifest["expected_false_authority_flags"]
        ),
        "required_true_declarations": copy.deepcopy(
            manifest["expected_true_declarations"]
        ),
        "json_safe": True,
    }


def _valid_payload():
    manifest = _manifest()
    checkpoint = manifest["expected_validator_checkpoint"]
    return {
        "runtime_authority_boundary_ready": True,
        "reason_code": "ready",
        "failures": [],
        "boundary": _valid_boundary(),
        "authority": copy.deepcopy(manifest["expected_authority_summary"]),
        "validator_checkpoint_tag": checkpoint["tag"],
        "validator_checkpoint_commit": checkpoint["commit"],
    }


def _consume(payload):
    return consume_runtime_authority_checker_enforcer_boundary_validator_ci(payload)


def _assert_json_safe_without_leak(test_case, value):
    encoded = json.dumps(value, sort_keys=True)
    test_case.assertNotIn("RUNTIME_LEAK_OBJECT", encoded)
    return encoded


class RuntimeAuthorityCheckerEnforcerBoundaryValidatorCiTests(unittest.TestCase):
    def test_public_api_and_all_are_exact(self):
        self.assertEqual(ci_module.__all__, EXPECTED_PUBLIC_API)
        self.assertIs(
            ci_module.runtime_authority_checker_enforcer_boundary_validator_ci_manifest,
            runtime_authority_checker_enforcer_boundary_validator_ci_manifest,
        )
        self.assertIs(
            ci_module.consume_runtime_authority_checker_enforcer_boundary_validator_ci,
            consume_runtime_authority_checker_enforcer_boundary_validator_ci,
        )

    def test_public_function_signatures_are_exact(self):
        self.assertEqual(
            str(
                inspect.signature(
                    runtime_authority_checker_enforcer_boundary_validator_ci_manifest
                )
            ),
            "()",
        )
        self.assertEqual(
            str(
                inspect.signature(
                    consume_runtime_authority_checker_enforcer_boundary_validator_ci
                )
            ),
            "(payload)",
        )

    def test_production_imports_are_limited(self):
        with open(ci_module.__file__, "r", encoding="utf-8") as source:
            tree = ast.parse(source.read())

        imports = []
        import_from = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                import_from.append(
                    (
                        node.module,
                        tuple(alias.name for alias in node.names),
                    )
                )

        self.assertEqual(imports, [])
        self.assertEqual(
            import_from,
            [
                ("collections.abc", ("Mapping",)),
                ("copy", ("deepcopy",)),
            ],
        )

    def test_source_boundary_forbidden_imports_and_calls_absent(self):
        with open(ci_module.__file__, "r", encoding="utf-8") as source:
            tree = ast.parse(source.read())

        imported_modules = []
        called_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_names.append(node.func.attr)

        forbidden_modules = {
            "kernel.lifecycle.runtime_authority_checker_enforcer_boundary_validator",
            "kernel.services.evidence_service",
            "kernel.services.approval_service",
            "kernel.services.review_service",
            "kernel.services.revision_seal_service",
            "kernel.stores.sqlite.repositories",
            "kernel.stores.sqlite.unit_of_work",
            "sqlite3",
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
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        self.assertNotIn(
            "validate_runtime_authority_checker_enforcer_boundary",
            called_names,
        )
        self.assertNotIn("open", called_names)

    def test_happy_path_accepts_rendered_validator_output(self):
        result = _consume(_valid_payload())

        self.assertTrue(result["ci_ok"])
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["validator_checkpoint"],
            _manifest()["expected_validator_checkpoint"],
        )
        self.assertEqual(
            result["boundary"]["surface"],
            "RuntimeAuthorityCheckerEnforcerBoundaryV1",
        )
        self.assertEqual(result["boundary"]["version"], 1)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        _assert_json_safe_without_leak(self, result)

    def test_old_incorrect_validator_surface_is_rejected(self):
        payload = _valid_payload()
        payload["boundary"]["surface"] = (
            "runtime_authority_checker_enforcer_boundary_validator"
        )

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["boundary_surface_invalid"])
        self.assertEqual(
            result["boundary"]["surface"],
            "RuntimeAuthorityCheckerEnforcerBoundaryV1",
        )

    def test_output_is_bounded_to_expected_keys(self):
        result = _consume(_valid_payload())

        self.assertEqual(
            list(result.keys()),
            [
                "ci_ok",
                "reason_code",
                "failures",
                "validator_checkpoint",
                "boundary",
                "authority",
            ],
        )
        self.assertEqual(
            set(result["boundary"].keys()),
            set(_manifest()["expected_boundary_keys"]),
        )
        self.assertEqual(
            result["boundary"]["source_refs"],
            _manifest()["expected_source_refs"],
        )

    def test_non_mapping_payload_fails_closed(self):
        result = _consume(["not", "mapping"])

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_not_mapping"])
        _assert_json_safe_without_leak(self, result)

    def test_missing_top_level_key_fails_closed(self):
        payload = _valid_payload()
        payload.pop("boundary")

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("payload_shape_mismatch", result["failures"])

    def test_extra_top_level_key_fails_closed(self):
        payload = _valid_payload()
        payload["extra"] = "not allowed"

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("payload_shape_mismatch", result["failures"])

    def test_wrong_checkpoint_tag_fails_closed(self):
        payload = _valid_payload()
        payload["validator_checkpoint_tag"] = "runtime-authority-wrong"

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("checkpoint_tag_invalid", result["failures"])

    def test_wrong_checkpoint_commit_fails_closed(self):
        payload = _valid_payload()
        payload["validator_checkpoint_commit"] = "0" * 40

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("checkpoint_commit_invalid", result["failures"])

    def test_missing_checkpoint_tag_fails_closed(self):
        payload = _valid_payload()
        payload.pop("validator_checkpoint_tag")

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("payload_shape_mismatch", result["failures"])
        self.assertIn("checkpoint_tag_invalid", result["failures"])

    def test_missing_checkpoint_commit_fails_closed(self):
        payload = _valid_payload()
        payload.pop("validator_checkpoint_commit")

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("payload_shape_mismatch", result["failures"])
        self.assertIn("checkpoint_commit_invalid", result["failures"])

    def test_ready_with_non_empty_failures_fails_closed(self):
        payload = _valid_payload()
        payload["failures"] = ["boundary_surface_invalid"]

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("readiness_reason_failure_mismatch", result["failures"])

    def test_ready_with_wrong_reason_fails_closed(self):
        payload = _valid_payload()
        payload["reason_code"] = "not_ready"

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("readiness_reason_failure_mismatch", result["failures"])

    def test_not_ready_with_empty_failures_fails_closed(self):
        payload = _valid_payload()
        payload["runtime_authority_boundary_ready"] = False
        payload["reason_code"] = "not_ready"

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("readiness_reason_failure_mismatch", result["failures"])

    def test_not_ready_with_unknown_failure_fails_closed(self):
        payload = _valid_payload()
        payload["runtime_authority_boundary_ready"] = False
        payload["reason_code"] = "not_ready"
        payload["failures"] = ["unknown_failure"]

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("validator_failure_unknown", result["failures"])

    def test_not_ready_with_allowed_validator_failure_passes_structural_ci_as_not_ready(
        self,
    ):
        payload = _valid_payload()
        payload["runtime_authority_boundary_ready"] = False
        payload["reason_code"] = "invalid_runtime_authority_payload"
        payload["failures"] = ["boundary_version_invalid"]

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["boundary_version_invalid"])

    def test_boundary_not_mapping_fails_closed(self):
        payload = _valid_payload()
        payload["boundary"] = RuntimeLeak()

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("boundary_not_mapping", result["failures"])
        _assert_json_safe_without_leak(self, result)

    def test_boundary_missing_key_fails_closed(self):
        payload = _valid_payload()
        payload["boundary"].pop("source_refs")

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("boundary_shape_mismatch", result["failures"])

    def test_boundary_extra_key_fails_closed(self):
        payload = _valid_payload()
        payload["boundary"]["extra"] = False

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("boundary_shape_mismatch", result["failures"])

    def test_wrong_boundary_surface_is_not_ready(self):
        payload = _valid_payload()
        payload["boundary"]["surface"] = "WrongSurface"

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["boundary_surface_invalid"])

    def test_bool_as_int_version_is_rejected(self):
        payload = _valid_payload()
        payload["boundary"]["version"] = True

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["boundary_version_invalid"])

    def test_wrong_boundary_version_is_not_ready(self):
        payload = _valid_payload()
        payload["boundary"]["version"] = 2

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["boundary_version_invalid"])

    def test_source_refs_exact_set_required(self):
        for mutation in ("missing", "wrong", "extra"):
            with self.subTest(mutation=mutation):
                payload = _valid_payload()
                refs = payload["boundary"]["source_refs"]
                if mutation == "missing":
                    refs.pop("read-only-governance-layer-v1")
                elif mutation == "wrong":
                    refs["service-method-authority-read-only-stack-v1"] = "wrong"
                else:
                    refs["extra-ref"] = "wrong"

                result = _consume(payload)

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn("source_ref_mismatch", result["failures"])

    def test_object_valued_source_refs_do_not_leak(self):
        payload = _valid_payload()
        payload["boundary"]["source_refs"] = {
            "read-only-governance-layer-v1": RuntimeLeak()
        }

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertIn("source_ref_mismatch", result["failures"])
        _assert_json_safe_without_leak(self, result)

    def test_readiness_signals_exact_false_values_required(self):
        for mutation in ("missing", "extra", "non_bool", "true"):
            with self.subTest(mutation=mutation):
                payload = _valid_payload()
                signals = payload["boundary"]["readiness_signals"]
                if mutation == "missing":
                    signals.pop("service_adapter_ready")
                elif mutation == "extra":
                    signals["extra_signal"] = False
                elif mutation == "non_bool":
                    signals["service_adapter_ready"] = "false"
                else:
                    signals["service_adapter_ready"] = True

                result = _consume(payload)

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn("readiness_signal_invalid", result["failures"])

    def test_boundary_model_groups_exact_true_values_required(self):
        groups = _manifest()["expected_boundary_model_groups"]
        mutations = ("missing", "extra", "non_bool", "false")
        for group_name, expected in groups.items():
            first_key = next(iter(expected.keys()))
            for mutation in mutations:
                with self.subTest(group=group_name, mutation=mutation):
                    payload = _valid_payload()
                    group = payload["boundary"][group_name]
                    if mutation == "missing":
                        group.pop(first_key)
                    elif mutation == "extra":
                        group["extra_field"] = True
                    elif mutation == "non_bool":
                        group[first_key] = "true"
                    else:
                        group[first_key] = False

                    result = _consume(payload)

                    self.assertFalse(result["ci_ok"])
                    self.assertEqual(result["reason_code"], "not_ready")
                    self.assertIn(
                        f"{group_name}_invalid",
                        result["failures"],
                    )

    def test_object_valued_invalid_group_does_not_leak(self):
        payload = _valid_payload()
        payload["boundary"]["checker_boundary"] = {"future_only": RuntimeLeak()}

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertIn("checker_boundary_invalid", result["failures"])
        _assert_json_safe_without_leak(self, result)

    def test_false_authority_flags_exact_false_values_required(self):
        mutations = ("missing", "extra", "non_bool", "true")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = _valid_payload()
                flags = payload["boundary"]["required_false_authority_flags"]
                first_key = "runtime_authority_checker_authorized"
                if mutation == "missing":
                    flags.pop(first_key)
                elif mutation == "extra":
                    flags["extra_authorized"] = False
                elif mutation == "non_bool":
                    flags[first_key] = "false"
                else:
                    flags[first_key] = True

                result = _consume(payload)

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn("authorization_flag_invalid", result["failures"])
                if mutation == "true":
                    self.assertIn("authorization_flag_true", result["failures"])
                self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_true_declarations_exact_true_values_required(self):
        mutations = ("missing", "extra", "non_bool", "false")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = _valid_payload()
                declarations = payload["boundary"]["required_true_declarations"]
                first_key = "spec_only_non_executable"
                if mutation == "missing":
                    declarations.pop(first_key)
                elif mutation == "extra":
                    declarations["extra_declaration"] = True
                elif mutation == "non_bool":
                    declarations[first_key] = "true"
                else:
                    declarations[first_key] = False

                result = _consume(payload)

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn(
                    "required_declaration_invalid",
                    result["failures"],
                )
                if mutation == "false":
                    self.assertIn(
                        "required_declaration_false",
                        result["failures"],
                    )

    def test_authority_summary_exact_false_values_required(self):
        mutations = ("missing", "extra", "non_bool", "true")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = _valid_payload()
                authority = payload["authority"]
                first_key = "runtime_authority_checker_authorized"
                if mutation == "missing":
                    authority.pop(first_key)
                elif mutation == "extra":
                    authority["extra_authorized"] = False
                elif mutation == "non_bool":
                    authority[first_key] = "false"
                else:
                    authority[first_key] = True

                result = _consume(payload)

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn("authority_summary_invalid", result["failures"])
                if mutation == "true":
                    self.assertIn("authority_summary_true", result["failures"])
                self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_json_safe_must_be_exact_true(self):
        for value in (False, "true", 1, None):
            with self.subTest(value=value):
                payload = _valid_payload()
                payload["boundary"]["json_safe"] = value

                result = _consume(payload)

                self.assertFalse(result["ci_ok"])
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn("json_safe_invalid", result["failures"])

    def test_missing_json_safe_fails_closed(self):
        payload = _valid_payload()
        payload["boundary"].pop("json_safe")

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertIn("boundary_shape_mismatch", result["failures"])
        self.assertIn("json_safe_invalid", result["failures"])

    def test_deterministic_failure_ordering(self):
        payload = _valid_payload()
        payload["validator_checkpoint_commit"] = "wrong"
        payload["validator_checkpoint_tag"] = "wrong"
        payload["boundary"]["surface"] = "WrongSurface"
        payload["boundary"]["source_refs"] = {}
        payload["authority"]["runtime_authority_checker_authorized"] = True

        result = _consume(payload)

        self.assertEqual(
            result["failures"],
            [
                "checkpoint_tag_invalid",
                "checkpoint_commit_invalid",
                "boundary_surface_invalid",
                "source_ref_mismatch",
                "authority_summary_invalid",
                "authority_summary_true",
            ],
        )

    def test_input_immutability(self):
        payload = _valid_payload()
        original = copy.deepcopy(payload)

        _consume(payload)

        self.assertEqual(payload, original)

    def test_manifest_defensive_copy_and_json_safe(self):
        manifest = _manifest()
        manifest["expected_source_refs"]["read-only-governance-layer-v1"] = "mutated"

        fresh = _manifest()

        self.assertNotEqual(
            fresh["expected_source_refs"]["read-only-governance-layer-v1"],
            "mutated",
        )
        _assert_json_safe_without_leak(self, fresh)

    def test_result_does_not_leak_raw_object_identity(self):
        payload = _valid_payload()
        payload["boundary"]["checker_boundary"]["future_only"] = RuntimeLeak()
        payload["authority"]["runtime_authority_checker_authorized"] = RuntimeLeak()

        result = _consume(payload)

        self.assertFalse(result["ci_ok"])
        _assert_json_safe_without_leak(self, result)

    def test_non_authority_semantics_are_hard_false(self):
        manifest = _manifest()
        statement = manifest["non_authority_statement"]

        self.assertEqual(
            statement["ci_ok_proves"],
            "structural_validity_for_read_only_stack_consolidation_only",
        )
        for key in (
            "runtime_authorized",
            "checker_runtime_authorized",
            "enforcer_runtime_authorized",
            "service_calls_authorized",
            "db_repository_uow_authorized",
            "evidence_audit_append_authorized",
            "transaction_runtime_authorized",
            "idempotency_reservation_authorized",
            "rollback_runtime_authorized",
            "executor_dispatch_authorized",
            "durable_writes_authorized",
            "irreversible_actions_authorized",
        ):
            self.assertIs(statement[key], False)

    def test_ci_ok_does_not_authorize_any_runtime_or_write_surface(self):
        result = _consume(_valid_payload())

        self.assertTrue(result["ci_ok"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        for flag in result["boundary"]["required_false_authority_flags"].values():
            self.assertIs(flag, False)
        for declaration in (
            "runtime_authority_checker_forbidden",
            "runtime_authority_enforcer_forbidden",
            "runtime_authority_runtime_forbidden",
            "service_calls_forbidden",
            "service_call_execution_forbidden",
            "db_repository_uow_writes_forbidden",
            "evidence_append_forbidden",
            "audit_append_forbidden",
            "transaction_runtime_forbidden",
            "idempotency_reservation_forbidden",
            "rollback_runtime_forbidden",
            "executor_dispatch_forbidden",
            "durable_writes_forbidden",
            "irreversible_actions_forbidden",
        ):
            self.assertIs(
                result["boundary"]["required_true_declarations"][declaration],
                True,
            )


if __name__ == "__main__":
    unittest.main()
