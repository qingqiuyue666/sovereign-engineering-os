"""Real replay engine runtime tracer bullet tests.

Covers all required behaviors:
- replay anchor creation
- input snapshot binding
- version tuple validation
- environment fingerprint validation
- replay request validation
- replay mode validation
- deterministic replay receipt
- replay readiness receipt
- replay failure receipt
- mismatch report
- mismatch report hash
- evidence vault binding
- exact replay gate
- cloud re-query rejection
- nondeterministic replay rejection
- corrupted evidence fail-closed
- no evidence mutation
- no raw payload in receipts
- no wall-clock in hash / receipt generation
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from replay_engine import (  # type: ignore[import-not-found]
    ReplayEngine,
    ReplayAnchor,
    ReplaySnapshot,
    ReplayVersionTuple,
    ReplayMismatch,
    MismatchReport,
    ReplayReceipt,
    ReplayReadinessReceipt,
    ReplayFailureReceipt,
    ReplayEvidenceBinding,
    ReplayFailure,
    ReplayFailures,
    ReplayModes,
    ReplaySecurity,
    ReplayCanonicalHash,
)

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64


class TestReplayAnchor(unittest.TestCase):
    """Replay anchor creation and validation."""

    def test_create_valid_anchor(self):
        anchor = ReplayAnchor.create(
            input_snapshot_hash=VALID_SHA256,
            policy_version="v1.0.0",
            code_version="abc123def456",
            environment_fingerprint="env-hash-001",
        )
        self.assertTrue(anchor.anchor_id)
        self.assertEqual(anchor.input_snapshot_hash, VALID_SHA256)
        self.assertTrue(anchor.deterministic_mode)
        self.assertTrue(anchor.no_cloud_requery)
        self.assertTrue(anchor.canonical_hash)

    def test_create_anchor_rejects_empty_snapshot(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create("", "v1", "code", "env")

    def test_create_anchor_rejects_short_snapshot_hash(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create("too-short", "v1", "code", "env")

    def test_create_anchor_rejects_empty_policy(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "", "code", "env")

    def test_create_anchor_rejects_empty_code_version(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "v1", "", "env")

    def test_create_anchor_rejects_empty_environment(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "v1", "code", "")

    def test_create_anchor_rejects_nondeterministic(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "v1", "code", "env", deterministic_mode=False)

    def test_create_anchor_rejects_cloud_requery(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "v1", "code", "env", no_cloud_requery=False)

    def test_anchor_is_immutable(self):
        anchor = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        with self.assertRaises(Exception):
            anchor.anchor_id = "mutated"  # type: ignore[misc]

    def test_anchor_deterministic(self):
        a1 = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        a2 = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        self.assertEqual(a1.anchor_id, a2.anchor_id)
        self.assertEqual(a1.canonical_hash, a2.canonical_hash)

    def test_anchor_different_inputs_different_hash(self):
        a1 = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        a2 = ReplayAnchor.create(VALID_SHA256_B, "v1", "code", "env")
        self.assertNotEqual(a1.anchor_id, a2.anchor_id)

    def test_anchor_to_dict_no_raw_payload(self):
        anchor = ReplayAnchor.create(VALID_SHA256, "v1", "code", "env")
        d = anchor.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("payload", d)
        self.assertNotIn("raw_data", d)


class TestReplaySnapshot(unittest.TestCase):
    """Input snapshot binding tests."""

    def test_create_valid_snapshot(self):
        snap = ReplaySnapshot.create(VALID_SHA256, 5, "evidence_vault")
        self.assertTrue(snap.snapshot_id)
        self.assertEqual(snap.artifact_count, 5)

    def test_create_snapshot_rejects_invalid_hash(self):
        with self.assertRaises(ValueError):
            ReplaySnapshot.create("short", 5, "evidence_vault")

    def test_create_snapshot_rejects_negative_count(self):
        with self.assertRaises(ValueError):
            ReplaySnapshot.create(VALID_SHA256, -1, "evidence_vault")

    def test_create_snapshot_rejects_empty_source(self):
        with self.assertRaises(ValueError):
            ReplaySnapshot.create(VALID_SHA256, 5, "")

    def test_snapshot_deterministic(self):
        s1 = ReplaySnapshot.create(VALID_SHA256, 5, "evidence_vault")
        s2 = ReplaySnapshot.create(VALID_SHA256, 5, "evidence_vault")
        self.assertEqual(s1.snapshot_id, s2.snapshot_id)


class TestReplayVersionTuple(unittest.TestCase):
    """Version tuple validation tests."""

    def test_valid_version_tuple(self):
        vt = ReplayVersionTuple.create("v1", "abc123", "env-hash")
        self.assertTrue(vt.is_valid)
        self.assertTrue(vt.tuple_id)
        self.assertTrue(vt.canonical_hash)

    def test_invalid_version_tuple_empty_policy(self):
        vt = ReplayVersionTuple.create("", "abc", "env")
        self.assertFalse(vt.is_valid)
        self.assertEqual(vt.canonical_hash, "")

    def test_invalid_version_tuple_empty_code(self):
        vt = ReplayVersionTuple.create("v1", "", "env")
        self.assertFalse(vt.is_valid)

    def test_invalid_version_tuple_empty_env(self):
        vt = ReplayVersionTuple.create("v1", "abc", "")
        self.assertFalse(vt.is_valid)

    def test_version_tuple_deterministic(self):
        v1 = ReplayVersionTuple.create("v1", "abc", "env")
        v2 = ReplayVersionTuple.create("v1", "abc", "env")
        self.assertEqual(v1.tuple_id, v2.tuple_id)


class TestReplayMismatch(unittest.TestCase):
    """Mismatch report tests."""

    def test_create_mismatch(self):
        m = ReplayMismatch.create("anchor-1", "output_hash", VALID_SHA256, VALID_SHA256_B)
        self.assertTrue(m.mismatch_id)
        self.assertEqual(m.field, "output_hash")
        self.assertEqual(m.severity, "error")
        self.assertTrue(m.report_hash)

    def test_mismatch_rejects_same_hashes(self):
        with self.assertRaises(ValueError):
            ReplayMismatch.create("anchor-1", "field", VALID_SHA256, VALID_SHA256)

    def test_mismatch_rejects_empty_field(self):
        with self.assertRaises(ValueError):
            ReplayMismatch.create("anchor-1", "", VALID_SHA256, VALID_SHA256_B)

    def test_mismatch_rejects_invalid_severity(self):
        with self.assertRaises(ValueError):
            ReplayMismatch.create("anchor-1", "field", VALID_SHA256, VALID_SHA256_B, severity="critical")

    def test_mismatch_report_aggregate_hash(self):
        report = MismatchReport("anchor-1")
        m1 = ReplayMismatch.create("anchor-1", "field_a", VALID_SHA256, VALID_SHA256_B)
        m2 = ReplayMismatch.create("anchor-1", "field_b", "c" * 64, "d" * 64)
        report.add(m1)
        report.add(m2)
        self.assertTrue(report.has_mismatches())
        self.assertTrue(report.aggregate_hash())

    def test_mismatch_report_empty(self):
        report = MismatchReport("anchor-1")
        self.assertFalse(report.has_mismatches())
        self.assertTrue(report.aggregate_hash())

    def test_mismatch_no_raw_payload(self):
        m = ReplayMismatch.create("anchor-1", "field", VALID_SHA256, VALID_SHA256_B)
        d = m.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)
        self.assertNotIn("expected_value", d)
        self.assertNotIn("actual_value", d)


class TestReplayReceipts(unittest.TestCase):
    """Receipt generation tests."""

    def test_produce_replay_receipt(self):
        from replay_engine.replay_receipt import produce_replay_receipt
        receipt = produce_replay_receipt("anchor-1", "snap-1", "vt-1", "ready", "strict", True)
        self.assertEqual(receipt.status, "ready")
        self.assertEqual(receipt.mode, "strict")
        self.assertTrue(receipt.no_replay_execution)
        self.assertTrue(receipt.canonical_hash)

    def test_replay_receipt_deterministic(self):
        from replay_engine.replay_receipt import produce_replay_receipt
        r1 = produce_replay_receipt("anchor-1", "snap-1", "vt-1", "ready", "strict", True)
        r2 = produce_replay_receipt("anchor-1", "snap-1", "vt-1", "ready", "strict", True)
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_produce_readiness_receipt(self):
        from replay_engine.replay_receipt import produce_readiness_receipt
        gates = {"anchor_valid": True, "snapshot_valid": True, "mode_valid": True}
        receipt = produce_readiness_receipt("anchor-1", "snap-1", "vt-1", gates)
        self.assertTrue(receipt.ready)
        self.assertTrue(receipt.no_replay_execution)

    def test_readiness_receipt_not_ready(self):
        from replay_engine.replay_receipt import produce_readiness_receipt
        gates = {"anchor_valid": True, "snapshot_valid": False, "mode_valid": True}
        receipt = produce_readiness_receipt("anchor-1", "snap-1", "vt-1", gates)
        self.assertFalse(receipt.ready)

    def test_produce_failure_receipt(self):
        from replay_engine.replay_receipt import produce_failure_receipt
        receipt = produce_failure_receipt(
            "anchor-1", "evidence corrupted", "REPLAY_EVIDENCE_CORRUPTED", evidence_corrupted=True,
        )
        self.assertEqual(receipt.failure_code, "REPLAY_EVIDENCE_CORRUPTED")
        self.assertTrue(receipt.evidence_corrupted)
        self.assertTrue(receipt.no_replay_execution)

    def test_failure_receipt_requires_reason(self):
        from replay_engine.replay_receipt import produce_failure_receipt
        with self.assertRaises(ValueError):
            produce_failure_receipt("anchor-1", "", "REPLAY_GATE_FAILED")

    def test_failure_receipt_requires_code(self):
        from replay_engine.replay_receipt import produce_failure_receipt
        with self.assertRaises(ValueError):
            produce_failure_receipt("anchor-1", "reason", "")

    def test_no_raw_payload_in_any_receipt(self):
        from replay_engine.replay_receipt import (
            produce_replay_receipt, produce_readiness_receipt, produce_failure_receipt,
        )
        r1 = produce_replay_receipt("a", "s", "v", "ready", "strict", True).to_dict()
        r2 = produce_readiness_receipt("a", "s", "v", {"g": True}).to_dict()
        r3 = produce_failure_receipt("a", "reason", "REPLAY_GATE_FAILED").to_dict()
        for r in (r1, r2, r3):
            self.assertNotIn("raw_payload", r)
            self.assertNotIn("payload", r)
            self.assertNotIn("raw_data", r)

    def test_no_wall_clock_in_receipt(self):
        from replay_engine.replay_receipt import produce_replay_receipt
        r1 = produce_replay_receipt("a", "s", "v", "ready", "strict", True)
        r2 = produce_replay_receipt("a", "s", "v", "ready", "strict", True)
        self.assertEqual(r1.created_at, r2.created_at)
        self.assertNotIn("timestamp", r1.to_dict())
        self.assertNotIn("wall_clock", r1.to_dict())


class TestReplayEvidenceBinding(unittest.TestCase):
    """Evidence binding tests."""

    def test_create_valid_binding(self):
        binding = ReplayEvidenceBinding.create("anchor-1", ["ev-1", "ev-2"])
        self.assertTrue(binding.is_valid)
        self.assertTrue(binding.binding_id)
        self.assertTrue(binding.evidence_hash)
        self.assertTrue(binding.canonical_hash)
        self.assertEqual(len(binding.evidence_ids), 2)

    def test_binding_rejects_empty_anchor(self):
        with self.assertRaises(ValueError):
            ReplayEvidenceBinding.create("", ["ev-1"])

    def test_binding_rejects_empty_evidence_ids(self):
        with self.assertRaises(ValueError):
            ReplayEvidenceBinding.create("anchor-1", [])

    def test_binding_rejects_invalid_evidence_id(self):
        with self.assertRaises(ValueError):
            ReplayEvidenceBinding.create("anchor-1", ["ev-1", ""])

    def test_corrupted_binding(self):
        binding = ReplayEvidenceBinding.corrupted("anchor-1", "hash mismatch")
        self.assertFalse(binding.is_valid)
        self.assertEqual(binding.binding_id, "")
        self.assertEqual(len(binding.evidence_ids), 0)
        self.assertTrue(binding.canonical_hash)  # still has hash for tracking

    def test_binding_deterministic(self):
        b1 = ReplayEvidenceBinding.create("anchor-1", ["ev-2", "ev-1"])
        b2 = ReplayEvidenceBinding.create("anchor-1", ["ev-1", "ev-2"])
        self.assertEqual(b1.binding_id, b2.binding_id)
        self.assertEqual(b1.evidence_hash, b2.evidence_hash)


class TestReplayModes(unittest.TestCase):
    """Mode validation tests."""

    def test_valid_mode_strict(self):
        result = ReplayModes.validate("strict")
        self.assertTrue(result["valid"])

    def test_valid_mode_dry_run(self):
        result = ReplayModes.validate("dry_run")
        self.assertTrue(result["valid"])

    def test_reject_empty_mode(self):
        result = ReplayModes.validate("")
        self.assertFalse(result["valid"])

    def test_reject_cloud_requery(self):
        result = ReplayModes.validate("cloud_requery")
        self.assertFalse(result["valid"])
        self.assertIn("forbidden", result["reason"])

    def test_reject_nondeterministic(self):
        result = ReplayModes.validate("nondeterministic")
        self.assertFalse(result["valid"])

    def test_reject_live(self):
        result = ReplayModes.validate("live")
        self.assertFalse(result["valid"])

    def test_reject_production(self):
        result = ReplayModes.validate("production")
        self.assertFalse(result["valid"])

    def test_enforce_raises_on_invalid(self):
        with self.assertRaises(ValueError):
            ReplayModes.enforce("cloud_requery")

    def test_enforce_passes_on_valid(self):
        ReplayModes.enforce("strict")  # should not raise


class TestReplayFailures(unittest.TestCase):
    """Failure recording and fail-closed tests."""

    def test_create_failure(self):
        f = ReplayFailure.create("anchor-1", "REPLAY_GATE_FAILED", "snapshot missing")
        self.assertTrue(f.failure_id)
        self.assertEqual(f.failure_code, "REPLAY_GATE_FAILED")
        self.assertFalse(f.fail_closed)

    def test_evidence_corrupted_fail_closed(self):
        f = ReplayFailure.create(
            "anchor-1", "REPLAY_EVIDENCE_CORRUPTED", "hash mismatch",
            evidence_corrupted=True,
        )
        self.assertTrue(f.fail_closed)

    def test_input_corrupted_fail_closed(self):
        f = ReplayFailure.create("anchor-1", "REPLAY_INPUT_CORRUPTED", "bad input")
        self.assertTrue(f.fail_closed)

    def test_reject_invalid_failure_code(self):
        with self.assertRaises(ValueError):
            ReplayFailure.create("anchor-1", "INVALID_CODE", "reason")

    def test_empty_anchor_allowed_for_anchor_failures(self):
        # Empty anchor_id is allowed for failures about anchor validation itself
        f = ReplayFailure.create("", "REPLAY_ANCHOR_INVALID", "bad anchor format")
        self.assertEqual(f.anchor_id, "")
        self.assertEqual(f.failure_code, "REPLAY_ANCHOR_INVALID")

    def test_failures_registry(self):
        rf = ReplayFailures()
        self.assertFalse(rf.has_failures())
        rf.record(ReplayFailure.create("a", "REPLAY_GATE_FAILED", "r"))
        self.assertTrue(rf.has_failures())
        self.assertFalse(rf.fail_closed())

    def test_failures_registry_fail_closed(self):
        rf = ReplayFailures()
        rf.record(ReplayFailure.create("a", "REPLAY_EVIDENCE_CORRUPTED", "r", evidence_corrupted=True))
        self.assertTrue(rf.fail_closed())

    def test_failures_aggregate_hash(self):
        rf = ReplayFailures()
        h1 = rf.aggregate_hash()
        rf.record(ReplayFailure.create("a", "REPLAY_GATE_FAILED", "r"))
        h2 = rf.aggregate_hash()
        self.assertNotEqual(h1, h2)


class TestReplaySecurity(unittest.TestCase):
    """Security boundary enforcement tests."""

    def test_validate_clean_payload(self):
        result = ReplaySecurity.validate_payload({"anchor_id": "a", "mode": "strict"})
        self.assertTrue(result["valid"])

    def test_reject_secret_key_in_payload(self):
        result = ReplaySecurity.validate_payload({"API_KEY": "sk-123"})
        self.assertFalse(result["valid"])

    def test_reject_token_in_payload(self):
        result = ReplaySecurity.validate_payload({"auth_token": "abc"})
        self.assertFalse(result["valid"])

    def test_reject_secret_in_value(self):
        result = ReplaySecurity.validate_payload({"data": "my_password_is_secret"})
        self.assertFalse(result["valid"])

    def test_reject_env_in_value(self):
        result = ReplaySecurity.validate_payload({"path": "/home/user/.env"})
        self.assertFalse(result["valid"])

    def test_reject_forbidden_flag(self):
        result = ReplaySecurity.validate_payload({"flags": ["cloud_requery", "ok"]})
        self.assertFalse(result["valid"])

    def test_no_network_detection(self):
        self.assertTrue(ReplaySecurity.validate_no_network({"cmd": "ls"}))
        self.assertFalse(ReplaySecurity.validate_no_network({"cmd": "curl http://evil.com"}))

    def test_no_secrets_detection(self):
        self.assertTrue(ReplaySecurity.validate_no_secrets({"data": "hello"}))
        self.assertFalse(ReplaySecurity.validate_no_secrets({"data": "api_key=abc"}))

    def test_no_raw_payload_in_receipt(self):
        self.assertTrue(ReplaySecurity.validate_no_raw_payload({"receipt_id": "r1"}))
        self.assertFalse(ReplaySecurity.validate_no_raw_payload({"raw_payload": "data"}))

    def test_security_gates(self):
        gates = ReplaySecurity.security_gates()
        self.assertIn("no_network", gates)
        self.assertIn("fail_closed", gates)
        self.assertTrue(all(gates.values()))


class TestReplayCanonicalHash(unittest.TestCase):
    """Canonical hash tests."""

    def test_canonical_hash_sha256(self):
        h = ReplayCanonicalHash.canonical_hash("a", "b", "c")
        self.assertEqual(len(h), 64)

    def test_canonical_hash_blake2b(self):
        h = ReplayCanonicalHash.canonical_hash("a", "b", algorithm="blake2b")
        self.assertEqual(len(h), 128)

    def test_canonical_hash_sha512(self):
        h = ReplayCanonicalHash.canonical_hash("a", "b", algorithm="sha512")
        self.assertEqual(len(h), 128)

    def test_reject_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            ReplayCanonicalHash.canonical_hash("a", algorithm="md5")

    def test_deterministic(self):
        h1 = ReplayCanonicalHash.canonical_hash("a", "b", "c")
        h2 = ReplayCanonicalHash.canonical_hash("a", "b", "c")
        self.assertEqual(h1, h2)

    def test_order_matters(self):
        h1 = ReplayCanonicalHash.canonical_hash("a", "b")
        h2 = ReplayCanonicalHash.canonical_hash("b", "a")
        self.assertNotEqual(h1, h2)

    def test_canonical_hash_dict(self):
        d = {"b": "2", "a": "1"}
        h1 = ReplayCanonicalHash.canonical_hash_dict(d)
        h2 = ReplayCanonicalHash.canonical_hash_dict({"a": "1", "b": "2"})
        self.assertEqual(h1, h2)

    def test_anchor_canonical_hash(self):
        h = ReplayCanonicalHash.anchor_canonical_hash(VALID_SHA256, "v1", "code", "env")
        self.assertEqual(len(h), 64)


class TestReplayEngine(unittest.TestCase):
    """Full ReplayEngine integration tests."""

    def setUp(self):
        self.engine = ReplayEngine()

    def test_full_happy_path(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("v1", "code", "env")
        binding = self.engine.bind_evidence(anchor.anchor_id, ["ev-1", "ev-2"])

        readiness = self.engine.check_readiness(anchor, snapshot, vt, "strict", binding)
        self.assertTrue(readiness.ready)

        receipt = self.engine.produce_receipt(anchor, snapshot, vt, "strict", binding)
        self.assertEqual(receipt.status, "ready")
        self.assertFalse(self.engine.has_failures())

    def test_failure_on_invalid_version(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("", "", "")  # invalid

        self.assertFalse(vt.is_valid)
        with self.assertRaises(ValueError):
            self.engine.produce_receipt(anchor, snapshot, vt, "strict")
        self.assertTrue(self.engine.has_failures())

    def test_failure_receipt_production(self):
        receipt = self.engine.produce_failure_receipt(
            "anchor-1", "evidence corrupted", "REPLAY_EVIDENCE_CORRUPTED",
            evidence_corrupted=True,
        )
        self.assertEqual(receipt.failure_code, "REPLAY_EVIDENCE_CORRUPTED")
        self.assertTrue(self.engine.has_failures())
        self.assertTrue(self.engine.fail_closed())

    def test_mismatch_recording(self):
        mismatch = self.engine.add_mismatch("anchor-1", "output", VALID_SHA256, VALID_SHA256_B)
        self.assertTrue(mismatch.mismatch_id)
        summary = self.engine.mismatch_summary()
        self.assertEqual(len(summary), 1)

    def test_engine_hash(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("v1", "code", "env")
        self.engine.produce_receipt(anchor, snapshot, vt, "strict")
        h = self.engine.engine_hash()
        self.assertTrue(h)

    def test_engine_hash_changes_with_state(self):
        h1 = self.engine.engine_hash()
        self.engine.record_failure("anchor-1", "REPLAY_GATE_FAILED", "test failure")
        h2 = self.engine.engine_hash()
        self.assertNotEqual(h1, h2)

    def test_reset(self):
        self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        self.engine.reset()
        self.assertFalse(self.engine.has_failures())
        self.assertEqual(self.engine.receipt_count(), 0)

    def test_cloud_requery_rejected_by_anchor(self):
        # Cloud re-query is rejected via no_cloud_requery=False
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "v1", "code", "env", no_cloud_requery=False)

    def test_nondeterministic_rejected(self):
        with self.assertRaises(ValueError):
            ReplayAnchor.create(VALID_SHA256, "v1", "code", "env", deterministic_mode=False)

    def test_empty_evidence_binding_rejected(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        with self.assertRaises(ValueError):
            self.engine.bind_evidence(anchor.anchor_id, [])

    def test_invalid_mode_rejected(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("v1", "code", "env")
        with self.assertRaises(ValueError):
            self.engine.produce_receipt(anchor, snapshot, vt, "cloud_requery")

    def test_no_invalid_anchor_causes_failure_record(self):
        try:
            self.engine.create_anchor("", "", "", "")
        except ValueError:
            pass
        self.assertTrue(self.engine.has_failures())

    def test_failure_summary_structure(self):
        self.engine.record_failure("a", "REPLAY_GATE_FAILED", "test")
        summary = self.engine.failure_summary()
        self.assertIn("failure_count", summary)
        self.assertIn("fail_closed", summary)
        self.assertIn("failures", summary)
        self.assertIn("aggregate_hash", summary)

    def test_readiness_all_gates(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("v1", "code", "env")
        readiness = self.engine.check_readiness(anchor, snapshot, vt, "strict")
        self.assertIn("anchor_valid", readiness.gates)
        self.assertIn("snapshot_valid", readiness.gates)
        self.assertIn("version_tuple_valid", readiness.gates)
        self.assertIn("mode_valid", readiness.gates)

    def test_engine_receipt_count_tracks(self):
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("v1", "code", "env")
        self.assertEqual(self.engine.receipt_count(), 0)
        self.engine.produce_receipt(anchor, snapshot, vt, "strict")
        self.assertEqual(self.engine.receipt_count(), 1)

    def test_no_wall_clock_anywhere(self):
        """No wall-clock time should appear in any hash or receipt."""
        anchor = self.engine.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot = self.engine.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt = self.engine.validate_version_tuple("v1", "code", "env")
        receipt = self.engine.produce_receipt(anchor, snapshot, vt, "strict")

        # Repeat and check determinism
        engine2 = ReplayEngine()
        anchor2 = engine2.create_anchor(VALID_SHA256, "v1", "code", "env")
        snapshot2 = engine2.bind_snapshot(VALID_SHA256, 10, "evidence_vault")
        vt2 = engine2.validate_version_tuple("v1", "code", "env")
        receipt2 = engine2.produce_receipt(anchor2, snapshot2, vt2, "strict")

        self.assertEqual(receipt.receipt_id, receipt2.receipt_id)
        self.assertEqual(receipt.canonical_hash, receipt2.canonical_hash)


class TestNoNetworkOrSubprocess(unittest.TestCase):
    """Verify no network/subprocess imports in replay engine modules."""

    def test_no_forbidden_imports(self):
        replay_dir = ROOT / "tools" / "replay_engine"
        for py_file in replay_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name} imports subprocess")
            self.assertNotIn("import socket", src, f"{py_file.name} imports socket")
            self.assertNotIn("import requests", src, f"{py_file.name} imports requests")
            self.assertNotIn("from urllib", src, f"{py_file.name} imports urllib")
            self.assertNotIn("import http.client", src, f"{py_file.name} imports http.client")
            self.assertNotIn("import anthropic", src, f"{py_file.name} imports anthropic")
            self.assertNotIn("import openai", src, f"{py_file.name} imports openai")
            self.assertNotIn("from anthropic", src, f"{py_file.name} imports anthropic")
            self.assertNotIn("from openai", src, f"{py_file.name} imports openai")

    def test_no_env_reads(self):
        replay_dir = ROOT / "tools" / "replay_engine"
        for py_file in replay_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("dotenv", src, f"{py_file.name} references dotenv")
            self.assertNotIn("os.environ", src, f"{py_file.name} reads os.environ")
            self.assertNotIn("os.getenv", src, f"{py_file.name} reads os.getenv")


if __name__ == "__main__":
    unittest.main()
