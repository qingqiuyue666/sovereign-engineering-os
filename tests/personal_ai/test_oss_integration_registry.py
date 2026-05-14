import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.oss_integration_registry import (
    get_oss_integration_registry,
    list_oss_integrations,
    write_oss_integration_registry,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class OSSIntegrationRegistryTests(unittest.TestCase):
    def test_registry_records_active_optional_design_and_rejected_entries(self):
        registry = get_oss_integration_registry()
        statuses = {
            integration["status"]
            for integration in registry["integrations"]
        }

        self.assertEqual(registry["authority"], "non_authority")
        self.assertEqual(registry["execution_capability"], "not_introduced")
        self.assertIs(registry["dynamic_plugin_loading"], False)
        self.assertIs(registry["external_tool_control"], False)
        self.assertIs(registry["network_required"], False)
        self.assertIn("active", statuses)
        self.assertIn("optional", statuses)
        self.assertIn("design_only", statuses)
        self.assertIn("rejected", statuses)
        self.assertGreaterEqual(registry["counts"]["active"], 5)

    def test_list_returns_defensive_copy(self):
        first = list_oss_integrations()
        first[0]["status"] = "mutated"
        second = list_oss_integrations()

        self.assertNotEqual(second[0]["status"], "mutated")

    def test_writes_registry_json(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_path = Path(temp_dir.name) / "oss_integration_registry.json"

        registry = write_oss_integration_registry(output_path)
        written = read_json(output_path)

        self.assertEqual(written["registry_type"], registry["registry_type"])
        self.assertEqual(written["counts"], registry["counts"])
