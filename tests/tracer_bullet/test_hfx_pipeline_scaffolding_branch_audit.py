"""Audit tests for the hfx-pipeline-scaffolding branch note."""

from __future__ import annotations

import unittest
from pathlib import Path


class HfxPipelineScaffoldingBranchAuditTests(unittest.TestCase):
    def test_audit_document_contains_required_decision(self) -> None:
        text = Path("docs/research/hfx_pipeline_scaffolding_branch_audit_v1.md").read_text(encoding="utf-8").lower()
        for phrase in (
            "decision: defer",
            "must not be merged now",
            "schema-only layers are not production landing",
            "job queue",
            "artifact store",
            "materialization",
            "no final hfx claim",
            "do not vendor raw assets",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
