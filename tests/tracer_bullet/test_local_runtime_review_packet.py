"""Tracer-bullet tests for local runtime review packet."""

import unittest
from pathlib import Path

from kernel.audit.hashchain import digest_payload
from kernel.runtime.local_runtime_review_packet import (
    LocalRuntimeReviewPacket,
    build_review_packet,
    validate_review_packet_material,
)

VALID_DIGEST = "sha256:" + "a" * 64
VALID_DIGEST_2 = "sha256:" + "b" * 64
VALID_DIGEST_3 = "sha256:" + "c" * 64


class ReviewPacketBuildTests(unittest.TestCase):
    def test_builds_valid_review_packet(self):
        packet = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="all_guards_passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
        )
        self.assertTrue(validate_review_packet_material(packet))
        self.assertEqual(packet.runtime_accepted, True)
        self.assertEqual(packet.guard_result_summary, "all_guards_passed")

    def test_content_hash_is_deterministic_and_excludes_observed_at(self):
        first = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        second = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            observed_at="2027-06-15T12:00:00Z",
        )
        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.deterministic_material(), second.deterministic_material())
        self.assertNotIn("observed_at", first.deterministic_material())
        self.assertNotIn("content_hash", first.deterministic_material())

    def test_content_hash_changes_when_input_differs(self):
        p1 = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        p2 = build_review_packet(
            run_id="run-002",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        self.assertNotEqual(p1.content_hash, p2.content_hash)

    def test_includes_optional_refs(self):
        packet = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=False,
            guard_result_summary="guard_failed:non_dry_run",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            failure_bundle_ref="failure-bundle-001",
            provider_dry_run_receipt_ref="provider-receipt-001",
        )
        self.assertTrue(validate_review_packet_material(packet))
        self.assertEqual(packet.failure_bundle_ref, "failure-bundle-001")
        self.assertEqual(packet.provider_dry_run_receipt_ref, "provider-receipt-001")
        self.assertFalse(packet.runtime_accepted)

    def test_includes_state_transition_hashes(self):
        packet = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            state_transition_hashes=(VALID_DIGEST, VALID_DIGEST_2),
        )
        self.assertTrue(validate_review_packet_material(packet))
        self.assertEqual(len(packet.state_transition_hashes), 2)

    def test_rejects_invalid_digest(self):
        with self.assertRaises(ValueError):
            build_review_packet(
                run_id="run-001",
                task_id="task-001",
                runtime_receipt_hash="not-a-digest",
                runtime_accepted=True,
                guard_result_summary="passed",
                audit_chain_head=VALID_DIGEST_2,
                deterministic_input_digest=VALID_DIGEST_3,
            )

    def test_rejects_empty_run_id(self):
        with self.assertRaises(ValueError):
            build_review_packet(
                run_id="",
                task_id="task-001",
                runtime_receipt_hash=VALID_DIGEST,
                runtime_accepted=True,
                guard_result_summary="passed",
                audit_chain_head=VALID_DIGEST_2,
                deterministic_input_digest=VALID_DIGEST_3,
            )

    def test_as_dict_includes_content_hash_and_observed_at(self):
        packet = build_review_packet(
            run_id="run-001",
            task_id="task-001",
            runtime_receipt_hash=VALID_DIGEST,
            runtime_accepted=True,
            guard_result_summary="passed",
            audit_chain_head=VALID_DIGEST_2,
            deterministic_input_digest=VALID_DIGEST_3,
            observed_at="2026-01-01T00:00:00Z",
        )
        d = packet.as_dict()
        self.assertIn("content_hash", d)
        self.assertIn("observed_at", d)
        self.assertEqual(d["content_hash"], packet.content_hash)
        self.assertEqual(d["observed_at"], "2026-01-01T00:00:00Z")

    def test_validate_rejects_non_packet(self):
        self.assertFalse(validate_review_packet_material(None))
        self.assertFalse(validate_review_packet_material("not-a-packet"))


class ReviewPacketSourceSafetyTests(unittest.TestCase):
    def test_source_does_not_import_forbidden_surfaces(self):
        for rel_path in (
            "kernel/runtime/local_runtime_review_packet.py",
        ):
            source = Path(rel_path).read_text(encoding="utf-8")
            for marker in ("import subprocess", "import socket", "import requests",
                           "import httpx", "import sqlite3"):
                self.assertNotIn(marker, source, rel_path)
            for marker in ("os.environ", "os.getenv", "load_dotenv"):
                self.assertNotIn(marker, source, rel_path)


if __name__ == "__main__":
    unittest.main()
