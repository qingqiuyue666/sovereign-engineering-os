import copy
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.tool_intake_register import (
    load_runtime_tool_admission_register,
    validate_runtime_tool_admission_register,
    validate_runtime_tool_admission_register_file,
)


REGISTER_PATH = Path("governance/integration/runtime_tool_admission_register.yaml")


def load_register():
    return load_runtime_tool_admission_register(REGISTER_PATH)


class ToolIntakeRegisterTests(unittest.TestCase):
    def test_default_register_validates_without_importing_candidate_tools(self):
        result = validate_runtime_tool_admission_register_file(REGISTER_PATH)

        self.assertTrue(result.accepted)
        self.assertGreaterEqual(result.entry_count, 30)
        self.assertEqual(result.failures, ())
        self.assertEqual(result.admitted_projects, ("openpyxl",))

    def test_register_covers_required_capability_categories(self):
        register = load_register()
        categories = {entry["capability_category"] for entry in register["entries"]}

        self.assertEqual(
            categories,
            {
                "agent_runtime_reference",
                "browser",
                "creative",
                "model_structured_output",
                "observability_evaluation",
                "orchestration",
                "validation_provenance",
                "xlsx_local_data",
            },
        )

    def test_register_records_all_named_candidate_families(self):
        register = load_register()
        project_ids = {entry["project_id"] for entry in register["entries"]}

        for project_id in (
            "openpyxl",
            "xlsxwriter",
            "libreoffice_headless",
            "pandas",
            "duckdb",
            "polars",
            "playwright",
            "browser_use",
            "selenium",
            "openai_structured_outputs",
            "openhands",
            "swe_agent",
            "autogpt",
            "crewai",
            "autogen",
            "temporal",
            "prefect",
            "dagster",
            "opentelemetry",
            "phoenix_arize",
            "langsmith",
            "comfyui",
            "blender_python_mcp",
            "unreal_python",
            "houdini_hom_hython_hda",
            "after_effects_extendscript_uxp_aerender",
            "zbrush_handoff",
            "jsonschema",
            "pydantic",
            "cyclonedx",
            "syft",
            "in_toto",
        ):
            self.assertIn(project_id, project_ids)

    def test_rejects_missing_required_fields(self):
        register = load_register()
        broken = {"register_type": register["register_type"], "entries": [{}]}

        result = validate_runtime_tool_admission_register(broken)

        self.assertFalse(result.accepted)
        self.assertIn("entry_0_missing_required_fields", result.failures)

    def test_rejects_unknown_enum_values(self):
        register = load_register()
        broken = _single_entry_register(register)
        broken["entries"][0]["adapter_mode"] = "unbounded"

        result = validate_runtime_tool_admission_register(broken)

        self.assertFalse(result.accepted)
        self.assertIn("entry_0_unknown_adapter_mode", result.failures)

    def test_rejects_missing_required_controls(self):
        register = load_register()
        broken = _single_entry_register(register)
        broken["entries"][0]["required_controls"] = ["human_approval"]

        result = validate_runtime_tool_admission_register(broken)

        self.assertFalse(result.accepted)
        self.assertIn("entry_0_missing_required_controls", result.failures)

    def test_rejects_direct_source_vendoring_posture(self):
        register = load_register()
        broken = _single_entry_register(register)
        broken["entries"][0]["required_controls"].append("direct_source_vendoring")

        result = validate_runtime_tool_admission_register(broken)

        self.assertFalse(result.accepted)
        self.assertIn("entry_0_direct_source_vendoring_posture", result.failures)

    def test_rejects_unrestricted_runtime_admission(self):
        register = load_register()
        broken = _single_entry_register(register)
        broken["entries"][0]["required_controls"].append("future_admission_required")

        result = validate_runtime_tool_admission_register(broken)

        self.assertFalse(result.accepted)
        self.assertIn("entry_0_unrestricted_runtime_admission", result.failures)

    def test_rejects_network_destructive_and_credential_executable_admission(self):
        register = load_register()
        broken = _single_entry_register(register)
        entry = broken["entries"][0]
        entry["network_required"] = True
        entry["credential_risk"] = "required"
        entry["destructive_action_risk"] = "possible"

        result = validate_runtime_tool_admission_register(broken)

        self.assertFalse(result.accepted)
        self.assertIn("entry_0_network_required_executable_admission", result.failures)
        self.assertIn("entry_0_credential_risk_executable_admission", result.failures)
        self.assertIn("entry_0_destructive_risk_executable_admission", result.failures)

    def test_loader_rejects_non_json_compatible_yaml(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        register_path = Path(temp_dir.name) / "runtime_tool_admission_register.yaml"
        register_path.write_text("entries:\n  - project_id: bad\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            load_runtime_tool_admission_register(register_path)


def _single_entry_register(register):
    return {
        "register_type": register["register_type"],
        "entries": [copy.deepcopy(register["entries"][0])],
    }


if __name__ == "__main__":
    unittest.main()
