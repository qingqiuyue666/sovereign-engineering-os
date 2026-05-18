"""Tests: audit trail and hash chain integrity.

Run:   python -m pytest 测试/test_audit.py -v
Expect: 10 tests pass — audit entries are recorded with incrementing sequence,
        hash chain verifies correctly, tampered chain detected, global audit
        convenience function works, JSON export is valid.
"""

from __future__ import annotations

import pytest

from kernel.audit.trail import AuditTrail, AuditEntry, audit, get_global_trail
from kernel.audit.hashchain import HashChain, HashChainEntry, verify_chain


# ── HashChain tests ────────────────────────────────────────────

def test_hash_chain_initial_state():
    hc = HashChain()
    assert hc.length == 0
    assert hc.latest_hash == HashChain.GENESIS_HASH


def test_hash_chain_append():
    hc = HashChain()
    entry = hc.append("abc123")
    assert entry.index == 0
    assert entry.prev_hash == HashChain.GENESIS_HASH
    assert entry.content_hash == "abc123"
    assert len(entry.current_hash) == 64  # SHA-256 hex digest
    assert hc.length == 1
    assert hc.latest_hash == entry.current_hash


def test_hash_chain_sequential_integrity():
    hc = HashChain()
    e0 = hc.append("data0")
    e1 = hc.append("data1")
    e2 = hc.append("data2")

    assert e1.prev_hash == e0.current_hash
    assert e2.prev_hash == e1.current_hash
    assert verify_chain([e0, e1, e2]) is True


def test_hash_chain_verify_empty():
    assert verify_chain([]) is True


def test_hash_chain_detect_tampered_index():
    hc = HashChain()
    e0 = hc.append("data0")
    e1 = hc.append("data1")
    # Tamper: change index
    tampered = [e0, HashChainEntry(index=99, prev_hash=e1.prev_hash, content_hash="bad", current_hash=e1.current_hash)]
    assert verify_chain(tampered) is False


def test_hash_chain_detect_tampered_prev_hash():
    hc = HashChain()
    e0 = hc.append("data0")
    e1 = hc.append("data1")
    tampered = [e0, HashChainEntry(index=1, prev_hash="deadbeef", content_hash=e1.content_hash, current_hash=e1.current_hash)]
    assert verify_chain(tampered) is False


def test_hash_chain_detect_tampered_content():
    hc = HashChain()
    e0 = hc.append("data0")
    e1 = hc.append("data1")
    # Tamper: change content_hash without rehashing
    tampered = [
        e0,
        HashChainEntry(
            index=1,
            prev_hash=e1.prev_hash,
            content_hash="tampered_content",
            current_hash=e1.current_hash
        ),
    ]
    assert verify_chain(tampered) is False


# ── AuditTrail tests ───────────────────────────────────────────

def test_audit_trail_record():
    trail = AuditTrail("test_trail")
    entry = trail.record("daemon.started", pid=42)
    assert entry.event == "daemon.started"
    assert entry.sequence == 1
    assert entry.payload == {"pid": 42}
    assert entry.hash_chain_entry is not None


def test_audit_trail_sequence_increments():
    trail = AuditTrail("test_trail")
    e1 = trail.record("event.1")
    e2 = trail.record("event.2")
    e3 = trail.record("event.3")
    assert e1.sequence == 1
    assert e2.sequence == 2
    assert e3.sequence == 3
    assert trail.count == 3


def test_audit_trail_verify_integrity():
    trail = AuditTrail("test_integrity")
    trail.record("a")
    trail.record("b")
    trail.record("c")
    assert trail.verify_integrity() is True


def test_audit_trail_query():
    trail = AuditTrail("test_query")
    trail.record("daemon.start")
    trail.record("task.create", task_id="t1")
    trail.record("daemon.stop")

    daemon_events = trail.query(event_filter="daemon")
    assert len(daemon_events) == 2
    assert all(e.event.startswith("daemon") for e in daemon_events)


def test_audit_trail_export_json():
    trail = AuditTrail("test_export")
    trail.record("event.one", key="val")
    exported = trail.export_json()
    assert "event.one" in exported
    assert "key" in exported


def test_global_audit_trail():
    """The global audit convenience function works."""
    trail = get_global_trail()
    before = trail.count
    audit("test.global_audit", source="test_suite")
    assert trail.count == before + 1


def test_audit_trail_clear():
    trail = AuditTrail("test_clear")
    trail.record("e1")
    trail.record("e2")
    assert trail.count == 2
    trail.clear()
    assert trail.count == 0
    assert trail.verify_integrity() is True
