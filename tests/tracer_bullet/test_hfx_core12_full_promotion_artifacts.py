"""Artifact tests for the HFX Core12 full promotion closure sweep."""

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
PRODUCTION_ROOT = ROOT / "300_PRODUCTION_UPGRADE"
INDEX_ROOT = ROOT / "00_INDEX_资产索引"
ROUTE_JSON = INDEX_ROOT / "HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.json"
ROUTE_MD = INDEX_ROOT / "HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.md"
PROOF_JSON = INDEX_ROOT / "HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json"
PROOF_MD = INDEX_ROOT / "HFX_CORE12_SHOT_RENDER_PROOF_PLAN.md"
MATRIX_JSON = INDEX_ROOT / "HFX_CORE12_PROMOTION_MATRIX.json"
MATRIX_MD = INDEX_ROOT / "HFX_CORE12_PROMOTION_MATRIX.md"
LEDGER_JSON = INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.json"
LEDGER_MD = INDEX_ROOT / "HFX_CORE12_COMPLETION_LEDGER.md"
PLAN_MD = INDEX_ROOT / "HFX_100_PERCENT_COMPLETION_PLAN.md"
FORBIDDEN_NEW_SUFFIXES = {".hip", ".hda", ".otl", ".vdb", ".exr", ".mov", ".mp4", ".abc", ".usd", ".fbx", ".obj"}
PROTECTED_ROOT_FILES = {"Makefile", "README.md"}
UNSAFE_FINAL_CLAIMS = (
    "hollywood-grade complete",
    "film-grade complete",
    "hollywood final-pixel",
    "final-pixel complete",
    "final pixel complete",
)


def closure_json_path(asset_id: str, dirname: str) -> Path:
    return PRODUCTION_ROOT / dirname / f"{asset_id}_PROMOTION_CLOSURE.json"


def closure_md_path(asset_id: str, dirname: str) -> Path:
    return PRODUCTION_ROOT / dirname / f"{asset_id}_PROMOTION_CLOSURE.md"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_changed_paths() -> list[Path]:
    paths = [
        Path("kernel/runtime/hfx_core12_promotion_closure.py"),
        Path("kernel/runtime/hfx_core12_completion_ledger.py"),
        Path("tools/generate_hfx_core12_full_promotion_closure.py"),
        Path("tests/tracer_bullet/test_hfx_core12_promotion_closure.py"),
        Path("tests/tracer_bullet/test_hfx_core12_full_promotion_artifacts.py"),
        ROUTE_JSON,
        ROUTE_MD,
        PROOF_JSON,
        PROOF_MD,
        MATRIX_JSON,
        MATRIX_MD,
        LEDGER_JSON,
        LEDGER_MD,
        PLAN_MD,
    ]
    for asset_id, dirname in ASSETS:
        paths.append(closure_json_path(asset_id, dirname))
        paths.append(closure_md_path(asset_id, dirname))
    return paths


