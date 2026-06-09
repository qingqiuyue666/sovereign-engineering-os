"""Behavior tests for the DaVinci Resolve real local API adapter."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from execution_plane.adapters.davinci_resolve import DaVinciResolveAdapter
from execution_plane.permits.builder import create_execution_permit
from execution_plane.runner.result_envelope import sha256_file


class DaVinciRealApiV1Tests(unittest.TestCase):
    def test_dependency_blocked_writes_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "dependency"
            with (
                mock.patch("execution_plane.adapters.davinci_resolve._load_resolve_script_module", return_value=None),
                mock.patch("execution_plane.adapters.davinci_resolve._process_running", return_value=True),
            ):
                result = DaVinciResolveAdapter().execute(_permit(output_root, "version_probe"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("DEPENDENCY_BLOCKED", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "DEPENDENCY_BLOCKED")

    def test_app_unavailable_writes_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "app"
            with (
                mock.patch("execution_plane.adapters.davinci_resolve._load_resolve_script_module", return_value=_Module(_Resolve())),
                mock.patch("execution_plane.adapters.davinci_resolve._process_running", return_value=False),
            ):
                result = DaVinciResolveAdapter().execute(_permit(output_root, "version_probe"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("APP_NOT_RUNNING", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "APP_NOT_RUNNING")

    def test_auto_provision_command_under_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "davinci.json"
            config_path.write_text(
                json.dumps(
                    {
                        "adapter": "davinci_resolve",
                        "api_probe_script": "execution_plane/adapters/scripts/probe_davinci_api.py",
                        "startup_command": ["open", "-a", "DaVinci Resolve"],
                        "startup_timeout_seconds": 1,
                    }
                ),
                encoding="utf-8",
            )
            adapter = DaVinciResolveAdapter(config_path=config_path)
            permit = _permit(Path(tempdir) / "out", "version_probe", auto_provision=True)
            with (
                mock.patch(
                    "execution_plane.adapters.davinci_resolve.subprocess.run",
                    return_value=subprocess.CompletedProcess(args=["open"], returncode=0, stdout="", stderr=""),
                ) as run,
                mock.patch.object(
                    adapter,
                    "detect",
                    side_effect=[
                        {"available": False, "failure_code": "APP_NOT_RUNNING"},
                        {"available": True, "failure_code": None},
                    ],
                ),
                mock.patch("execution_plane.adapters.davinci_resolve.sleep", return_value=None),
            ):
                result = adapter.auto_provision(permit, permit)
        self.assertEqual(result.status, "PROVISIONED")
        run.assert_called_once()

    def test_version_probe_success_writes_json_artifact_hash_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "version"
            resolve = _Resolve(version="18.6.6")
            with (
                mock.patch("execution_plane.adapters.davinci_resolve._load_resolve_script_module", return_value=_Module(resolve)),
                mock.patch("execution_plane.adapters.davinci_resolve._process_running", return_value=True),
            ):
                result = DaVinciResolveAdapter().execute(_permit(output_root, "version_probe"))
            artifact = output_root / "davinci_version_probe.json"
            receipt = json.loads((output_root / "execution_receipt.json").read_text(encoding="utf-8"))
            artifact_hash = sha256_file(artifact)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(receipt["status"], "SUCCEEDED")
        output_record = next(item for item in result["outputs"] if item["relative_path"] == "davinci_version_probe.json")
        self.assertEqual(output_record["sha256"], artifact_hash)
        self.assertTrue(result["artifact_refs"])

    def test_project_probe_success_under_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "project"
            resolve = _Resolve(project=_Project("Demo Project", timeline=_Timeline("Timeline 1")))
            with (
                mock.patch("execution_plane.adapters.davinci_resolve._load_resolve_script_module", return_value=_Module(resolve)),
                mock.patch("execution_plane.adapters.davinci_resolve._process_running", return_value=True),
            ):
                result = DaVinciResolveAdapter().execute(_permit(output_root, "project_probe"))
            artifact = json.loads((output_root / "davinci_project_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(artifact["project_name"], "Demo Project")
        self.assertEqual(artifact["current_timeline_name"], "Timeline 1")

    def test_project_not_found_creates_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "project-missing"
            resolve = _Resolve(project=None)
            with (
                mock.patch("execution_plane.adapters.davinci_resolve._load_resolve_script_module", return_value=_Module(resolve)),
                mock.patch("execution_plane.adapters.davinci_resolve._process_running", return_value=True),
            ):
                result = DaVinciResolveAdapter().execute(_permit(output_root, "project_probe"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("PROJECT_NOT_FOUND", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "PROJECT_NOT_FOUND")


class _Module:
    def __init__(self, resolve: object | None) -> None:
        self.resolve = resolve

    def scriptapp(self, app_name: str) -> object | None:
        if app_name != "Resolve":
            raise AssertionError(app_name)
        return self.resolve


class _Resolve:
    def __init__(self, *, version: str = "18.6", project: object | None = None) -> None:
        self.version = version
        self.manager = _ProjectManager(project)

    def GetVersionString(self) -> str:
        return self.version

    def GetProjectManager(self) -> object:
        return self.manager


class _ProjectManager:
    def __init__(self, project: object | None) -> None:
        self.project = project

    def GetCurrentProject(self) -> object | None:
        return self.project

    def LoadProject(self, _name: str) -> object | None:
        return self.project


class _Project:
    def __init__(self, name: str, *, timeline: object | None = None) -> None:
        self.name = name
        self.timeline = timeline

    def GetName(self) -> str:
        return self.name

    def GetCurrentTimeline(self) -> object | None:
        return self.timeline


class _Timeline:
    def __init__(self, name: str) -> None:
        self.name = name

    def GetName(self) -> str:
        return self.name


def _permit(output_root: Path, action: str, *, auto_provision: bool = False) -> dict[str, object]:
    return create_execution_permit(
        task_id=f"TASK_DAVINCI_{action.upper()}",
        operator_approval_id=f"RCPT_DAVINCI_{action.upper()}",
        allowed_adapter="davinci_resolve",
        allowed_action=action,
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
        auto_provision={
            "enabled": auto_provision,
            "allowed_adapters": ["davinci_resolve"] if auto_provision else [],
            "max_wait_seconds": 1 if auto_provision else 0,
            "heartbeat_interval_seconds": 1,
        },
    )


if __name__ == "__main__":
    unittest.main()
