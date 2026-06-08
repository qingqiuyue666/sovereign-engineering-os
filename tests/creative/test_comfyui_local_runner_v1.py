from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path

from creative.runners.comfyui_local_runner import (
    ComfyUIHttpResponse,
    ComfyUILocalRunnerError,
    ComfyUIWorkflowRequest,
    run_comfyui_workflow_smoke,
)

REPO = Path(__file__).resolve().parents[2]
WORKFLOW_FIXTURE = REPO / "tests/fixtures/creative/comfyui/api_workflow_fixture_v1.json"
OBSERVED_AT = "2026-06-08T00:00:00Z"


class FakeComfyUITransport:
    def __init__(self, *, mode: str = "success") -> None:
        self.mode = mode
        self.calls: list[tuple[str, str]] = []
        self.prompt_id = ""

    def __call__(
        self,
        method: str,
        url: str,
        body: bytes | None,
        headers: object,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> ComfyUIHttpResponse:
        del headers, timeout_seconds, max_response_bytes
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        self.calls.append((method, path))
        if self.mode == "unavailable" and path == "/system_stats":
            raise OSError("connection refused")
        if path == "/system_stats":
            return _json_response(
                {
                    "devices": [{"name": "fixture gpu", "type": "cuda"}],
                    "system": {
                        "comfyui_frontend_version": "fixture-frontend",
                        "comfyui_version": "fixture-comfy",
                        "embedded_python": False,
                        "python_version": "3.11.fixture",
                        "pytorch_version": "2.fixture",
                    },
                }
            )
        if path == "/prompt":
            payload = json.loads((body or b"{}").decode("utf-8"))
            self.prompt_id = str(payload.get("prompt_id") or "fixture-prompt")
            if self.mode == "prompt_rejected":
                return _json_response(
                    {
                        "error": "fixture validation failed",
                        "node_errors": {"1": {"errors": ["bad node"]}},
                    }
                )
            return _json_response({"number": 1, "prompt_id": self.prompt_id})
        if path.startswith("/history/"):
            if self.mode == "timeout":
                time.sleep(0.001)
                return _json_response({})
            return _json_response(
                {
                    self.prompt_id: {
                        "outputs": {
                            "2": {
                                "images": [
                                    {
                                        "filename": "seos_comfyui_smoke_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                        "status": {
                            "completed": True,
                            "messages": [["execution_start", {}], ["execution_success", {}]],
                            "status_str": "success",
                        },
                    }
                }
            )
        if path == "/view":
            return ComfyUIHttpResponse(
                status_code=200,
                body=b"\x89PNG\r\n\x1a\nfixture-image",
                headers={"content-type": "image/png"},
            )
        return _json_response({"error": "unexpected path"}, status_code=404)


def _json_response(payload: object, *, status_code: int = 200) -> ComfyUIHttpResponse:
    return ComfyUIHttpResponse(
        status_code=status_code,
        body=json.dumps(payload, sort_keys=True).encode("utf-8"),
        headers={"content-type": "application/json"},
    )


class ComfyUILocalRunnerV1Tests(unittest.TestCase):
    def test_missing_workflow_returns_env_not_found_without_contacting_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            transport = FakeComfyUITransport()
            result = run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=temp_dir / "missing_workflow.json",
                    output_root=temp_dir / "out",
                    observed_at=OBSERVED_AT,
                ),
                transport=transport,
            )

            self.assertEqual(result["status"], "ENV_NOT_FOUND")
            self.assertEqual(result["error_code"], "ENV_NOT_FOUND")
            self.assertFalse(result["execution_attempted"])
            self.assertEqual(transport.calls, [])
            self.assertEqual(result["materialization"]["status"], "blocked_resource_missing")

    def test_service_unavailable_returns_truthful_preflight_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            result = run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=WORKFLOW_FIXTURE,
                    output_root=Path(temp_dir_name) / "out",
                    observed_at=OBSERVED_AT,
                ),
                transport=FakeComfyUITransport(mode="unavailable"),
            )

            self.assertEqual(result["status"], "SERVICE_UNAVAILABLE")
            self.assertEqual(result["error_code"], "SERVICE_UNAVAILABLE")
            self.assertFalse(result["execution_attempted"])
            self.assertEqual(result["service"]["status"], "SERVICE_UNAVAILABLE")

    def test_service_available_requires_approval_before_prompt_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            transport = FakeComfyUITransport()
            result = run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=WORKFLOW_FIXTURE,
                    output_root=Path(temp_dir_name) / "out",
                    observed_at=OBSERVED_AT,
                ),
                transport=transport,
            )

            self.assertEqual(result["status"], "USER_APPROVAL_REQUIRED")
            self.assertFalse(result["execution_attempted"])
            self.assertIn(("GET", "/system_stats"), transport.calls)
            self.assertNotIn(("POST", "/prompt"), transport.calls)
            self.assertEqual(result["materialization"]["status"], "blocked_human_review_required")

    def test_fake_success_writes_summaries_and_downloaded_artifact_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            result = run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=WORKFLOW_FIXTURE,
                    output_root=temp_dir / "out",
                    approved=True,
                    approval_id="approval-comfyui-smoke-001",
                    observed_at=OBSERVED_AT,
                ),
                transport=FakeComfyUITransport(),
            )

            self.assertEqual(result["status"], "EXECUTED")
            self.assertTrue(result["complete"])
            self.assertTrue(result["execution_attempted"])
            self.assertEqual(result["error_code"], None)
            self.assertEqual(result["outputs"]["artifact_count"], 1)
            self.assertTrue(result["outputs"]["artifacts"][0]["sha256"].startswith("sha256:"))
            self.assertTrue((temp_dir / "out/comfyui_prompt_response_summary_v1.json").exists())
            self.assertTrue((temp_dir / "out/comfyui_history_summary_v1.json").exists())
            self.assertTrue((temp_dir / "out/comfyui_output_000_2_seos_comfyui_smoke_00001_.png").exists())
            self.assertEqual(result["materialization"]["status"], "materialized_valid")
            self.assertNotIn("3158064", json.dumps(result, sort_keys=True))
            self.assertFalse(result["prompt"]["raw_prompt_persisted"])
            self.assertFalse(result["history"]["raw_history_persisted"])

    def test_prompt_validation_error_does_not_claim_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            result = run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=WORKFLOW_FIXTURE,
                    output_root=Path(temp_dir_name) / "out",
                    approved=True,
                    approval_id="approval-comfyui-smoke-002",
                    observed_at=OBSERVED_AT,
                ),
                transport=FakeComfyUITransport(mode="prompt_rejected"),
            )

            self.assertEqual(result["status"], "EXECUTION_FAILED")
            self.assertEqual(result["error_code"], "VALIDATION_FAILED")
            self.assertFalse(result["complete"])
            self.assertEqual(result["prompt"]["status"], "REJECTED")
            self.assertEqual(result["prompt"]["node_error_count"], 1)

    def test_timeout_is_classified_as_long_task_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            result = run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=WORKFLOW_FIXTURE,
                    output_root=Path(temp_dir_name) / "out",
                    approved=True,
                    approval_id="approval-comfyui-smoke-003",
                    timeout_seconds=0.02,
                    poll_interval_seconds=0.001,
                    observed_at=OBSERVED_AT,
                ),
                transport=FakeComfyUITransport(mode="timeout"),
            )

            self.assertEqual(result["status"], "LONG_TASK_BLOCKED")
            self.assertEqual(result["error_code"], "LONG_TASK_BLOCKED")
            self.assertFalse(result["complete"])

    def test_non_loopback_endpoint_is_rejected_before_contact(self) -> None:
        with self.assertRaises(ComfyUILocalRunnerError):
            run_comfyui_workflow_smoke(
                ComfyUIWorkflowRequest(
                    workflow_json=WORKFLOW_FIXTURE,
                    output_root="work/unused",
                    endpoint_url="https://example.com:8188",
                ),
                transport=FakeComfyUITransport(),
            )

    def test_cli_script_writes_env_not_found_report_without_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            result_json = temp_dir / "result.json"
            materialization_json = temp_dir / "materialization.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/creative_comfyui_workflow_smoke_v1.py",
                    "--workflow-json",
                    (temp_dir / "missing_workflow.json").as_posix(),
                    "--output-root",
                    (temp_dir / "out").as_posix(),
                    "--observed-at",
                    OBSERVED_AT,
                    "--result-json",
                    result_json.as_posix(),
                    "--materialization-json",
                    materialization_json.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "ENV_NOT_FOUND")
            self.assertTrue(result_json.exists())
            self.assertTrue(materialization_json.exists())
            self.assertEqual(json.loads(result_json.read_text(encoding="utf-8"))["status"], "ENV_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
