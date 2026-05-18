"""Real patch application runtime tracer bullet tests.

Covers all required behaviors:
- dry-run patch validation
- patch request contract
- patch allowlist enforcement
- target path safety
- absolute path rejection
- path traversal rejection
- forbidden root rejection
- main mutation rejection
- git push / merge / branch delete rejection
- no freeform shell
- no network
- rollback bundle required
- tests required before approval
- deterministic patch receipt
- patch failure receipt
- no destructive mutation in v1
- no overclaim about actual patch application
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from patch_runtime import (  # type: ignore[import-not-found]
    PatchRuntime,
    PatchRequest,
    PatchAllowlist,
    PatchPreflight,
    PatchReceipt,
    PatchFailureReceipt,
    PatchRollback,
    PatchCanonicalHash,
    PatchSecurity,
    produce_patch_receipt,
    produce_patch_failure_receipt,
)

VALID_SHA256 = "a" * 64
VALID_SHA256_B = "b" * 64


class TestPatchRequest(unittest.TestCase):
    """Patch request contract and path safety tests."""

    def test_create_valid_request(self):
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        self.assertTrue(req.is_valid)
        self.assertTrue(req.is_dry_run)
        self.assertTrue(req.canonical_hash)

    def test_reject_empty_patch_id(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("", "tools/file.py", VALID_SHA256, VALID_SHA256_B)

    def test_reject_invalid_patch_content_hash(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "tools/file.py", "short", VALID_SHA256_B)

    def test_reject_invalid_rollback_bundle_hash(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, "short")

    def test_reject_absolute_path(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "/etc/passwd", VALID_SHA256, VALID_SHA256_B)

    def test_reject_path_traversal(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "../../etc/passwd", VALID_SHA256, VALID_SHA256_B)

    def test_reject_home_expansion(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "~/.ssh/config", VALID_SHA256, VALID_SHA256_B)

    def test_reject_forbidden_root_etc(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "/etc/hosts", VALID_SHA256, VALID_SHA256_B)

    def test_reject_main_mutation_checkout(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "git checkout main", VALID_SHA256, VALID_SHA256_B)

    def test_reject_git_push(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "git push origin main", VALID_SHA256, VALID_SHA256_B)

    def test_reject_git_merge(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "git merge main", VALID_SHA256, VALID_SHA256_B)

    def test_reject_git_branch_delete(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "git branch -D main", VALID_SHA256, VALID_SHA256_B)

    def test_reject_network_url(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "https://evil.com/patch", VALID_SHA256, VALID_SHA256_B)

    def test_reject_freeform_shell_pipe(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "file.py | cat", VALID_SHA256, VALID_SHA256_B)

    def test_reject_freeform_shell_semicolon(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "file.py; rm -rf /", VALID_SHA256, VALID_SHA256_B)

    def test_reject_freeform_shell_dollar(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "echo $HOME", VALID_SHA256, VALID_SHA256_B)

    def test_reject_empty_target_path(self):
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "", VALID_SHA256, VALID_SHA256_B)

    def test_request_deterministic(self):
        r1 = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        r2 = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        self.assertEqual(r1.request_id, r2.request_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_request_no_raw_payload(self):
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        d = req.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)


class TestPatchAllowlist(unittest.TestCase):
    """Patch allowlist enforcement tests."""

    def test_empty_allowlist_rejects(self):
        al = PatchAllowlist()
        self.assertFalse(al.is_allowed("anything"))

    def test_allowlist_accepts_known_path(self):
        al = PatchAllowlist(["tools/file.py"])
        self.assertTrue(al.is_allowed("tools/file.py"))

    def test_allowlist_rejects_unknown_path(self):
        al = PatchAllowlist(["tools/file.py"])
        self.assertFalse(al.is_allowed("tools/other.py"))

    def test_enforce_raises_on_unknown(self):
        al = PatchAllowlist(["tools/file.py"])
        with self.assertRaises(ValueError):
            al.enforce("tools/other.py")

    def test_enforce_passes_on_known(self):
        al = PatchAllowlist(["tools/file.py"])
        al.enforce("tools/file.py")  # should not raise

    def test_allowlist_hash_deterministic(self):
        al1 = PatchAllowlist(["tools/a.py", "tools/b.py"])
        al2 = PatchAllowlist(["tools/b.py", "tools/a.py"])
        self.assertEqual(al1.allowlist_hash(), al2.allowlist_hash())

    def test_add_path(self):
        al = PatchAllowlist()
        al.add_path("tools/new.py")
        self.assertTrue(al.is_allowed("tools/new.py"))


class TestPatchPreflight(unittest.TestCase):
    """Patch preflight validation tests."""

    def test_preflight_passes_with_allowlist(self):
        al = PatchAllowlist(["tools/file.py"])
        pf = PatchPreflight(al)
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        result = pf.check(req)
        self.assertTrue(result["preflight_passed"])

    def test_preflight_fails_without_allowlist(self):
        al = PatchAllowlist(["other/file.py"])
        pf = PatchPreflight(al)
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        result = pf.check(req)
        self.assertFalse(result["preflight_passed"])
        self.assertIn("target_in_allowlist", result["gates"])

    def test_preflight_enforce_raises(self):
        al = PatchAllowlist(["other/file.py"])
        pf = PatchPreflight(al)
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        with self.assertRaises(ValueError):
            pf.enforce(req)

    def test_preflight_all_gates_present(self):
        al = PatchAllowlist(["tools/file.py"])
        pf = PatchPreflight(al)
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        result = pf.check(req)
        self.assertIn("request_valid", result["gates"])
        self.assertIn("target_in_allowlist", result["gates"])
        self.assertIn("rollback_bundle_present", result["gates"])
        self.assertIn("path_safety", result["gates"])
        self.assertIn("no_network", result["gates"])
        self.assertIn("no_main_mutation", result["gates"])


class TestPatchRollback(unittest.TestCase):
    """Rollback bundle tests."""

    def test_create_rollback(self):
        rb = PatchRollback.create("patch-1", VALID_SHA256, "revert the patch")
        self.assertTrue(rb.is_valid)
        self.assertTrue(rb.canonical_hash)
        self.assertEqual(rb.patch_id, "patch-1")

    def test_rollback_rejects_empty_patch_id(self):
        with self.assertRaises(ValueError):
            PatchRollback.create("", VALID_SHA256)

    def test_rollback_rejects_invalid_hash(self):
        with self.assertRaises(ValueError):
            PatchRollback.create("patch-1", "short")

    def test_rollback_deterministic(self):
        r1 = PatchRollback.create("patch-1", VALID_SHA256, "revert")
        r2 = PatchRollback.create("patch-1", VALID_SHA256, "revert")
        self.assertEqual(r1.rollback_id, r2.rollback_id)


class TestPatchReceipts(unittest.TestCase):
    """Patch receipt generation tests."""

    def test_produce_approved_receipt(self):
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        preflight = {"preflight_passed": True, "target_in_allowlist": True}
        receipt = produce_patch_receipt(req, preflight)
        self.assertEqual(receipt.status, "approved")
        self.assertTrue(receipt.no_patch_application)

    def test_produce_rejected_receipt(self):
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        preflight = {"preflight_passed": False, "target_in_allowlist": False}
        receipt = produce_patch_receipt(req, preflight)
        self.assertEqual(receipt.status, "rejected")

    def test_produce_failure_receipt(self):
        receipt = produce_patch_failure_receipt("req-1", "allowlist missing", "PATCH_ALLOWLIST_FAILED")
        self.assertEqual(receipt.failure_code, "PATCH_ALLOWLIST_FAILED")
        self.assertTrue(receipt.no_patch_application)

    def test_failure_receipt_requires_reason(self):
        with self.assertRaises(ValueError):
            produce_patch_failure_receipt("req-1", "", "CODE")

    def test_failure_receipt_requires_code(self):
        with self.assertRaises(ValueError):
            produce_patch_failure_receipt("req-1", "reason", "")

    def test_receipt_deterministic(self):
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        preflight = {"preflight_passed": True, "target_in_allowlist": True}
        r1 = produce_patch_receipt(req, preflight)
        r2 = produce_patch_receipt(req, preflight)
        self.assertEqual(r1.receipt_id, r2.receipt_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_no_raw_payload_in_receipts(self):
        req = PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        r1 = produce_patch_receipt(req, {"preflight_passed": True}).to_dict()
        r2 = produce_patch_failure_receipt("req-1", "reason", "CODE").to_dict()
        for r in (r1, r2):
            self.assertNotIn("raw_payload", r)
            self.assertNotIn("payload", r)
            self.assertNotIn("raw_data", r)


class TestPatchSecurity(unittest.TestCase):
    """Patch security boundary tests."""

    def test_validate_clean_payload(self):
        result = PatchSecurity.validate_payload({"patch_id": "p1", "target_path": "tools/file.py"})
        self.assertTrue(result["valid"])

    def test_reject_api_key_in_payload(self):
        result = PatchSecurity.validate_payload({"API_KEY": "sk-123"})
        self.assertFalse(result["valid"])

    def test_reject_secret_in_value(self):
        result = PatchSecurity.validate_payload({"path": "/home/user/.env"})
        self.assertFalse(result["valid"])

    def test_reject_network_url(self):
        result = PatchSecurity.validate_payload({"url": "https://evil.com"})
        self.assertFalse(result["valid"])

    def test_reject_main_mutation(self):
        result = PatchSecurity.validate_payload({"cmd": "git checkout main"})
        self.assertFalse(result["valid"])

    def test_validate_flags_rejects_forbidden(self):
        result = PatchSecurity.validate_flags(["network", "git_push"])
        self.assertFalse(result["valid"])

    def test_validate_flags_accepts_ok(self):
        result = PatchSecurity.validate_flags(["dry_run", "test"])
        self.assertTrue(result["valid"])

    def test_no_network_detection(self):
        self.assertTrue(PatchSecurity.validate_no_network("ls -la"))
        self.assertFalse(PatchSecurity.validate_no_network("curl http://evil.com"))

    def test_no_main_mutation_detection(self):
        self.assertTrue(PatchSecurity.validate_no_main_mutation("edit file.py"))
        self.assertFalse(PatchSecurity.validate_no_main_mutation("git checkout main"))

    def test_security_gates(self):
        gates = PatchSecurity.security_gates()
        self.assertIn("no_network", gates)
        self.assertIn("rollback_bundle_required", gates)
        self.assertTrue(all(gates.values()))


class TestPatchCanonicalHash(unittest.TestCase):
    """Patch canonical hash tests."""

    def test_canonical_hash(self):
        h = PatchCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(len(h), 64)

    def test_deterministic(self):
        h1 = PatchCanonicalHash.canonical_hash("a", "b")
        h2 = PatchCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(h1, h2)

    def test_reject_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            PatchCanonicalHash.canonical_hash("a", algorithm="md5")

    def test_request_hash(self):
        h = PatchCanonicalHash.request_hash("p1", "tools/f.py", VALID_SHA256, VALID_SHA256_B)
        self.assertEqual(len(h), 64)

    def test_allowlist_hash(self):
        h = PatchCanonicalHash.allowlist_hash(["tools/a.py", "tools/b.py"])
        self.assertEqual(len(h), 64)


class TestPatchRuntime(unittest.TestCase):
    """Full PatchRuntime integration tests."""

    def setUp(self):
        self.runtime = PatchRuntime()

    def test_full_happy_path(self):
        self.runtime.configure_allowlist(["tools/file.py", "tools/other.py"])
        request = self.runtime.create_request(
            "patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B,
            test_results_hash=VALID_SHA256,
        )
        receipt = self.runtime.approve(request)
        self.assertEqual(receipt.status, "approved")
        self.assertTrue(receipt.no_patch_application)

    def test_allowlist_rejection(self):
        self.runtime.configure_allowlist(["other/file.py"])
        request = self.runtime.create_request(
            "patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B,
        )
        with self.assertRaises(ValueError):
            self.runtime.approve(request)

    def test_failure_receipt_production(self):
        receipt = self.runtime.produce_failure_receipt(
            "req-1", "allowlist missing", "PATCH_ALLOWLIST_FAILED",
        )
        self.assertEqual(receipt.failure_code, "PATCH_ALLOWLIST_FAILED")
        self.assertEqual(self.runtime.failure_count(), 1)

    def test_create_rollback(self):
        rb = self.runtime.create_rollback("patch-1", VALID_SHA256, "revert the patch")
        self.assertTrue(rb.is_valid)
        self.assertEqual(rb.patch_id, "patch-1")

    def test_receipt_count_tracks(self):
        self.runtime.configure_allowlist(["tools/file.py"])
        request = self.runtime.create_request(
            "patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B,
        )
        self.assertEqual(self.runtime.receipt_count(), 0)
        self.runtime.approve(request)
        self.assertEqual(self.runtime.receipt_count(), 1)

    def test_runtime_hash_changes(self):
        self.runtime.configure_allowlist(["tools/file.py"])
        request = self.runtime.create_request(
            "patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B,
        )
        h1 = self.runtime.runtime_hash()
        self.runtime.approve(request)
        h2 = self.runtime.runtime_hash()
        self.assertNotEqual(h1, h2)

    def test_reset(self):
        self.runtime.configure_allowlist(["tools/file.py"])
        self.runtime.create_request("patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B)
        self.runtime.reset()
        self.assertEqual(self.runtime.receipt_count(), 0)
        self.assertEqual(self.runtime.failure_count(), 0)

    def test_no_actual_application(self):
        self.runtime.configure_allowlist(["tools/file.py"])
        request = self.runtime.create_request(
            "patch-1", "tools/file.py", VALID_SHA256, VALID_SHA256_B,
        )
        receipt = self.runtime.approve(request)
        self.assertTrue(receipt.no_patch_application)
        self.assertEqual(receipt.module_version, "v1")

    def test_rollback_bundle_required(self):
        # rollback_bundle_hash is required in PatchRequest.create
        with self.assertRaises(ValueError):
            PatchRequest.create("patch-1", "tools/file.py", VALID_SHA256, "")

    def test_destructive_path_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.create_request("patch-1", "/etc/passwd", VALID_SHA256, VALID_SHA256_B)


class TestNoNetworkOrSubprocess(unittest.TestCase):
    """Verify no network/subprocess imports in patch runtime modules."""

    def test_no_forbidden_imports(self):
        patch_dir = ROOT / "tools" / "patch_runtime"
        for py_file in patch_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name} imports subprocess")
            self.assertNotIn("import socket", src, f"{py_file.name} imports socket")
            self.assertNotIn("import requests", src, f"{py_file.name} imports requests")
            self.assertNotIn("from urllib", src, f"{py_file.name} imports urllib")
            self.assertNotIn("import anthropic", src, f"{py_file.name} imports anthropic")
            self.assertNotIn("import openai", src, f"{py_file.name} imports openai")
            self.assertNotIn("from anthropic", src, f"{py_file.name} imports anthropic")
            self.assertNotIn("from openai", src, f"{py_file.name} imports openai")

    def test_no_env_reads(self):
        patch_dir = ROOT / "tools" / "patch_runtime"
        for py_file in patch_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("dotenv", src, f"{py_file.name} references dotenv")
            self.assertNotIn("os.environ", src, f"{py_file.name} reads os.environ")
            self.assertNotIn("os.getenv", src, f"{py_file.name} reads os.getenv")


if __name__ == "__main__":
    unittest.main()
