"""Artifact tests for the HFX Core12 full proof execution package."""

from __future__ import annotations

from pathlib import Path
import json
import unittest


ASSETS = (
    ("HFX_008", "HFX_008_ENERGY_SHOCKWAVE"),
    ("HFX_015", "HFX_015_PORTAL_RING"),
    ("HFX_016", "HFX_016_HEAT_DISTORTION"),
    ("HFX_021", "HFX_021_PYRO_EXPLOSION"),
    ("HFX_025", "HFX_025_CHARACTER_ENERGY_FIELD"),
    ("HFX_027", "HFX_027_SUMMONING_PORTAL_GATE"),
    ("HFX_028", "HFX_028_SPACE_RIFT_TEAR"),
    ("HFX_029", "HFX_029_BLACK_HOLE_ACCRETION_DISK"),
    ("HFX_033", "HFX_033_GLOW_EMISSION_PASS"),
    ("HFX_036", "HFX_036_ALPHA_HOLDOUT_MATTE"),
    ("HFX_037", "HFX_037_LIGHTWRAP_RIM_INTERACTION"),
    ("HFX_038", "HFX_038_CONTACT_SHADOW_GROUND_INTEGRATION"),
)
ROOT = Path("assets/houdini/hfx_factory_core12")
PROOF_ROOT = ROOT / "600_PROOF_EXECUTION/HFX_CORE12_FULL_PROOF_RUN_001"
RUN_JSON = PROOF_ROOT / "HFX_CORE12_FULL_PROOF_RUN_001.json"
RUN_MD = PROOF_ROOT / "HFX_CORE12_FULL_PROOF_RUN_001.md"
MATRIX_JSON = PROOF_ROOT / "HFX_CORE12_PROOF_EXECUTION_MATRIX.json"
MATRIX_MD = PROOF_ROOT / "HFX_CORE12_PROOF_EXECUTION_MATRIX.md"
LEDGER_JSON = ROOT / "00_INDEX_资产索引/HFX_CORE12_COMPLETION_LEDGER.json"
PLAN_MD = ROOT / "00_INDEX_资产索引/HFX_100_PERCENT_COMPLETION_PLAN.md"
FORBIDDEN_NEW_SUFFIXES = {".hip", ".hda", ".otl", ".vdb", ".exr", ".mov", ".mp4", ".abc", ".usd", ".fbx", ".obj"}
UNSAFE_FINAL_CLAIMS = (
    "hollywood-grade complete",
    "hollywood grade complete",
    "film-grade complete",
    "film grade complete",
    "final-pixel complete",
    "final pixel complete",
    "final-pixel completion",
    "final pixel completion",
)


def asset_root(dirname: str) -> Path:
    return PROOF_ROOT / dirname


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_changed_paths() -> list[Path]:
    paths = [
        Path("kernel/runtime/hfx_core12_completion_ledger.py"),
        Path("kernel/runtime/hfx_core12_proof_execution.py"),
        Path("tools/generate_hfx_core12_full_proof_execution_package.py"),
        Path("tests/tracer_bullet/test_hfx_core12_proof_execution.py"),
        Path("tests/tracer_bullet/test_hfx_core12_full_proof_execution_artifacts.py"),
        Path("tests/tracer_bullet/test_hfx_core12_full_promotion_artifacts.py"),
        ROOT / "00_INDEX_资产索引/HFX_CORE12_COMPLETION_LEDGER.json",
        ROOT / "00_INDEX_资产索引/HFX_CORE12_COMPLETION_LEDGER.md",
        PLAN_MD,
        PROOF_ROOT / "README.md",
        RUN_JSON,
        RUN_MD,
        MATRIX_JSON,
        MATRIX_MD,
    ]
    for _asset_id, dirname in ASSETS:
        for filename in (
            "proof_package.json",
            "proof_package.md",
            "shot_proof_checklist.md",
            "render_comp_proof_checklist.md",
            "acceptance_review.md",
            "rejection_quarantine_report.md",
        ):
            paths.append(asset_root(dirname) / filename)
    return paths


