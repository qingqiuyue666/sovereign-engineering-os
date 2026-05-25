"""Tracer-bullet tests for tool manifest normalizer v1."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.runtime.tool_manifest_normalizer import (
    SUPPORTED_SOURCE_TYPES,
    normalize_tool_manifest_candidate,
)

POLICY_PATH = Path("governance/tools/tool_manifest_normalizer_v1.json")
SOURCE_PATH = Path("kernel/runtime/tool_manifest_normalizer.py")


def _candidate(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "source_type": "MCP_SERVER",
        "tool_name": "Fixture MCP Server",
        "declared_capabilities": ["read_only", "mcp_tool"],
        "declared_inputs": {"schema": "metadata"},
        "declared_outputs": {"schema": "metadata"},
        "filesystem_scope": "none",
        "network_scope": "metadata_only",
        "process_scope": "none",
        "credential_scope": "none",
        "provider_scope": "none",
        "dcc_scope": "none",
        "model_scope": "none",
        "browser_scope": "none",
        "plugin_scope": "none",
        "version": "1.0",
        "source_ref": "mcp://fixture/server",
        "notes": "metadata only",
    }
    fields.update(overrides)
    return fields


class ToolManifestNormalizerTests(unittest.TestCase):
    def test_policy_file_exists_and_records_boundary(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["policy_type"], "tool_manifest_normalizer_v1")
        self.assertTrue(policy["normalization_only"])
        self.assertFalse(policy["execution_allowed"])
        self.assertFalse(policy["subprocess_allowed"])
        self.assertFalse(policy["network_allowed"])
        self.assertFalse(policy["browser_allowed"])
        self.assertFalse(policy["provider_api_allowed"])
        self.assertFalse(policy["credential_storage_allowed"])
        self.assertFalse(policy["dcc_launch_allowed"])
        self.assertFalse(policy["comfyui_launch_allowed"])
        self.assertEqual(set(policy["supported_source_types"]), set(SUPPORTED_SOURCE_TYPES))

    def test_normalize_mcp_server_candidate(self):
        manifest = normalize_tool_manifest_candidate(_candidate())
        self.assertEqual(manifest.source_type, "MCP_SERVER")
        self.assertEqual(manifest.display_name, "Fixture MCP Server")
        self.assertIn("mcp_tool", manifest.declared_capabilities)
        self.assertFalse(manifest.direct_execution_allowed)
        self.assertFalse(manifest.runtime_integration_allowed)

    def test_normalize_cli_tool_candidate(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="CLI_TOOL",
                tool_name="Read Only CLI",
                declared_capabilities=["read_only"],
                network_scope="none",
                source_ref="local-cli-reference",
            )
        )
        self.assertEqual(manifest.source_type, "CLI_TOOL")
        self.assertEqual(manifest.tool_id, "tool.cli_tool.read-only-cli")

    def test_normalize_dcc_app_candidate(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="DCC_APP",
                tool_name="Houdini",
                declared_capabilities=["dcc_control"],
                dcc_scope="metadata_only",
                network_scope="none",
                source_ref="dcc://houdini",
            )
        )
        self.assertEqual(manifest.source_type, "DCC_APP")
        self.assertEqual(manifest.dcc_scope, "metadata_only")

    def test_normalize_comfyui_workflow_candidate(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="COMFYUI_WORKFLOW",
                tool_name="Image Workflow",
                declared_capabilities=["comfyui_execution", "model_execution"],
                model_scope="metadata_only",
                network_scope="none",
                source_ref="workflow://fixture",
            )
        )
        self.assertEqual(manifest.source_type, "COMFYUI_WORKFLOW")
        self.assertIn("model_execution", manifest.declared_capabilities)

    def test_normalize_github_repo_candidate(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="GITHUB_REPO",
                tool_name="Example Repo",
                declared_capabilities=["read_only"],
                network_scope="metadata_only",
                source_ref="https://github.com/example/project",
            )
        )
        self.assertEqual(manifest.source_type, "GITHUB_REPO")
        self.assertEqual(manifest.network_scope, "metadata_only")

    def test_normalize_wasm_plugin_candidate(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="WASM_PLUGIN",
                tool_name="Policy WASM",
                declared_capabilities=["plugin_execution"],
                plugin_scope="sandbox_strategy_defined",
                network_scope="none",
            )
        )
        self.assertEqual(manifest.source_type, "WASM_PLUGIN")
        self.assertEqual(manifest.plugin_scope, "sandbox_strategy_defined")

    def test_unknown_source_type_becomes_unknown_and_not_runtime_admitted(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(source_type="MAGIC_TOOL", network_scope="none")
        )
        self.assertEqual(manifest.source_type, "UNKNOWN")
        self.assertFalse(manifest.runtime_integration_allowed)
        self.assertFalse(manifest.direct_execution_allowed)

    def test_raw_command_rejected(self):
        with self.assertRaisesRegex(ValueError, "command"):
            normalize_tool_manifest_candidate(_candidate(COMMAND="rm -rf ."))

    def test_command_line_rejected(self):
        with self.assertRaisesRegex(ValueError, "command_line"):
            normalize_tool_manifest_candidate(_candidate(command_line="python script.py"))

    def test_argv_rejected(self):
        with self.assertRaisesRegex(ValueError, "argv"):
            normalize_tool_manifest_candidate(_candidate(declared_inputs={"argv": ["x"]}))

    def test_executable_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "executable_path"):
            normalize_tool_manifest_candidate(
                _candidate(declared_inputs={"executable_path": "/bin/tool"})
            )

    def test_credential_material_rejected(self):
        with self.assertRaisesRegex(ValueError, "api_key"):
            normalize_tool_manifest_candidate(_candidate(declared_outputs={"api_key": "x"}))

    def test_github_url_not_fetched(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="GITHUB_REPO",
                tool_name="Repo Candidate",
                declared_capabilities=["read_only"],
                network_scope="metadata_only",
                source_ref="https://github.com/example/not-fetched",
            )
        )
        self.assertEqual(manifest.source_type, "GITHUB_REPO")

    def test_mcp_reference_not_called(self):
        manifest = normalize_tool_manifest_candidate(_candidate(source_ref="mcp://not-called"))
        self.assertEqual(manifest.source_type, "MCP_SERVER")

    def test_dcc_app_not_launched(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(source_type="DCC_APP", tool_name="Blender", dcc_scope="metadata_only")
        )
        self.assertFalse(manifest.direct_execution_allowed)

    def test_comfyui_not_launched(self):
        manifest = normalize_tool_manifest_candidate(
            _candidate(
                source_type="COMFYUI_WORKFLOW",
                tool_name="Workflow",
                declared_capabilities=["comfyui_execution"],
                network_scope="none",
            )
        )
        self.assertFalse(manifest.runtime_integration_allowed)

    def test_content_hash_deterministic(self):
        first = normalize_tool_manifest_candidate(
            _candidate(), normalized_at="2026-05-25T00:00:00+00:00"
        )
        second = normalize_tool_manifest_candidate(
            _candidate(), normalized_at="2030-01-01T00:00:00+00:00"
        )
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.manifest_id, second.manifest_id)
        self.assertNotEqual(first.normalized_at, second.normalized_at)

    def test_no_subprocess_network_browser_or_provider_usage(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
