"""Tests for Post-529 Operator Closure V1 runbook."""

from __future__ import annotations

import unittest
from pathlib import Path

RUNBOOK_PATH = Path("docs/runbooks/post_529_operator_closure_v1.md")
MANDATORY_COMMANDS = (
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests",
    "make ci",
    "git diff --check",
    "git status --short",
)
PRIORITY_MARKERS = (
    "#529",
    "P530",
    "P531",
    "P532",
    "P533",
    "P534",
    "P535",
    "P536",
)
ARTIFACT_PATHS = (
    "release-candidate-final-signoff/reports/final-signoff-report.json",
    "independent-final-signoff-verification/reports/independent-verification-report.json",
    "evidence-transparency-merkle/reports/transparency-report.json",
    "declarative-policy-gate-bundle/reports/policy-decision-report.json",
    "deterministic-fault-simulation/reports/fault-simulation-report.json",
    "release-ceremony-tagging/tag-command/tag-command-proposal.json",
    "integrated-hard-audit/reports/integrated-hard-audit-report.md",
)


def _runbook_text() -> str:
    return RUNBOOK_PATH.read_text(encoding="utf-8")


class Post529OperatorClosureRunbookV1Tests(unittest.TestCase):
    def test_runbook_links_all_priorities_and_required_sections(self) -> None:
        text = _runbook_text()
        for marker in PRIORITY_MARKERS:
            self.assertIn(marker, text)
        for heading in (
            "## Exact Command Order",
            "## Failure Interpretation",
            "## Evidence Artifact Paths",
            "## Release And Tagging Approval Boundary",
            "## Rollback And Recovery",
            "## Clean Reset Instructions",
            "## No-Go Conditions",
            "## Do-Not-Proceed Conditions",
        ):
            self.assertIn(heading, text)

    def test_mandatory_commands_are_present_in_exact_order_twice(self) -> None:
        text = _runbook_text()
        first_positions = [text.index(command) for command in MANDATORY_COMMANDS]
        self.assertEqual(first_positions, sorted(first_positions))
        second_start = text.index("After merge, rerun")
        second_positions = [
            text.index(command, second_start)
            for command in MANDATORY_COMMANDS
        ]
        self.assertEqual(second_positions, sorted(second_positions))

    def test_pr_merge_and_branch_retention_commands_are_documented(self) -> None:
        text = _runbook_text()
        self.assertIn("gh pr merge 536 --squash --match-head-commit <P536_HEAD_SHA>", text)
        self.assertIn(
            "git ls-remote --heads origin codex/post-529-p536-docs-operator-runbook-closure-v1",
            text,
        )
        self.assertIn("git pull --ff-only origin main", text)

    def test_artifact_paths_and_release_boundary_are_documented(self) -> None:
        text = _runbook_text()
        for path in ARTIFACT_PATHS:
            self.assertIn(path, text)
        for phrase in (
            "Do not create a tag.",
            "Do not push",
            "Do not publish a release.",
            "tag command proposal only",
        ):
            self.assertIn(phrase, text)

    def test_no_go_clean_reset_and_secret_boundary_are_documented(self) -> None:
        text = _runbook_text()
        for phrase in (
            "git fetch origin main",
            "git switch main",
            "git status --short",
            "Do not use destructive reset commands",
            "credentials, `.env` files, or secret-bearing material",
            "transparency proof verification fails",
            "policy decision denies the release ceremony",
            "fault simulation reports unsafe recovery",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
