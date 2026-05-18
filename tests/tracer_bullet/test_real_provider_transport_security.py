"""Tracer-bullet tests for provider transport security enforcement."""

import unittest
import sys
import os

from tools.provider_transport.provider_no_network_enforcement import (
    NetworkEnforcementResult,
    enforce_no_network,
    FORBIDDEN_MODULES,
    scan_source_for_forbidden_imports,
)
from tools.provider_transport.provider_request_contract import (
    SECRET_MARKERS,
    ENV_MARKERS,
    RAW_PAYLOAD_FIELDS,
    validate_provider_request,
)


class NoNetworkEnforcementTests(unittest.TestCase):
    """Tests for no-network enforcement — runtime and source scanning."""

    def test_enforce_no_network_runs(self):
        result = enforce_no_network()
        self.assertIsInstance(result, NetworkEnforcementResult)

    def test_no_forbidden_modules_from_our_code(self):
        """Verify that provider_transport modules do not load forbidden modules.

        sys.modules may contain modules loaded by Python itself or the test runner
        (e.g., socket, http.client, subprocess are loaded by unittest internals).
        We check that our modules' source files don't import forbidden modules.
        """
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        provider_dir = os.path.join(root, "tools", "provider_transport")
        all_clean = True
        violations_found = []
        for fname in os.listdir(provider_dir):
            if fname.endswith(".py"):
                fpath = os.path.join(provider_dir, fname)
                with open(fpath) as f:
                    source = f.read()
                v = scan_source_for_forbidden_imports(source)
                if v:
                    all_clean = False
                    violations_found.append(f"{fname}: {v}")
        self.assertTrue(all_clean, f"Forbidden imports in source: {violations_found}")

    def test_active_forbidden_modules_is_tuple(self):
        result = enforce_no_network()
        self.assertIsInstance(result.active_forbidden_modules, tuple)

    def test_result_as_dict(self):
        result = enforce_no_network()
        d = result.as_dict()
        self.assertIn("valid", d)
        self.assertIn("active_forbidden_modules", d)
        self.assertIn("failures", d)

    def test_forbidden_modules_list_is_non_empty(self):
        """The forbidden modules list must cover key network modules."""
        self.assertIn("socket", FORBIDDEN_MODULES)
        self.assertIn("requests", FORBIDDEN_MODULES)
        self.assertIn("httpx", FORBIDDEN_MODULES)
        self.assertIn("urllib", FORBIDDEN_MODULES)
        self.assertIn("subprocess", FORBIDDEN_MODULES)
        self.assertIn("http.client", FORBIDDEN_MODULES)

    # --- source scanning ---

    def test_scan_clean_source_returns_empty(self):
        clean = """
def foo():
    x = 1 + 1
    return x
"""
        violations = scan_source_for_forbidden_imports(clean)
        self.assertEqual(len(violations), 0)

    def test_scan_detects_socket_import(self):
        dirty = "import socket\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(any("socket" in v for v in violations))

    def test_scan_detects_requests_import(self):
        dirty = "import requests\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(any("requests" in v for v in violations))

    def test_scan_detects_httpx_import(self):
        dirty = "from httpx import Client\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(any("httpx" in v for v in violations))

    def test_scan_detects_urllib_import(self):
        dirty = "import urllib.request\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(any("urllib" in v for v in violations))

    def test_scan_detects_subprocess_import(self):
        dirty = "import subprocess\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(any("subprocess" in v for v in violations))

    def test_scan_detects_http_client_import(self):
        dirty = "from http.client import HTTPConnection\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(any("http.client" in v for v in violations))

    def test_scan_ignores_comments(self):
        clean_with_comment = "# import socket for debugging\n"
        violations = scan_source_for_forbidden_imports(clean_with_comment)
        self.assertEqual(len(violations), 0)

    def test_scan_detects_multiple_violations(self):
        dirty = "import socket\nimport requests\nimport subprocess\n"
        violations = scan_source_for_forbidden_imports(dirty)
        self.assertTrue(len(violations) >= 3)

    def test_scan_returns_tuple(self):
        violations = scan_source_for_forbidden_imports("import socket")
        self.assertIsInstance(violations, tuple)


