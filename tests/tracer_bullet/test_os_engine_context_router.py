"""Hardening tests for sanitized OS engine context packets."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.context_router import ContextRouter, ContextUseCase


class OsEngineContextRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="seos-context-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        self._write("kernel/os_engine/job_queue.py", "print('queue')\n")
        self._write("apps/sovereign_desktop.py", "APP = 'desktop'\n")
        self._write("assets/houdini/hfx_note.md", "hfx note\n")
        self._write("tests/tracer_bullet/test_sample.py", "def test_x(): pass\n")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        self.output = self.tmp / "packs"
        self.router = ContextRouter(repo_root=self.repo, output_dir=self.output, command_output_limit_bytes=16_384)

    def _write(self, relative: str, text: str | bytes) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    async def test_single_md_context_packet_is_generated_deterministically(self) -> None:
        self._write("kernel/os_engine/job_queue.py", "TOKEN = 'abc'\n")
        first = await self.router.build_context_pack(
            task_instructions="Codex branch hardening packet",
            deterministic=True,
            max_output_bytes=32_000,
        )
        second = await self.router.build_context_pack(
            task_instructions="Codex branch hardening packet",
            deterministic=True,
            max_output_bytes=32_000,
        )
        self.assertEqual(first.path.suffix, ".md")
        self.assertEqual(first.sha256, second.sha256)
        text = first.path.read_text(encoding="utf-8")
        self.assertIn("Task Instructions: Codex branch hardening packet", text)
        self.assertIn("[REDACTED_SECRET]", text)
        self.assertNotIn("TOKEN = 'abc'", text)

    async def test_binary_cache_ds_store_and_secret_files_are_excluded(self) -> None:
        self._write("binary.exr", b"\x00\x01raw")
        self._write("__pycache__/x.pyc", b"\x00pyc")
        self._write(".DS_Store", b"raw")
        self._write(".env", "TOKEN=raw\n")
        result = await self.router.build_context_pack(changed_files_only=False, deterministic=True)
        text = result.path.read_text(encoding="utf-8")
        self.assertNotIn("raw", text)
        self.assertIn("binary.exr", text)
        self.assertIn("__pycache__/x.pyc", text)
        self.assertIn(".DS_Store", text)
        self.assertIn(".env", text)

    async def test_token_budget_enforces_summary_mode(self) -> None:
        self._write("kernel/os_engine/huge.py", "x = 1\n" * 1000)
        result = await self.router.build_context_pack(deterministic=True, max_output_bytes=800)
        text = result.path.read_text(encoding="utf-8")
        self.assertTrue(result.summary_mode)
        self.assertLessEqual(result.size_bytes, 900)
        self.assertIn("Summary Mode", text)

    async def test_topic_filters_changed_file_mode_and_required_use_cases(self) -> None:
        self._write("kernel/os_engine/job_queue.py", "print('changed')\n")
        hfx = await self.router.build_context_pack(
            use_case=ContextUseCase.HFX_PHYSICAL_PROOF_REVIEW,
            changed_files_only=False,
            deterministic=True,
        )
        hfx_text = hfx.path.read_text(encoding="utf-8")
        self.assertIn("hfx_note.md", hfx_text)
        self.assertNotIn("sovereign_desktop.py", hfx_text)

        desktop = await self.router.build_context_pack(
            use_case=ContextUseCase.DESKTOP_OS_ENGINE_REVIEW,
            changed_files_only=False,
            deterministic=True,
        )
        desktop_text = desktop.path.read_text(encoding="utf-8")
        self.assertIn("sovereign_desktop.py", desktop_text)
        self.assertIn("kernel/os_engine/job_queue.py", desktop_text)

        tests_only = await self.router.build_context_pack(
            topic_filters=("tests/",),
            changed_files_only=False,
            deterministic=True,
        )
        self.assertIn("tests/tracer_bullet/test_sample.py", tests_only.path.read_text(encoding="utf-8"))

        changed = await self.router.build_context_pack(changed_files_only=True, deterministic=True)
        self.assertIn("kernel/os_engine/job_queue.py", changed.path.read_text(encoding="utf-8"))

        gemini = await self.router.build_context_pack(
            use_case=ContextUseCase.GEMINI_FULL_SYSTEM_REVIEW,
            changed_files_only=False,
            deterministic=True,
        )
        self.assertIn("gemini_full_system_review", gemini.path.read_text(encoding="utf-8"))

    async def test_context_packet_does_not_include_raw_environment_values(self) -> None:
        os.environ["SEOS_TEST_RAW_ENV_SECRET"] = "DO_NOT_PERSIST_THIS_VALUE"
        self._write("kernel/os_engine/job_queue.py", "print('changed')\n")
        result = await self.router.build_context_pack(deterministic=True)
        self.assertNotIn("DO_NOT_PERSIST_THIS_VALUE", result.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