class HFXCore12FullPromotionArtifactTests(unittest.TestCase):
    def test_all_12_per_asset_closure_json_files_exist(self):
        for asset_id, dirname in ASSETS:
            self.assertTrue(closure_json_path(asset_id, dirname).is_file())

    def test_all_12_per_asset_closure_markdown_files_exist(self):
        for asset_id, dirname in ASSETS:
            self.assertTrue(closure_md_path(asset_id, dirname).is_file())

    def test_rollback_quarantine_route_files_exist(self):
        self.assertTrue(ROUTE_JSON.is_file())
        self.assertTrue(ROUTE_MD.is_file())

    def test_shot_render_proof_plan_files_exist(self):
        self.assertTrue(PROOF_JSON.is_file())
        self.assertTrue(PROOF_MD.is_file())

    def test_promotion_matrix_files_exist(self):
        self.assertTrue(MATRIX_JSON.is_file())
        self.assertTrue(MATRIX_MD.is_file())

    def test_completion_ledger_files_exist(self):
        self.assertTrue(LEDGER_JSON.is_file())
        self.assertTrue(LEDGER_MD.is_file())

    def test_100_percent_plan_exists(self):
        self.assertTrue(PLAN_MD.is_file())

    def test_no_closure_markdown_claims_final_hollywood_or_film_grade_completion(self):
        for asset_id, dirname in ASSETS:
            text = closure_md_path(asset_id, dirname).read_text(encoding="utf-8").lower()
            for claim in UNSAFE_FINAL_CLAIMS:
                self.assertNotIn(claim, text)

    def test_hfx_008_preserves_internal_gold_boundary(self):
        payload = load_json(closure_json_path("HFX_008", "HFX_008_ENERGY_SHOCKWAVE"))
        matrix = load_json(MATRIX_JSON)
        row = next(asset for asset in matrix["assets"] if asset["asset_id"] == "HFX_008")

        self.assertEqual(payload["promotion_decision"], "gold_complete")
        self.assertTrue(payload["render_or_comp_evidence"]["present"])
        self.assertFalse(row["final_claim_allowed"])
        self.assertIn("not a final public film-grade status claim", payload["render_or_comp_evidence"]["summary"])

    def test_hfx_015_has_rollback_quarantine_route(self):
        payload = load_json(closure_json_path("HFX_015", "HFX_015_PORTAL_RING"))

        self.assertEqual(payload["promotion_decision"], "production_complete_pending_shot_proof")
        self.assertTrue(payload["rollback_route"]["present"])
        self.assertTrue(payload["quarantine_route"]["present"])

    def test_all_12_assets_appear_in_promotion_matrix(self):
        payload = load_json(MATRIX_JSON)
        asset_ids = [asset["asset_id"] for asset in payload["assets"]]

        self.assertEqual(asset_ids, [asset_id for asset_id, _dirname in ASSETS])

    def test_no_external_raw_assets_were_added_by_this_branch(self):
        for path in expected_changed_paths():
            self.assertNotIn("external_raw", path.as_posix().lower())
            self.assertIn(path.suffix, {".py", ".json", ".md"})

    def test_no_binary_asset_extensions_are_added_by_this_branch(self):
        for path in expected_changed_paths():
            self.assertNotIn(path.suffix.lower(), FORBIDDEN_NEW_SUFFIXES)

    def test_protected_root_integrity_and_health_wiring_files_are_not_modified(self):
        changed = {path.as_posix() for path in expected_changed_paths()}

        self.assertTrue(PROTECTED_ROOT_FILES.isdisjoint(changed))
        self.assertTrue(all("integrity" not in path.lower() for path in changed))
        self.assertTrue(all("health" not in path.lower() or not path.startswith("tests/") for path in changed))

    def test_routes_cover_all_assets_and_forbid_unsafe_recovery(self):
        payload = load_json(ROUTE_JSON)
        asset_ids = [asset["asset_id"] for asset in payload["assets"]]

        self.assertEqual(asset_ids, [asset_id for asset_id, _dirname in ASSETS])
        for asset in payload["assets"]:
            self.assertIn("rollback_action", asset)
            self.assertIn("quarantine_action", asset)
            self.assertIn("enable_external_raw_assets", asset["forbidden_recovery_actions"])
            self.assertIn("launch_houdini_or_hython", asset["forbidden_recovery_actions"])
            self.assertIn("run_render_or_comp_output", asset["forbidden_recovery_actions"])

    def test_route_files_do_not_claim_tool_execution(self):
        text = ROUTE_MD.read_text(encoding="utf-8").lower()

        for phrase in ("launched houdini", "executed hython", "rendered output", "render output created"):
            self.assertNotIn(phrase, text)

    def test_proof_plan_lists_requirements_as_planned_not_executed(self):
        payload = load_json(PROOF_JSON)

        self.assertEqual(payload["proof_execution_status"], "planned_not_executed")
        self.assertEqual([asset["asset_id"] for asset in payload["assets"]], [asset_id for asset_id, _dirname in ASSETS])
        for asset in payload["assets"]:
            self.assertIn("minimum_shot_proof", asset)
            self.assertIn("minimum_render_comp_proof", asset)
            self.assertIn("required_final_proof", asset)
            self.assertIn("no final-pixel status is asserted", asset["no_fake_final_pixel_claim_boundary"].lower())

    def test_matrix_final_claim_false_when_shot_render_proof_missing(self):
        payload = load_json(MATRIX_JSON)

        for asset in payload["assets"]:
            if asset["shot_proof_status"] == "planned_not_executed" or asset["render_comp_proof_status"] == "planned_not_executed":
                self.assertFalse(asset["final_claim_allowed"])

    def test_hfx_015_rollback_quarantine_route_recorded_in_matrix(self):
        payload = load_json(MATRIX_JSON)
        hfx_015 = next(asset for asset in payload["assets"] if asset["asset_id"] == "HFX_015")

        self.assertEqual(hfx_015["rollback_route"], "recorded")
        self.assertEqual(hfx_015["quarantine_route"], "recorded")

    def test_updated_ledger_records_all_closure_and_plan_paths(self):
        payload = load_json(LEDGER_JSON)

        self.assertEqual(payload["completion_decision"], "proof_package_complete_pending_execution")
        self.assertEqual(len(payload["per_asset_closure_paths"]), 12)
        self.assertEqual(payload["promotion_matrix_path"], MATRIX_JSON.as_posix())
        self.assertEqual(payload["rollback_quarantine_route_path"], ROUTE_JSON.as_posix())
        self.assertEqual(payload["shot_render_proof_plan_path"], PROOF_JSON.as_posix())
        self.assertEqual(len(payload["per_asset_proof_package_paths"]), 12)
        self.assertEqual(payload["proof_execution_status"], "package_created_pending_actual_execution")
        self.assertIn("Deferred", payload["external_asset_decision"])

    def test_ledger_does_not_claim_complete_unless_final_gates_true(self):
        payload = load_json(LEDGER_JSON)

        self.assertNotEqual(payload["completion_decision"], "complete")
        self.assertTrue(payload["exact_remaining_gates"])
        self.assertTrue(all(asset["final_claim_allowed"] is False for asset in payload["core12_assets"]))

    def test_completion_plan_records_real_remaining_100_percent_gate(self):
        text = PLAN_MD.read_text(encoding="utf-8").lower()

        self.assertIn("does not claim current 100%", text)
        self.assertIn("final shot/render/comp proof", text)
        self.assertIn("no fake film-grade claims", text)
        self.assertIn("external friend asset decision remains deferred", text)
        self.assertIn("no external raw assets are committed", text)

    def test_source_safety_passes(self):
        sources = [
            Path("kernel/runtime/hfx_core12_promotion_closure.py"),
            Path("kernel/runtime/hfx_core12_completion_ledger.py"),
            Path("tools/generate_hfx_core12_full_promotion_closure.py"),
        ]
        for source_path in sources:
            source = source_path.read_text(encoding="utf-8")
            for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
