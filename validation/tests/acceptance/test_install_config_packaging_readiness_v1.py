"""
Install/Config/Packaging Readiness V1 acceptance.

The repository must expose static packaging metadata and console entry-point
configuration without installing dependencies or executing entry points.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from kernel.install_config.packaging_readiness import build_packaging_readiness_report


class InstallConfigPackagingReadinessAcceptanceTests(unittest.TestCase):
    def test_packaging_metadata_and_entrypoints_are_ready_without_install(self) -> None:
        report = build_packaging_readiness_report(Path.cwd())

        self.assertTrue(report.accepted)
        self.assertEqual(report.failure_codes, ())
        self.assertEqual(report.project_name, "sovereign-engineering-os")
        self.assertEqual(report.build_backend, "setuptools.build_meta")
        self.assertIn("setuptools>=69", report.build_requires)
        self.assertEqual(report.scripts["seos"], "apps.operator_cli.main:main")
        self.assertEqual(report.scripts["seos-local"], "kernel.personal_ai.local_mvp_cli:main")
        self.assertTrue(report.script_targets_importable["seos"])
        self.assertTrue(report.script_targets_importable["seos-local"])
        self.assertTrue(report.config_hash)
        self.assertFalse(report.installation_performed)
        self.assertFalse(report.dependency_install_performed)
        self.assertFalse(report.subprocess_spawned)
        self.assertFalse(report.network_accessed)
        self.assertFalse(report.entrypoint_executed)
        self.assertFalse(report.secret_value_read)


if __name__ == "__main__":
    unittest.main()