class NoForbiddenImportTests(unittest.TestCase):
    """Verify that provider_transport modules do NOT import forbidden modules."""

    def _read_module_source(self, module_rel_path):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_path = os.path.join(root, module_rel_path)
        if not os.path.exists(full_path):
            return ""
        with open(full_path, "r") as f:
            return f.read()

    def _check_module(self, module_rel_path):
        source = self._read_module_source(module_rel_path)
        violations = scan_source_for_forbidden_imports(source)
        return violations

    def test_no_socket_import_in_any_provider_module(self):
        for mod in [
            "tools/provider_transport/provider_transport_runtime.py",
            "tools/provider_transport/provider_adapter_registry.py",
            "tools/provider_transport/provider_request_contract.py",
            "tools/provider_transport/provider_transport_preflight.py",
            "tools/provider_transport/provider_dry_run_receipt.py",
            "tools/provider_transport/provider_failure_receipt.py",
            "tools/provider_transport/provider_capability_boundary.py",
            "tools/provider_transport/provider_evidence_binding.py",
            "tools/provider_transport/provider_rate_limit_budget.py",
            "tools/provider_transport/provider_no_network_enforcement.py",
        ]:
            violations = self._check_module(mod)
            if violations:
                self.fail(f"{mod} has forbidden imports: {violations}")

    def test_no_requests_import_in_any_provider_module(self):
        for mod in [
            "tools/provider_transport/provider_transport_runtime.py",
            "tools/provider_transport/provider_adapter_registry.py",
            "tools/provider_transport/provider_request_contract.py",
            "tools/provider_transport/provider_transport_preflight.py",
            "tools/provider_transport/provider_dry_run_receipt.py",
            "tools/provider_transport/provider_failure_receipt.py",
            "tools/provider_transport/provider_capability_boundary.py",
            "tools/provider_transport/provider_evidence_binding.py",
            "tools/provider_transport/provider_rate_limit_budget.py",
            "tools/provider_transport/provider_no_network_enforcement.py",
        ]:
            violations = self._check_module(mod)
            if violations:
                self.fail(f"{mod} has forbidden imports: {violations}")

    def test_no_forbidden_imports_in_init(self):
        source = self._read_module_source("tools/provider_transport/__init__.py")
        violations = scan_source_for_forbidden_imports(source)
        self.assertEqual(len(violations), 0, f"__init__.py has violations: {violations}")


class SecretMarkerTests(unittest.TestCase):
    """Tests that secret and .env markers are comprehensive."""

    def test_secret_markers_cover_key_patterns(self):
        self.assertIn("secret", SECRET_MARKERS)
        self.assertIn("api_key", SECRET_MARKERS)
        self.assertIn("password", SECRET_MARKERS)
        self.assertIn("credential", SECRET_MARKERS)
        self.assertIn("private_key", SECRET_MARKERS)
        self.assertIn("access_key", SECRET_MARKERS)
        self.assertIn("authorization", SECRET_MARKERS)

    def test_env_markers_cover_key_patterns(self):
        self.assertIn(".env", ENV_MARKERS)
        self.assertIn("dotenv", ENV_MARKERS)
        self.assertIn("environ", ENV_MARKERS)
        self.assertIn("getenv", ENV_MARKERS)

    def test_raw_payload_fields_comprehensive(self):
        self.assertIn("raw_payload", RAW_PAYLOAD_FIELDS)
        self.assertIn("raw_response", RAW_PAYLOAD_FIELDS)
        self.assertIn("raw_data", RAW_PAYLOAD_FIELDS)
        self.assertIn("payload", RAW_PAYLOAD_FIELDS)


