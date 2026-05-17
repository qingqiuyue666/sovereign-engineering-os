"""Tests for local core authority gate and protected assets."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kernel.security.local_core_authority_gate import (
    PROTECTED_ASSET_IDS,
    validate_core_asset_protection,
    validate_local_authority_gate,
)


def valid_authority(**overrides):
    payload = {
        "branch_name": "v12-local-core-operating-foundation-v1",
        "clean_base_required": True,
        "dirty_worktree_before_apply": False,
        "git_diff_check_passed": True,
        "local_tests_passed": True,
        "local_ci_passed": True,
        "human_review_required": True,
        "cloud_ai_is_authority": False,
        "authority_delegations": [],
    }
    payload.update(overrides)
    return payload


def valid_asset(**overrides):
    payload = {
        "asset_id": "runtime_spine_design",
        "asset_class": "C",
        "local_only_required": True,
        "cloud_ai_allowed": False,
        "exposure_mode": "local_only",
    }
    payload.update(overrides)
    return payload


class LocalCoreAuthorityGateTests(unittest.TestCase):
    def test_registry_and_runbook_exist(self):
        self.assertTrue(Path("governance/security/core_asset_protection_registry_v1.json").is_file())
        self.assertTrue(Path("docs/runbooks/local_core_operating_foundation_v1.md").is_file())

    def test_registry_json_is_active(self):
        payload = json.loads(Path("governance/security/core_asset_protection_registry_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["registry_version"], "v1")
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["default_rule"], "local_only_no_cloud_ai")

    def test_valid_local_authority_gate_is_accepted(self):
        self.assertTrue(validate_local_authority_gate(valid_authority()).accepted)

    def test_main_branch_direct_work_is_rejected(self):
        receipt = validate_local_authority_gate(valid_authority(branch_name="main"))
        self.assertFalse(receipt.accepted)
        self.assertIn("main_branch_direct_work_forbidden", receipt.failures)

    def test_dirty_worktree_is_rejected(self):
        receipt = validate_local_authority_gate(valid_authority(dirty_worktree_before_apply=True))
        self.assertFalse(receipt.accepted)
        self.assertIn("dirty_worktree_before_apply_forbidden", receipt.failures)

    def test_local_ci_must_pass(self):
        receipt = validate_local_authority_gate(valid_authority(local_ci_passed=False))
        self.assertFalse(receipt.accepted)
        self.assertIn("local_ci_must_pass", receipt.failures)

    def test_cloud_ai_must_not_be_authority(self):
        receipt = validate_local_authority_gate(valid_authority(cloud_ai_is_authority=True))
        self.assertFalse(receipt.accepted)
        self.assertIn("cloud_ai_must_not_be_authority", receipt.failures)

    def test_forbidden_authority_delegations_are_rejected(self):
        receipt = validate_local_authority_gate(valid_authority(authority_delegations=["cloud_ai_git_authority", "cloud_ai_push_authority"]))
        self.assertFalse(receipt.accepted)
        self.assertIn("cloud_ai_git_authority_forbidden", receipt.failures)
        self.assertIn("cloud_ai_push_authority_forbidden", receipt.failures)

    def test_valid_core_asset_is_accepted(self):
        self.assertTrue(validate_core_asset_protection(valid_asset()).accepted)

    def test_all_registered_assets_require_local_only(self):
        for asset_id in PROTECTED_ASSET_IDS:
            self.assertTrue(validate_core_asset_protection(valid_asset(asset_id=asset_id)).accepted, asset_id)

    def test_unregistered_asset_is_rejected(self):
        receipt = validate_core_asset_protection(valid_asset(asset_id="unknown_asset"))
        self.assertFalse(receipt.accepted)
        self.assertIn("asset_id_not_registered_protected_asset", receipt.failures)

    def test_protected_asset_must_be_c_layer(self):
        receipt = validate_core_asset_protection(valid_asset(asset_class="B"))
        self.assertFalse(receipt.accepted)
        self.assertIn("protected_asset_must_be_c_layer", receipt.failures)

    def test_protected_asset_forbids_cloud_ai(self):
        receipt = validate_core_asset_protection(valid_asset(cloud_ai_allowed=True))
        self.assertFalse(receipt.accepted)
        self.assertIn("protected_asset_forbids_cloud_ai", receipt.failures)

    def test_protected_asset_requires_local_only(self):
        receipt = validate_core_asset_protection(valid_asset(local_only_required=False))
        self.assertFalse(receipt.accepted)
        self.assertIn("protected_asset_requires_local_only", receipt.failures)

    def test_exposure_mode_must_be_local_only(self):
        receipt = validate_core_asset_protection(valid_asset(exposure_mode="minimal_snippets"))
        self.assertFalse(receipt.accepted)
        self.assertIn("exposure_mode_must_be_local_only", receipt.failures)

    def test_non_mapping_payloads_raise(self):
        with self.assertRaises(TypeError):
            validate_local_authority_gate(None)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            validate_core_asset_protection(None)  # type: ignore[arg-type]

    def test_source_does_not_import_network_subprocess_or_git_mutation(self):
        source = Path("kernel/security/local_core_authority_gate.py").read_text(encoding="utf-8")
        forbidden = ("socket", "requests", "urllib", "subprocess", "os.system", "git push", "git merge")
        for item in forbidden:
            self.assertNotIn(item, source)

    def test_runbook_records_no_real_runtime_claim(self):
        text = Path("docs/runbooks/local_core_operating_foundation_v1.md").read_text(encoding="utf-8")
        self.assertIn("does not implement real provider execution", text)
        self.assertIn("Cloud AI is not authority", text)
        self.assertIn("Protected assets are C-layer and local-only", text)


if __name__ == "__main__":
    unittest.main()
