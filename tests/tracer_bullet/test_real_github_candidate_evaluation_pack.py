import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from kernel.capabilities.github_capability_intake_packet import (
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
    build_github_capability_intake_packet,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_DIR = REPO_ROOT / "docs" / "capability_candidates" / "github_real_candidates_v1"
MATRIX_PATH = PACK_DIR / "candidate_selection_matrix.json"

CANDIDATE_FILES = (
    (
        "github-candidate-microsoft-playwright-v1",
        PACK_DIR / "microsoft_playwright_candidate_manifest.json",
    ),
    (
        "github-candidate-ultrafunkamsterdam-nodriver-v1",
        PACK_DIR / "ultrafunkamsterdam_nodriver_candidate_manifest.json",
    ),
    (
        "github-candidate-ahujasid-blender-mcp-v1",
        PACK_DIR / "ahujasid_blender_mcp_candidate_manifest.json",
    ),
)

PACK_JSON_FILES = tuple(path for _candidate_id, path in CANDIDATE_FILES) + (
    MATRIX_PATH,
)

INTAKE_GENERATED_RELATIVE_PATHS = {
    GITHUB_CAPABILITY_INTAKE_PACKET_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
}

INTAKE_FALSE_FIELDS = (
    "adapter_generation_allowed",
    "auto_adoption_allowed",
    "third_party_code_execution_allowed",
    "dependency_installation_allowed",
    "network_fetch_allowed",
    "clone_allowed",
    "model_api_allowed",
    "secret_access_allowed",
    "file_system_write_to_candidate_repo_allowed",
)

MATRIX_FALSE_FIELDS = (
    "network_access_performed",
    "github_network_search_performed_by_code",
    "git_clone_performed",
    "git_command_performed",
    "dependency_installation_performed",
    "third_party_code_execution_performed",
    "candidate_code_imported",
    "adapter_generated",
    "adapter_registered",
    "auto_adoption_performed",
    "autonomous_execution_performed",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fail_if_called(*_args, **_kwargs):
    raise AssertionError("real candidate pack tests must not perform external actions")


class RealGitHubCandidateEvaluationPackTests(unittest.TestCase):
    def build_packets(self):
        results = {}
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)

        with ExitStack() as stack:
            for target in (
                "subprocess.run",
                "subprocess.call",
                "subprocess.check_call",
                "subprocess.check_output",
                "subprocess.Popen",
                "os.system",
                "os.popen",
                "socket.create_connection",
            ):
                stack.enter_context(patch(target, side_effect=fail_if_called))

            for candidate_id, manifest_path in CANDIDATE_FILES:
                output_dir = root / candidate_id
                output_dir.mkdir()
                result = build_github_capability_intake_packet(
                    manifest_path,
                    output_dir,
                    f"intake-{candidate_id}",
                    project_id="real-github-candidate-evaluation-pack-v1",
                    reviewer_id="tracer-bullet",
                    operator_notes="real candidate metadata intake only",
                )
                results[candidate_id] = result

        return results

    def test_all_three_candidate_manifest_files_exist(self):
        self.assertEqual(len(CANDIDATE_FILES), 3)
        for _candidate_id, manifest_path in CANDIDATE_FILES:
            self.assertTrue(manifest_path.exists(), manifest_path)

    def test_each_candidate_manifest_builds_ready_intake_packet_without_repo_dir(self):
        results = self.build_packets()

        for candidate_id, result in results.items():
            self.assertTrue(result.complete, candidate_id)
            self.assertEqual(
                result.intake_status,
                "github_capability_intake_packet_ready",
            )
            packet = read_json(result.packet_path)
            self.assertEqual(
                packet["intake_status"],
                "github_capability_intake_packet_ready",
            )
            self.assertEqual(packet["candidate_id"], candidate_id)
            self.assertFalse(packet["candidate_repo_dir_provided"])
            for field_name in INTAKE_FALSE_FIELDS:
                self.assertFalse(packet[field_name], field_name)
            self.assertTrue(packet["license_review_required"])
            self.assertTrue(packet["security_review_required"])
            self.assertTrue(packet["sandbox_review_required"])

    def test_matrix_contains_expected_selection_decisions(self):
        matrix = read_json(MATRIX_PATH)
        candidates = matrix["candidates"]
        by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
        selected = [
            candidate
            for candidate in candidates
            if candidate["selected_for_first_sandbox_smoke"]
        ]

        self.assertEqual(matrix["matrix_type"], "real_github_candidate_selection_matrix_v1")
        self.assertEqual(len(candidates), 3)
        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["candidate_id"],
            "github-candidate-microsoft-playwright-v1",
        )
        self.assertEqual(
            by_id["github-candidate-ultrafunkamsterdam-nodriver-v1"]["decision"],
            "hold_high_risk_reference_only",
        )
        self.assertFalse(
            by_id["github-candidate-ultrafunkamsterdam-nodriver-v1"][
                "selected_for_first_sandbox_smoke"
            ]
        )
        self.assertEqual(
            by_id["github-candidate-ahujasid-blender-mcp-v1"]["decision"],
            "hold_for_later_creative_sandbox",
        )
        self.assertFalse(
            by_id["github-candidate-ahujasid-blender-mcp-v1"][
                "selected_for_first_sandbox_smoke"
            ]
        )

    def test_matrix_boundary_fields_remain_false(self):
        matrix = read_json(MATRIX_PATH)

        for field_name in MATRIX_FALSE_FIELDS:
            self.assertFalse(matrix[field_name], field_name)
        for candidate in matrix["candidates"]:
            self.assertTrue(candidate["license_review_required"])
            self.assertTrue(candidate["security_review_required"])
            self.assertTrue(candidate["sandbox_review_required"])
            self.assertFalse(candidate["adapter_generation_allowed"])

    def test_artifact_indexes_include_only_generated_intake_artifacts(self):
        results = self.build_packets()

        for candidate_id, result in results.items():
            artifact_index = read_json(result.artifact_index_path)
            relative_paths = {
                entry["relative_path"] for entry in artifact_index["entries"]
            }
            artifact_index_manifest = read_json(result.artifact_index_manifest_path)

            self.assertEqual(relative_paths, INTAKE_GENERATED_RELATIVE_PATHS)
            self.assertEqual(artifact_index["indexed_artifacts"], 4)
            self.assertFalse(
                artifact_index["candidate_repo_evidence_files_indexed"],
                candidate_id,
            )
            self.assertEqual(
                set(artifact_index_manifest["indexed_relative_paths"]),
                INTAKE_GENERATED_RELATIVE_PATHS,
            )

    def test_pack_json_files_are_sorted_deterministic_json(self):
        for path in PACK_JSON_FILES:
            payload = read_json(path)
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                path.as_posix(),
            )

    def test_tests_do_not_import_candidate_code_or_external_network_clients(self):
        source = Path(__file__).read_text(encoding="utf-8")

        self.assertNotIn("requ" + "ests", source)
        self.assertNotIn("htt" + "px", source)
        self.assertNotIn("url" + "lib", source)
        self.assertNotIn("git " + "clone", source)
        self.assertNotIn("pip " + "install", source)
        self.assertNotIn("npm " + "install", source)


if __name__ == "__main__":
    unittest.main()
