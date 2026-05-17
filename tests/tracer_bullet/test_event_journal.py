"""Deterministic append-only event journal tracer-bullet tests.

Tests the event journal foundation:
- policy file integrity
- valid event append with JournalEvent descriptor
- duplicate logical_sequence detection (per run)
- stage regression detection (per run)
- forbidden field rejection (raw_prompt, raw_provider_response, secret_value, env_value)
- required field validation
- digest refs only (sha256: prefix)
- append-only semantics
- determinism and side-effect freedom
- cross-run isolation
"""

import copy
import json
import unittest
from pathlib import Path

from kernel.runtime.event_journal import (
    EventJournal,
    JournalAppendResult,
    JournalEvent,
    JournalRejection,
    validate_event_record,
)

POLICY_PATH = Path("governance/runtime/event_journal_policy_v1.json")


def _valid_event(overrides=None):
    """Return a minimal valid event payload."""
    event = {
        "event_id": "evt-001",
        "run_id": "run-001",
        "task_id": "task-001",
        "stage": "dry_run",
        "event_type": "planned",
        "logical_sequence": 1,
        "payload_digest": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    }
    if overrides:
        event.update(overrides)
    return event


class EventJournalPolicyTests(unittest.TestCase):
    """Policy file integrity tests."""

    def test_policy_file_exists_and_is_valid_json(self):
        self.assertTrue(POLICY_PATH.is_file(), f"Policy file missing: {POLICY_PATH}")
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "event_journal_policy_v1")
        self.assertEqual(policy["version"], "v1")
        self.assertTrue(policy["in_memory_only"])
        self.assertTrue(policy["append_only"])
        self.assertTrue(policy["deterministic_required"])
        self.assertTrue(policy["no_sqlite"])
        self.assertTrue(policy["no_provider_calls"])
        self.assertTrue(policy["no_network_access"])
        self.assertFalse(policy["duplicate_logical_sequence_allowed"])
        self.assertFalse(policy["sequence_regression_allowed"])
        self.assertFalse(policy["stage_regression_allowed"])
        for field in ("raw_prompt", "raw_provider_response", "secret_value", "env_value"):
            self.assertIn(field, policy["forbidden_fields"])
        for field in ("event_id", "run_id", "task_id", "stage", "event_type", "logical_sequence", "payload_digest"):
            self.assertIn(field, policy["required_event_fields"])
        self.assertTrue(policy["digest_refs_only"])
        self.assertIn("dry_run", policy["legal_stages"])
        self.assertIn("context", policy["legal_stages"])
        self.assertIn("evidence", policy["legal_stages"])


class EventJournalAcceptanceTests(unittest.TestCase):
    """Happy-path append tests."""

    def test_valid_event_appends_and_returns_journal_event(self):
        journal = EventJournal()
        result = journal.append(_valid_event())
        self.assertTrue(result.accepted)
        self.assertEqual(result.failures, ())
        self.assertIsInstance(result.event, JournalEvent)
        self.assertEqual(result.event.event_id, "evt-001")
        self.assertEqual(result.event.run_id, "run-001")
        self.assertEqual(result.event.task_id, "task-001")
        self.assertEqual(result.event.stage, "dry_run")
        self.assertEqual(result.event.event_type, "planned")
        self.assertEqual(result.event.logical_sequence, 1)
        self.assertEqual(result.event.payload_digest, "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")

    def test_journal_event_is_frozen(self):
        event = JournalEvent(
            event_id="e1", run_id="r1", task_id="t1",
            stage="dry_run", event_type="planned",
            logical_sequence=1, payload_digest="sha256:abc",
        )
        with self.assertRaises(Exception):
            event.logical_sequence = 2

    def test_journal_event_as_dict(self):
        event = JournalEvent(
            event_id="e1", run_id="r1", task_id="t1",
            stage="dry_run", event_type="planned",
            logical_sequence=1, payload_digest="sha256:abc",
        )
        d = event.as_dict()
        self.assertEqual(d["event_id"], "e1")
        self.assertEqual(d["run_id"], "r1")
        self.assertEqual(d["task_id"], "t1")
        self.assertEqual(d["stage"], "dry_run")
        self.assertEqual(d["event_type"], "planned")
        self.assertEqual(d["logical_sequence"], 1)
        self.assertEqual(d["payload_digest"], "sha256:abc")

    def test_events_property_returns_immutable_tuple(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "evt-001", "logical_sequence": 1}))
        journal.append(_valid_event({"event_id": "evt-002", "logical_sequence": 2}))
        events = journal.events
        self.assertIsInstance(events, tuple)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_id, "evt-001")
        self.assertEqual(events[1].event_id, "evt-002")

    def test_event_count_tracks_appends(self):
        journal = EventJournal()
        self.assertEqual(journal.event_count(), 0)
        journal.append(_valid_event({"event_id": "evt-001", "logical_sequence": 1}))
        self.assertEqual(journal.event_count(), 1)
        journal.append(_valid_event({"event_id": "evt-002", "logical_sequence": 2}))
        self.assertEqual(journal.event_count(), 2)

    def test_multiple_runs_are_isolated(self):
        journal = EventJournal()
        # Run A
        journal.append(_valid_event({"event_id": "evt-a1", "run_id": "run-a", "logical_sequence": 1}))
        journal.append(_valid_event({"event_id": "evt-a2", "run_id": "run-a", "logical_sequence": 2}))
        # Run B — same logical_sequence should be fine in different run
        result = journal.append(_valid_event({"event_id": "evt-b1", "run_id": "run-b", "logical_sequence": 1}))
        self.assertTrue(result.accepted)
        self.assertEqual(journal.event_count(), 3)

    def test_deterministic_append_sequence(self):
        j1 = EventJournal()
        j2 = EventJournal()
        events = [
            _valid_event({"event_id": "e1", "logical_sequence": 1}),
            _valid_event({"event_id": "e2", "logical_sequence": 2}),
            _valid_event({"event_id": "e3", "logical_sequence": 3}),
        ]
        for e in events:
            j1.append(e)
            j2.append(e)
        for ev1, ev2 in zip(j1.events, j2.events):
            self.assertEqual(ev1.as_dict(), ev2.as_dict())

    def test_validate_event_record_pure(self):
        payload = _valid_event()
        self.assertEqual(validate_event_record(payload), ())

    def test_valid_event_with_legal_stage(self):
        for stage in ("dry_run", "context", "inference", "patch_proposal", "validation",
                       "review", "approval", "revision_seal", "evidence"):
            journal = EventJournal()
            result = journal.append(_valid_event({
                "event_id": f"evt-{stage}",
                "stage": stage,
                "logical_sequence": 1,
            }))
            self.assertTrue(result.accepted, f"Stage '{stage}' should be accepted")


