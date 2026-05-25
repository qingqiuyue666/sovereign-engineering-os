"""Read-only tests for Artifact Ledger Viewer V1."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.evidence.artifact_ledger_viewer import (
    ArtifactLedgerFilter,
    list_artifact_ledger,
    render_artifact_ledger_summary,
)
from tools.artifact_ledger_viewer import main as artifact_ledger_viewer_main


class ArtifactLedgerViewerV1Tests(unittest.TestCase):
    def make_ledger(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "receipts").mkdir()
        (root / "failures").mkdir()
        (root / "replay").mkdir()
        self.write_json(
            root / "receipts" / "runner_receipt.json",
            {
                "receipt_type": "runner_receipt_v1",
                "receipt_id": "receipt-001",
                "task_id": "task-1",
                "run_id": "run-1",
                "milestone": "A3",
                "secret_token": "SHOULD_NOT_RENDER",
                "metadata": {"api_key": "ALSO_SECRET"},
            },
        )
        self.write_json(
            root / "failures" / "failure_bundle.json",
            {
                "artifact_type": "failure_bundle_v1",
                "failure_bundle_id": "failure-001",
                "task_id": "task-1",
                "run_id": "run-2",
                "milestone": "C1",
                "raw_prompt": "DO_NOT_SHOW",
            },
        )
        self.write_json(
            root / "replay" / "replay_manifest.json",
            {
                "manifest_type": "replay_manifest_v1",
                "replay_manifest_id": "replay-001",
                "task_id": "task-2",
                "run_id": "run-3",
                "milestone": "C1",
            },
        )
        (root / "notes.txt").write_text("not json", encoding="utf-8")
        return temp_dir, root

    def write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_lists_receipts_failures_and_replay_manifests_read_only(self) -> None:
        _temp_dir, root = self.make_ledger()
        before = self.snapshot(root)

        summary = list_artifact_ledger(root)
        rendered = render_artifact_ledger_summary(summary)

        self.assertEqual(summary.total_entries, 3)
        self.assertEqual(summary.receipt_entries, 1)
        self.assertEqual(summary.failure_bundle_entries, 1)
        self.assertEqual(summary.replay_manifest_entries, 1)
        self.assertIs(summary.mutation_performed, False)
        self.assertIs(summary.deletion_performed, False)
        self.assertEqual(before, self.snapshot(root))
        self.assertNotIn("SHOULD_NOT_RENDER", rendered)
        self.assertNotIn("ALSO_SECRET", rendered)
        self.assertNotIn("DO_NOT_SHOW", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_filters_by_task_run_milestone_and_kind(self) -> None:
        _temp_dir, root = self.make_ledger()

        task_summary = list_artifact_ledger(root, ArtifactLedgerFilter(task_id="task-1"))
        run_summary = list_artifact_ledger(root, ArtifactLedgerFilter(run_id="run-3"))
        milestone_summary = list_artifact_ledger(root, ArtifactLedgerFilter(milestone="C1"))
        receipt_summary = list_artifact_ledger(
            root,
            ArtifactLedgerFilter(artifact_kind="receipt"),
        )

        self.assertEqual(task_summary.total_entries, 2)
        self.assertEqual(run_summary.total_entries, 1)
        self.assertEqual(milestone_summary.total_entries, 2)
        self.assertEqual(receipt_summary.total_entries, 1)
        self.assertEqual(receipt_summary.entries[0].receipt_id, "receipt-001")

    def test_cli_prints_redacted_summary_without_writing(self) -> None:
        _temp_dir, root = self.make_ledger()
        before = self.snapshot(root)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = artifact_ledger_viewer_main_with_args(
                [root.as_posix(), "--milestone", "C1"]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["total_entries"], 2)
        self.assertIs(payload["mutation_performed"], False)
        self.assertIs(payload["deletion_performed"], False)
        self.assertEqual(before, self.snapshot(root))

    def test_source_has_no_mutation_deletion_runtime_or_network_surface(self) -> None:
        source = Path("kernel/evidence/artifact_ledger_viewer.py").read_text(encoding="utf-8")
        cli_source = Path("tools/artifact_ledger_viewer.py").read_text(encoding="utf-8")
        combined = source + "\n" + cli_source

        for marker in (
            "unlink(",
            "remove(",
            "rmtree(",
            "subprocess",
            "requests.",
            "urllib.",
            "webbrowser",
            "socket",
            "open_browser",
        ):
            self.assertNotIn(marker, combined)

    def snapshot(self, root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }


def artifact_ledger_viewer_main_with_args(args: list[str]) -> int:
    import sys

    original = sys.argv
    try:
        sys.argv = ["artifact_ledger_viewer.py", *args]
        return artifact_ledger_viewer_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    unittest.main()
