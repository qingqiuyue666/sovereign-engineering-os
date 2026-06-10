"""Tests for install/config/packaging readiness."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.install_config.packaging_readiness import (
    build_packaging_readiness_report,
    render_packaging_readiness_report,
)
from tools.install_config_readiness import main as install_config_readiness_main


class InstallConfigPackagingReadinessTests(unittest.TestCase):
    def test_repo_pyproject_is_packaging_ready_without_installing(self) -> None:
        report = build_packaging_readiness_report(Path.cwd())
        rendered = render_packaging_readiness_report(report)

        self.assertTrue(report.accepted)
        self.assertEqual(report.project_name, "sovereign-engineering-os")
        self.assertEqual(report.requires_python, ">=3.13")
        self.assertEqual(report.build_backend, "setuptools.build_meta")
        self.assertIn("seos", report.scripts)
        self.assertIn("seos-local", report.scripts)
        self.assertTrue(report.script_targets_importable["seos"])
        self.assertTrue(report.script_targets_importable["seos-local"])
        self.assertIn("apps*", report.package_find_include)
        self.assertIn("kernel*", report.package_find_include)
        self.assertIn("tools*", report.package_find_include)
        self.assertTrue(report.namespace_packages_enabled)
        self.assertFalse(report.installation_performed)
        self.assertFalse(report.dependency_install_performed)
        self.assertFalse(report.subprocess_spawned)
        self.assertFalse(report.network_accessed)
        self.assertFalse(report.entrypoint_executed)
        self.assertNotIn("site-packages", rendered)

    def test_missing_or_incomplete_pyproject_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = build_packaging_readiness_report(Path(tmp))
            self.assertFalse(missing.accepted)
            self.assertEqual(missing.failure_codes, ("pyproject_missing",))

            root = Path(tmp) / "incomplete"
            root.mkdir()
            (root / "pyproject.toml").write_text(
                """
[project]
name = "sovereign-engineering-os"
requires-python = ">=3.13"
dependencies = []
""".strip()
                + "\n",
                encoding="utf-8",
            )
            incomplete = build_packaging_readiness_report(root)

        self.assertFalse(incomplete.accepted)
        self.assertIn("build_backend_missing", incomplete.failure_codes)
        self.assertIn("required_dependency_missing", incomplete.failure_codes)
        self.assertIn("script_seos_missing", incomplete.failure_codes)

    def test_cli_prints_readiness_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = install_config_readiness_main_with_args([Path.cwd().as_posix()])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["accepted"])
        self.assertFalse(payload["installation_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertEqual(payload["scripts"]["seos"], "apps.operator_cli.main:main")

    def test_source_has_no_install_network_or_subprocess_execution_surface(self) -> None:
        source = Path("kernel/install_config/packaging_readiness.py").read_text(encoding="utf-8")
        cli_source = Path("tools/install_config_readiness.py").read_text(encoding="utf-8")
        combined = source + "\n" + cli_source

        for marker in (
            "subprocess.run",
            "subprocess.Popen",
            "Popen",
            "os.system",
            "pip ",
            "pip3 ",
            "requests.",
            "urllib.",
            "socket",
        ):
            self.assertNotIn(marker, combined)


def install_config_readiness_main_with_args(args: list[str]) -> int:
    import sys

    original = sys.argv
    try:
        sys.argv = ["install_config_readiness.py", *args]
        return install_config_readiness_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    unittest.main()
