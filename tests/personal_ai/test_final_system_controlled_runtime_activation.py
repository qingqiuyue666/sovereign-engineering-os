import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.blender_activation_package import (
    build_blender_activation_package,
    validate_blender_activation_package,
)
from kernel.personal_ai.adapters.browser_local_smoke import (
    build_browser_local_smoke_plan,
    validate_browser_local_smoke_plan,
)
from kernel.personal_ai.adapters.comfyui_activation_package import (
    build_comfyui_activation_package,
    validate_comfyui_activation_package,
)
from kernel.personal_ai.adapters.model_provider_activation_package import (
    build_model_provider_activation_package,
)
from kernel.personal_ai.adapters.model_provider_live_smoke import (
    build_disabled_model_provider_live_smoke_plan,
    validate_disabled_model_provider_live_smoke_plan,
)


class FinalSystemControlledRuntimeActivationTests(unittest.TestCase):
    def make_output_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_json(self, path: Path, payload: dict) -> Path:
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_model_activation_and_disabled_live_smoke_remain_non_executing(self):
        root = self.make_output_dir()
        activation_dir = root / "activation"
        smoke_dir = root / "smoke"
        activation_dir.mkdir()
        smoke_dir.mkdir()

        activation = build_model_provider_activation_package(
            activation_dir,
            provider_id="openai",
            schema_name="job_route_classification_v1",
            reviewer_id="reviewer-1",
            environ={"OPENAI_API_KEY": "secret-value-not-persisted"},
        )
        smoke = build_disabled_model_provider_live_smoke_plan(
            activation_dir,
            smoke_dir,
            provider_id="openai",
            api_key_env_var="OPENAI_API_KEY",
            environ={"OPENAI_API_KEY": "secret-value-not-persisted"},
        )

        self.assertTrue(activation.complete)
        self.assertTrue(smoke.complete)
        self.assertFalse(smoke.live_provider_called)
        self.assertFalse(smoke.network_used)
        smoke_plan_text = smoke.plan_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-value-not-persisted", smoke_plan_text)
        smoke_plan = json.loads(smoke_plan_text)
        self.assertFalse(smoke_plan["live_smoke_enabled"])
        self.assertFalse(smoke_plan["network_call_allowed"])
        self.assertFalse(smoke_plan["live_provider_call_performed"])
        validation = validate_disabled_model_provider_live_smoke_plan(smoke.plan_path)
        self.assertTrue(validation["complete"])

    def test_browser_local_smoke_rejects_external_and_sensitive_actions(self):
        output_dir = self.make_output_dir()
        actions_path = self.write_json(
            output_dir / "actions.json",
            {"actions": [{"action": "open", "selector": "body"}]},
        )
        result = build_browser_local_smoke_plan(
            actions_path,
            output_dir,
            target_url="http://127.0.0.1:8080",
        )
        self.assertTrue(result.complete)
        plan = json.loads(result.plan_path.read_text(encoding="utf-8"))
        self.assertTrue(plan["loopback_only"])
        self.assertFalse(plan["real_browser_called"])
        self.assertFalse(plan["external_network_used"])
        self.assertTrue(validate_browser_local_smoke_plan(result.plan_path)["complete"])

        bad_output = self.make_output_dir()
        bad_actions = self.write_json(
            bad_output / "bad_actions.json",
            {"actions": [{"action": "open", "text": "login password"}]},
        )
        with self.assertRaisesRegex(ValueError, "forbidden intent"):
            build_browser_local_smoke_plan(
                bad_actions,
                bad_output,
                target_url="http://127.0.0.1:8080",
            )
        with self.assertRaisesRegex(ValueError, "loopback"):
            build_browser_local_smoke_plan(
                actions_path,
                self.make_output_dir(),
                target_url="https://example.com",
            )

    def test_comfyui_activation_package_remains_dry_run_only(self):
        output_dir = self.make_output_dir()
        workflow_path = self.write_json(
            output_dir / "workflow.json",
            {
                "nodes": [
                    {"id": "1", "type": "LoadImage"},
                    {"id": "2", "type": "KSampler"},
                ]
            },
        )
        result = build_comfyui_activation_package(workflow_path, output_dir)
        self.assertTrue(result.complete)
        self.assertFalse(result.real_endpoint_called)
        self.assertFalse(result.network_used)
        validation = validate_comfyui_activation_package(output_dir)
        self.assertTrue(validation["complete"])
        plan = json.loads(result.activation_plan_path.read_text(encoding="utf-8"))
        self.assertFalse(plan["activation_enabled"])
        self.assertFalse(plan["real_comfyui_endpoint_called"])
        self.assertFalse(plan["network_call_allowed"])
        self.assertFalse(plan["external_downloads_allowed"])
        self.assertFalse(plan["arbitrary_node_execution_allowed"])

    def test_blender_activation_package_remains_dry_run_only(self):
        output_dir = self.make_output_dir()
        scene_path = output_dir / "scene.blend"
        scene_path.write_bytes(b"fake-blender-scene")
        operation_plan_path = self.write_json(
            output_dir / "operations.json",
            {
                "operations": [
                    {"operation": "add_camera"},
                    {"operation": "render_preview"},
                ]
            },
        )
        result = build_blender_activation_package(
            scene_path,
            operation_plan_path,
            output_dir,
        )
        self.assertTrue(result.complete)
        self.assertFalse(result.real_blender_called)
        self.assertFalse(result.subprocess_used)
        validation = validate_blender_activation_package(output_dir)
        self.assertTrue(validation["complete"])
        plan = json.loads(result.activation_plan_path.read_text(encoding="utf-8"))
        self.assertFalse(plan["activation_enabled"])
        self.assertFalse(plan["real_blender_called"])
        self.assertFalse(plan["subprocess_allowed"])
        self.assertFalse(plan["arbitrary_python_allowed"])

    def test_tampering_activation_plans_is_detected(self):
        output_dir = self.make_output_dir()
        actions_path = self.write_json(
            output_dir / "actions.json",
            {"actions": [{"action": "open"}]},
        )
        result = build_browser_local_smoke_plan(
            actions_path,
            output_dir,
            target_url="http://localhost:8000",
        )
        plan = json.loads(result.plan_path.read_text(encoding="utf-8"))
        plan["external_network_used"] = True
        result.plan_path.write_text(json.dumps(plan), encoding="utf-8")
        validation = validate_browser_local_smoke_plan(result.plan_path)
        self.assertFalse(validation["complete"])
        self.assertIn("external_network_used_must_be_false", validation["failures"])


if __name__ == "__main__":
    unittest.main()
