"""
P0-46 phase 1 - RecoverySessionHost cross-phase digest contract acceptance.

These tests prove the read-only cross-phase digest contract checker consumes
real rendered cross-phase digest payloads derived from the frozen operator
surface through aggregation, summary, manifest check, comparator, and digest.
"""

from __future__ import annotations

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from uuid import uuid4

from kernel.lifecycle import recovery_session_host_cli
from kernel.lifecycle import recovery_session_host_verdict_aggregator as aggregator_module
from kernel.lifecycle import (
    recovery_session_host_verdict_cross_phase_digest as digest_module,
)
from kernel.lifecycle import (
    recovery_session_host_verdict_cross_phase_digest_contract as contract_module,
)
from kernel.lifecycle import (
    recovery_session_host_verdict_summary as summary_module,
)
from kernel.lifecycle import (
    recovery_session_host_verdict_summary_comparator as comparator_module,
)
from kernel.lifecycle import (
    recovery_session_host_verdict_summary_manifest as manifest_module,
)
from kernel.lifecycle.recovery_session_host_cli import (
    EXIT_FACTORY_ERROR,
    EXIT_OK,
    current_recovery_session_host_cli_readiness_payload,
    current_recovery_session_host_cli_readiness_smoke,
    render_recovery_session_host_cli_readiness_smoke,
)
from kernel.lifecycle.recovery_session_host_verdict_aggregator import (
    aggregate_recovery_session_host_operator_verdicts,
    render_recovery_session_host_verdict_aggregation,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest import (
    build_recovery_session_host_verdict_cross_phase_digest,
    render_recovery_session_host_verdict_cross_phase_digest,
)
from kernel.lifecycle.recovery_session_host_verdict_cross_phase_digest_contract import (
    check_recovery_session_host_verdict_cross_phase_digest_contract,
    render_recovery_session_host_verdict_cross_phase_digest_contract_check,
)
from kernel.lifecycle.recovery_session_host_verdict_summary import (
    build_recovery_session_host_verdict_summary,
    render_recovery_session_host_verdict_summary,
)
from kernel.lifecycle.recovery_session_host_verdict_summary_comparator import (
    compare_recovery_session_host_verdict_summary_checks,
    render_recovery_session_host_verdict_summary_comparison,
)
from kernel.lifecycle.recovery_session_host_verdict_summary_manifest import (
    check_recovery_session_host_verdict_summary_contract,
    render_recovery_session_host_verdict_summary_contract_check,
)
from tests.tracer_bullet.test_recovery_session_host_cli import (
    _assert_json_safe_no_runtime_types,
    _assert_no_runtime_repr_strings,
    _assert_single_json_line,
    _invoke,
    _table_row_counts,
)
from tests.tracer_bullet.test_recovery_session_host_factory import (
    _initialize_empty_db,
    _seed_inference_stage,
)


_FORBIDDEN_SOURCE_MARKERS = (
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "build_parser",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "render_recovery_session_host_verdict_aggregation",
    "build_recovery_session_host_verdict_summary",
    "render_recovery_session_host_verdict_summary",
    "check_recovery_session_host_verdict_summary_contract",
    "render_recovery_session_host_verdict_summary_contract_check",
    "compare_recovery_session_host_verdict_summary_checks",
    "render_recovery_session_host_verdict_summary_comparison",
    "build_recovery_session_host_verdict_cross_phase_digest",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
    "recovery_session_host_verdict_summary_manifest",
    "recovery_session_host_verdict_summary_comparator",
    "sqlite3",
    "open_connection",
    "apply_migrations",
    "KernelUnitOfWork",
)
_ALLOWED_CROSS_PHASE_DIGEST_CONTRACT_SOURCE_LINES = {
    '"surface": "recovery_session_host_verdict_cross_phase_digest",',
    "def recovery_session_host_verdict_cross_phase_digest_contract_manifest() -> (",
    "def check_recovery_session_host_verdict_cross_phase_digest_contract(",
    "contract = recovery_session_host_verdict_cross_phase_digest_contract_manifest()",
    "def render_recovery_session_host_verdict_cross_phase_digest_contract_check(",
}


def _invoke_json_payload(
    argv: list[str],
    *,
    expected_code: int,
    name: str,
) -> dict[str, object]:
    code, stdout, stderr = _invoke(argv)
    if code != expected_code:
        raise AssertionError(
            f"{name} expected exit code {expected_code}, got {code}"
        )
    if stderr != "":
        raise AssertionError(f"{name} emitted stderr: {stderr!r}")
    return _assert_single_json_line(stdout)


def _collect_real_operator_payloads(
    *,
    tmpdir: Path,
    db_path: Path,
    task_id: str,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], Path]:
    missing_path = tmpdir / "missing.db"
    cases = (
        (
            "factory_check_valid",
            ["factory-check", "--db", str(db_path)],
            EXIT_OK,
        ),
        (
            "evaluate_existing",
            ["evaluate", "--db", str(db_path), "--task-id", task_id],
            EXIT_OK,
        ),
        (
            "evaluate_unknown",
            [
                "evaluate",
                "--db",
                str(db_path),
                "--task-id",
                "unknown-task",
            ],
            EXIT_OK,
        ),
        (
            "factory_check_missing",
            ["factory-check", "--db", str(missing_path)],
            EXIT_FACTORY_ERROR,
        ),
        (
            "evaluate_missing",
            [
                "evaluate",
                "--db",
                str(missing_path),
                "--task-id",
                "missing-task",
            ],
            EXIT_FACTORY_ERROR,
        ),
    )

    payloads: list[dict[str, object]] = []
    by_name: dict[str, dict[str, object]] = {}
    for name, argv, expected_code in cases:
        payload = _invoke_json_payload(
            argv,
            expected_code=expected_code,
            name=name,
        )
        by_name[name] = payload
        payloads.append(payload)

    readiness_payload = current_recovery_session_host_cli_readiness_payload()
    smoke_payload = render_recovery_session_host_cli_readiness_smoke(
        current_recovery_session_host_cli_readiness_smoke()
    )
    by_name["readiness"] = readiness_payload
    by_name["smoke"] = smoke_payload
    payloads.extend([readiness_payload, smoke_payload])
    return payloads, by_name, missing_path