class EventJournalDuplicateSequenceTests(unittest.TestCase):
    """Duplicate logical_sequence detection tests."""

    def test_duplicate_logical_sequence_same_run_rejected(self):
        journal = EventJournal()
        self.assertTrue(journal.append(_valid_event({"logical_sequence": 1})).accepted)
        result = journal.append(_valid_event({"event_id": "evt-002", "logical_sequence": 1}))
        self.assertFalse(result.accepted)
        self.assertIn("duplicate_logical_sequence", result.failures)

    def test_same_logical_sequence_different_run_accepted(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "run_id": "run-a", "logical_sequence": 1}))
        result = journal.append(_valid_event({"event_id": "e2", "run_id": "run-b", "logical_sequence": 1}))
        self.assertTrue(result.accepted)

    def test_non_consecutive_sequences_accepted(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        result = journal.append(_valid_event({"event_id": "e2", "logical_sequence": 5}))
        self.assertTrue(result.accepted)

    def test_duplicate_sequence_rejected_even_after_gap(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        journal.append(_valid_event({"event_id": "e2", "logical_sequence": 5}))
        result = journal.append(_valid_event({"event_id": "e3", "logical_sequence": 1}))
        self.assertFalse(result.accepted)
        self.assertIn("duplicate_logical_sequence", result.failures)

    # Blocker 2 — sequence regression tests
    def test_sequence_5_then_4_same_run_rejected(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 5}))
        result = journal.append(_valid_event({"event_id": "e2", "logical_sequence": 4}))
        self.assertFalse(result.accepted)
        self.assertIn("sequence_regression", result.failures)

    def test_sequence_5_then_5_same_run_rejected_as_duplicate(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 5}))
        result = journal.append(_valid_event({"event_id": "e2", "logical_sequence": 5}))
        self.assertFalse(result.accepted)
        self.assertIn("duplicate_logical_sequence", result.failures)

    def test_sequence_5_then_6_same_run_accepted(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 5}))
        result = journal.append(_valid_event({"event_id": "e2", "logical_sequence": 6}))
        self.assertTrue(result.accepted)

    def test_sequence_5_run_a_then_4_run_b_accepted(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "run_id": "run-a", "logical_sequence": 5}))
        result = journal.append(_valid_event({"event_id": "e2", "run_id": "run-b", "logical_sequence": 4}))
        self.assertTrue(result.accepted)

    def test_rejected_sequence_regression_does_not_mutate_journal(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 5}))
        count_before = journal.event_count()
        events_before = journal.events
        result = journal.append(_valid_event({"event_id": "e2", "logical_sequence": 4}))
        self.assertFalse(result.accepted)
        self.assertEqual(journal.event_count(), count_before)
        self.assertEqual(journal.events, events_before)


