"""Tests for the #525 local install/config runnable path."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.install_config.local_runtime_path import (
    bootstrap_local_runtime,
    default_local_runtime_config,
    render_local_runtime_config,
    reset_local_runtime,
    run_local_runtime_smoke,
    stop_local_runtime,
    validate_local_runtime_config,
)
from tools.local_runtime_setup import main as local_runtime_setup_main


class InstallConfigPackagingRunnablePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.repo_root = Path(self.tempdir.name) / "fresh-clone"
        self.repo_root.mkdir()
        shutil.copyfile(Path.cwd() / "pyproject.toml", self.repo_root / "pyproject.toml")

    def test_default_config_is_disabled_dry_run_and_layout_ready(self) -> None:
        config = default_local_runtime_config()
        rendered = render_local_runtime_config(config)
        report = validate_local_runtime_config(self.repo_root, config)

        self.assertTrue(report.accepted)
        self.assertEqual(report.failure_codes, ())
        self.assertEqual(report.schema_version, 1)
        self.assertFalse(report.runtime_enabled)
        self.assertEqual(report.default_mode, "dry_run")
        self.assertFalse(report.network_access)
        self.assertFalse(report.provider_execution)
        self.assertFalse(report.background_daemon)
        self.assertIn("wal", report.runtime_layout_dirs)
        self.assertIn("receipts", report.runtime_layout_dirs)
        self.assertIn("quarantine", report.runtime_layout_dirs)
        self.assertTrue(report.config_hash)
        self.assertTrue(report.layout_hash)
        self.assertFalse(json.loads(rendered)["runtime_enabled"])
        self.assertEqual(report.migration_policy["automatic"], False)
        self.assertEqual(report.migration_policy["unknown_schema"], "fail_closed")
        self.assertEqual(report.rollback_policy["requires_marker"], True)
        self.assertIn(
            "docs/runbooks/install_config_packaging_runnable_path_v1.md",
            report.release_artifact_layout,
        )
        for path in report.runtime_layout_paths:
            self.assertTrue(Path(path).is_relative_to(self.repo_root.resolve()))

    def test_bootstrap_dry_run_does_not_mutate_then_apply_creates_marked_layout(self) -> None:
        config = default_local_runtime_config()
        dry_run = bootstrap_local_runtime(self.repo_root, config)

        self.assertTrue(dry_run.accepted)
        self.assertTrue(dry_run.dry_run_mode)
        self.assertFalse(dry_run.mutation_performed)
        self.assertFalse((self.repo_root / ".seos-runtime").exists())
        self.assertEqual(dry_run.one_command_bootstrap, "python3 tools/local_runtime_setup.py bootstrap . --apply")

        applied = bootstrap_local_runtime(self.repo_root, config, apply=True)

        self.assertTrue(applied.accepted)
        self.assertFalse(applied.dry_run_mode)
        self.assertTrue(applied.mutation_performed)
        runtime = self.repo_root / ".seos-runtime"
        self.assertTrue((runtime / "config" / "local-runtime-config-v1.json").is_file())
        self.assertTrue((runtime / "runtime-root-marker-v1.json").is_file())
        for name in ("wal", "queues", "artifacts", "snapshots", "receipts", "backups", "release"):
            self.assertTrue((runtime / name).is_dir(), name)
        persisted_config = json.loads((runtime / "config" / "local-runtime-config-v1.json").read_text())
        self.assertFalse(persisted_config["runtime_enabled"])
        self.assertFalse(persisted_config["network_access"])

    def test_smoke_stop_and_reset_are_receipt_backed_without_network_or_daemon(self) -> None:
        config = default_local_runtime_config()
        bootstrap = bootstrap_local_runtime(self.repo_root, config, apply=True)
        smoke = run_local_runtime_smoke(self.repo_root, config, apply=True)
        stop = stop_local_runtime(self.repo_root, config, apply=True)
        reset = reset_local_runtime(self.repo_root, config, apply=True)

        self.assertTrue(bootstrap.accepted)
        self.assertTrue(smoke.accepted)
        self.assertTrue(stop.accepted)
        self.assertTrue(reset.accepted)
        self.assertTrue(smoke.smoke_run_mode)
        for receipt in (bootstrap, smoke, stop, reset):
            self.assertFalse(receipt.network_accessed)
            self.assertFalse(receipt.subprocess_spawned)
            self.assertFalse(receipt.dependency_install_performed)
            self.assertFalse(receipt.provider_execution_performed)
            self.assertFalse(receipt.entrypoint_executed)
            self.assertFalse(receipt.background_daemon_enabled)
            self.assertTrue(receipt.config_hash)
            self.assertTrue(receipt.layout_hash)
        self.assertFalse((self.repo_root / ".seos-runtime").exists())
        self.assertEqual(reset.removed_paths, ((self.repo_root / ".seos-runtime").resolve().as_posix(),))

    def test_config_version_sensitive_material_and_path_escape_fail_closed(self) -> None:
        bad_version = default_local_runtime_config()
        bad_version["schema_version"] = 2
        self.assertIn(
            "unsupported_config_schema_version",
            validate_local_runtime_config(self.repo_root, bad_version).failure_codes,
        )

        enabled = default_local_runtime_config()
        enabled["runtime_enabled"] = True
        enabled["network_access"] = True
        enabled["provider_execution"] = True
        enabled["background_daemon"] = True
        report = validate_local_runtime_config(self.repo_root, enabled)
        self.assertFalse(report.accepted)
        self.assertIn("runtime_must_default_disabled", report.failure_codes)
        self.assertIn("network_access_must_be_disabled", report.failure_codes)
        self.assertIn("provider_execution_must_be_disabled", report.failure_codes)
        self.assertIn("background_daemon_must_be_disabled", report.failure_codes)

        escaped = default_local_runtime_config(runtime_root="../outside")
        self.assertIn("runtime_root_path_invalid", validate_local_runtime_config(self.repo_root, escaped).failure_codes)

        sensitive = default_local_runtime_config()
        sensitive["api_key"] = "sk-abcdefghijklmnopqrstuvwxyz123456"
        sensitive_report = validate_local_runtime_config(self.repo_root, sensitive)
        self.assertFalse(sensitive_report.accepted)
        self.assertIn("sensitive_config_material", sensitive_report.failure_codes)

    def test_reset_refuses_unmarked_or_symlink_runtime_roots(self) -> None:
        config = default_local_runtime_config()
        runtime = self.repo_root / ".seos-runtime"
        runtime.mkdir()
        unmarked = reset_local_runtime(self.repo_root, config, apply=True)

        self.assertFalse(unmarked.accepted)
        self.assertIn("runtime_marker_missing", unmarked.failure_codes)
        self.assertTrue(runtime.exists())

        if hasattr(os, "symlink"):
            runtime.rmdir()
            outside = Path(self.tempdir.name) / "outside"
            outside.mkdir()
            os.symlink(outside, runtime)
            rejected = validate_local_runtime_config(self.repo_root, config)
            self.assertFalse(rejected.accepted)
            self.assertIn("runtime_root_path_invalid", rejected.failure_codes)

    def test_cli_one_command_sequence_uses_same_safe_receipts(self) -> None:
        bootstrap_stdout = io.StringIO()
        with contextlib.redirect_stdout(bootstrap_stdout):
            bootstrap_exit = _run_cli(["bootstrap", self.repo_root.as_posix(), "--apply"])
        self.assertEqual(bootstrap_exit, 0)
        self.assertTrue(json.loads(bootstrap_stdout.getvalue())["accepted"])

        for command in ("smoke", "stop", "reset"):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = _run_cli([command, self.repo_root.as_posix(), "--apply"])
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0, payload)
            self.assertTrue(payload["accepted"])
            self.assertFalse(payload["network_accessed"])
            self.assertFalse(payload["provider_execution_performed"])

    def test_cli_rejects_config_path_escape_or_sensitive_path(self) -> None:
        outside = Path(self.tempdir.name) / "outside-config.json"
        outside.write_text(json.dumps(default_local_runtime_config()), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "config_path_must_remain_inside_repo"):
            _run_cli(["validate", self.repo_root.as_posix(), "--config", outside.as_posix()])

        sensitive = self.repo_root / ".env"
        sensitive.write_text(json.dumps(default_local_runtime_config()), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "config_path_sensitive_material_rejected"):
            _run_cli(["validate", self.repo_root.as_posix(), "--config", ".env"])

    def test_source_has_no_install_network_provider_or_subprocess_execution_surface(self) -> None:
        source = Path("kernel/install_config/local_runtime_path.py").read_text(encoding="utf-8")
        cli_source = Path("tools/local_runtime_setup.py").read_text(encoding="utf-8")
        combined = source + "\n" + cli_source

        for marker in (
            "subprocess.run",
            "subprocess.Popen",
            "Popen(",
            "os.system",
            "pip ",
            "pip3 ",
            "requests.",
            "urllib.",
            "socket",
            "import http",
        ):
            self.assertNotIn(marker, combined)


def _run_cli(args: list[str]) -> int:
    original = sys.argv
    try:
        sys.argv = ["local_runtime_setup.py", *args]
        return local_runtime_setup_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    unittest.main()
