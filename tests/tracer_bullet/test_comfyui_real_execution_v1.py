"""Behavior tests for ComfyUI real local execution adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from unittest import mock

from execution_plane.adapters.comfyui_local import ComfyUILocalAdapter, collect_comfyui_outputs
from execution_plane.permits.builder import create_execution_permit


PNG_BYTES = b"\x89PNG\r\n\x1a\nseos-test"


class ComfyUIRealExecutionV1Tests(unittest.TestCase):
    def test_mock_service_probe_success_writes_receipt_and_artifact_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "probe"
            router = _ComfyUIRouter()
            with mock.patch("execution_plane.adapters.comfyui_local.urlopen", side_effect=router):
                result = ComfyUILocalAdapter().execute(_permit(output_root, "service_probe"))
            self.assertTrue((output_root / "artifact_manifest.json").exists())
            self.assertTrue((output_root / "execution_receipt.json").exists())
            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertTrue(result["artifact_refs"])
            self.assertTrue(any(req["path"] == "/system_stats" for req in router.requests))

    def test_mock_service_unavailable_writes_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "unavailable"
            with mock.patch("execution_plane.adapters.comfyui_local.urlopen", side_effect=URLError("down")):
                result = ComfyUILocalAdapter().execute(_permit(output_root, "service_probe"))
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("SERVICE_UNAVAILABLE", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "SERVICE_UNAVAILABLE")
        self.assertTrue(any(item["relative_path"] == "failure_bundle.json" for item in result["outputs"]))

    def test_mock_auto_provision_launch_command_and_heartbeat_success(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "comfyui_local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "adapter": "comfyui_local",
                        "base_url": "http://127.0.0.1:8188",
                        "heartbeat_path": "/system_stats",
                        "launch_command": ["python3", "-c", "print('ready')"],
                        "startup_timeout_seconds": 1,
                        "working_dir": tempdir,
                    }
                ),
                encoding="utf-8",
            )
            adapter = ComfyUILocalAdapter(config_path=config_path)
            permit = _permit(Path(tempdir) / "out", "service_probe", auto_provision=True)
            fake_process = mock.Mock(pid=1234)
            with (
                mock.patch("execution_plane.adapters.comfyui_local.subprocess.Popen", return_value=fake_process) as popen,
                mock.patch(
                    "execution_plane.adapters.comfyui_local.probe_comfyui",
                    side_effect=[
                        {"adapter": "comfyui_local", "available": False},
                        {"adapter": "comfyui_local", "available": True},
                    ],
                ),
                mock.patch("execution_plane.adapters.comfyui_local.sleep", return_value=None),
            ):
                result = adapter.auto_provision(permit, permit)
        self.assertEqual(result.status, "PROVISIONED")
        self.assertEqual(result.heartbeat_status, "READY")
        popen.assert_called_once()

    def test_submit_workflow_posts_prompt_polls_history_and_collects_outputs(self) -> None:
        workflow = _workflow()
        history = {
            "prompt-1": {
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "seos_test.png", "subfolder": "", "type": "output"},
                        ]
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "submit"
            router = _ComfyUIRouter(history=history)
            with mock.patch("execution_plane.adapters.comfyui_local.urlopen", side_effect=router):
                result = ComfyUILocalAdapter().execute(
                    _permit(output_root, "submit_workflow"),
                    {
                        "workflow": workflow,
                        "history_timeout_seconds": 0,
                        "poll_interval_seconds": 0,
                    },
                )
            posted = next(req for req in router.requests if req["path"] == "/prompt")
            posted_body = json.loads(posted["data"].decode("utf-8"))
            output_exists = (output_root / "comfyui_outputs" / "seos_test.png").exists()
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(posted["method"], "POST")
        self.assertEqual(posted_body["prompt"], workflow)
        self.assertTrue(output_exists)
        self.assertTrue(any(ref["media_type"] == "image/png" for ref in result["artifact_refs"]))
        self.assertTrue(any(req["path"] == "/history/prompt-1" for req in router.requests))
        self.assertTrue(any(req["path"] == "/view" for req in router.requests))

    def test_poll_history_action_writes_history_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "history"
            router = _ComfyUIRouter(history={"prompt-1": {"outputs": {}}})
            with mock.patch("execution_plane.adapters.comfyui_local.urlopen", side_effect=router):
                result = ComfyUILocalAdapter().execute(
                    _permit(output_root, "poll_history"),
                    {"prompt_id": "prompt-1"},
                )
            history_exists = (output_root / "history.json").exists()
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertTrue(history_exists)
        self.assertTrue(any(req["path"] == "/history/prompt-1" for req in router.requests))

    def test_collect_outputs_downloads_view_artifact(self) -> None:
        history = {
            "prompt-2": {
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "nested.png", "subfolder": "batch_a", "type": "output"},
                        ]
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "collect"
            router = _ComfyUIRouter(history=history)
            with mock.patch("execution_plane.adapters.comfyui_local.urlopen", side_effect=router):
                result = ComfyUILocalAdapter().execute(
                    _permit(output_root, "collect_outputs"),
                    {"prompt_id": "prompt-2", "history": history},
                )
            output_exists = (output_root / "comfyui_outputs" / "batch_a" / "nested.png").exists()
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertTrue(output_exists)
        self.assertTrue(any(item["relative_path"].endswith("nested.png") for item in result["outputs"]))

    def test_collect_comfyui_outputs_helper_returns_hashes(self) -> None:
        history = {
            "prompt-3": {
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "direct.png", "subfolder": "", "type": "output"},
                        ]
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir)
            client = mock.Mock()
            client.output_directory_mapping = {"output": "comfyui_outputs"}
            client.view.return_value = PNG_BYTES
            outputs = collect_comfyui_outputs(
                client=client,
                history_payload=history,
                prompt_id="prompt-3",
                output_root=output_root,
            )
        self.assertEqual(outputs[0]["relative_path"], "comfyui_outputs/direct.png")
        self.assertTrue(outputs[0]["sha256"].startswith("sha256:"))

    def test_output_missing_is_failure_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output_root = Path(tempdir) / "missing"
            router = _ComfyUIRouter(history={"prompt-1": {"outputs": {}}})
            with mock.patch("execution_plane.adapters.comfyui_local.urlopen", side_effect=router):
                result = ComfyUILocalAdapter().execute(
                    _permit(output_root, "submit_workflow"),
                    {
                        "workflow": _workflow(),
                        "history_timeout_seconds": 0,
                        "poll_interval_seconds": 0,
                    },
                )
            bundle = json.loads((output_root / "failure_bundle.json").read_text(encoding="utf-8"))
            receipt = json.loads((output_root / "execution_receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("OUTPUT_MISSING", result["policy_blocks"])
        self.assertEqual(bundle["failure_code"], "OUTPUT_MISSING")
        self.assertEqual(receipt["status"], "FAILED")


class _Response:
    def __init__(self, payload: object, *, raw: bool = False) -> None:
        self.status = 200
        self._body = payload if raw else json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return bytes(self._body)


class _ComfyUIRouter:
    def __init__(self, *, history: dict[str, object] | None = None) -> None:
        self.history = history or {"prompt-1": {"outputs": {}}}
        self.requests: list[dict[str, object]] = []

    def __call__(self, request: object, timeout: float = 0) -> _Response:
        url = getattr(request, "full_url", str(request))
        parsed = urlparse(url)
        data = getattr(request, "data", None)
        method = request.get_method() if hasattr(request, "get_method") else "GET"
        self.requests.append({"method": method, "path": parsed.path, "query": parsed.query, "data": data, "timeout": timeout})
        if parsed.path == "/system_stats":
            return _Response({"system": {"os": "mock"}, "devices": []})
        if parsed.path == "/prompt":
            return _Response({"prompt_id": "prompt-1"})
        if parsed.path.startswith("/history/"):
            return _Response(self.history)
        if parsed.path == "/view":
            return _Response(PNG_BYTES, raw=True)
        raise AssertionError(f"unexpected ComfyUI URL: {url}")


def _permit(output_root: Path, action: str, *, auto_provision: bool = False) -> dict[str, object]:
    return create_execution_permit(
        task_id=f"TASK_COMFYUI_{action.upper()}",
        operator_approval_id=f"RCPT_COMFYUI_{action.upper()}",
        allowed_adapter="comfyui_local",
        allowed_action=action,
        allowed_output_root=output_root,
        expires_at="2099-01-01T00:00:00Z",
        auto_provision={
            "enabled": auto_provision,
            "allowed_adapters": ["comfyui_local"] if auto_provision else [],
            "max_wait_seconds": 1 if auto_provision else 0,
            "heartbeat_interval_seconds": 1,
        },
    )


def _workflow() -> dict[str, object]:
    return {
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "seos_test",
                "images": ["8", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2],
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