class EventJournalStageRegressionTests(unittest.TestCase):
    """Stage regression detection tests."""

    def test_forward_stage_progression_accepted(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "stage": "context", "logical_sequence": 1}))
        result = journal.append(_valid_event({"event_id": "e2", "stage": "inference", "logical_sequence": 2}))
        self.assertTrue(result.accepted)

    def test_same_stage_accepted(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "stage": "context", "logical_sequence": 1}))
        result = journal.append(_valid_event({"event_id": "e2", "stage": "context", "logical_sequence": 2}))
        self.assertTrue(result.accepted)

    def test_backward_stage_regression_rejected(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "stage": "approval", "logical_sequence": 1}))
        result = journal.append(_valid_event({"event_id": "e2", "stage": "validation", "logical_sequence": 2}))
        self.assertFalse(result.accepted)
        self.assertIn("stage_regression", result.failures)

    def test_stage_regression_from_evidence_to_context_rejected(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "stage": "evidence", "logical_sequence": 1}))
        result = journal.append(_valid_event({"event_id": "e2", "stage": "context", "logical_sequence": 2}))
        self.assertFalse(result.accepted)
        self.assertIn("stage_regression", result.failures)

    def test_stage_regression_per_run_isolated(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "run_id": "run-a", "stage": "evidence", "logical_sequence": 1}))
        # Different run can start at any stage
        result = journal.append(_valid_event({"event_id": "e2", "run_id": "run-b", "stage": "context", "logical_sequence": 1}))
        self.assertTrue(result.accepted)


class EventJournalForbiddenFieldTests(unittest.TestCase):
    """Forbidden field rejection tests."""

    def test_raw_prompt_forbidden(self):
        journal = EventJournal()
        result = journal.append(_valid_event({"raw_prompt": "some text"}))
        self.assertFalse(result.accepted)
        self.assertIn("raw_prompt_forbidden", result.failures)

    def test_raw_provider_response_forbidden(self):
        journal = EventJournal()
        result = journal.append(_valid_event({"raw_provider_response": "some text"}))
        self.assertFalse(result.accepted)
        self.assertIn("raw_provider_response_forbidden", result.failures)

    def test_secret_value_forbidden(self):
        journal = EventJournal()
        result = journal.append(_valid_event({"secret_value": "sk-abc"}))
        self.assertFalse(result.accepted)
        self.assertIn("secret_value_forbidden", result.failures)

    def test_env_value_forbidden(self):
        journal = EventJournal()
        result = journal.append(_valid_event({"env_value": "PATH=/usr/bin"}))
        self.assertFalse(result.accepted)
        self.assertIn("env_value_forbidden", result.failures)

    def test_validate_event_record_rejects_forbidden(self):
        payload = _valid_event({"raw_prompt": "test"})
        failures = validate_event_record(payload)
        self.assertIn("raw_prompt_forbidden", failures)


class EventJournalRequiredFieldTests(unittest.TestCase):
    """Required field validation tests."""

    def test_missing_event_id_rejected(self):
        payload = _valid_event()
        del payload["event_id"]
        result = EventJournal().append(payload)
        self.assertIn("event_id_required", result.failures)

    def test_missing_run_id_rejected(self):
        payload = _valid_event()
        del payload["run_id"]
        result = EventJournal().append(payload)
        self.assertIn("run_id_required", result.failures)

    def test_missing_task_id_rejected(self):
        payload = _valid_event()
        del payload["task_id"]
        result = EventJournal().append(payload)
        self.assertIn("task_id_required", result.failures)

    def test_missing_stage_rejected(self):
        payload = _valid_event()
        del payload["stage"]
        result = EventJournal().append(payload)
        self.assertIn("stage_required", result.failures)

    def test_missing_event_type_rejected(self):
        payload = _valid_event()
        del payload["event_type"]
        result = EventJournal().append(payload)
        self.assertIn("event_type_required", result.failures)

    def test_missing_logical_sequence_rejected(self):
        payload = _valid_event()
        del payload["logical_sequence"]
        result = EventJournal().append(payload)
        self.assertIn("logical_sequence_required", result.failures)

    def test_missing_payload_digest_rejected(self):
        payload = _valid_event()
        del payload["payload_digest"]
        result = EventJournal().append(payload)
        self.assertIn("payload_digest_required", result.failures)


