"""Real local execution kernel runtime tracer bullet tests.

Covers all required behaviors including edge cases:
- python3 allowed only with exact python3 allowlist
- pythonmalicious rejected when allowlist contains python
- python3 tests/test_main.py not rejected only because it contains main
- git checkout/switch/push/merge main rejected
- curl/wget/ssh/scp/nc rejected
- API_KEY/SECRET/TOKEN/.env rejected
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from local_execution_kernel import (  # type: ignore[import-not-found]
    LocalExecutionKernel,
    ExecutionRequest,
    CommandAllowlist,
    ExecutionPreflight,
    ExecutionReceipt,
    ExecutionFailureReceipt,
    ExecutionCanonicalHash,
    ExecutionSecurity,
    produce_execution_receipt,
    produce_execution_failure_receipt,
)


class TestExecutionRequest(unittest.TestCase):
    """Command request model tests."""

    def test_create_valid_request(self):
        req = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        self.assertTrue(req.is_valid)
        self.assertEqual(req.first_token, "python3")
        self.assertEqual(req.command_category, "test")

    def test_reject_empty_execution_id(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("", "test", "python3 -m pytest")

    def test_reject_invalid_category(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "deploy", "python3 app.py")

    def test_reject_empty_command_text(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "")

    def test_shlex_parsing(self):
        req = ExecutionRequest.create("exec-1", "test", "python3 -m pytest -v")
        self.assertEqual(req.parsed_tokens, ["python3", "-m", "pytest", "-v"])

    def test_shlex_parsing_quotes(self):
        req = ExecutionRequest.create("exec-1", "test", "echo 'hello world'")
        self.assertEqual(req.parsed_tokens, ["echo", "hello world"])

    def test_reject_forbidden_first_token_curl(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "curl http://example.com")

    def test_reject_forbidden_first_token_git(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "git status")

    def test_reject_network_substring(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "echo 'use curl here'")

    def test_reject_main_mutation_checkout(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "git checkout main")

    def test_reject_main_mutation_push(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "git push origin main")

    def test_reject_branch_delete(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "git branch -D feature")

    def test_reject_secret_in_command(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "export API_KEY=abc123")

    def test_reject_env_in_command(self):
        with self.assertRaises(ValueError):
            ExecutionRequest.create("exec-1", "test", "cat .env")

    def test_request_deterministic(self):
        r1 = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        r2 = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        self.assertEqual(r1.request_id, r2.request_id)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_request_no_raw_payload(self):
        req = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        d = req.to_dict()
        self.assertNotIn("raw_payload", d)
        self.assertNotIn("raw_data", d)


class TestCommandAllowlist(unittest.TestCase):
    """Exact first-token allowlist tests."""

    def test_empty_allowlist_rejects(self):
        al = CommandAllowlist()
        self.assertFalse(al.is_allowed("python3 -m pytest"))

    def test_exact_match_accepts(self):
        al = CommandAllowlist(["python3"])
        self.assertTrue(al.is_allowed("python3 -m pytest"))

    def test_no_partial_match(self):
        al = CommandAllowlist(["python"])
        self.assertFalse(al.is_allowed("python3 -m pytest"))

    def test_exact_python3_match(self):
        """python3 allowed only with exact python3 allowlist."""
        al = CommandAllowlist(["python3"])
        self.assertTrue(al.is_allowed("python3 tests/test_main.py"))
        # python3 is an exact match
        result = al.validate("python3 -c 'print(1)'")
        self.assertTrue(result["valid"])

    def test_pythonmalicious_rejected(self):
        """pythonmalicious rejected when allowlist contains python (exact match)."""
        al = CommandAllowlist(["python"])
        # "pythonmalicious" has first token "pythonmalicious" not "python"
        self.assertFalse(al.is_allowed("pythonmalicious --evil"))
        # But "python" itself would be allowed
        self.assertTrue(al.is_allowed("python script.py"))

    def test_main_not_rejected_in_path(self):
        """python3 tests/test_main.py not rejected because filename contains main."""
        al = CommandAllowlist(["python3"])
        # The first token is python3, which IS in allowlist
        # test_main.py in the path should NOT cause rejection
        self.assertTrue(al.is_allowed("python3 tests/test_main.py"))

    def test_validate_returns_first_token(self):
        al = CommandAllowlist(["pytest"])
        result = al.validate("pytest -v")
        self.assertTrue(result["valid"])
        self.assertEqual(result["first_token"], "pytest")

    def test_enforce_raises_on_unknown(self):
        al = CommandAllowlist(["python3"])
        with self.assertRaises(ValueError):
            al.enforce("node app.js")

    def test_enforce_passes_on_known(self):
        al = CommandAllowlist(["python3"])
        al.enforce("python3 script.py")  # should not raise

    def test_add_remove(self):
        al = CommandAllowlist()
        al.add("pytest")
        self.assertTrue("pytest" in al)
        al.remove("pytest")
        self.assertFalse("pytest" in al)

    def test_allowlist_hash_deterministic(self):
        al1 = CommandAllowlist(["python3", "pytest"])
        al2 = CommandAllowlist(["pytest", "python3"])
        self.assertEqual(al1.allowlist_hash(), al2.allowlist_hash())


class TestExecutionPreflight(unittest.TestCase):
    """Execution preflight tests."""

    def test_preflight_passes(self):
        al = CommandAllowlist(["python3"])
        pf = ExecutionPreflight(al)
        req = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        result = pf.check(req)
        self.assertTrue(result["preflight_passed"])

    def test_preflight_fails_without_allowlist(self):
        al = CommandAllowlist(["pytest"])
        pf = ExecutionPreflight(al)
        req = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        result = pf.check(req)
        self.assertFalse(result["preflight_passed"])
        self.assertFalse(result["gates"]["allowlist_valid"])

    def test_preflight_detects_production(self):
        al = CommandAllowlist(["deploy"])
        pf = ExecutionPreflight(al)
        req = ExecutionRequest.create("exec-1", "test", "deploy production")
        result = pf.check(req)
        self.assertFalse(result["preflight_passed"])
        self.assertFalse(result["gates"]["no_production_execution"])

    def test_preflight_all_gates(self):
        al = CommandAllowlist(["python3"])
        pf = ExecutionPreflight(al)
        req = ExecutionRequest.create("exec-1", "test", "python3 -m pytest")
        result = pf.check(req)
        self.assertIn("request_valid", result["gates"])
        self.assertIn("category_valid", result["gates"])
        self.assertIn("allowlist_valid", result["gates"])
        self.assertIn("no_network_patterns", result["gates"])
        self.assertIn("no_secret_patterns", result["gates"])
        self.assertIn("no_main_mutation", result["gates"])
        self.assertIn("no_production_execution", result["gates"])


class TestExecutionReceipts(unittest.TestCase):
    """Execution receipt tests."""

    def test_produce_receipt_approved(self):
        preflight = {"preflight_passed": True, "allowlist_valid": True}
        receipt = produce_execution_receipt("exec-1", "approved", "test", preflight)
        self.assertEqual(receipt.status, "approved")
        self.assertTrue(receipt.no_execution_performed)

    def test_produce_receipt_rejected(self):
        preflight = {"preflight_passed": False, "allowlist_valid": False}
        receipt = produce_execution_receipt("exec-1", "rejected", "test", preflight)
        self.assertEqual(receipt.status, "rejected")

    def test_produce_failure_receipt(self):
        receipt = produce_execution_failure_receipt(
            "exec-1", "network command", "EXEC_NETWORK_REJECTED",
        )
        self.assertEqual(receipt.failure_code, "EXEC_NETWORK_REJECTED")
        self.assertTrue(receipt.no_execution_performed)

    def test_failure_receipt_requires_fields(self):
        with self.assertRaises(ValueError):
            produce_execution_failure_receipt("exec-1", "", "CODE")
        with self.assertRaises(ValueError):
            produce_execution_failure_receipt("exec-1", "reason", "")

    def test_receipt_deterministic(self):
        preflight = {"preflight_passed": True, "allowlist_valid": True}
        r1 = produce_execution_receipt("exec-1", "approved", "test", preflight)
        r2 = produce_execution_receipt("exec-1", "approved", "test", preflight)
        self.assertEqual(r1.receipt_id, r2.receipt_id)

    def test_no_raw_payload(self):
        r1 = produce_execution_receipt("e1", "approved", "test", {"preflight_passed": True}).to_dict()
        r2 = produce_execution_failure_receipt("e1", "reason", "CODE").to_dict()
        for r in (r1, r2):
            self.assertNotIn("raw_payload", r)
            self.assertNotIn("raw_data", r)


class TestExecutionSecurity(unittest.TestCase):
    """Execution security boundary tests."""

    def test_validate_clean(self):
        result = ExecutionSecurity.validate_payload({"command_text": "python3 -m pytest"})
        self.assertTrue(result["valid"])

    def test_reject_curl(self):
        result = ExecutionSecurity.validate_payload({"command_text": "curl http://evil.com"})
        self.assertFalse(result["valid"])

    def test_reject_wget(self):
        result = ExecutionSecurity.validate_payload({"command_text": "wget http://file"})
        self.assertFalse(result["valid"])

    def test_reject_ssh(self):
        result = ExecutionSecurity.validate_payload({"command_text": "ssh user@host"})
        self.assertFalse(result["valid"])

    def test_reject_scp(self):
        result = ExecutionSecurity.validate_payload({"command_text": "scp file host:"})
        self.assertFalse(result["valid"])

    def test_reject_nc(self):
        result = ExecutionSecurity.validate_payload({"command_text": "nc -l 1234"})
        self.assertFalse(result["valid"])

    def test_reject_git_checkout_main(self):
        result = ExecutionSecurity.validate_payload({"command_text": "git checkout main"})
        self.assertFalse(result["valid"])

    def test_reject_git_switch_main(self):
        result = ExecutionSecurity.validate_payload({"command_text": "git switch main"})
        self.assertFalse(result["valid"])

    def test_reject_git_push_main(self):
        result = ExecutionSecurity.validate_payload({"command_text": "git push origin main"})
        self.assertFalse(result["valid"])

    def test_reject_git_merge_main(self):
        result = ExecutionSecurity.validate_payload({"command_text": "git merge main"})
        self.assertFalse(result["valid"])

    def test_reject_api_key(self):
        result = ExecutionSecurity.validate_payload({"command_text": "export API_KEY=secret"})
        self.assertFalse(result["valid"])

    def test_reject_token(self):
        result = ExecutionSecurity.validate_payload({"command_text": "echo $TOKEN"})
        self.assertFalse(result["valid"])

    def test_reject_dotenv(self):
        result = ExecutionSecurity.validate_payload({"command_text": "source .env"})
        self.assertFalse(result["valid"])

    def test_reject_production(self):
        result = ExecutionSecurity.validate_payload({"command_text": "deploy production"})
        self.assertFalse(result["valid"])

    def test_validate_flags_rejects_forbidden(self):
        result = ExecutionSecurity.validate_flags(["network", "execute"])
        self.assertFalse(result["valid"])

    def test_security_gates(self):
        gates = ExecutionSecurity.security_gates()
        self.assertIn("no_execution_by_default", gates)
        self.assertTrue(all(gates.values()))


class TestExecutionCanonicalHash(unittest.TestCase):
    """Execution canonical hash tests."""

    def test_canonical_hash(self):
        h = ExecutionCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(len(h), 64)

    def test_deterministic(self):
        h1 = ExecutionCanonicalHash.canonical_hash("a", "b")
        h2 = ExecutionCanonicalHash.canonical_hash("a", "b")
        self.assertEqual(h1, h2)


class TestLocalExecutionKernel(unittest.TestCase):
    """Full kernel integration tests."""

    def setUp(self):
        self.kernel = LocalExecutionKernel()

    def test_full_happy_path(self):
        self.kernel.configure_allowlist(["python3", "pytest"])
        request = self.kernel.create_request("exec-1", "test", "python3 -m pytest -v")
        receipt = self.kernel.approve(request)
        self.assertEqual(receipt.status, "approved")
        self.assertTrue(receipt.no_execution_performed)

    def test_allowlist_rejection(self):
        self.kernel.configure_allowlist(["node"])
        request = self.kernel.create_request("exec-1", "test", "python3 -m pytest")
        with self.assertRaises(ValueError):
            self.kernel.approve(request)

    def test_python3_with_exact_allowlist(self):
        """python3 allowed only with exact python3 in allowlist."""
        self.kernel.configure_allowlist(["python3"])
        request = self.kernel.create_request("exec-1", "test", "python3 script.py")
        receipt = self.kernel.approve(request)
        self.assertEqual(receipt.status, "approved")

    def test_pythonmalicious_rejected_exact_match(self):
        """pythonmalicious rejected even when python is in allowlist."""
        self.kernel.configure_allowlist(["python"])
        # Request creation succeeds (pythonmalicious is not a forbidden first token)
        request = self.kernel.create_request("exec-1", "test", "pythonmalicious --evil")
        # But approval fails because pythonmalicious != python (exact allowlist match)
        with self.assertRaises(ValueError):
            self.kernel.approve(request)

    def test_python3_with_main_in_path_not_rejected(self):
        """python3 tests/test_main.py not rejected because filename contains 'main'."""
        self.kernel.configure_allowlist(["python3"])
        # This should work - "main" in filename path, not in git checkout main command
        request = self.kernel.create_request("exec-1", "test", "python3 tests/test_main.py")
        receipt = self.kernel.approve(request)
        self.assertEqual(receipt.status, "approved")

    def test_git_checkout_main_rejected(self):
        self.kernel.configure_allowlist(["git"])
        with self.assertRaises(ValueError):
            self.kernel.create_request("exec-1", "test", "git checkout main")

    def test_curl_rejected(self):
        self.kernel.configure_allowlist(["curl"])
        with self.assertRaises(ValueError):
            self.kernel.create_request("exec-1", "test", "curl http://example.com")

    def test_ssh_rejected(self):
        self.kernel.configure_allowlist(["ssh"])
        with self.assertRaises(ValueError):
            self.kernel.create_request("exec-1", "test", "ssh user@host")

    def test_api_key_rejected(self):
        self.kernel.configure_allowlist(["python3"])
        with self.assertRaises(ValueError):
            self.kernel.create_request("exec-1", "test", "python3 -c 'print(API_KEY)'")

    def test_dotenv_rejected(self):
        self.kernel.configure_allowlist(["cat"])
        with self.assertRaises(ValueError):
            self.kernel.create_request("exec-1", "test", "cat .env")

    def test_production_rejected(self):
        self.kernel.configure_allowlist(["deploy"])
        request = self.kernel.create_request("exec-1", "test", "deploy production")
        # Preflight should reject production execution
        with self.assertRaises(ValueError):
            self.kernel.approve(request)

    def test_failure_receipt_tracks(self):
        receipt = self.kernel.produce_failure_receipt(
            "exec-1", "network command", "EXEC_NETWORK_REJECTED",
        )
        self.assertEqual(self.kernel.failure_count(), 1)

    def test_receipt_count(self):
        self.kernel.configure_allowlist(["python3"])
        request = self.kernel.create_request("exec-1", "test", "python3 -m pytest")
        self.assertEqual(self.kernel.receipt_count(), 0)
        self.kernel.approve(request)
        self.assertEqual(self.kernel.receipt_count(), 1)

    def test_kernel_hash_changes(self):
        h1 = self.kernel.kernel_hash()
        self.kernel.produce_failure_receipt("exec-1", "test", "EXEC_TEST_FAILED")
        h2 = self.kernel.kernel_hash()
        self.assertNotEqual(h1, h2)

    def test_reset(self):
        self.kernel.configure_allowlist(["python3"])
        self.kernel.create_request("exec-1", "test", "python3 -m pytest")
        self.kernel.reset()
        self.assertEqual(self.kernel.receipt_count(), 0)
        self.assertEqual(self.kernel.failure_count(), 0)

    def test_no_execution_performed(self):
        self.kernel.configure_allowlist(["python3"])
        request = self.kernel.create_request("exec-1", "test", "python3 -m pytest")
        receipt = self.kernel.approve(request)
        self.assertTrue(receipt.no_execution_performed)


class TestNoNetworkOrSubprocess(unittest.TestCase):
    """Verify no network/subprocess imports in kernel modules."""

    def test_no_forbidden_imports(self):
        kernel_dir = ROOT / "tools" / "local_execution_kernel"
        for py_file in kernel_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name} imports subprocess")
            self.assertNotIn("import socket", src, f"{py_file.name} imports socket")
            self.assertNotIn("import requests", src, f"{py_file.name} imports requests")
            self.assertNotIn("from urllib", src, f"{py_file.name} imports urllib")
            self.assertNotIn("import anthropic", src, f"{py_file.name} imports anthropic")
            self.assertNotIn("import openai", src, f"{py_file.name} imports openai")

    def test_no_env_reads(self):
        kernel_dir = ROOT / "tools" / "local_execution_kernel"
        for py_file in kernel_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("dotenv", src, f"{py_file.name} references dotenv")
            self.assertNotIn("os.environ", src, f"{py_file.name} reads os.environ")
            self.assertNotIn("os.getenv", src, f"{py_file.name} reads os.getenv")

    def test_no_subprocess_import(self):
        kernel_dir = ROOT / "tools" / "local_execution_kernel"
        for py_file in kernel_dir.glob("*.py"):
            with open(py_file) as f:
                src = f.read()
            self.assertNotIn("import subprocess", src, f"{py_file.name}")
            self.assertNotIn("from subprocess", src, f"{py_file.name}")


if __name__ == "__main__":
    unittest.main()
