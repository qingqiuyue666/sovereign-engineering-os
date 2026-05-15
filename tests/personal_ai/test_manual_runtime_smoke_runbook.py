import unittest
from pathlib import Path


class ManualRuntimeSmokeRunbookTests(unittest.TestCase):
    def read_runbook(self) -> str:
        path = Path("docs/usage/manual_runtime_smoke_runbook_v1.md")
        self.assertTrue(path.is_file())
        return path.read_text(encoding="utf-8")

    def test_runbook_exists_and_records_status(self):
        text = self.read_runbook()
        self.assertIn("MANUAL_RUNTIME_SMOKE_RUNBOOK_READY_FOR_LOCAL_TESTS", text)
        self.assertIn("Real Runtime Smoke Entry Ready", text)
        self.assertIn("Manual Runbook Documented", text)
        self.assertIn("Default Disabled", text)
        self.assertIn("Human Review Required", text)

    def test_global_batch_gate_is_documented(self):
        text = self.read_runbook()
        self.assertIn("allow_batch=True", text)
        self.assertIn("SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true", text)
        self.assertIn("per-runtime allow-gated", text)
        self.assertIn("artifact-gated", text)
        self.assertIn("explicit environment-gated", text)

    def test_model_provider_manual_smoke_boundaries_are_documented(self):
        text = self.read_runbook()
        for marker in (
            "Model Provider Manual Smoke",
            "OPENAI_API_KEY",
            "SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true",
            "SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true",
            "allow_model_smoke=True",
            "do not persist API key values",
            "do not log API key values",
            "do not persist raw provider responses",
            "do not allow model-output tool calls",
            "do not allow model-output file edits",
        ):
            self.assertIn(marker, text)

    def test_browser_manual_smoke_boundaries_are_documented(self):
        text = self.read_runbook()
        for marker in (
            "Browser / Playwright Loopback Manual Smoke",
            "allow_browser_smoke=True",
            "loopback target only",
            "isolated temporary profile only",
            "no external network",
            "no real user browser profile",
            "no persistent browser profile",
            "no login/signup/payment/account authority",
            "no raw DOM persistence",
            "no screenshot payload persistence by default",
        ):
            self.assertIn(marker, text)

    def test_comfyui_manual_smoke_boundaries_are_documented(self):
        text = self.read_runbook()
        for marker in (
            "ComfyUI Loopback Endpoint Manual Smoke",
            "http://127.0.0.1:8188",
            "allow_comfyui_smoke=True",
            "explicit ComfyUI transport",
            "no external downloads",
            "no arbitrary node execution",
            "no model downloads",
            "no raw image payload persistence",
        ):
            self.assertIn(marker, text)

    def test_blender_manual_smoke_boundaries_are_documented(self):
        text = self.read_runbook()
        for marker in (
            "Blender Runtime Manual Smoke",
            ".blend",
            ".glb",
            ".gltf",
            "allow_blender_smoke=True",
            "explicit Blender transport",
            "no subprocess authority",
            "no arbitrary Python authority",
            "no external network",
            "no source asset overwrite",
        ):
            self.assertIn(marker, text)

    def test_creative_tools_remain_handoff_only(self):
        text = self.read_runbook()
        for marker in (
            "Creative Tools Manual Boundary",
            "AE auto-control is not called",
            "Unreal auto-control is not called",
            "Houdini auto-control is not called",
            "ZBrush auto-control is not called",
            "handoff package or manifest",
        ):
            self.assertIn(marker, text)

    def test_normal_tests_must_not_call_real_runtime(self):
        text = self.read_runbook()
        for marker in (
            "Normal Test Rule",
            "fake or injected transports only",
            "call OpenAI or any real model API",
            "launch Playwright or any browser",
            "call a real ComfyUI endpoint",
            "launch Blender",
            "launch AE / Unreal / Houdini / ZBrush",
            "access external network",
            "read or persist real secrets",
        ):
            self.assertIn(marker, text)

    def test_runbook_mentions_required_verification_commands(self):
        text = self.read_runbook()
        for marker in (
            "python3 -m unittest tests.personal_ai.test_manual_runtime_smoke_runbook -v",
            "python3 -m unittest tests.personal_ai.test_post_real_runtime_smoke_main_health -v",
            "python3 -m unittest tests.personal_ai.test_real_runtime_smoke_execution_batch -v",
            "python3 -m unittest discover -s tests/personal_ai -v",
            "make ci",
            "git diff --check",
            "git status --short",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
