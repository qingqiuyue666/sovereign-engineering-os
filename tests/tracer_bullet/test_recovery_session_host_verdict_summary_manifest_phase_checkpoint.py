"""
P0-39 phase 1 - RecoverySessionHost verdict summary manifest checkpoint.

These tests pin the verdict summary manifest/check boundary as a
read-only contract surface over realistic rendered summary payloads.
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
from kernel.lifecycle.recovery_session_host_verdict_summary import (
    build_recovery_session_host_verdict_summary,
    render_recovery_session_host_verdict_summary,
)
from kernel.lifecycle.recovery_session_host_verdict_summary_manifest import (
    RecoverySessionHostVerdictSummaryContractCheck,
    check_recovery_session_host_verdict_summary_contract,
    recovery_session_host_verdict_summary_contract_manifest,
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


_EXPECTED_PUBLIC_API = {
    "RecoverySessionHostVerdictSummaryContractCheck",
    "recovery_session_host_verdict_summary_contract_manifest",
    "check_recovery_session_host_verdict_summary_contract",
    "render_recovery_session_host_verdict_summary_contract_check",
}

_FORBIDDEN_RUNTIME_REFERENCES = (
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "build_parser",
    "try_build_recovery_session_host_from_sqlite",
    "aggregate_recovery_session_host_operator_verdicts",
    "build_recovery_session_host_verdict_summary",
    "render_recovery_session_host_verdict_summary",
    "recovery_session_host_cli",
    "recovery_session_host_verdict_aggregator",
    "recovery_session_host_verdict_summary",
    "recovery_cli",
    "sqlite3",
    "open_connection",
    "apply_migrations",
    "KernelUnitOfWork",
)

_ALLOWED_SUMMARY_CONTRACT_TOKENS = (
    "recovery_session_host_verdict_summary_contract_manifest",
    "check_recovery_session_host_verdict_summary_contract",
    "render_recovery_session_host_verdict_summary_contract_check",
    '"recovery_session_host_verdict_summary"',
)


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


def _seeded_db(tmpdir: Path) -> tuple[Path, str]:
    db_path = tmpdir / "factory.db"
    task_id = f"task-{uuid4().hex[:8]}"
    _initialize_empty_db(db_path)
    _seed_inference_stage(db_path, task_id)
    return db_path, task_id


def _collect_real_operator_payloads(
    *,
    tmpdir: Path,
    db_path: Path,
    task_id: str,
) -> tuple[list[dict[str, object]], Path]:
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
    for name, argv, expected_code in cases:
        payloads.append(
            _invoke_json_payload(
                argv,
                expected_code=expected_code,
                name=name,
            )
        )

    payloads.append(current_recovery_session_host_cli_readiness_payload())
    payloads.append(
        render_recovery_session_host_cli_readiness_smoke(
            current_recovery_session_host_cli_readiness_smoke()
        )
    )
    return payloads, missing_path


def _render_summary_from_payloads(
    payloads: list[object],
) -> tuple[object, dict[str, object], object, dict[str, object]]:
    aggregation = aggregate_recovery_session_host_operator_verdicts(payloads)
    rendered_aggregation = render_recovery_session_host_verdict_aggregation(
        aggregation
    )
    summary = build_recovery_session_host_verdict_summary(
        rendered_aggregation
    )
    rendered_summary = render_recovery_session_host_verdict_summary(summary)
    return aggregation, rendered_aggregation, summary, rendered_summary


def _real_rendered_summary(
    tmpdir: Path,
) -> tuple[dict[str, object], Path, Path]:
    db_path, task_id = _seeded_db(tmpdir)
    payloads, missing_path = _collect_real_operator_payloads(
        tmpdir=tmpdir,
        db_path=db_path,
        task_id=task_id,
    )
    _aggregation, _rendered_aggregation, _summary, rendered_summary = (
        _render_summary_from_payloads(list(payloads))
    )
    return rendered_summary, db_path, missing_path


def _json_round_trips(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if json.loads(encoded) != payload:
        raise AssertionError("payload did not round-trip through JSON")


def _relative_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(str(path.relative_to(root)) for path in root.rglob("*"))
    )


def _manifest_source_without_allowed_contract_tokens() -> str:
    source = inspect.getsource(manifest_module)
    for token in _ALLOWED_SUMMARY_CONTRACT_TOKENS:
        source = source.replace(token, "")
    return source


class TestRecoverySessionHostVerdictSummaryManifestPhaseCheckpoint(
    unittest.TestCase
):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_phase_checkpoint_manifest_boundary_is_frozen_read_only(
        self,
    ) -> None:
        manifest = recovery_session_host_verdict_summary_contract_manifest()
        rendered_summary, _db_path, _missing_path = _real_rendered_summary(
            self.tmpdir
        )

        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        self.assertEqual(
            manifest["surface"],
            "recovery_session_host_verdict_summary",
        )
        self.assertEqual(manifest["version"], 1)
        self.assertIs(manifest["restore_supported"], False)
        self.assertIs(manifest["durable_writes"], False)
        self.assertEqual(manifest["cli_commands"], [])
        self.assertEqual(manifest["runtime_dependencies"], [])
        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        _json_round_trips(rendered_check)

    def test_phase_checkpoint_manifest_boundary_has_no_runtime_mutation_paths(
        self,
    ) -> None:
        db_path, task_id = _seeded_db(self.tmpdir)
        before_counts = _table_row_counts(db_path)

        payloads, missing_path = _collect_real_operator_payloads(
            tmpdir=self.tmpdir,
            db_path=db_path,
            task_id=task_id,
        )
        _aggregation, _rendered_aggregation, _summary, rendered_summary = (
            _render_summary_from_payloads(list(payloads))
        )
        files_before_manifest = _relative_files(self.tmpdir)

        recovery_session_host_verdict_summary_contract_manifest()
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        render_recovery_session_host_verdict_summary_contract_check(check)

        self.assertEqual(_table_row_counts(db_path), before_counts)
        self.assertFalse(missing_path.exists())
        self.assertEqual(_relative_files(self.tmpdir), files_before_manifest)

    def test_phase_checkpoint_manifest_checker_rejects_all_guard_categories(
        self,
    ) -> None:
        base_rendered_summary, _db_path, _missing_path = (
            _real_rendered_summary(self.tmpdir)
        )
        cases = (
            (
                "top_level_extra_key",
                lambda payload: payload.update({"extra": True}),
                "summary_shape_mismatch",
            ),
            (
                "reason_code_weird",
                lambda payload: payload.update({"reason_code": "weird"}),
                "reason_code_invalid",
            ),
            (
                "failures_invalid",
                lambda payload: payload.update({"failures": ["x", 1]}),
                "failures_invalid",
            ),
            (
                "failure_value_unknown",
                lambda payload: payload.update(
                    {
                        "ok": False,
                        "reason_code": "invalid_aggregation",
                        "failures": ["not_declared"],
                    }
                ),
                "failure_value_unknown",
            ),
            (
                "digest_invalid",
                lambda payload: payload.update({"digest": "bad"}),
                "digest_invalid",
            ),
            (
                "digest_shape_mismatch",
                lambda payload: payload["digest"].pop("operator_safe"),
                "digest_shape_mismatch",
            ),
            (
                "digest_counter_invalid",
                lambda payload: payload["digest"].update(
                    {"total_payloads": True}
                ),
                "digest_counter_invalid",
            ),
            (
                "digest_bool_invalid",
                lambda payload: payload["digest"].update(
                    {"aggregation_ok": "yes"}
                ),
                "digest_bool_invalid",
            ),
            (
                "digest_string_invalid",
                lambda payload: payload["digest"].update(
                    {"aggregation_reason_code": 123}
                ),
                "digest_string_invalid",
            ),
            (
                "digest_list_invalid",
                lambda payload: payload["digest"].update(
                    {"aggregation_failures": ["x", 1]}
                ),
                "digest_list_invalid",
            ),
            (
                "digest_count_dict_invalid",
                lambda payload: payload["digest"].update(
                    {"payload_type_counts": {"z": 1, "a": 2}}
                ),
                "digest_count_dict_invalid",
            ),
            (
                "operator_safe_inconsistent",
                lambda payload: payload["digest"].update(
                    {"operator_safe": True, "rejected_payloads": 1}
                ),
                "operator_safe_inconsistent",
            ),
            (
                "restore_surface_present",
                lambda payload: payload["digest"].update(
                    {"restore_supported_true": 1}
                ),
                "restore_surface_present",
            ),
            (
                "durable_writes_present",
                lambda payload: payload["digest"].update(
                    {"durable_writes_true": 1}
                ),
                "durable_writes_present",
            ),
            (
                "summary_status_inconsistent",
                lambda payload: payload.update(
                    {"reason_code": "invalid_aggregation"}
                ),
                "summary_status_inconsistent",
            ),
        )

        for name, mutate, expected_failure in cases:
            with self.subTest(name=name):
                rendered_summary = copy.deepcopy(base_rendered_summary)
                mutate(rendered_summary)

                check = check_recovery_session_host_verdict_summary_contract(
                    rendered_summary
                )

                self.assertIn(expected_failure, check.failures)

    def test_phase_checkpoint_manifest_check_accepts_valid_failure_summary(
        self,
    ) -> None:
        db_path, task_id = _seeded_db(self.tmpdir)
        factory_payload = _invoke_json_payload(
            ["factory-check", "--db", str(db_path)],
            expected_code=EXIT_OK,
            name="factory_check_valid",
        )
        evaluate_payload = _invoke_json_payload(
            ["evaluate", "--db", str(db_path), "--task-id", task_id],
            expected_code=EXIT_OK,
            name="evaluate_existing",
        )
        mixed_payloads: list[object] = [
            factory_payload,
            evaluate_payload,
            "not-a-mapping",
            {"phase": "unknown"},
            {"command": "factory-check"},
        ]

        aggregation, _rendered_aggregation, summary, rendered_summary = (
            _render_summary_from_payloads(mixed_payloads)
        )
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )

        self.assertIs(aggregation.ok, False)
        self.assertIs(summary.ok, True)
        self.assertIs(rendered_summary["ok"], True)
        self.assertIs(rendered_summary["digest"]["aggregation_ok"], False)
        self.assertIs(rendered_summary["digest"]["operator_safe"], False)
        self.assertIs(check.ready, True)
        self.assertEqual(check.failures, ())

    def test_phase_checkpoint_manifest_check_output_is_json_safe_and_defensive(
        self,
    ) -> None:
        rendered_summary, _db_path, _missing_path = _real_rendered_summary(
            self.tmpdir
        )
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )
        expected_rendered_check = copy.deepcopy(rendered_check)

        _json_round_trips(rendered_check)
        _assert_json_safe_no_runtime_types(rendered_check)
        _assert_no_runtime_repr_strings(rendered_check)

        rendered_check["manifest"]["digest_keys"].append("mutated")
        fresh_rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )

        self.assertNotIn("mutated", check.manifest["digest_keys"])
        self.assertEqual(fresh_rendered_check, expected_rendered_check)

    def test_phase_checkpoint_manifest_surface_public_api_is_frozen(
        self,
    ) -> None:
        public_api = {
            name
            for name, value in inspect.getmembers(manifest_module)
            if not name.startswith("_")
            and getattr(value, "__module__", None) == manifest_module.__name__
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        self.assertEqual(public_api, _EXPECTED_PUBLIC_API)

    def test_phase_checkpoint_manifest_surface_has_no_forbidden_runtime_references(
        self,
    ) -> None:
        public_function_names = {
            name
            for name, value in manifest_module.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(value)
        }
        for name in public_function_names:
            with self.subTest(name=name):
                self.assertNotIn("restore", name)

        for marker in _FORBIDDEN_RUNTIME_REFERENCES:
            with self.subTest(module_dict=marker):
                self.assertNotIn(marker, manifest_module.__dict__)

        runtime_source = _manifest_source_without_allowed_contract_tokens()
        for marker in _FORBIDDEN_RUNTIME_REFERENCES:
            with self.subTest(source=marker):
                self.assertNotIn(marker, runtime_source)

    def test_phase_checkpoint_manifest_contract_summary_for_ci(
        self,
    ) -> None:
        rendered_summary, _db_path, _missing_path = _real_rendered_summary(
            self.tmpdir
        )
        check = check_recovery_session_host_verdict_summary_contract(
            rendered_summary
        )
        rendered_check = (
            render_recovery_session_host_verdict_summary_contract_check(check)
        )
        checkpoint_summary = {
            "phase": (
                "recovery_session_host_verdict_summary_manifest_checkpoint"
            ),
            "contract_ready": rendered_check["ready"],
            "reason_code": rendered_check["reason_code"],
            "surface": rendered_check["manifest"]["surface"],
            "version": rendered_check["manifest"]["version"],
            "restore_supported": rendered_check["manifest"][
                "restore_supported"
            ],
            "durable_writes": rendered_check["manifest"]["durable_writes"],
            "cli_commands": rendered_check["manifest"]["cli_commands"],
            "runtime_dependencies": rendered_check["manifest"][
                "runtime_dependencies"
            ],
            "json_safe": rendered_check["manifest"]["json_safe"],
        }

        self.assertEqual(
            checkpoint_summary["phase"],
            "recovery_session_host_verdict_summary_manifest_checkpoint",
        )
        self.assertIs(checkpoint_summary["contract_ready"], True)
        self.assertEqual(checkpoint_summary["reason_code"], "ready")
        self.assertEqual(
            checkpoint_summary["surface"],
            "recovery_session_host_verdict_summary",
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
