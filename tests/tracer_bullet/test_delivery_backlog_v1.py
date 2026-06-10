"""Static governance tests for the delivery backlog."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKLOG_PATH = REPO_ROOT / "governance" / "delivery" / "sovereign_os_delivery_backlog_v1.md"


class DeliveryBacklogV1Tests(unittest.TestCase):
    def test_backlog_contains_required_delivery_sections(self) -> None:
        text = BACKLOG_PATH.read_text(encoding="utf-8")

        for heading in (
            "## Milestone Queue",
            "## Dependency Map",
            "## Branch Naming Rules",
            "## PR Title Rules",
            "## Validation Rules",
            "## Forbidden Surface Rules",
            "## Audit Packet Format",
            "## Merge Readiness Criteria",
            "## Waiting-For-Merge State Definition",
            "## Non-Authority Statement",
        ):
            self.assertIn(heading, text)

    def test_backlog_defines_required_milestones_and_dependency_states(self) -> None:
        text = BACKLOG_PATH.read_text(encoding="utf-8")

        for milestone in (
            "Delivery Backlog V1",
            "Milestone Dependency Graph V1",
            "PR Factory And Merge Audit V1",
            "Real Local Runner Boundary V1",
            "Capability Token Lifecycle V1",
            "Local Job Queue V1",
            "Replay Engine V1",
            "Artifact Ledger Viewer V1",
            "Operator Dashboard Model V1",
            "Bounded Worker Registry V1",
            "Domain Adapter Foundation V1",
            "ComfyUI Local Adapter Contract V1",
            "DCC Adapter Foundation V1",
            "End-To-End Acceptance Matrix V1",
            "Mainline Release Readiness Gate V1",
            "WAITING_FOR_PREVIOUS_PR_MERGE",
            "WAITING_FOR_DOMAIN_ADAPTER_FOUNDATION_MERGE",
        ):
            self.assertIn(milestone, text)

    def test_backlog_locks_forbidden_delivery_authority(self) -> None:
        text = BACKLOG_PATH.read_text(encoding="utf-8")
        lowered = text.lower()

        for required_denial in (
            "never push directly to `main`",
            "no auto-merge is permitted",
            "push to main",
            "enable auto-merge",
            "delete branches",
            "no executable runtime behavior",
        ):
            self.assertIn(required_denial, lowered)

        for forbidden_grant in (
            "auto-merge allowed",
            "enable auto-merge automatically",
            "push to main allowed",
            "delete branches allowed",
            "merge without human review",
        ):
            self.assertNotIn(forbidden_grant, lowered)


if __name__ == "__main__":
    unittest.main()
