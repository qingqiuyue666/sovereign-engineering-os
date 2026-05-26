"""Tracer-bullet tests for the system landing master plan."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


PLAN_PATH = Path("docs/landing/sovereign_engineering_os_system_landing_master_plan_v1.md")


REQUIRED_SYSTEM_AREAS = (
    "real WAL storage",
    "durable job queue",
    "artifact store",
    "snapshot/replay store",
    "approval/policy runtime",
    "failure bundle center",
    "worker registry",
    "resource watchdog",
    "operator console",
    "replay browser",
    "install/config/packaging",
    "AI worker router",
    "DCC/media adapter integration",
    "system-level E2E acceptance",
)


REQUIRED_SECTIONS = (
    "## Definition Of 100 Percent Landing",
    "## Current State",
    "## Required Missing System Areas",
    "## Module Weight Model",
    "## Completion Stage Definitions",
    "## Dependency Graph",
    "## Phase Roadmap",
    "## Acceptance Gates",
    "## Blocker Policy",
    "## PR Train Policy",
    "## No Giant PR Policy",
    "## Local-First Policy",
    "## Evidence And Replay Policy",
    "## Production-Grade Criteria",
)


class SovereignEngineeringOsSystemLandingMasterPlanV1Tests(unittest.TestCase):
    def _plan(self) -> str:
        self.assertTrue(PLAN_PATH.is_file())
        return PLAN_PATH.read_text(encoding="utf-8")

    def test_plan_contains_required_sections(self) -> None:
        plan = self._plan()

        for section in REQUIRED_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, plan)

    def test_missing_system_areas_are_required_completion_targets(self) -> None:
        plan = self._plan()

        self.assertIn("required completion targets", plan)
        self.assertIn("not optional future work", plan)
        for area in REQUIRED_SYSTEM_AREAS:
            with self.subTest(area=area):
                self.assertIn(area, plan)

    def test_weight_model_is_complete_and_sums_to_100(self) -> None:
        plan = self._plan()
        weights = [
            int(match.group(1))
            for match in re.finditer(r"\| [^|\n]+ \| ([0-9]+) \|", plan)
        ]

        self.assertEqual(len(weights), 15)
        self.assertEqual(sum(weights), 100)

    def test_completion_stages_are_distinct(self) -> None:
        plan = self._plan()

        for stage in (
            "Foundation completion means",
            "Integration completion means",
            "Alpha completion means",
            "Beta completion means",
            "Production completion means",
        ):
            with self.subTest(stage=stage):
                self.assertIn(stage, plan)

        self.assertIn("not enough for system use", plan)
        self.assertIn("No module can be marked production complete", plan)

    def test_roadmap_covers_authorized_phase_sequence(self) -> None:
        plan = self._plan()

        for phase in tuple(f"Phase {letter}" for letter in "ABCDEFGHIJKLMNOP"):
            with self.subTest(phase=phase):
                self.assertIn(phase, plan)

        self.assertLess(plan.index("Phase A"), plan.index("Phase B"))
        self.assertLess(plan.index("Phase B"), plan.index("Phase C"))
        self.assertLess(plan.index("Phase O"), plan.index("Phase P"))

    def test_dependency_graph_and_policies_preserve_local_first_replay_scope(self) -> None:
        plan = self._plan()

        for marker in (
            "minimal controlled execution",
            "-> real WAL storage",
            "-> durable job queue",
            "-> system-level E2E acceptance",
            "local-first",
            "cold local state",
            "read-only projections",
            "No Giant PR",
            "small validated draft PRs",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, plan)

    def test_acceptance_and_blocker_policy_forbid_fake_or_unsafe_completion(self) -> None:
        plan = self._plan()

        for marker in (
            "Acceptance tests must prove real behavior",
            "uncontrolled daemon",
            "uncontrolled network calls",
            "raw stdout/stderr persistence",
            "secret persistence",
            "weakening tests",
            "pushing main",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, plan)


if __name__ == "__main__":
    unittest.main()
