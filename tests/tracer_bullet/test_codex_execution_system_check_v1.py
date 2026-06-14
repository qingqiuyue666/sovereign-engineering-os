import unittest
from pathlib import Path

from scripts import codex_execution_system_check_v1 as check


class CodexExecutionSystemCheckTests(unittest.TestCase):
    def test_text_safety_rejects_local_paths_and_overclaims(self):
        errors: list[str] = []

        check._check_text_safety(
            {
                Path("reports/checkpoints/sample.md"): (
                    "This text references /Users/example and says "
                    "production ready achieved."
                )
            },
            errors,
        )

        self.assertTrue(
            any("contains local path marker" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("contains forbidden positive claim" in error for error in errors),
            errors,
        )

    def test_eleven_core_delivery_requires_structured_evidence(self):
        errors: list[str] = []

        check._check_eleven_core_delivery(
            {
                Path("CODEX_REAL_TASK_THROUGHPUT_LAYER.md"): "# Missing sections\n",
                Path("reports/checkpoints/whole-content-completion-checklist-v1.md"): (
                    "Section 0 PASS\nSection 1 PASS\n"
                ),
            },
            errors,
        )

        self.assertTrue(any("Connected Loop" in error for error in errors), errors)
        self.assertTrue(any("Section 9" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
