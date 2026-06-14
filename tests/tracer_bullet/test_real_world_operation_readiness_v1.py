"""Tests for AI Agent Control Plane V4-V7 operation readiness."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FINAL_SCORECARD = REPO_ROOT / "reports" / "control-plane" / "final-scorecard-v1.json"
EXTERNAL_LEDGER = REPO_ROOT / "reports" / "control-plane" / "external-evidence-ledger-v1.json"
NON_CLAIM = REPO_ROOT / "reports" / "control-plane" / "non-claim-audit-v1.json"
TASK_FIXTURES = REPO_ROOT / "reports" / "control-plane" / "task-fixtures-v1.json"
PRODUCTION_BLOCKERS = REPO_ROOT / "reports" / "control-plane" / "production-operation-blocker-ledger-v1.json"


class RealWorldOperationReadinessV1Tests(unittest.TestCase):
    def test_full_stack_operation_readiness_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/real_world_operation_readiness_check_v1.py", "--stage", "all"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("real_world_operation_readiness_check_v1: PASS (all)", completed.stdout)

    def test_task_fixtures_cover_allow_dry_run_deny_and_tool_poisoning(self) -> None:
        fixtures = json.loads(TASK_FIXTURES.read_text(encoding="utf-8"))["fixtures"]
        decisions = {fixture["expected_policy_decision"] for fixture in fixtures}
        self.assertIn("ALLOW", decisions)
        self.assertIn("DRY_RUN_ONLY", decisions)
        self.assertIn("DENY", decisions)
        self.assertTrue(
            any("untrusted_tool_instruction" in fixture["risk_hints"] for fixture in fixtures)
        )

    def test_external_evidence_ledger_is_empty_and_schema_bound(self) -> None:
        ledger = json.loads(EXTERNAL_LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(ledger["entries"], [])
        self.assertTrue(ledger["empty_ledger_is_allowed"])
        self.assertTrue(ledger["fabricated_ledger_is_forbidden"])
        for field in (
            "source",
            "actor",
            "date",
            "artifact",
            "claim_supported",
            "claim_not_supported",
            "confidence",
            "next_action",
        ):
            self.assertIn(field, ledger["required_fields"])

    def test_non_claim_audit_blocks_external_claims(self) -> None:
        audit = json.loads(NON_CLAIM.read_text(encoding="utf-8"))
        self.assertEqual(audit["status"], "passed_local")
        self.assertEqual(audit["audit_result"], "unsupported external claims are blocked")
        for claim in audit["unsupported_claims"]:
            self.assertFalse(claim["supported"], claim["claim"])

    def test_final_scorecard_records_local_readiness_and_external_blockers(self) -> None:
        scorecard = json.loads(FINAL_SCORECARD.read_text(encoding="utf-8"))
        self.assertEqual(
            scorecard["terminal_status"],
            "CONTROLLED_AUTONOMOUS_ENGINEERING_OS_FULL_STACK_OPERATION_READY",
        )
        rows = {row["area"]: row for row in scorecard["scorecard"]}
        self.assertEqual(rows["V4 core"]["status"], "implemented_local")
        self.assertEqual(rows["V5 commercial validation"]["status"], "implemented_local")
        self.assertEqual(
            rows["V6 real-world validation"]["status"],
            "implemented_local_external_evidence_pending",
        )
        self.assertEqual(
            rows["V7 commercial operation"]["status"],
            "implemented_local_external_evidence_pending",
        )
        self.assertIn("real customer validation", scorecard["what_still_cannot_be_claimed"])

    def test_production_blocker_ledger_keeps_production_claim_blocked(self) -> None:
        blockers = json.loads(PRODUCTION_BLOCKERS.read_text(encoding="utf-8"))["blockers"]
        names = {blocker["blocker"] for blocker in blockers}
        for required in (
            "hosting/deployment mode",
            "secrets management",
            "auth/access control",
            "audit retention",
            "backups and recovery",
            "incident response",
            "monitoring and telemetry",
            "customer data handling",
            "legal/compliance",
        ):
            self.assertIn(required, names)

    def test_makefile_and_ci_wire_the_gate(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("controlled-execution-check:", makefile)
        self.assertIn("commercial-readiness-check:", makefile)
        self.assertIn("real-world-validation-check:", makefile)
        self.assertIn("real-world-operation-check:", makefile)
        self.assertIn("full-stack-operation-readiness-check:", makefile)
        self.assertIn("Run AI Agent Control Plane full-stack operation readiness check", workflow)


if __name__ == "__main__":
    unittest.main()

