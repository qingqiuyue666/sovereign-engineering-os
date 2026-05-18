import dataclasses
import unittest

from kernel.audit.hashchain import HashChain, HashChainEntry, digest_payload, verify_chain
from kernel.audit.trail import AuditTrail
from kernel.errors.hierarchy import AuditIntegrityError


class HashChainTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tampering(self):
        chain = HashChain()
        first = chain.append(digest_payload({"event": "a"}))
        second = chain.append(digest_payload({"event": "b"}))

        self.assertEqual(first.previous_hash, HashChain.GENESIS_HASH)
        self.assertEqual(second.previous_hash, first.current_hash)
        self.assertTrue(verify_chain(chain.entries))

        tampered = dataclasses.replace(second, content_hash=digest_payload({"event": "tampered"}))
        self.assertFalse(verify_chain((first, tampered)))

    def test_hashchain_rejects_non_digest_content_hash(self):
        with self.assertRaises(AuditIntegrityError):
            HashChain().append("not-a-digest")


class AuditTrailTests(unittest.TestCase):
    def test_observed_at_does_not_enter_content_or_chain_hashes(self):
        first = AuditTrail("first").record("task.accepted", {"task_id": "task_1"}, observed_at="2026-01-01T00:00:00Z")
        second = AuditTrail("second").record("task.accepted", {"task_id": "task_1"}, observed_at="2027-01-01T00:00:00Z")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.hash_chain_entry.current_hash, second.hash_chain_entry.current_hash)

    def test_trail_integrity_and_defensive_payload_copy(self):
        trail = AuditTrail("defensive")
        source = {"task_id": "task_1", "nested": {"state": "planned"}}
        entry = trail.record("task.planned", source, observed_at="2026-01-01T00:00:00Z")
        source["nested"]["state"] = "mutated"

        self.assertEqual(entry.payload["nested"]["state"], "planned")
        self.assertTrue(trail.verify_integrity())
        self.assertIn('"observed_at"', trail.export_json())

    def test_raw_prompt_and_secret_fields_fail_closed(self):
        trail = AuditTrail("rejects_raw")
        with self.assertRaises(AuditIntegrityError):
            trail.record("bad", {"raw_prompt": "do not persist"})
        with self.assertRaises(AuditIntegrityError):
            trail.record("bad", {"nested": {"secret_value": "do not persist"}})


if __name__ == "__main__":
    unittest.main()
