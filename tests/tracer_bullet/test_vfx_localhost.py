"""Tracer-bullet tests for the desktop ComfyUI localhost bridge."""

from __future__ import annotations

from urllib.error import URLError
from unittest.mock import patch
import asyncio
import unittest

from kernel.ipc.vfx_localhost import (
    ComfyUIEndpointRejected,
    VfxPromptRequest,
    VfxSubmissionError,
    build_text_to_image_dag,
    submit_prompt,
)


class _FakeResponse:
    def __init__(self, raw: bytes) -> None:
        self._raw = raw

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _size: int) -> bytes:
        return self._raw


class VfxLocalhostTests(unittest.TestCase):
    def test_connection_refusal_is_returned_as_submission_error(self) -> None:
        request = VfxPromptRequest(positive_prompt="controlled render")
        with patch(
            "kernel.ipc.vfx_localhost.urlopen",
            side_effect=URLError(ConnectionRefusedError(61, "connection refused")),
        ):
            with self.assertRaisesRegex(VfxSubmissionError, "unavailable"):
                asyncio.run(submit_prompt(request, timeout_seconds=0.01))

    def test_timeout_is_returned_as_submission_error(self) -> None:
        request = VfxPromptRequest(positive_prompt="controlled render")
        with patch("kernel.ipc.vfx_localhost.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(VfxSubmissionError, "timed out"):
                asyncio.run(submit_prompt(request, timeout_seconds=0.01))

    def test_malformed_json_response_is_rejected(self) -> None:
        request = VfxPromptRequest(positive_prompt="controlled render")
        with patch("kernel.ipc.vfx_localhost.urlopen", return_value=_FakeResponse(b"{not-json")):
            with self.assertRaisesRegex(VfxSubmissionError, "valid JSON"):
                asyncio.run(submit_prompt(request, timeout_seconds=1))

    def test_non_loopback_endpoint_is_rejected(self) -> None:
        request = VfxPromptRequest(positive_prompt="controlled render")
        with self.assertRaises(ComfyUIEndpointRejected):
            asyncio.run(submit_prompt(request, base_url="http://192.168.1.10:8188", timeout_seconds=1))

    def test_dag_builder_does_not_execute_comfyui(self) -> None:
        dag = build_text_to_image_dag(VfxPromptRequest(positive_prompt="controlled render"))

        self.assertEqual(sorted(dag), ["1", "2", "3", "4", "5", "6", "7"])
        self.assertEqual(dag["7"]["class_type"], "SaveImage")


if __name__ == "__main__":
    unittest.main()