class SecurityPolicyTests(unittest.TestCase):
    """Verify policy file is loadable and consistent."""

    def _policy_path(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root, "governance", "security", "real_provider_transport_runtime_policy_v1.json")

    def test_policy_file_exists(self):
        import json
        self.assertTrue(os.path.exists(self._policy_path()), f"Policy not found at {self._policy_path()}")

    def test_policy_is_valid_json(self):
        import json
        with open(self._policy_path()) as f:
            policy = json.load(f)
        self.assertEqual(policy["status"], "active")
        self.assertEqual(policy["policy_version"], "v1")

    def test_policy_forbids_network(self):
        import json
        with open(self._policy_path()) as f:
            policy = json.load(f)
        self.assertIn("network_execution", policy["forbidden"])
        self.assertIn("live_provider_calls", policy["forbidden"])

    def test_policy_requires_dry_run_only(self):
        import json
        with open(self._policy_path()) as f:
            policy = json.load(f)
        self.assertIn("dry_run_only_execution", policy["required_behaviors"])

    def test_policy_security_gates(self):
        import json
        with open(self._policy_path()) as f:
            policy = json.load(f)
        gates = policy["security_gates"]
        self.assertTrue(gates["no_network"])
        self.assertTrue(gates["no_live_provider"])
        self.assertTrue(gates["dry_run_only"])
        self.assertTrue(gates["no_secrets"])


class RegistryTests(unittest.TestCase):
    """Verify registry file is loadable and consistent."""

    def _registry_path(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root, "governance", "local_train", "real_provider_transport_runtime_registry_v1.json")

    def test_registry_file_exists(self):
        import json
        self.assertTrue(os.path.exists(self._registry_path()))

    def test_registry_is_valid_json(self):
        import json
        with open(self._registry_path()) as f:
            registry = json.load(f)
        self.assertEqual(registry["status"], "active")
        self.assertEqual(registry["registry_version"], "v1")

    def test_registry_lists_known_providers(self):
        import json
        with open(self._registry_path()) as f:
            registry = json.load(f)
        self.assertIn("mock-finance", registry["known_providers"])
        self.assertIn("mock-market-data", registry["known_providers"])

    def test_registry_lists_all_functions(self):
        import json
        with open(self._registry_path()) as f:
            registry = json.load(f)
        self.assertIn("validate_provider_request", registry["functions"])
        self.assertIn("execute_provider_transport", registry["functions"])
        self.assertIn("produce_dry_run_receipt", registry["functions"])
        self.assertIn("produce_failure_receipt", registry["functions"])

    def test_registry_spine_integration(self):
        import json
        with open(self._registry_path()) as f:
            registry = json.load(f)
        self.assertTrue(registry["spine_integration"]["linkable_to_runtime_spine"])
        self.assertTrue(registry["spine_integration"]["linkable_in_future_branch"])


class RunbookTests(unittest.TestCase):
    """Verify runbook is present and says the right things."""

    def _runbook_path(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root, "docs", "runbooks", "real_provider_transport_runtime_v1.md")

    def test_runbook_exists(self):
        self.assertTrue(os.path.exists(self._runbook_path()))

    def test_runbook_says_dry_run_local_validation_only(self):
        with open(self._runbook_path()) as f:
            content = f.read()
        self.assertIn("dry-run only", content.lower())
        self.assertIn("no network", content.lower())
        self.assertIn("no live provider", content.lower())
        self.assertIn("local", content.lower())
        self.assertIn("deterministic", content.lower())

    def test_runbook_no_overclaim(self):
        """Runbook must not claim live execution, production, or network capability."""
        with open(self._runbook_path()) as f:
            content = f.read().lower()
        self.assertNotIn("live execution", content)
        self.assertNotIn("production ready", content)
        self.assertNotIn("real-time", content)
        self.assertNotIn("cloud api", content)


if __name__ == "__main__":
    unittest.main()
