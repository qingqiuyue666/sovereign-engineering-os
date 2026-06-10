"""Tests for normalized concurrent adapter kernel contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from execution_plane.adapters.base import SUPPORTED_ADAPTER_ACTIONS
from execution_plane.adapters.comfyui_local import ComfyUILocalAdapter
from execution_plane.adapters.davinci_resolve import DaVinciResolveAdapter
from execution_plane.adapters.registry import adapter_registry
from execution_plane.permits.builder import create_execution_permit


class ConcurrentAdapterKernelV1Tests(unittest.TestCase):
    def test_registry_exposes_same_level_adapter_contracts(self) -> None:
        registry = adapter_registry()
        self.assertEqual(set(registry), set(SUPPORTED_ADAPTER_ACTIONS))
        for adapter_name, adapter in registry.items():
            self.assertEqual(adapter.name, adapter_name)
            for method_name in (
                "detect",
                "preflight",
                "auto_provision",
                "execute",
                "collect_outputs",
                "classify_failure",
                "repair_hint",
            ):
                self.assertTrue(callable(getattr(adapter, method_name)))

    def test_fake_adapter_result_includes_artifact_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = create_execution_permit(
                task_id="TASK_ARTIFACT_REF",
                operator_approval_id="RCPT_ARTIFACT_REF",
                allowed_adapter="fake_dcc",
                allowed_action="smoke_generate_file",
                allowed_output_root=Path(tempdir) / "out",
                expires_at="2099-01-01T00:00:00Z",
            )
            result = adapter_registry()["fake_dcc"].execute(
                permit,
                {"output_path": "cache/output.txt", "content": "zero copy ref\n"},
            )
        self.assertEqual(result["status"], "SUCCEEDED")
        refs = result["artifact_refs"]
        self.assertTrue(refs)
        self.assertEqual(refs[0]["storage_mode"], "path_ref")
        self.assertEqual(refs[0]["copy_policy"], "zero_copy_reference")
        self.assertTrue(refs[0]["uri"].startswith("seos://run/"))
        self.assertNotIn(tempdir, str(result))

    def test_comfyui_unavailable_can_attempt_policy_controlled_provision(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            permit = create_execution_permit(
                task_id="TASK_COMFY",
                operator_approval_id="RCPT_COMFY",
                allowed_adapter="comfyui_local",
                allowed_action="service_probe",
                allowed_output_root=Path(tempdir) / "out",
                expires_at="2099-01-01T00:00:00Z",
                auto_provision={
                    "enabled": True,
                    "allowed_adapters": ["comfyui_local"],
                    "max_wait_seconds": 1,
                    "heartbeat_interval_seconds": 1,
                },
            )
            adapter = ComfyUILocalAdapter(config_path=Path(tempdir) / "missing.json")
            with mock.patch("execution_plane.adapters.comfyui_local.probe_comfyui") as probe:
                probe.return_value = {
                    "adapter": "comfyui_local",
                    "available": False,
                    "status": "BLOCKED",
                    "heartbeat_status": "UNAVAILABLE",
                }
                result = adapter.execute(permit)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("SERVICE_UNAVAILABLE", result["policy_blocks"])
        self.assertEqual(result["provision_result"]["status"], "FAILED")

    def test_davinci_unavailable_is_dependency_blocked_without_startup_command(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config = Path(tempdir) / "davinci.json"
            config.write_text(
                '{"adapter":"davinci_resolve","startup_command":[],"api_probe_script":"missing.py"}\n',
                encoding="utf-8",
            )
            permit = create_execution_permit(
                task_id="TASK_DAVINCI",
                operator_approval_id="RCPT_DAVINCI",
                allowed_adapter="davinci_resolve",
                allowed_action="project_probe",
                allowed_output_root=Path(tempdir) / "out",
                expires_at="2099-01-01T00:00:00Z",
                auto_provision={
                    "enabled": True,
                    "allowed_adapters": ["davinci_resolve"],
                    "max_wait_seconds": 1,
                    "heartbeat_interval_seconds": 1,
                },
            )
            adapter = DaVinciResolveAdapter(config_path=config)
            with mock.patch("execution_plane.adapters.davinci_resolve._process_running", return_value=False):
                result = adapter.execute(permit)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("DEPENDENCY_BLOCKED", result["policy_blocks"])
        self.assertEqual(result["provision_result"]["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
