"""
P0-47 phase 1 - RecoverySessionHost cross-phase digest contract checkpoint.

These tests pin the rendered cross-phase digest contract boundary as a
read-only contract envelope for downstream consumers.
"""

from __future__ import annotations

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from kernel.lifecycle import (
    recovery_session_host_verdict_cross_phase_digest_contract as contract_module,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract import (
    check_recovery_session_host_verdict_cross_phase_digest_contract,
    recovery_session_host_verdict_cross_phase_digest_contract_manifest,
    render_recovery_session_host_verdict_cross_phase_digest_contract_check,
)
from tests.tracer_bullet.test_recovery_session_host_cli import (
    _assert_json_safe_no_runtime_types,
    _assert_no_runtime_repr_strings,
    _table_row_counts,
)
from tests.tracer_bullet.test_recovery_session_host_factory import (
    _initialize_empty_db,
    _seed_inference_stage,
)
from tests.tracer_bullet.test_recovery_session_host_verdict_cross_phase_digest_contract_acceptance import (
    _collect_real_operator_payloads,
    _rendered_check_from_payloads,
    _rendered_contract_check,
    _rendered_cross_phase_digest,
    _rendered_self_comparison,
)


_EXPECTED_MANIFEST_KEYS = {
    "surface",
    "version",
    "input_shape",
    "top_level_keys",
    "digest_keys",
    "failure_values",
    "reason_codes",
    "contract_ready_requires",
    "restore_supported",
    "durable_writes",
    "cli_commands",
    "runtime_dependencies",
    "json_safe",
}
_EXPECTED_DIGEST_KEYS = [
    "after_manifest_version",
    "after_reason_code",
    "after_ready",
    "before_manifest_version",
    "before_reason_code",
    "before_ready",
    "cli_command_count",
    "comparison_change_count",
    "comparison_changed",
    "comparison_failure_count",
    "comparison_ok",
    "comparison_reason_code",
    "contract_failure_count",
    "contract_ready",
    "contract_reason_code",
    "cross_phase_ok",
    "durable_writes",
    "failures",
    "has_cli_commands",
    "has_contract_failure",
    "has_drift",
    "has_restore_or_durable_surface",
    "has_runtime_dependencies",
    "json_safe",
    "manifest_surface",
    "manifest_version",
    "operator_safe",
    "reason_code",
    "restore_supported",
    "runtime_dependency_count",
]
_EXPECTED_FAILURE_VALUES = [
    "check_failures_invalid",
    "check_manifest_invalid",
    "check_manifest_shape_mismatch",
    "check_not_mapping",
    "check_shape_mismatch",
    "comparison_failures_invalid",
    "comparison_not_mapping",
    "comparison_report_invalid",
    "comparison_report_shape_mismatch",
    "comparison_shape_mismatch",
]
_EXPECTED_READY_REQUIRES = {
    "ok": True,
    "reason_code": "ok",
    "failures": [],
    "digest.cross_phase_ok": True,
    "digest.reason_code": "ok",
    "digest.failures": [],
    "digest.operator_safe": True,
}
_EXPECTED_PUBLIC_API = {
    "RecoverySessionHostVerdictCrossPhaseDigestContractCheck",
    "recovery_session_host_verdict_cross_phase_digest_contract_manifest",
    "check_recovery_session_host_verdict_cross_phase_digest_contract",
    "render_recovery_session_host_verdict_cross_phase_digest_contract_check",
}
_FORBIDDEN_RUNTIME_NAMES = {
    "sqlite3",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
    "recovery_session_host_verdict_summary_manifest",
    "recovery_session_host_verdict_summary_comparator",
    "recovery_session_host_verdict_cross_phase_digest",
    "recovery_cli",
    "RecoverySessionHost",
    "RecoveryGate",
    "SignablePathOrchestrator",
    "KernelUnitOfWork",
    "build_parser",
    "main",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "build_recovery_session_host_verdict_summary",
    "check_recovery_session_host_verdict_summary_contract",
    "compare_recovery_session_host_verdict_summary_checks",
    "build_recovery_session_host_verdict_cross_phase_digest",
}
_FORBIDDEN_SOURCE_MARKERS = {
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "KernelUnitOfWork",
    "open_connection",
    "sqlite3",
    "apply_migrations",
    "build_parser",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "build_recovery_session_host_verdict_summary",
    "check_recovery_session_host_verdict_summary_contract",
    "compare_recovery_session_host_verdict_summary_checks",
    "build_recovery_session_host_verdict_cross_phase_digest",
    "recovery_session_host_cli",
}


def _seeded_db(tmpdir: Path) -> tuple[Path, str]:
    db_path = tmpdir / "factory.db"
    task_id = f"task-{uuid4().hex[:8]}"
    _initialize_empty_db(db_path)
    _seed_inference_stage(db_path, task_id)
    return db_path, task_id


def _safe_real_rendered_cross_phase_digest(
    tmpdir: Path,
) -> tuple[dict[str, object], Path, Path]:
    db_path, task_id = _seeded_db(tmpdir)
    payloads, _by_name, missing_path = _collect_real_operator_payloads(
        tmpdir=tmpdir,
        db_path=db_path,
        task_id=task_id,
    )
    rendered_check = _rendered_check_from_payloads(list(payloads))
    rendered_comparison = _rendered_self_comparison(rendered_check)
    rendered_digest = _rendered_cross_phase_digest(
        rendered_check,
        rendered_comparison,
    )
    return rendered_digest, db_path, missing_path


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


def _contract_public_api() -> set[str]:
    return {
        name
        for name, value in inspect.getmembers(contract_module)
        if not name.startswith("_")
        and getattr(value, "__module__", None) == contract_module.__name__
        and (inspect.isclass(value) or inspect.isfunction(value))
    }


class TestRecoverySessionHostVerdictCrossPhaseDigestContractPhaseCheckpoint(
    unittest.TestCase
):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_phase_checkpoint_contract_boundary_is_frozen_read_only(
        self,
    ) -> None:
        rendered_digest, _db_path, _missing_path = (
            _safe_real_rendered_cross_phase_digest(self.tmpdir)
        )

        contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )

        self.assertIs(contract_check.ready, True)
        self.assertEqual(contract_check.reason_code, "ready")
        self.assertEqual(contract_check.failures, ())
        self.assertEqual(
            set(rendered_contract),
            {"ready", "reason_code", "failures", "contract"},
        )
        self.assertIs(rendered_contract["ready"], True)
        self.assertEqual(rendered_contract["reason_code"], "ready")
        self.assertEqual(rendered_contract["failures"], [])
        contract = rendered_contract["contract"]
        self.assertIsInstance(contract, dict)
        self.assertEqual(
            contract["surface"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertEqual(contract["version"], 1)
        _json_round_trips(rendered_contract)

    def test_phase_checkpoint_contract_boundary_has_no_runtime_mutation_paths(
        self,
    ) -> None:
        db_path, task_id = _seeded_db(self.tmpdir)
        before_counts = _table_row_counts(db_path)
        files_before_pipeline = _relative_files(self.tmpdir)
        payloads, _by_name, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        rendered_check = _rendered_check_from_payloads(list(payloads))
        rendered_comparison = _rendered_self_comparison(rendered_check)
        rendered_digest = _rendered_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )
        files_before_contract = _relative_files(self.tmpdir)

        contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )

        self.assertIs(contract_check.ready, True)
        self.assertIs(rendered_contract["ready"], True)
        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_pipeline)
        self.assertEqual(_relative_files(self.tmpdir), files_before_contract)

    def test_phase_checkpoint_contract_manifest_shape_is_frozen(
        self,
    ) -> None:
        manifest = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )

        self.assertEqual(set(manifest), _EXPECTED_MANIFEST_KEYS)
        self.assertEqual(
            manifest["surface"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            manifest["input_shape"],
            "rendered_cross_phase_digest",
        )
        self.assertEqual(
            manifest["top_level_keys"],
            ["digest", "failures", "ok", "reason_code"],
        )
        self.assertIs(manifest["restore_supported"], False)
        self.assertIs(manifest["durable_writes"], False)
        self.assertEqual(manifest["cli_commands"], [])
        self.assertEqual(manifest["runtime_dependencies"], [])
        self.assertIs(manifest["json_safe"], True)
        _json_round_trips(manifest)

    def test_phase_checkpoint_contract_digest_keys_are_frozen(self) -> None:
        manifest = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )

        self.assertEqual(manifest["digest_keys"], _EXPECTED_DIGEST_KEYS)

    def test_phase_checkpoint_contract_failure_values_are_frozen(
        self,
    ) -> None:
        manifest = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )

        self.assertEqual(
            manifest["failure_values"],
            _EXPECTED_FAILURE_VALUES,
        )

    def test_phase_checkpoint_contract_ready_requires_is_frozen(self) -> None:
        manifest = (
            recovery_session_host_verdict_cross_phase_digest_contract_manifest()
        )

        self.assertEqual(
            manifest["contract_ready_requires"],
            _EXPECTED_READY_REQUIRES,
        )

    def test_phase_checkpoint_contract_ready_not_ready_invalid_semantics_are_frozen(
        self,
    ) -> None:
        rendered_digest, _db_path, _missing_path = (
            _safe_real_rendered_cross_phase_digest(self.tmpdir)
        )

        safe_check = (
            check_recovery_session_host_verdict_cross_phase_digest_contract(
                rendered_digest
            )
        )

        self.assertIs(safe_check.ready, True)
        self.assertEqual(safe_check.reason_code, "ready")
        self.assertEqual(safe_check.failures, ())

        unsafe_digest = copy.deepcopy(rendered_digest)
        digest = unsafe_digest["digest"]
        self.assertIsInstance(digest, dict)
        digest["operator_safe"] = False
        digest["has_drift"] = True
        digest["comparison_changed"] = True
        digest["comparison_change_count"] = 1

        unsafe_check = (
            check_recovery_session_host_verdict_cross_phase_digest_contract(
                unsafe_digest
            )
        )

        self.assertIs(unsafe_check.ready, False)
        self.assertEqual(unsafe_check.reason_code, "not_ready")
        self.assertEqual(unsafe_check.failures, ())

        invalid_digest = copy.deepcopy(rendered_digest)
        invalid_digest["extra"] = True

        invalid_check = (
            check_recovery_session_host_verdict_cross_phase_digest_contract(
                invalid_digest
            )
        )

        self.assertIs(invalid_check.ready, False)
        self.assertEqual(
            invalid_check.reason_code,
            "invalid_cross_phase_digest",
        )
        self.assertIn("payload_shape_mismatch", invalid_check.failures)

    def test_phase_checkpoint_contract_validation_failure_order_is_frozen(
        self,
    ) -> None:
        rendered_digest, _db_path, _missing_path = (
            _safe_real_rendered_cross_phase_digest(self.tmpdir)
        )
        rendered_digest["extra"] = True
        rendered_digest["reason_code"] = "weird"
        rendered_digest["failures"] = ["ok", 1]
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)
        digest["operator_safe"] = "yes"
        digest["runtime_dependency_count"] = "1"
        digest["cli_command_count"] = 1
        digest["has_cli_commands"] = False

        check = check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )

        self.assertEqual(
            check.failures,
            (
                "payload_shape_mismatch",
                "reason_code_invalid",
                "failures_invalid",
                "digest_bool_invalid",
                "digest_counter_invalid",
                "hazard_flag_inconsistent",
            ),
        )

        non_mapping_check = (
            check_recovery_session_host_verdict_cross_phase_digest_contract(
                "bad"
            )
        )

        self.assertEqual(non_mapping_check.failures, ("payload_not_mapping",))

    def test_phase_checkpoint_contract_hazard_flags_are_frozen(self) -> None:
        cases = (
            (
                "runtime dependency count",
                {
                    "runtime_dependency_count": 1,
                    "has_runtime_dependencies": False,
                },
            ),
            (
                "cli command count",
                {"cli_command_count": 1, "has_cli_commands": False},
            ),
            (
                "restore supported",
                {
                    "restore_supported": True,
                    "has_restore_or_durable_surface": False,
                },
            ),
            (
                "durable writes",
                {
                    "durable_writes": True,
                    "has_restore_or_durable_surface": False,
                },
            ),
            (
                "contract failure",
                {"contract_ready": False, "has_contract_failure": False},
            ),
            (
                "drift",
                {
                    "comparison_changed": True,
                    "comparison_change_count": 1,
                    "has_drift": False,
                },
            ),
        )

        for name, updates in cases:
            with self.subTest(name=name):
                rendered_digest, _db_path, _missing_path = (
                    _safe_real_rendered_cross_phase_digest(self.tmpdir)
                )
                digest = rendered_digest["digest"]
                self.assertIsInstance(digest, dict)
                digest["operator_safe"] = False
                digest.update(updates)

                check = (
                    check_recovery_session_host_verdict_cross_phase_digest_contract(
                        rendered_digest
                    )
                )

                self.assertIn("hazard_flag_inconsistent", check.failures)

    def test_phase_checkpoint_contract_renderer_shape_and_defensive_copy_are_frozen(
        self,
    ) -> None:
        rendered_digest, _db_path, _missing_path = (
            _safe_real_rendered_cross_phase_digest(self.tmpdir)
        )
        check, rendered_contract = _rendered_contract_check(rendered_digest)
        original_contract = copy.deepcopy(check.contract)

        self.assertEqual(
            set(rendered_contract),
            {"ready", "reason_code", "failures", "contract"},
        )
        contract = rendered_contract["contract"]
        self.assertIsInstance(contract, dict)
        digest_keys = contract["digest_keys"]
        self.assertIsInstance(digest_keys, list)
        digest_keys.append("mutated")
        rendered_again = (
            render_recovery_session_host_verdict_cross_phase_digest_contract_check(
                check
            )
        )

        self.assertEqual(check.contract, original_contract)
        self.assertEqual(rendered_again["contract"], original_contract)

    def test_phase_checkpoint_contract_output_is_json_safe_and_no_runtime_repr(
        self,
    ) -> None:
        rendered_digest, _db_path, _missing_path = (
            _safe_real_rendered_cross_phase_digest(self.tmpdir)
        )
        _check, rendered_contract = _rendered_contract_check(rendered_digest)

        _json_round_trips(rendered_contract)
        _assert_json_safe_no_runtime_types(rendered_contract)
        _assert_no_runtime_repr_strings(rendered_contract)

    def test_phase_checkpoint_contract_surface_public_api_is_frozen(
        self,
    ) -> None:
        self.assertEqual(_contract_public_api(), _EXPECTED_PUBLIC_API)

    def test_phase_checkpoint_contract_surface_has_no_forbidden_runtime_references(
        self,
    ) -> None:
        public_function_names = {
            name
            for name, value in inspect.getmembers(contract_module)
            if not name.startswith("_")
            and getattr(value, "__module__", None) == contract_module.__name__
            and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(function=name):
                self.assertNotIn("restore", name)

        for name in _FORBIDDEN_RUNTIME_NAMES:
            with self.subTest(module_name=name):
                self.assertNotIn(name, contract_module.__dict__)

        source = inspect.getsource(contract_module)
        for marker in _FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(source_marker=marker):
                self.assertNotIn(marker, source)

    def test_phase_checkpoint_contract_summary_for_ci(self) -> None:
        rendered_digest, _db_path, _missing_path = (
            _safe_real_rendered_cross_phase_digest(self.tmpdir)
        )
        _check, rendered_contract = _rendered_contract_check(rendered_digest)
        contract = rendered_contract["contract"]
        self.assertIsInstance(contract, dict)
        checkpoint_summary = {
            "phase": (
                "recovery_session_host_verdict_cross_phase_digest_contract_checkpoint"
            ),
            "contract_ready": rendered_contract["ready"],
            "reason_code": rendered_contract["reason_code"],
            "surface": contract["surface"],
            "version": contract["version"],
            "restore_supported": contract["restore_supported"],
            "durable_writes": contract["durable_writes"],
            "cli_commands": contract["cli_commands"],
            "runtime_dependencies": contract["runtime_dependencies"],
            "json_safe": contract["json_safe"],
        }

        self.assertEqual(
            checkpoint_summary["phase"],
            "recovery_session_host_verdict_cross_phase_digest_contract_checkpoint",
        )
        self.assertIs(checkpoint_summary["contract_ready"], True)
        self.assertEqual(checkpoint_summary["reason_code"], "ready")
        self.assertEqual(
            checkpoint_summary["surface"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertEqual(checkpoint_summary["version"], 1)
        self.assertIs(checkpoint_summary["restore_supported"], False)
        self.assertIs(checkpoint_summary["durable_writes"], False)
        self.assertEqual(checkpoint_summary["cli_commands"], [])
        self.assertEqual(checkpoint_summary["runtime_dependencies"], [])
        self.assertIs(checkpoint_summary["json_safe"], True)
        _json_round_trips(checkpoint_summary)


if __name__ == "__main__":
    unittest.main()
