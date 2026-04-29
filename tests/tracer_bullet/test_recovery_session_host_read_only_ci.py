"""Tests for the read-only CI consumer over rendered contract checks."""

import inspect
import json
import unittest
from copy import deepcopy
from unittest import mock

from kernel.lifecycle import recovery_session_host_read_only_ci
from kernel.lifecycle.recovery_session_host_read_only_ci import (
    consume_recovery_session_host_read_only_ci,
    recovery_session_host_read_only_ci_manifest,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract import (
    check_recovery_session_host_verdict_cross_phase_digest_contract,
    render_recovery_session_host_verdict_cross_phase_digest_contract_check,
)


def _safe_digest() -> dict[str, object]:
    return {
        "ok": True,
        "reason_code": "ok",
        "failures": [],
        "digest": {
            "after_manifest_version": 1,
            "after_reason_code": "ok",
            "after_ready": True,
            "before_manifest_version": 1,
            "before_reason_code": "ok",
            "before_ready": True,
            "cli_command_count": 0,
            "comparison_change_count": 0,
            "comparison_changed": False,
            "comparison_failure_count": 0,
            "comparison_ok": True,
            "comparison_reason_code": "ok",
            "contract_failure_count": 0,
            "contract_ready": True,
            "contract_reason_code": "ok",
            "cross_phase_ok": True,
            "durable_writes": False,
            "failures": [],
            "has_cli_commands": False,
            "has_contract_failure": False,
            "has_drift": False,
            "has_restore_or_durable_surface": False,
            "has_runtime_dependencies": False,
            "json_safe": True,
            "manifest_surface": "recovery_session_host_verdict_summary",
            "manifest_version": 1,
            "operator_safe": True,
            "reason_code": "ok",
            "restore_supported": False,
            "runtime_dependency_count": 0,
        },
    }


def _rendered_payload(digest: dict[str, object]) -> dict[str, object]:
    check = check_recovery_session_host_verdict_cross_phase_digest_contract(
        digest
    )
    return render_recovery_session_host_verdict_cross_phase_digest_contract_check(
        check
    )


class TestRecoverySessionHostReadOnlyCi(unittest.TestCase):
    def test_public_api_is_exact(self) -> None:
        self.assertEqual(
            sorted(recovery_session_host_read_only_ci.__all__),
            [
                "consume_recovery_session_host_read_only_ci",
                "recovery_session_host_read_only_ci_manifest",
            ],
        )

    def test_manifest_is_defensive_and_json_safe(self) -> None:
        manifest_a = recovery_session_host_read_only_ci_manifest()
        manifest_b = recovery_session_host_read_only_ci_manifest()
        self.assertEqual(manifest_a, manifest_b)
        manifest_a["restore_supported"] = True
        manifest_a["cli_commands"].append("rogue")
        manifest_c = recovery_session_host_read_only_ci_manifest()
        self.assertEqual(manifest_b, manifest_c)
        json.dumps(manifest_c)
        self.assertEqual(manifest_c["restore_supported"], False)
        self.assertEqual(manifest_c["durable_writes"], False)
        self.assertEqual(manifest_c["cli_commands"], [])
        self.assertEqual(manifest_c["runtime_dependencies"], [])
        self.assertIs(manifest_c["json_safe"], True)

    def test_accepts_real_safe_rendered_contract_check_payload(self) -> None:
        payload = _rendered_payload(_safe_digest())
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(
            result["surface"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertEqual(result["version"], 1)
        self.assertIs(result["contract_ready"], True)
        self.assertEqual(result["contract_reason_code"], "ready")
        self.assertIs(result["restore_supported"], False)
        self.assertIs(result["durable_writes"], False)
        self.assertEqual(result["cli_command_count"], 0)
        self.assertEqual(result["runtime_dependency_count"], 0)
        self.assertIs(result["json_safe"], True)

    def test_output_shape_is_exact(self) -> None:
        payload = _rendered_payload(_safe_digest())
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertEqual(
            sorted(result.keys()),
            [
                "ci_ok",
                "cli_command_count",
                "contract_ready",
                "contract_reason_code",
                "durable_writes",
                "failures",
                "json_safe",
                "reason_code",
                "restore_supported",
                "runtime_dependency_count",
                "surface",
                "version",
            ],
        )

    def test_output_is_json_safe(self) -> None:
        payload = _rendered_payload(_safe_digest())
        result = consume_recovery_session_host_read_only_ci(payload)
        json.dumps(result)
        self.assertIsInstance(result["failures"], list)

    def test_rejects_non_mapping_payload(self) -> None:
        for bad in [None, 0, "ready", [], (), 3.14, True]:
            with self.subTest(bad=bad):
                result = consume_recovery_session_host_read_only_ci(bad)
                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["invalid_ci_payload"])
                self.assertIs(result["contract_ready"], False)
                self.assertEqual(
                    result["contract_reason_code"], "invalid_ci_payload"
                )
                self.assertIsNone(result["surface"])
                self.assertIsNone(result["version"])
                self.assertIsNone(result["restore_supported"])
                self.assertIsNone(result["durable_writes"])
                self.assertIsNone(result["cli_command_count"])
                self.assertIsNone(result["runtime_dependency_count"])
                self.assertIsNone(result["json_safe"])

    def test_rejects_payload_with_extra_or_missing_keys(self) -> None:
        payload = _rendered_payload(_safe_digest())
        extra = dict(payload)
        extra["extra"] = True
        result = consume_recovery_session_host_read_only_ci(extra)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")

        missing = dict(payload)
        del missing["contract"]
        result_missing = consume_recovery_session_host_read_only_ci(missing)
        self.assertEqual(
            result_missing["reason_code"], "invalid_ci_payload"
        )

    def test_rejects_invalid_field_types(self) -> None:
        base = _rendered_payload(_safe_digest())
        cases = [
            {**base, "ready": "yes"},
            {**base, "ready": 1},
            {**base, "reason_code": 7},
            {**base, "failures": "ready"},
            {**base, "failures": [1]},
            {**base, "contract": "ready"},
            {**base, "contract": None},
        ]
        for bad in cases:
            with self.subTest(bad=bad):
                result = consume_recovery_session_host_read_only_ci(bad)
                self.assertIs(result["ci_ok"], False)
                self.assertEqual(
                    result["reason_code"], "invalid_ci_payload"
                )

    def test_marks_real_not_ready_payload_ci_ok_false(self) -> None:
        unsafe = _safe_digest()
        unsafe["digest"]["operator_safe"] = False
        # Make the digest internally consistent for the contract check.
        unsafe["digest"]["cross_phase_ok"] = False
        unsafe["digest"]["reason_code"] = "invalid_cross_phase_digest"
        unsafe["digest"]["failures"] = ["check_failures_invalid"]
        unsafe["ok"] = False
        unsafe["reason_code"] = "invalid_cross_phase_digest"
        unsafe["failures"] = ["check_failures_invalid"]
        payload = _rendered_payload(unsafe)
        # The contract check itself returns invalid_cross_phase_digest because
        # the digest fails internal validation; contract_ready False at CI.
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIs(result["contract_ready"], False)
        self.assertNotEqual(result["contract_reason_code"], "ready")

    def test_marks_structurally_valid_not_ready_payload_ci_ok_false(
        self,
    ) -> None:
        # Hand-crafted payload that is structurally valid but contract is not
        # ready. We bypass the contract module entirely so the test is direct.
        payload = {
            "ready": False,
            "reason_code": "not_ready",
            "failures": [],
            "contract": dict(recovery_session_host_read_only_ci_manifest()),
        }
        # Re-shape contract to the digest contract manifest's surface.
        payload["contract"] = {
            "surface": "recovery_session_host_verdict_cross_phase_digest",
            "version": 1,
            "restore_supported": False,
            "durable_writes": False,
            "cli_commands": [],
            "runtime_dependencies": [],
            "json_safe": True,
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIs(result["contract_ready"], False)
        self.assertEqual(result["contract_reason_code"], "not_ready")
        self.assertEqual(result["failures"], [])

    def test_detects_restore_hazard(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": "x",
                "version": 1,
                "restore_supported": True,
                "durable_writes": False,
                "cli_commands": [],
                "runtime_dependencies": [],
                "json_safe": True,
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIn("restore_supported", result["failures"])
        self.assertIs(result["restore_supported"], True)

    def test_detects_durable_writes_hazard(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": "x",
                "version": 1,
                "restore_supported": False,
                "durable_writes": True,
                "cli_commands": [],
                "runtime_dependencies": [],
                "json_safe": True,
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn("durable_writes", result["failures"])
        self.assertIs(result["durable_writes"], True)

    def test_detects_cli_commands_hazard(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": "x",
                "version": 1,
                "restore_supported": False,
                "durable_writes": False,
                "cli_commands": ["recovery", "restore"],
                "runtime_dependencies": [],
                "json_safe": True,
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn("has_cli_commands", result["failures"])
        self.assertEqual(result["cli_command_count"], 2)

    def test_detects_runtime_dependency_hazard(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": "x",
                "version": 1,
                "restore_supported": False,
                "durable_writes": False,
                "cli_commands": [],
                "runtime_dependencies": ["sqlite3"],
                "json_safe": True,
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn("has_runtime_dependencies", result["failures"])
        self.assertEqual(result["runtime_dependency_count"], 1)

    def test_detects_json_safe_false_hazard(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": "x",
                "version": 1,
                "restore_supported": False,
                "durable_writes": False,
                "cli_commands": [],
                "runtime_dependencies": [],
                "json_safe": False,
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIn("not_json_safe", result["failures"])
        self.assertIs(result["json_safe"], False)

    def test_detects_invalid_contract_field_types(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": 0,
                "version": "v1",
                "restore_supported": "no",
                "durable_writes": 0,
                "cli_commands": "none",
                "runtime_dependencies": [1, 2],
                "json_safe": "yes",
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        self.assertIs(result["ci_ok"], False)
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])
        self.assertIsNone(result["restore_supported"])
        self.assertIsNone(result["durable_writes"])
        self.assertIsNone(result["cli_command_count"])
        self.assertIsNone(result["runtime_dependency_count"])
        self.assertIsNone(result["json_safe"])
        self.assertIn(
            "contract_restore_supported_invalid", result["failures"]
        )
        self.assertIn("contract_durable_writes_invalid", result["failures"])
        self.assertIn("contract_cli_commands_invalid", result["failures"])
        self.assertIn(
            "contract_runtime_dependencies_invalid", result["failures"]
        )
        self.assertIn("contract_json_safe_invalid", result["failures"])

    def test_does_not_mutate_input(self) -> None:
        payload = _rendered_payload(_safe_digest())
        snapshot = deepcopy(payload)
        consume_recovery_session_host_read_only_ci(payload)
        self.assertEqual(payload, snapshot)

    def test_output_failures_list_is_independent(self) -> None:
        payload = {
            "ready": True,
            "reason_code": "ready",
            "failures": [],
            "contract": {
                "surface": "x",
                "version": 1,
                "restore_supported": True,
                "durable_writes": False,
                "cli_commands": [],
                "runtime_dependencies": [],
                "json_safe": True,
            },
        }
        result = consume_recovery_session_host_read_only_ci(payload)
        result["failures"].append("rogue")
        result_again = consume_recovery_session_host_read_only_ci(payload)
        self.assertNotIn("rogue", result_again["failures"])

    def test_module_has_no_runtime_dependencies(self) -> None:
        source = inspect.getsource(recovery_session_host_read_only_ci)
        forbidden_imports = (
            "recovery_session_host_verdict_cross_phase_digest_contract",
            "recovery_session_host_verdict_cross_phase_digest",
            "recovery_session_host_verdict_summary_comparator",
            "recovery_session_host_verdict_summary_manifest",
            "recovery_session_host_verdict_summary",
            "recovery_session_host_verdict_aggregator",
            "recovery_session_host_cli",
            "recovery_session_host_factory",
            "recovery_session_host",
            "recovery_cli",
            "recovery_gate",
            "task_recovery",
        )
        for name in forbidden_imports:
            with self.subTest(name=name):
                self.assertNotIn(f"import {name}", source)
                self.assertNotIn(f"from kernel.lifecycle.{name}", source)
        forbidden_runtime = (
            "import os",
            "import sys",
            "import sqlite3",
            "import subprocess",
            "import asyncio",
            "import threading",
            "open(",
            "os.environ",
            "subprocess.",
            "Path(",
        )
        for name in forbidden_runtime:
            with self.subTest(name=name):
                self.assertNotIn(name, source)

    def test_no_restore_or_command_creep(self) -> None:
        source = inspect.getsource(recovery_session_host_read_only_ci)
        forbidden_terms = (
            "def restore",
            "perform_restore",
            "execute_restore",
            "argparse",
            "sys.argv",
            "click.",
            "typer.",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_does_not_call_upstream_runtime(self) -> None:
        payload = _rendered_payload(_safe_digest())
        with mock.patch(
            "kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract"
            ".check_recovery_session_host_verdict_cross_phase_digest_contract"
        ) as check_call, mock.patch(
            "kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract"
            ".render_recovery_session_host_verdict_cross_phase_digest_contract_check"
        ) as render_call:
            consume_recovery_session_host_read_only_ci(payload)
            self.assertEqual(check_call.call_count, 0)
            self.assertEqual(render_call.call_count, 0)


if __name__ == "__main__":
    unittest.main()
