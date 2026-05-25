"""Tracer-bullet tests for the dry-run expansion freeze policy."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path


POLICY_PATH = Path("governance/policy/dry_run_expansion_freeze_v1.json")
DOC_PATH = Path("docs/architecture/dry_run_expansion_freeze_v1.md")


def _policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _content_hash(policy: dict[str, object]) -> str:
    material = {
        key: value
        for key, value in policy.items()
        if key not in {"content_hash", "effective_at"}
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DryRunExpansionFreezePolicyTests(unittest.TestCase):
    def test_policy_declares_dry_run_layer_complete(self):
        policy = _policy()
        self.assertEqual(policy["object_type"], "DryRunExpansionFreezePolicy")
        self.assertEqual(policy["policy_id"], "dry_run_expansion_freeze_v1")
        self.assertEqual(policy["status"], "ACTIVE")
        self.assertEqual(policy["dry_run_layer_status"], "COMPLETE")

    def test_no_new_dry_run_abstraction_is_true(self):
        self.assertIs(_policy()["no_new_dry_run_abstraction"], True)

    def test_allowed_pr_classes_include_execution_risk_and_evidence(self):
        allowed = set(_policy()["allowed_pr_classes"])
        self.assertIn("Execution Closure", allowed)
        self.assertIn("Risk Reduction", allowed)
        self.assertIn("Evidence Strengthening", allowed)

    def test_disallowed_pr_classes_include_abstraction_and_placeholder(self):
        disallowed = set(_policy()["disallowed_pr_classes"])
        self.assertIn("new dry-run-only abstraction", disallowed)
        self.assertIn("new future adapter placeholder", disallowed)

    def test_exception_requires_use_case_id(self):
        self.assertIn("use_case_id", _policy()["exception_required_fields"])

    def test_exception_requires_evidence_output(self):
        self.assertIn("evidence_output", _policy()["exception_required_fields"])

    def test_exception_requires_rollback_or_failure_boundary(self):
        self.assertIn("rollback_or_failure_boundary", _policy()["exception_required_fields"])

    def test_content_hash_is_deterministic_excluding_effective_at(self):
        policy = _policy()
        self.assertEqual(policy["content_hash"], _content_hash(policy))
        changed = copy.deepcopy(policy)
        changed["effective_at"] = "2030-01-01T00:00:00Z"
        self.assertEqual(_content_hash(policy), _content_hash(changed))

    def test_no_existing_module_mutation_required(self):
        policy = _policy()
        doc = " ".join(DOC_PATH.read_text(encoding="utf-8").split())
        self.assertFalse(policy["module_mutation_required"])
        self.assertIn("does not require mutation of existing modules", doc)


if __name__ == "__main__":
    unittest.main()
