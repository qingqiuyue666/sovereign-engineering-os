"""Tracer-bullet tests for private production sprint plans."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.private_production_sprint_plan import (
    PrivateProductionSprintPlan,
    build_private_production_sprint_plan,
    render_private_production_sprint_plan_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "sprint_id": "private-production-sprint-plan-v1",
        "sprint_name": "Production Workbench Activation",
        "duration_days": 7,
        "daily_plan": [
            {"day": 1, "focus": "Code Audit operational loop and branch audit report setup."},
            {"day": 2, "focus": "Merge readiness and AI worker result review packet setup."},
            {"day": 3, "focus": "Post-merge retrospective and daily report integration."},
            {"day": 4, "focus": "Creative production bible and shot plan finalization."},
            {"day": 5, "focus": "Houdini / ComfyUI / DaVinci specifications finalized."},
            {"day": 6, "focus": "Creative review rubric and sample asset review preparation."},
            {
                "day": 7,
                "focus": "Private production review, next sprint decision, and no-kernel-expansion enforcement.",
            },
        ],
        "deliverables": ["code audit reports", "creative production specs"],
        "verification_plan": ["run tracer tests", "run make ci"],
        "stop_conditions": ["kernel expansion attempt", "blocked capability violation"],
        "blocked_actions": ["provider execution", "external tool execution"],
        "review_cadence": ["daily operator review"],
        "rollback_plan": ["revert sprint plan files as a unit"],
        "policy_version": "private-production-sprint-plan-v1",
        "code_version": "0.1.0",
    }


class PrivateProductionSprintPlanTests(unittest.TestCase):
    def test_valid_sprint_plan_builds_deterministic_object(self):
        plan = build_private_production_sprint_plan(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(plan, PrivateProductionSprintPlan)
        self.assertTrue(plan.content_hash.startswith("sha256:"))
        self.assertEqual(plan.content_hash, digest_payload(plan.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_private_production_sprint_plan(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_private_production_sprint_plan(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_private_production_sprint_plan_markdown(
            build_private_production_sprint_plan(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_private_production_sprint_plan_markdown(
            build_private_production_sprint_plan(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_duration_not_7_fails_closed(self):
        material = valid_material()
        material["duration_days"] = 6

        with self.assertRaises(ValueError):
            build_private_production_sprint_plan(material)

    def test_daily_plan_not_length_7_fails_closed(self):
        material = valid_material()
        material["daily_plan"] = material["daily_plan"][:6]

        with self.assertRaises(ValueError):
            build_private_production_sprint_plan(material)

    def test_missing_deliverables_fails_closed(self):
        material = valid_material()
        del material["deliverables"]

        with self.assertRaises(ValueError):
            build_private_production_sprint_plan(material)

    def test_doc_exists(self):
        self.assertTrue(Path("docs/operator/private_production_sprint_plan_v1.md").is_file())

    def test_doc_has_day_1_through_day_7(self):
        text = Path("docs/operator/private_production_sprint_plan_v1.md").read_text(encoding="utf-8")

        for day in range(1, 8):
            self.assertIn(f"Day {day}", text)

    def test_doc_says_no_kernel_expansion_enforcement(self):
        text = Path("docs/operator/private_production_sprint_plan_v1.md").read_text(encoding="utf-8").lower()

        self.assertIn("no-kernel-expansion enforcement", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/private_production_sprint_plan.py").read_text(encoding="utf-8")

        for marker in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
