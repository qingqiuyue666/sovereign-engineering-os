"""Tests for Wave 6 AI-provider admission safety evidence."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.model_adapter_contract import build_model_provider_registry


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_TERMS = (
    "providers disabled by default",
    "secret-ref only",
    "no API key printing",
    "no `.env` reading by default",
    "request envelope",
    "response receipt",
    "network access receipt",
    "token budget ceiling",
    "context redaction",
    "prompt provenance",
    "model output artifact",
    "proposal-first",
    "patch requires human approval",
    "validation before PR",
    "deterministic mock provider only unless explicit future admission",
    "no direct AI execution",
)


class AIProviderAdmissionSafetyV1Tests(unittest.TestCase):
    def test_ai_admission_check_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/ai_admission_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("ai_admission_check_v1: PASS", completed.stdout)

    def test_required_ai_admission_terms_are_documented(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((REPO_ROOT / "docs" / "ai_admission").glob("*.md"))
        ).lower()
        for term in REQUIRED_TERMS:
            self.assertIn(term.lower(), combined)

    def test_provider_registry_keeps_live_providers_disabled(self) -> None:
        providers = {entry.provider_id: entry for entry in build_model_provider_registry()}
        self.assertTrue(providers["deterministic_mock"].admitted)
        self.assertTrue(providers["deterministic_mock"].enabled_by_default)
        self.assertFalse(providers["deterministic_mock"].live_provider_runtime)
        for provider in providers.values():
            self.assertFalse(provider.policy["network_allowed_by_default"])
            if provider.live_provider_runtime:
                self.assertFalse(provider.admitted)
                self.assertFalse(provider.enabled_by_default)
                self.assertFalse(provider.policy["real_provider_calls_allowed"])
                self.assertFalse(provider.policy["api_key_persistence_allowed"])
                self.assertFalse(provider.policy["api_key_logging_allowed"])

    def test_ai_admission_gate_is_wired(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/ai_admission_check_v1.py", makefile)
        self.assertIn("scripts/ai_admission_check_v1.py", workflow)
        self.assertIn("test-ai-provider-admission-safety", makefile)


if __name__ == "__main__":
    unittest.main()
