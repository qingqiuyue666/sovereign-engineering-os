"""Tracer-bullet tests for private production roadmaps."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.private_production_roadmap import (
    PrivateProductionRoadmap,
    build_private_production_roadmap,
    render_private_production_roadmap_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "roadmap_id": "private-production-roadmap-v1",
        "current_phase": "private production operating layer",
        "completed_layers": [
            "durable decision store",
            "durable review store",
            "recovery",
            "audit export",
            "reports",
        ],
        "frozen_layers": [
            "kernel expansion is frozen after durable/recovery/audit/export/report layers",
        ],
        "next_workbenches": [
            "Code Audit Daily Report is first",
            "Creative Asset Factory is second",
            "Macro Signal Research Boundary is research-only",
        ],
        "forbidden_directions": [
            "automatic financial execution is forbidden",
            "no provider execution until separately authorized",
            "no production autonomy until separately authorized",
        ],
        "decision_rules": [
            "prefer output workbenches over kernel expansion",
        ],
        "success_metrics": [
            "priority tests pass",
        ],
        "stop_conditions": [
            "slice requires trading automation",
        ],
        "policy_version": "private-production-roadmap-v1",
        "code_version": "0.1.0",
    }


class PrivateProductionRoadmapTests(unittest.TestCase):
    def test_valid_roadmap_builds_deterministic_object(self):
        roadmap = build_private_production_roadmap(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(roadmap, PrivateProductionRoadmap)
        self.assertTrue(roadmap.content_hash.startswith("sha256:"))
        self.assertEqual(roadmap.content_hash, digest_payload(roadmap.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_private_production_roadmap_markdown(
            build_private_production_roadmap(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_private_production_roadmap_markdown(
            build_private_production_roadmap(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_private_production_roadmap(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_private_production_roadmap(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_missing_roadmap_id_fails_closed(self):
        material = valid_material()
        del material["roadmap_id"]

        with self.assertRaises(ValueError):
            build_private_production_roadmap(material)

    def test_missing_next_workbenches_fails_closed(self):
        material = valid_material()
        del material["next_workbenches"]

        with self.assertRaises(ValueError):
            build_private_production_roadmap(material)

    def test_missing_forbidden_directions_fails_closed(self):
        material = valid_material()
        del material["forbidden_directions"]

        with self.assertRaises(ValueError):
            build_private_production_roadmap(material)

    def test_forbidden_raw_and_sensitive_fields_fail_closed(self):
        for field_name in (
            "raw_prompt",
            "raw_response",
            "raw_exception",
            "raw_traceback",
            "env",
            "secret",
            "token",
            "api_key",
            "password",
            "private_key",
            "authorization",
        ):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_private_production_roadmap(material)

    def test_generated_roadmap_doc_exists(self):
        self.assertTrue(Path("docs/operator/private_production_roadmap.md").is_file())

    def test_doc_says_kernel_expansion_is_frozen(self):
        text = Path("docs/operator/private_production_roadmap.md").read_text(encoding="utf-8").lower()

        self.assertIn("kernel expansion is frozen", text)

    def test_doc_says_output_workbenches_are_next(self):
        text = Path("docs/operator/private_production_roadmap.md").read_text(encoding="utf-8").lower()

        self.assertIn("output workbenches are next", text)

    def test_doc_says_automatic_financial_execution_is_forbidden(self):
        text = Path("docs/operator/private_production_roadmap.md").read_text(encoding="utf-8").lower()

        self.assertIn("automatic financial execution is forbidden", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/private_production_roadmap.py").read_text(encoding="utf-8")

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
