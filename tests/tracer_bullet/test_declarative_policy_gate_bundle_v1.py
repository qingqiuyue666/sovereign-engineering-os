"""Tests for Declarative Policy Gate Bundle V1."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.declarative_policy_gate_bundle import (
    ZERO_HASH,
    FileBackedDeclarativePolicyGateBundle,
    compute_declarative_policy_bundle_digest,
    compute_declarative_policy_decision_receipt_hash,
    load_declarative_policy_bundle,
)
from kernel.stores.real_wal_storage import FileBackedRealWalStorage

OBSERVED_AT = "2026-05-29T05:00:00+00:00"


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _evidence() -> dict[str, object]:
    return {
        "final_signoff": {"accepted": True, "receipt_hash": _digest("signoff")},
        "independent_verification": {
            "accepted": True,
            "receipt_hash": _digest("verification"),
        },
        "transparency": {"root_hash": _digest("transparency-root")},
        "ci": {"canonical_health": "SUCCESS"},
        "blockers": [],
    }


def _policy_bundle() -> dict[str, object]:
    return {
        "policy_version": "declarative_policy_gate_bundle_v1",
        "bundle_id": "post-529-release-gates",
        "required_rule_ids": [
            "final-signoff-accepted",
            "verification-accepted",
            "canonical-health-success",
            "transparency-root-bound",
            "no-blockers",
        ],
        "rules": [
            {
                "rule_id": "final-signoff-accepted",
                "operator": "truthy",
                "path": "final_signoff.accepted",
            },
            {
                "rule_id": "verification-accepted",
                "operator": "truthy",
                "path": "independent_verification.accepted",
            },
            {
                "rule_id": "canonical-health-success",
                "operator": "status_in",
                "path": "ci.canonical_health",
                "values": ["success"],
            },
            {
                "rule_id": "transparency-root-bound",
                "operator": "sha256",
                "path": "transparency.root_hash",
            },
            {
                "rule_id": "no-blockers",
                "operator": "equals",
                "path": "blockers",
                "value": [],
            },
        ],
    }


class DeclarativePolicyGateBundleV1Tests(unittest.TestCase):
    def test_valid_policy_allows_and_persists_deterministic_receipt_and_wal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            first = FileBackedDeclarativePolicyGateBundle(
                runtime_root=root / "first",
            ).evaluate(_policy_bundle(), _evidence(), observed_at=OBSERVED_AT)
            second = FileBackedDeclarativePolicyGateBundle(
                runtime_root=root / "second",
            ).evaluate(_policy_bundle(), _evidence(), observed_at=OBSERVED_AT)
            report = json.loads(
                (
                    root
                    / "first"
                    / "declarative-policy-gate-bundle"
                    / "reports"
                    / "policy-decision-report.json"
                ).read_text(encoding="utf-8")
            )
            wal_records = FileBackedRealWalStorage(
                root
                / "first"
                / "declarative-policy-gate-bundle"
                / "policy.real-wal.jsonl"
            ).read_records()

        self.assertTrue(first.allowed, first.failures)
        self.assertEqual(first.decision, "allow")
        self.assertEqual(first.receipt_hash, second.receipt_hash)
        self.assertEqual(
            first.receipt_hash,
            compute_declarative_policy_decision_receipt_hash(first),
        )
        self.assertEqual(first.policy_digest, compute_declarative_policy_bundle_digest(_policy_bundle()))
        self.assertEqual(report["receipt_hash"], first.receipt_hash)
        self.assertEqual(wal_records[-1].record_type, "SYSTEM_ACCEPTANCE_EVENT")
        self.assertEqual(wal_records[-1].record_hash, first.wal_record_hash)
        self.assertNotEqual(first.wal_record_hash, ZERO_HASH)

    def test_missing_gate_malformed_unknown_failed_contradiction_and_digest_mismatch_deny(self) -> None:
        cases = (
            (
                "missing-required-rule",
                lambda policy, evidence: policy["required_rule_ids"].append("missing-gate"),  # type: ignore[union-attr]
                "missing_required_rule:missing-gate",
                (),
            ),
            (
                "malformed-policy",
                lambda policy, evidence: policy["rules"].append(  # type: ignore[union-attr]
                    {"rule_id": "bad-rule", "operator": "unsupported", "path": "ci.canonical_health"}
                ),
                "malformed_rule:bad-rule",
                (),
            ),
            (
                "unknown-version",
                lambda policy, evidence: policy.update({"policy_version": "future_policy_v9"}),
                "unknown_policy_version",
                (),
            ),
            (
                "failed-rule",
                lambda policy, evidence: evidence["ci"].update({"canonical_health": "PENDING"}),  # type: ignore[union-attr]
                "rule_failed:canonical-health-success",
                ("canonical-health-success",),
            ),
            (
                "contradiction",
                lambda policy, evidence: policy["rules"].append(  # type: ignore[union-attr]
                    {
                        "rule_id": "canonical-health-success",
                        "operator": "equals",
                        "path": "ci.canonical_health",
                        "value": "FAILURE",
                    }
                ),
                "contradiction_duplicate_rule_id:canonical-health-success",
                (),
            ),
            (
                "policy-digest-mismatch",
                lambda policy, evidence: policy.update({"policy_digest": ZERO_HASH}),
                "policy_digest_mismatch",
                (),
            ),
            (
                "input-digest-mismatch",
                lambda policy, evidence: policy.update(
                    {"expected_input_evidence_digest": ZERO_HASH}
                ),
                "input_evidence_digest_mismatch",
                (),
            ),
        )
        for label, mutate, expected_failure, failed_rules in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tempdir:
                policy = _policy_bundle()
                evidence = _evidence()
                mutate(policy, evidence)
                receipt = FileBackedDeclarativePolicyGateBundle(
                    runtime_root=tempdir,
                ).evaluate(policy, evidence, observed_at=OBSERVED_AT)

            self.assertFalse(receipt.allowed)
            self.assertEqual(receipt.decision, "deny")
            self.assertIn(expected_failure, receipt.failures)
            for rule_id in failed_rules:
                self.assertIn(rule_id, receipt.failed_rule_ids)

    def test_json_policy_bundle_loader_uses_bundle_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            policy_path = Path(tempdir) / "policy.json"
            policy_path.write_text(
                json.dumps(_policy_bundle(), sort_keys=True),
                encoding="utf-8",
            )
            loaded = load_declarative_policy_bundle(policy_path)
            receipt = FileBackedDeclarativePolicyGateBundle(
                runtime_root=Path(tempdir) / "runtime",
            ).evaluate(policy_path, _evidence(), observed_at=OBSERVED_AT)

        self.assertEqual(loaded, _policy_bundle())
        self.assertTrue(receipt.allowed)
        self.assertEqual(
            receipt.policy_digest,
            compute_declarative_policy_bundle_digest(_policy_bundle()),
        )


if __name__ == "__main__":
    unittest.main()