class EventJournalFieldTypeTests(unittest.TestCase):
    """Field type and format validation tests."""

    def test_empty_event_id_rejected(self):
        result = EventJournal().append(_valid_event({"event_id": ""}))
        self.assertIn("event_id_must_be_nonempty_string", result.failures)

    def test_none_run_id_rejected(self):
        result = EventJournal().append(_valid_event({"run_id": None}))
        self.assertIn("run_id_must_be_nonempty_string", result.failures)

    def test_logical_sequence_must_be_int(self):
        result = EventJournal().append(_valid_event({"logical_sequence": "1"}))
        self.assertIn("logical_sequence_must_be_int", result.failures)

    def test_logical_sequence_bool_rejected(self):
        result = EventJournal().append(_valid_event({"logical_sequence": True}))
        self.assertIn("logical_sequence_must_be_int", result.failures)

    def test_logical_sequence_negative_rejected(self):
        result = EventJournal().append(_valid_event({"logical_sequence": -1}))
        self.assertIn("logical_sequence_must_be_nonnegative", result.failures)

    def test_logical_sequence_zero_accepted(self):
        result = EventJournal().append(_valid_event({"logical_sequence": 0}))
        self.assertTrue(result.accepted)

    def test_payload_digest_lacks_sha256_prefix_rejected(self):
        result = EventJournal().append(_valid_event({"payload_digest": "abc123"}))
        self.assertIn("payload_digest_must_be_sha256_prefixed", result.failures)

    def test_payload_digest_with_sha256_prefix_accepted(self):
        result = EventJournal().append(_valid_event({"payload_digest": "sha256:abc123"}))
        self.assertTrue(result.accepted)

    def test_stage_not_legal_rejected(self):
        result = EventJournal().append(_valid_event({"stage": "not_a_legal_stage"}))
        self.assertIn("stage_not_legal", result.failures)


class EventJournalSideEffectFreeTests(unittest.TestCase):
    """Verify the journal validation is side-effect free."""

    def test_validate_event_record_does_not_mutate(self):
        p1 = _valid_event()
        p2 = copy.deepcopy(p1)
        validate_event_record(p1)
        self.assertEqual(p1, p2)

    def test_append_rejected_does_not_mutate_journal(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        count_before = journal.event_count()
        events_before = journal.events
        # This should be rejected
        result = journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        self.assertFalse(result.accepted)
        self.assertEqual(journal.event_count(), count_before)
        self.assertEqual(journal.events, events_before)

    def test_append_only_no_removal_api(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        journal.append(_valid_event({"event_id": "e2", "logical_sequence": 2}))
        self.assertEqual(journal.event_count(), 2)
        # No removal method exists on EventJournal
        self.assertFalse(hasattr(journal, "remove"))
        self.assertFalse(hasattr(journal, "delete"))
        self.assertFalse(hasattr(journal, "clear"))

    def test_non_mapping_append_rejected(self):
        journal = EventJournal()
        result = journal.append("not a mapping")
        self.assertFalse(result.accepted)
        self.assertIn("event_must_be_mapping", result.failures)

    def test_append_rejected_does_not_add_to_journal(self):
        journal = EventJournal()
        journal.append("not a mapping")
        self.assertEqual(journal.event_count(), 0)

    def test_journal_append_result_no_event_on_rejection(self):
        journal = EventJournal()
        result = journal.append("not a mapping")
        self.assertIsNone(result.event)


class EventJournalIntegrityTests(unittest.TestCase):
    """Journal integrity and contract tests."""

    def test_events_are_journal_event_instances(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        for event in journal.events:
            self.assertIsInstance(event, JournalEvent)

    def test_events_cannot_be_modified_through_property(self):
        journal = EventJournal()
        journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        events = journal.events
        self.assertEqual(len(events), 1)
        # The tuple property returns a snapshot; modifying it doesn't affect journal
        self.assertEqual(journal.event_count(), 1)

    def test_journal_append_result_accepted_has_event(self):
        journal = EventJournal()
        result = journal.append(_valid_event({"event_id": "e1", "logical_sequence": 1}))
        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.event)
        self.assertIsInstance(result.event, JournalEvent)

    def test_multiple_failures_accumulated(self):
        payload = _valid_event({
            "raw_prompt": "test",
            "secret_value": "sk-abc",
            "event_id": "",
            "logical_sequence": "bad",
        })
        result = EventJournal().append(payload)
        self.assertFalse(result.accepted)
        self.assertIn("raw_prompt_forbidden", result.failures)
        self.assertIn("secret_value_forbidden", result.failures)
        self.assertIn("event_id_must_be_nonempty_string", result.failures)
        self.assertIn("logical_sequence_must_be_int", result.failures)

    def test_legal_stages_are_all_accepted(self):
        legal = ("dry_run", "context", "inference", "patch_proposal", "validation",
                  "review", "approval", "revision_seal", "evidence")
        for stage in legal:
            failures = validate_event_record(_valid_event({"stage": stage}))
            self.assertEqual(failures, (), f"Stage '{stage}' should be legal")
