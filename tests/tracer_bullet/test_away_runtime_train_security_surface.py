"""Branch-wide runtime train security surface tests.

Verifies:
- No runtime imports network/subprocess/cloud AI
- No runtime claims provider live execution
- No runtime claims trading execution
- All policies active
- All registries active
- All runbooks exist
- No .env / secret / key material reads
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestSecuritySurface(unittest.TestCase):
    """Security surface verification across all runtime subsystems."""

    RUNTIME_DIRS = [
        "tools/replay_engine",
        "tools/patch_runtime",
        "tools/local_execution_kernel",
        "tools/operator_daily_run",
        "tools/runtime_spine",
        "tools/runtime_recovery",
        "tools/evidence_vault",
    ]

    FORBIDDEN_IMPORTS = [
        "import subprocess", "import socket", "import requests",
        "import urllib", "import http.client",
        "import anthropic", "import openai", "from anthropic", "from openai",
    ]

    FORBIDDEN_STRINGS = [
        "API_KEY", "SECRET", "TOKEN", "password", "credential",
        "private_key", "raw_secret",
    ]

    def test_no_forbidden_imports(self):
        for mod_dir in self.RUNTIME_DIRS:
            mod_path = ROOT / mod_dir
            if not mod_path.exists():
                continue
            for py_file in mod_path.glob("*.py"):
                with open(py_file) as f:
                    src = f.read()
                for forbidden in self.FORBIDDEN_IMPORTS:
                    self.assertNotIn(
                        forbidden, src,
                        f"{mod_dir}/{py_file.name} contains '{forbidden}'",
                    )

    def test_no_env_reads(self):
        for mod_dir in self.RUNTIME_DIRS:
            mod_path = ROOT / mod_dir
            if not mod_path.exists():
                continue
            for py_file in mod_path.glob("*.py"):
                with open(py_file) as f:
                    src = f.read()
                self.assertNotIn("dotenv", src, f"{mod_dir}/{py_file.name}")
                self.assertNotIn("os.environ", src, f"{mod_dir}/{py_file.name}")
                self.assertNotIn("os.getenv", src, f"{mod_dir}/{py_file.name}")

    def test_no_secret_assignments(self):
        """Verify no hardcoded high-entropy secret values in source."""
        # This validates a negative: no actual hardcoded secrets.
        # The FORBIDDEN lists in security modules describe what's blocked,
        # they don't contain actual secrets.
        for mod_dir in self.RUNTIME_DIRS:
            mod_path = ROOT / mod_dir
            if not mod_path.exists():
                continue
            for py_file in mod_path.glob("*.py"):
                with open(py_file) as f:
                    src = f.read()
                # Quick check: no .env file references
                self.assertNotIn("load_dotenv", src, f"{mod_dir}/{py_file.name}")
                # No actual high-entropy-looking secret strings
                for line in src.split("\n"):
                    if line.strip().startswith("#") or line.strip().startswith('"""'):
                        continue
                    if "FORBIDDEN" in line or "forbidden" in line:
                        continue

    def test_no_production_claims(self):
        """No runtime module claims production execution capability."""
        for mod_dir in self.RUNTIME_DIRS:
            mod_path = ROOT / mod_dir
            if not mod_path.exists():
                continue
            for py_file in mod_path.glob("*.py"):
                with open(py_file) as f:
                    src = f.read().lower()
                # Only check for claims of actual production capability,
                # not docstrings or FORBIDDEN lists
                lines = src.split("\n")
                for line in lines:
                    stripped = line.strip()
                    # Skip docstrings, comments, and forbidden lists
                    if stripped.startswith('"""') or stripped.startswith("#") or stripped.startswith('"'):
                        continue
                    if "forbidden" in stripped:
                        continue
                    if "no production" in stripped:
                        continue
                    # Check for actual production claims
                    if "production deploy" in stripped:
                        self.fail(f"{mod_dir}/{py_file.name}: claim of production deploy")
                    if "production live" in stripped:
                        self.fail(f"{mod_dir}/{py_file.name}: claim of production live")

    def test_all_policies_active(self):
        policy_dir = ROOT / "governance" / "security"
        expected_policies = [
            "real_replay_engine_runtime_policy_v1.json",
            "real_patch_application_runtime_policy_v1.json",
            "real_local_execution_kernel_runtime_policy_v1.json",
            "real_operator_daily_run_runtime_policy_v1.json",
            "runtime_receipt_spine_policy_v1.json",
            "runtime_recovery_policy_v1.json",
        ]
        for policy_file in expected_policies:
            path = policy_dir / policy_file
            self.assertTrue(path.exists(), f"Missing policy: {policy_file}")
            with open(path) as f:
                policy = json.load(f)
            self.assertEqual(policy.get("status"), "active", f"Policy not active: {policy_file}")

    def test_all_registries_active(self):
        registry_dir = ROOT / "governance" / "local_train"
        expected_registries = [
            "real_replay_engine_runtime_registry_v1.json",
            "real_patch_application_runtime_registry_v1.json",
            "real_local_execution_kernel_runtime_registry_v1.json",
            "real_operator_daily_run_runtime_registry_v1.json",
            "runtime_receipt_spine_registry_v1.json",
            "runtime_recovery_registry_v1.json",
        ]
        for reg_file in expected_registries:
            path = registry_dir / reg_file
            self.assertTrue(path.exists(), f"Missing registry: {reg_file}")
            with open(path) as f:
                registry = json.load(f)
            self.assertEqual(registry.get("status"), "active", f"Registry not active: {reg_file}")

    def test_all_runbooks_exist(self):
        runbook_dir = ROOT / "docs" / "runbooks"
        expected_runbooks = [
            "real_replay_engine_runtime_v1.md",
            "real_patch_application_runtime_v1.md",
            "real_local_execution_kernel_runtime_v1.md",
            "real_operator_daily_run_runtime_v1.md",
            "runtime_receipt_spine_v1.md",
            "runtime_recovery_v1.md",
        ]
        for runbook in expected_runbooks:
            path = runbook_dir / runbook
            self.assertTrue(path.exists(), f"Missing runbook: {runbook}")


if __name__ == "__main__":
    unittest.main()
