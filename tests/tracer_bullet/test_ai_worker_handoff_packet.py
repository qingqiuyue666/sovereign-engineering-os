"""Tracer-bullet tests for deterministic AI worker handoff packets."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.ai_worker_handoff_packet import (
    AIWorkerHandoffPacket,
    build_ai_worker_handoff_packet,
    render_ai_worker_handoff_packet_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "packet_id": "ai-worker-handoff-packet-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "2d25ab23f371a9539855d8271e5743f3e83afa99",
        "required_reading": [
            "docs/operator/operator_command_center.md",
            "docs/operator/current_state.md",
        ],
        "current_state_summary": "Durable control plane complete; private production assets next.",
        "allowed_work": [
            "deterministic private reports",
            "caller-provided material validators",
        ],
        "forbidden_work": [
            "provider execution",
            "production autonomy",
            "financial execution",
            "trading automation",
            "network/subprocess/env/SQLite",
            "root README edits",
            "Makefile/root integrity/health wiring edits",
        ],
        "required_verification": [
            "python3 -m unittest tests.tracer_bullet.test_ai_worker_handoff_packet -v",
            "make ci",
        ],
        "merge_rules": [
            "start from latest main",
            "merge only after tests pass",
        ],
        "rollback_rules": [
            "revert completed packet files as a unit",
        ],
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
        ],
        "policy_version": "ai-worker-handoff-packet-v1",
        "code_version": "0.1.0",
    }


class AIWorkerHandoffPacketTests(unittest.TestCase):
    def test_valid_packet_builds_deterministic_object(self):
        packet = build_ai_worker_handoff_packet(valid_material(), observed_at="2026-05-19T00:00:00+08:00")

        self.assertIsInstance(packet, AIWorkerHandoffPacket)
        self.assertTrue(packet.content_hash.startswith("sha256:"))
        self.assertEqual(packet.content_hash, digest_payload(packet.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_ai_worker_handoff_packet_markdown(
            build_ai_worker_handoff_packet(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_ai_worker_handoff_packet_markdown(
            build_ai_worker_handoff_packet(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_ai_worker_handoff_packet(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_ai_worker_handoff_packet(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_missing_packet_id_fails_closed(self):
        material = valid_material()
        del material["packet_id"]

        with self.assertRaises(ValueError):
            build_ai_worker_handoff_packet(material)

    def test_missing_required_reading_fails_closed(self):
        material = valid_material()
        del material["required_reading"]

        with self.assertRaises(ValueError):
            build_ai_worker_handoff_packet(material)

    def test_missing_forbidden_work_fails_closed(self):
        material = valid_material()
        del material["forbidden_work"]

        with self.assertRaises(ValueError):
            build_ai_worker_handoff_packet(material)

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
                    build_ai_worker_handoff_packet(material)

    def test_generated_handoff_doc_exists(self):
        self.assertTrue(Path("docs/operator/ai_worker_handoff_packet.md").is_file())

    def test_doc_says_ai_worker_must_read_operator_command_center_first(self):
        text = Path("docs/operator/ai_worker_handoff_packet.md").read_text(encoding="utf-8").lower()

        self.assertIn("ai worker must read operator command center first", text)

    def test_doc_says_no_makefile_root_integrity_health_wiring_edits(self):
        text = Path("docs/operator/ai_worker_handoff_packet.md").read_text(encoding="utf-8").lower()

        self.assertIn("no makefile/root integrity/health wiring edits", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/ai_worker_handoff_packet.py").read_text(encoding="utf-8")

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
