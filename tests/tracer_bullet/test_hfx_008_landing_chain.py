"""Tests for the HFX_008 dry-run landing chain."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.hfx_008_landing_chain import (
    HFX_008_STAGES,
    build_hfx_008_dry_run_jobs,
    execute_hfx_008_dry_run_chain,
    summarize_hfx_008_landing_chain,
)
from kernel.os_engine.local_os_runtime import LocalOSRuntime


class Hfx008LandingChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_chain_builds_deterministically(self) -> None:
        with LocalOSRuntime(root=self.root / "runtime", repo_root=Path.cwd()) as runtime:
            first = build_hfx_008_dry_run_jobs(runtime)
            second = build_hfx_008_dry_run_jobs(runtime)
            self.assertEqual(first, second)
            self.assertEqual(len(first), len(HFX_008_STAGES))

    def test_dry_run_records_artifacts_and_blocks_final_claim(self) -> None:
        with LocalOSRuntime(root=self.root / "runtime", repo_root=Path.cwd()) as runtime:
            summary = execute_hfx_008_dry_run_chain(runtime)
            self.assertFalse(summary.final_claim_allowed)
            self.assertTrue(summary.artifact_ids)
            self.assertIn("resource package missing", summary.blockers)
            self.assertIn("real visual proof missing", summary.blockers)
            self.assertIn("human review approval missing", summary.blockers)
            self.assertTrue(any("hfx_008_topology_audit_json" in item["target_artifact_id"] for item in summary.materialization_statuses))

    def test_approval_alone_cannot_unlock_without_valid_artifact(self) -> None:
        with LocalOSRuntime(root=self.root / "runtime", repo_root=Path.cwd()) as runtime:
            execute_hfx_008_dry_run_chain(runtime)
            review = runtime.human_review_gate.list_reviews()[0]
            runtime.human_review_gate.approve_review(review_id=review.review_id, reviewer="operator", reason="dry-run approval test")
            summary = summarize_hfx_008_landing_chain(runtime)
            self.assertFalse(summary.final_claim_allowed)
            self.assertIn("approval alone cannot unlock final claim without valid visual proof", summary.blockers)

    def test_no_houdini_launch_or_binary_artifact_in_tests(self) -> None:
        source = Path("kernel/os_engine/hfx_008_landing_chain.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        with LocalOSRuntime(root=self.root / "runtime", repo_root=Path.cwd()) as runtime:
            execute_hfx_008_dry_run_chain(runtime)
            suffixes = {Path(item.local_path).suffix for item in runtime.artifact_store.list_artifacts()}
            self.assertFalse(suffixes & {".hip", ".hiplc", ".exr", ".mov", ".mp4", ".vdb"})

    def test_replay_after_db_reopen_preserves_chain_state(self) -> None:
        runtime = LocalOSRuntime(root=self.root / "runtime", repo_root=Path.cwd())
        summary = execute_hfx_008_dry_run_chain(runtime)
        content_hash = summary.content_hash
        runtime.close()
        reopened = LocalOSRuntime(root=self.root / "runtime", repo_root=Path.cwd())
        try:
            self.assertEqual(content_hash, summarize_hfx_008_landing_chain(reopened).content_hash)
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