def _rendered_check_from_payloads(payloads: list[object]) -> dict[str, object]:
    aggregation = aggregate_recovery_session_host_operator_verdicts(payloads)
    rendered_aggregation = render_recovery_session_host_verdict_aggregation(
        aggregation
    )
    summary = build_recovery_session_host_verdict_summary(
        rendered_aggregation
    )
    rendered_summary = render_recovery_session_host_verdict_summary(summary)
    check = check_recovery_session_host_verdict_summary_contract(
        rendered_summary
    )
    return render_recovery_session_host_verdict_summary_contract_check(check)


def _rendered_comparison(
    before: dict[str, object],
    after: dict[str, object],
) -> dict[str, object]:
    comparison = compare_recovery_session_host_verdict_summary_checks(
        before,
        after,
    )
    return render_recovery_session_host_verdict_summary_comparison(
        comparison
    )


def _rendered_self_comparison(
    rendered_check: dict[str, object],
) -> dict[str, object]:
    return _rendered_comparison(
        rendered_check,
        copy.deepcopy(rendered_check),
    )


def _rendered_cross_phase_digest(
    rendered_check: dict[str, object],
    rendered_comparison: dict[str, object],
) -> dict[str, object]:
    cross_phase = build_recovery_session_host_verdict_cross_phase_digest(
        rendered_check,
        rendered_comparison,
    )
    return render_recovery_session_host_verdict_cross_phase_digest(
        cross_phase
    )


