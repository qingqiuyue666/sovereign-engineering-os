"""Tracer-bullet tests for AI worker result review packets."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.ai_worker_result_review_packet import (
    AIWorkerResultReviewPacket,
    build_ai_worker_result_review_packet,
    render_ai_worker_result_review_packet_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "packet_id": "ai-worker-result-review-v1-sample",
        "worker_name": "codex-worker",
        "claimed_branch": "codex-production-workbench-activation-v1",
        "claimed_commit": "3d25ab23f371a9539855d8271e5743f3e83afa99",
        "claimed_files_changed": ["kernel/runtime/ai_worker_result_review_packet.py"],
        "claimed_tests_run": ["python3 -m unittest tests.tracer_bullet.test_ai_worker_result_review_packet -v"],
        "claimed_results": ["worker reported pass"],
        "claimed_boundaries_preserved": ["no provider execution introduced"],
        "claimed_risks": [],
        "claimed_rollback_plan": ["revert result review packet files as a unit"],
        "missing_sections": [],
        "contradiction_findings": [],
        "review_decision": "structurally_complete",
        "required_human_checks": [],
        "policy_version": "ai-worker-result-review-packet-v1",
        "code_version": "0.1.0",
    }


class AIWorkerResultReviewPacketTests(unittest.TestCase):
    def test_valid_packet_builds_deterministic_object(self):
        packet = build_ai_worker_result_review_packet(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(packet, AIWorkerResultReviewPacket)
        self.assertTrue(packet.content_hash.startswith("sha256:"))
        self.assertEqual(packet.content_hash, digest_payload(packet.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_ai_worker_result_review_packet(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_ai_worker_result_review_packet(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_ai_worker_result_review_packet_markdown(
            build_ai_worker_result_review_packet(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_ai_worker_result_review_packet_markdown(
            build_ai_worker_result_review_packet(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_missing_required_section_blocks_structurally_complete(self):
        material = valid_material()
        material["missing_sections"] = ["FINAL_COMMIT"]

        with self.assertRaises(ValueError):
            build_ai_worker_result_review_packet(material)

    def test_contradiction_blocks_structurally_complete(self):
        material = valid_material()
        material["contradiction_findings"] = ["claims no files changed but lists changed files"]

        with self.assertRaises(ValueError):
            build_ai_worker_result_review_packet(material)

    def test_invalid_review_decision_fails_closed(self):
        material = valid_material()
        material["review_decision"] = "trusted"

        with self.assertRaises(ValueError):
            build_ai_worker_result_review_packet(material)

    def test_forbidden_raw_env_secret_fields_fail_closed(self):
        for field_name in ("raw_prompt", "raw_response", "env", "secret", "token", "api_key", "password"):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_ai_worker_result_review_packet(material)

    def test_generated_workflow_doc_exists(self):
        self.assertTrue(Path("docs/operator/ai_worker_result_review_packet_workflow.md").is_file())

    def test_workflow_doc_says_worker_claims_are_not_trusted(self):
        text = Path("docs/operator/ai_worker_result_review_packet_workflow.md").read_text(encoding="utf-8").lower()

        self.assertIn("worker claims are not trusted", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/ai_worker_result_review_packet.py").read_text(encoding="utf-8")

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