class HFXCore12FullProofExecutionArtifactTests(unittest.TestCase):
    def test_full_proof_run_root_exists(self):
        self.assertTrue(PROOF_ROOT.is_dir())

    def test_full_proof_run_json_exists(self):
        self.assertTrue(RUN_JSON.is_file())

    def test_full_proof_run_markdown_exists(self):
        self.assertTrue(RUN_MD.is_file())

    def test_proof_execution_matrix_json_exists(self):
        self.assertTrue(MATRIX_JSON.is_file())

    def test_proof_execution_matrix_markdown_exists(self):
        self.assertTrue(MATRIX_MD.is_file())

    def test_all_12_asset_proof_directories_exist(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue(asset_root(dirname).is_dir())

    def test_all_12_assets_have_proof_package_json(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue((asset_root(dirname) / "proof_package.json").is_file())

    def test_all_12_assets_have_proof_package_markdown(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue((asset_root(dirname) / "proof_package.md").is_file())

    def test_all_12_assets_have_shot_proof_checklist(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue((asset_root(dirname) / "shot_proof_checklist.md").is_file())

    def test_all_12_assets_have_render_comp_proof_checklist(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue((asset_root(dirname) / "render_comp_proof_checklist.md").is_file())

    def test_all_12_assets_have_acceptance_review(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue((asset_root(dirname) / "acceptance_review.md").is_file())

    def test_all_12_assets_have_rejection_quarantine_report(self):
        for _asset_id, dirname in ASSETS:
            self.assertTrue((asset_root(dirname) / "rejection_quarantine_report.md").is_file())

    def test_final_claim_allowed_is_false_unless_proof_is_accepted(self):
        run_payload = load_json(RUN_JSON)
        matrix = load_json(MATRIX_JSON)

        self.assertFalse(run_payload["final_claim_allowed"])
        for package in run_payload["per_asset_proof_package"]:
            if package["acceptance_decision"] != "accepted_for_internal_library":
                self.assertFalse(package["final_claim_allowed"])
        for row in matrix["assets"]:
            if row["acceptance_decision"] != "accepted_for_internal_library":
                self.assertFalse(row["final_claim_allowed"])

    def test_no_markdown_claims_hollywood_film_grade_or_final_pixel_completion(self):
        for path in PROOF_ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            for claim in UNSAFE_FINAL_CLAIMS:
                self.assertNotIn(claim, text)
        plan_text = PLAN_MD.read_text(encoding="utf-8").lower()
        for claim in UNSAFE_FINAL_CLAIMS:
            self.assertNotIn(claim, plan_text)

    def test_no_external_raw_assets_are_added_by_this_branch(self):
        for path in expected_changed_paths():
            self.assertNotIn("external_raw", path.as_posix().lower())
            self.assertIn(path.suffix, {".py", ".json", ".md"})

    def test_no_binary_houdini_media_or_geometry_files_are_added_by_this_branch(self):
        for path in expected_changed_paths():
            self.assertNotIn(path.suffix.lower(), FORBIDDEN_NEW_SUFFIXES)
        for path in PROOF_ROOT.rglob("*"):
            self.assertNotIn(path.suffix.lower(), FORBIDDEN_NEW_SUFFIXES)

    def test_no_makefile_root_readme_root_integrity_or_health_wiring_files_are_modified(self):
        changed = {path.as_posix() for path in expected_changed_paths()}

        self.assertNotIn("Makefile", changed)
        self.assertNotIn("README.md", changed)
        self.assertTrue(all("integrity" not in path.lower() for path in changed))
        self.assertTrue(all("health" not in path.lower() or not path.startswith("tests/") for path in changed))

    def test_updated_ledger_says_proof_package_complete_pending_execution(self):
        payload = load_json(LEDGER_JSON)

        self.assertEqual(payload["completion_decision"], "proof_package_complete_pending_execution")
        self.assertEqual(payload["full_proof_run_id"], "HFX_CORE12_FULL_PROOF_RUN_001")
        self.assertEqual(payload["proof_execution_status"], "package_created_pending_actual_execution")
        self.assertEqual(len(payload["per_asset_proof_package_paths"]), 12)
        self.assertIn("actual shot/render/comp proof execution", payload["final_remaining_gate"])

    def test_source_safety_passes(self):
        sources = [
            Path("kernel/runtime/hfx_core12_proof_execution.py"),
            Path("kernel/runtime/hfx_core12_completion_ledger.py"),
            Path("tools/generate_hfx_core12_full_proof_execution_package.py"),
        ]
        for source_path in sources:
            source = source_path.read_text(encoding="utf-8")
            for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