def _rendered_contract_check(
    rendered_digest: dict[str, object],
) -> tuple[object, dict[str, object]]:
    contract_check = (
        check_recovery_session_host_verdict_cross_phase_digest_contract(
            rendered_digest
        )
    )
    rendered_contract = (
        render_recovery_session_host_verdict_cross_phase_digest_contract_check(
            contract_check
        )
    )
    return contract_check, rendered_contract


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


class TestRecoverySessionHostVerdictCrossPhaseDigestContractAcceptance(
    unittest.TestCase
):
    """Acceptance coverage for real rendered digest contract consumption."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _seeded_db(self) -> tuple[Path, str]:
        db_path = self.tmpdir / "factory.db"
        task_id = f"task-{uuid4().hex[:8]}"
        _initialize_empty_db(db_path)
        _seed_inference_stage(db_path, task_id)
        return db_path, task_id

    def _real_payloads(
        self,
    ) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], Path]:
        db_path, task_id = self._seeded_db()
        return _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )

    def _real_rendered_check(self) -> dict[str, object]:
        payloads, _by_name, _missing_path = self._real_payloads()
        return _rendered_check_from_payloads(list(payloads))

    def _safe_real_rendered_digest(self) -> dict[str, object]:
        rendered_check = self._real_rendered_check()
        rendered_comparison = _rendered_self_comparison(rendered_check)
        return _rendered_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )

    def test_acceptance_contract_accepts_real_safe_operator_ready_digest(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
        payloads, _by_name, _missing_path = _collect_real_operator_payloads(
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
        contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )

        self.assertIs(contract_check.ready, True)
        self.assertEqual(contract_check.reason_code, "ready")
        self.assertEqual(contract_check.failures, ())
        self.assertIs(rendered_check["ready"], True)
        self.assertEqual(rendered_check["reason_code"], "ready")
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

    def test_acceptance_contract_marks_real_drift_digest_not_ready(
        self,
    ) -> None:
        before = self._real_rendered_check()
        after = copy.deepcopy(before)
        manifest = after["manifest"]
        self.assertIsInstance(manifest, dict)
        version = manifest["version"]
        self.assertIsInstance(version, int)
        manifest["version"] = version + 1
        rendered_comparison = _rendered_comparison(before, after)
        rendered_digest = _rendered_cross_phase_digest(
            before,
            rendered_comparison,
        )

        contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(rendered_digest["ok"], True)
        self.assertIs(digest["operator_safe"], False)
        self.assertIs(digest["has_drift"], True)
        self.assertIs(contract_check.ready, False)
        self.assertEqual(contract_check.reason_code, "not_ready")
        self.assertEqual(contract_check.failures, ())
        _json_round_trips(rendered_contract)

    def test_acceptance_contract_marks_real_contract_failure_digest_not_ready(
        self,
    ) -> None:
        mutated_check = self._real_rendered_check()
        mutated_check["ready"] = False
        mutated_check["reason_code"] = "not_ready"
        mutated_check["failures"] = ["digest_shape_mismatch"]
        rendered_comparison = _rendered_self_comparison(mutated_check)
        rendered_digest = _rendered_cross_phase_digest(
            mutated_check,
            rendered_comparison,
        )

        contract_check, _rendered_contract = _rendered_contract_check(
            rendered_digest
        )
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)

        self.assertIs(rendered_digest["ok"], True)
        self.assertIs(digest["has_contract_failure"], True)
        self.assertIs(digest["operator_safe"], False)
        self.assertIs(contract_check.ready, False)
        self.assertEqual(contract_check.reason_code, "not_ready")
        self.assertEqual(contract_check.failures, ())

    def test_acceptance_contract_rejects_real_malformed_rendered_digest(
        self,
    ) -> None:
        rendered_digest = self._safe_real_rendered_digest()
        rendered_digest["extra"] = True
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)
        digest["operator_safe"] = "yes"

        contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )

        self.assertIs(contract_check.ready, False)
        self.assertEqual(
            contract_check.reason_code,
            "invalid_cross_phase_digest",
        )
        self.assertIn("payload_shape_mismatch", contract_check.failures)
        self.assertIn("digest_bool_invalid", contract_check.failures)
        _json_round_trips(rendered_contract)

    def test_acceptance_contract_detects_real_hazard_flag_inconsistency(
        self,
    ) -> None:
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
                rendered_digest = self._safe_real_rendered_digest()
                digest = rendered_digest["digest"]
                self.assertIsInstance(digest, dict)
                digest["operator_safe"] = False
                digest.update(updates)

                contract_check = (
                    check_recovery_session_host_verdict_cross_phase_digest_contract(
                        rendered_digest
                    )
                )

                self.assertIn(
                    "hazard_flag_inconsistent",
                    contract_check.failures,
                )

    def test_acceptance_contract_detects_operator_safe_inconsistency(
        self,
    ) -> None:
        rendered_digest = self._safe_real_rendered_digest()
        digest = rendered_digest["digest"]
        self.assertIsInstance(digest, dict)
        digest["operator_safe"] = True
        digest["has_drift"] = True
        digest["comparison_changed"] = True
        digest["comparison_change_count"] = 1

        contract_check = (
            check_recovery_session_host_verdict_cross_phase_digest_contract(
                rendered_digest
            )
        )

        self.assertIn("operator_safe_inconsistent", contract_check.failures)

    def test_acceptance_contract_preserves_read_only_runtime_boundary(
        self,
    ) -> None:
        db_path, task_id = self._seeded_db()
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

    def test_acceptance_contract_handles_valid_failure_cross_phase_digest(
        self,
    ) -> None:
        _payloads, by_name, _missing_path = self._real_payloads()
        mixed_payloads: list[object] = [
            by_name["factory_check_valid"],
            by_name["evaluate_existing"],
            "not-a-mapping",
            {"phase": "unknown"},
            {"command": "factory-check"},
        ]
        rendered_check = _rendered_check_from_payloads(mixed_payloads)
        rendered_comparison = _rendered_self_comparison(rendered_check)
        rendered_digest = _rendered_cross_phase_digest(
            rendered_check,
            rendered_comparison,
        )

        contract_check, _rendered_contract = _rendered_contract_check(
            rendered_digest
        )

        self.assertIs(contract_check.ready, True)
        self.assertEqual(contract_check.reason_code, "ready")
        self.assertEqual(contract_check.failures, ())

    def test_acceptance_contract_output_has_no_runtime_repr_leakage(
        self,
    ) -> None:
        rendered_digest = self._safe_real_rendered_digest()

        contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )

        self.assertIs(contract_check.ready, True)
        _assert_json_safe_no_runtime_types(rendered_contract)
        _assert_no_runtime_repr_strings(rendered_contract)

    def test_acceptance_contract_does_not_call_digest_comparator_manifest_summary_aggregator_or_operator_runtime(
        self,
    ) -> None:
        rendered_digest = self._safe_real_rendered_digest()

        with (
            mock.patch.object(
                digest_module,
                "build_recovery_session_host_verdict_cross_phase_digest",
                side_effect=AssertionError("digest builder called"),
            ),
            mock.patch.object(
                digest_module,
                "render_recovery_session_host_verdict_cross_phase_digest",
                side_effect=AssertionError("digest renderer called"),
            ),
            mock.patch.object(
                comparator_module,
                "compare_recovery_session_host_verdict_summary_checks",
                side_effect=AssertionError("comparator called"),
            ),
            mock.patch.object(
                comparator_module,
                "render_recovery_session_host_verdict_summary_comparison",
                side_effect=AssertionError("comparison renderer called"),
            ),
            mock.patch.object(
                manifest_module,
                "check_recovery_session_host_verdict_summary_contract",
                side_effect=AssertionError("manifest checker called"),
            ),
            mock.patch.object(
                manifest_module,
                "render_recovery_session_host_verdict_summary_contract_check",
                side_effect=AssertionError("manifest renderer called"),
            ),
            mock.patch.object(
                summary_module,
                "build_recovery_session_host_verdict_summary",
                side_effect=AssertionError("summary builder called"),
            ),
            mock.patch.object(
                summary_module,
                "render_recovery_session_host_verdict_summary",
                side_effect=AssertionError("summary renderer called"),
            ),
            mock.patch.object(
                aggregator_module,
                "aggregate_recovery_session_host_operator_verdicts",
                side_effect=AssertionError("aggregator called"),
            ),
            mock.patch.object(
                aggregator_module,
                "render_recovery_session_host_verdict_aggregation",
                side_effect=AssertionError("aggregation renderer called"),
            ),
            mock.patch.object(
                recovery_session_host_cli,
                "main",
                side_effect=AssertionError("main called"),
            ),
            mock.patch.object(
                recovery_session_host_cli,
                "build_parser",
                side_effect=AssertionError("build_parser called"),
            ),
            mock.patch.object(
                recovery_session_host_cli,
                "try_build_recovery_session_host_from_sqlite",
                side_effect=AssertionError("factory called"),
            ),
        ):
            contract_check, rendered_contract = _rendered_contract_check(
                rendered_digest
            )

        self.assertIs(contract_check.ready, True)
        self.assertIs(rendered_contract["ready"], True)
        _json_round_trips(rendered_contract)

    def test_acceptance_contract_no_restore_or_command_creep(self) -> None:
        public_function_names = {
            name
            for name, value in contract_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        source = inspect.getsource(contract_module)
        for marker in _FORBIDDEN_SOURCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)
        self.assertNotIn(
            "render_recovery_session_host_verdict_cross_phase_digest(",
            source,
        )
        self.assertNotIn(
            "recovery_session_host_verdict_cross_phase_digest.",
            source,
        )

        for line in source.splitlines():
            if "recovery_session_host_verdict_cross_phase_digest" not in line:
                continue
            with self.subTest(line=line):
                self.assertIn(
                    line.strip(),
                    _ALLOWED_CROSS_PHASE_DIGEST_CONTRACT_SOURCE_LINES,
                )

    def test_acceptance_contract_summary_for_ci_display(self) -> None:
        rendered_digest = self._safe_real_rendered_digest()
        _contract_check, rendered_contract = _rendered_contract_check(
            rendered_digest
        )
        contract = rendered_contract["contract"]
        self.assertIsInstance(contract, dict)
        display = {
            "phase": (
                "recovery_session_host_verdict_cross_phase_digest_contract"
            ),
            "contract_ready": rendered_contract["ready"],
            "contract_reason_code": rendered_contract["reason_code"],
            "surface": contract["surface"],
            "version": contract["version"],
            "restore_supported": contract["restore_supported"],
            "durable_writes": contract["durable_writes"],
            "cli_commands": contract["cli_commands"],
            "runtime_dependencies": contract["runtime_dependencies"],
            "json_safe": contract["json_safe"],
        }

        self.assertEqual(
            display["phase"],
            "recovery_session_host_verdict_cross_phase_digest_contract",
        )
        self.assertIs(display["contract_ready"], True)
        self.assertEqual(display["contract_reason_code"], "ready")
        self.assertEqual(
            display["surface"],
            "recovery_session_host_verdict_cross_phase_digest",
        )
        self.assertEqual(display["version"], 1)
        self.assertIs(display["restore_supported"], False)
        self.assertIs(display["durable_writes"], False)
        self.assertEqual(display["cli_commands"], [])
        self.assertEqual(display["runtime_dependencies"], [])
        self.assertIs(display["json_safe"], True)
        _json_round_trips(display)


if __name__ == "__main__":
    unittest.main()
