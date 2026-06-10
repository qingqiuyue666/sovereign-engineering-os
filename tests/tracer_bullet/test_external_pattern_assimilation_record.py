"""Tracer bullet tests for external architecture pattern assimilation record."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "research" / "external_pattern_assimilation_v1.md"
NEW_CORE_FILES = (
    REPO_ROOT / "kernel" / "os_engine" / "database.py",
    REPO_ROOT / "kernel" / "os_engine" / "event_log.py",
    REPO_ROOT / "kernel" / "os_engine" / "job_projection.py",
    REPO_ROOT / "kernel" / "os_engine" / "sqlite_job_queue.py",
    REPO_ROOT / "kernel" / "os_engine" / "sqlite_artifact_store.py",
    REPO_ROOT / "kernel" / "os_engine" / "materialization.py",
    REPO_ROOT / "kernel" / "os_engine" / "human_review_gate.py",
    REPO_ROOT / "kernel" / "os_engine" / "os_engine_bootstrap.py",
    REPO_ROOT / "kernel" / "os_engine" / "hfx_materialization_plans.py",
    REPO_ROOT / "apps" / "sovereign_desktop.py",
)


class ExternalPatternAssimilationRecordTests(unittest.TestCase):
    def test_document_exists_and_contains_required_sections(self) -> None:
        self.assertTrue(DOC.exists())
        text = DOC.read_text(encoding="utf-8")
        for heading in ("## Absorbed Now", "## Deferred", "## Rejected For Now", "## Boundaries"):
            self.assertIn(heading, text)
        for required in (
            "Dagster -> asset-centric materialization",
            "Temporal -> event-sourced job history",
            "SQLite WAL -> durable local brain",
            "GUI/worker split -> desktop safety boundary",
            "qasync -> GUI async hardening",
            "AYON -> DCC environment injection",
            "Aider/Tree-sitter -> AST context compression",
            "DuckDB/FSEvents -> large asset indexing",
            "ComfyUI DAG/status streaming -> future ComfyUIWorker",
            "OTIO -> future DaVinci handoff",
            "direct Temporal dependency",
            "direct Dagster dependency",
            "NATS message bus",
            "Memray runtime watchdog",
            "sandbox-exec enforcement",
            "OpenUSD/MaterialX deep integration",
            "random MCP plugin sprawl",
            "GUI automation before API/CLI control",
            "No final HFX claim",
            "No raw asset vendoring",
            "`hfx-pipeline-scaffolding` remains out of scope",
            "OS core durability, not VFX final completion",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_new_core_does_not_import_rejected_heavy_frameworks_or_network_clients(self) -> None:
        forbidden = (
            "import dagster",
            "import temporal",
            "import prefect",
            "import nats",
            "import duckdb",
            "import polars",
            "import memray",
            "import tree_sitter",
            "requests.",
            "httpx.",
            "urllib.request",
            "aiohttp",
            "shell=True",
        )
        for path in NEW_CORE_FILES:
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token.lower(), text)

    def test_no_env_reads_or_unbounded_execution_surface_in_new_core(self) -> None:
        forbidden = (
            'open(".env"',
            "open('.env'",
            "read_text('.env'",
            'read_text(".env"',
            "dotenv",
            "os.environ",
            "socket.create_connection",
            "DaVinciResolveScript",
        )
        for path in NEW_CORE_FILES:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_branch_does_not_depend_on_hfx_pipeline_scaffolding_or_vendor_binary_assets(self) -> None:
        base_ref = "origin/main"
        if subprocess.run(
            ["git", "rev-parse", "--verify", base_ref],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).returncode != 0:
            base_ref = "main"
        tracked = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        changed = sorted(
            {
                line.strip()
                for output in (tracked.stdout, untracked.stdout)
                for line in output.splitlines()
                if line.strip()
            }
        )
        if not changed:
            self.skipTest("no branch-local changed files to inspect")
        for relative in changed:
            with self.subTest(relative=relative):
                self.assertNotIn("hfx-pipeline-scaffolding", relative)
                self.assertNotIn(Path(relative).suffix.lower(), {".exr", ".mov", ".mp4", ".hip", ".hiplc", ".hipnc"})

    def test_no_final_completion_or_production_autonomy_claim_is_added(self) -> None:
        text = DOC.read_text(encoding="utf-8").lower()
        self.assertIn("no final hfx claim", text)
        self.assertIn("not vfx final completion", text)
        self.assertNotIn("final hfx completion is achieved", text)
        self.assertNotIn("production autonomy enabled", text)


if __name__ == "__main__":
    unittest.main()
