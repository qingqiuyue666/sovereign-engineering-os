import json
import pathlib
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "houdini"))

from hfx_real_pipeline_lib import hfx_real_pipeline as hfx  # noqa: E402


SYSTEM_STATE = hfx.SYSTEM_STATE


class HFXRealResourceShotPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def sample_scan(self):
        inbox = self.tmp_path / "inbox"
        out = self.tmp_path / "resource_out"
        hfx.create_sample_resource_inbox(inbox)
        return hfx.scan_resource_inbox(inbox, out), inbox, out

    def test_01_resource_scanning(self):
        result, _, _ = self.sample_scan()
        self.assertGreaterEqual(result["manifest"]["resource_count"], 10)
        self.assertEqual(result["seal"]["status"], "PASS")

    def test_02_resource_type_classification(self):
        cases = {
            "hero_albedo.png": "PBR",
            "studio.hdr": "HDRI",
            "smoke.vdb": "VDB",
            "creature.abc": "ABC",
            "env.usd": "USD",
            "actor_plate.mov": "plate",
            "show_lut.cube": "LUT",
            "hero_material.mtlx": "shader",
            "hero_model.obj": "model",
            "shot_camera.camera.json": "camera",
            "shot_lens.lens.json": "lens",
        }
        for file_name, resource_type in cases.items():
            with self.subTest(file=file_name):
                self.assertEqual(hfx.classify_resource(pathlib.Path(file_name)), resource_type)

    def test_03_checksum_generation(self):
        path = self.tmp_path / "asset.usd"
        path.write_text("usd-data", encoding="utf-8")
        self.assertEqual(hfx.sha256_file(path), hfx.sha256_file(path))

    def test_04_license_source_validation(self):
        inbox = self.tmp_path / "inbox"
        hfx.create_sample_resource_inbox(inbox)
        for metadata in inbox.rglob("hero_albedo.png.metadata.json"):
            metadata.unlink()
        result = hfx.scan_resource_inbox(inbox, self.tmp_path / "out")
        self.assertEqual(result["missing_report"]["status"], "BLOCKED_MISSING_METADATA")

    def test_05_quarantine_behavior(self):
        inbox = self.tmp_path / "inbox"
        hfx.create_sample_resource_inbox(inbox)
        for metadata in inbox.rglob("studio.hdr.metadata.json"):
            metadata.unlink()
        result = hfx.scan_resource_inbox(inbox, self.tmp_path / "out")
        self.assertEqual(result["quarantine_manifest"]["quarantine_count"], 1)

    def test_06_resource_registry_generation(self):
        result, _, _ = self.sample_scan()
        registry = result["registry"]
        self.assertIn("PBR", registry["resources_by_type"])
        self.assertIn("HDRI", registry["resources_by_type"])

    def test_07_missing_field_report_generation(self):
        inbox = self.tmp_path / "inbox"
        hfx.create_sample_resource_inbox(inbox)
        for metadata in inbox.rglob("smoke.vdb.metadata.json"):
            metadata.unlink()
        result = hfx.scan_resource_inbox(inbox, self.tmp_path / "out")
        self.assertTrue(result["missing_report"]["missing"])

    def test_08_shot_resource_binding(self):
        scan, _, _ = self.sample_scan()
        result = hfx.bind_resources_to_shot(scan["registry"], self.tmp_path / "binding")
        self.assertEqual(result["validation"]["status"], "PASS")
        self.assertEqual(len(result["binding"]["bindings"]), len(hfx.SLOT_RULES))

    def test_09_missing_resource_fail_closed_behavior(self):
        result = hfx.bind_resources_to_shot({"resources": []}, self.tmp_path / "binding")
        self.assertEqual(result["validation"]["status"], "BLOCKED")
        self.assertTrue(result["validation"]["failures"])

    def test_10_hda_readiness(self):
        result = hfx.build_hda_assetization(self.tmp_path / "hda")
        self.assertEqual(result["registry"]["asset_count"], 12)
        self.assertEqual(result["validation"]["status"], "PASS")

    def test_11_hda_parameter_interface_locking(self):
        result = hfx.build_hda_assetization(self.tmp_path / "hda")
        self.assertTrue(all(asset["locked_parameters"] for asset in result["registry"]["assets"]))

    def test_12_hda_rollback(self):
        result = hfx.build_hda_assetization(self.tmp_path / "hda")
        self.assertTrue(all(asset["rollback_target"] for asset in result["registry"]["assets"]))

    def test_13_hda_read_only_release_enforcement(self):
        result = hfx.build_hda_assetization(self.tmp_path / "hda")
        self.assertTrue(all(asset["release_immutable"] for asset in result["registry"]["assets"]))

    def test_14_render_job_creation(self):
        job = hfx.create_render_job(self.tmp_path / "render")
        self.assertEqual(job["renderer"], "hython_dry_run")
        self.assertTrue((self.tmp_path / "render" / "RENDER_JOB_MANIFEST.json").is_file())

    def test_15_render_queue(self):
        hfx.create_render_job(self.tmp_path / "render", job_id="JOB_A")
        queue = hfx.read_json(self.tmp_path / "render" / "RENDER_QUEUE.json")
        self.assertEqual(queue["jobs"], ["JOB_A"])

    def test_16_aov_validation(self):
        job = hfx.create_render_job(self.tmp_path / "render")
        report = hfx.validate_render_outputs(job, self.tmp_path / "render")
        self.assertEqual(report["aov"]["status"], "PASS")

    def test_17_missing_frame_detection(self):
        job = hfx.create_render_job(self.tmp_path / "render")
        report = hfx.validate_render_outputs(job, self.tmp_path / "render")
        self.assertEqual(report["missing"]["status"], "BLOCKED_MISSING_FRAMES")

    def test_18_bad_frame_detection(self):
        render_dir = self.tmp_path / "render"
        job = hfx.create_render_job(render_dir, frames=[1001])
        exr = pathlib.Path(job["output_dir"])
        exr.mkdir(parents=True)
        (exr / "HFX_RENDER_JOB_001.1001.exr").write_bytes(b"")
        report = hfx.validate_render_outputs(job, render_dir)
        self.assertEqual(report["bad"]["status"], "BLOCKED_BAD_FRAMES")

    def test_19_render_checksum(self):
        render_dir = self.tmp_path / "render"
        job = hfx.create_render_job(render_dir, frames=[1001, 1002])
        exr = pathlib.Path(job["output_dir"])
        exr.mkdir(parents=True)
        for frame in job["frames"]:
            (exr / f"{job['job_id']}.{frame:04d}.exr").write_text(f"dry-run-frame-{frame}", encoding="utf-8")
        report = hfx.validate_render_outputs(job, render_dir)
        self.assertEqual(report["checksum"]["status"], "PASS")
        self.assertEqual(len(report["checksum"]["frames"]), 2)

    def test_20_failed_frame_retry(self):
        job = hfx.create_render_job(self.tmp_path / "render", frames=[1001])
        report = hfx.validate_render_outputs(job, self.tmp_path / "render")
        self.assertEqual(report["retry"]["status"], "RETRY_REQUIRED")

    def test_21_aov_matrix_validation(self):
        result = hfx.build_aov_pass(self.tmp_path / "aov")
        self.assertEqual(result["validation"]["status"], "PASS")

    def test_22_beauty_only_render_rejection(self):
        matrix = {"assets": [{"asset_id": "A", "required_aovs": ["Beauty"]}], "required_aovs": ["Beauty"]}
        contract = {"required_aovs": ["Beauty"]}
        result = hfx.validate_aov_contract(matrix, contract)
        self.assertEqual(result["status"], "BLOCKED")

    def test_23_shader_slot_registry(self):
        hfx.build_lookdev(self.tmp_path / "lookdev")
        registry = hfx.read_json(self.tmp_path / "lookdev" / "SHADER_SLOT_REGISTRY.json")
        self.assertIn("base_color", registry["slots"])

    def test_24_pbr_texture_rules(self):
        hfx.build_lookdev(self.tmp_path / "lookdev")
        rules = hfx.read_json(self.tmp_path / "lookdev" / "PBR_TEXTURE_CONNECTION_RULES.json")
        self.assertIn("normal", rules)

    def test_25_lookdev_approval_blocker(self):
        result = hfx.build_lookdev(self.tmp_path / "lookdev")
        self.assertEqual(result["approval"]["status"], "LOOKDEV_APPROVAL_BLOCKED")

    def test_26_plate_camera_binding(self):
        hfx.build_plate_camera(self.tmp_path / "plate")
        binding = hfx.read_json(self.tmp_path / "plate" / "PLATE_CAMERA_BINDING.json")
        self.assertIn("camera_solve", binding)

    def test_27_tracking_validation(self):
        hfx.build_plate_camera(self.tmp_path / "plate")
        tracking = hfx.read_json(self.tmp_path / "plate" / "TRACKING_VALIDATION_REPORT.json")
        self.assertEqual(tracking["status"], "PASS")

    def test_28_alignment_validation(self):
        hfx.build_plate_camera(self.tmp_path / "plate")
        alignment = hfx.read_json(self.tmp_path / "plate" / "PLATE_CAMERA_ALIGNMENT_REPORT.json")
        self.assertTrue(alignment["frame_rate_match"])
        self.assertTrue(alignment["resolution_match"])
        self.assertTrue(alignment["shutter_metadata_exists"])
        self.assertTrue(alignment["color_space_match"])

    def test_29_ocio_aces_configuration_validation(self):
        result = hfx.build_color_management(self.tmp_path / "color")
        self.assertEqual(result["validation"]["status"], "PASS")

    def test_30_color_management_final_pixel_blocker(self):
        result = hfx.validate_color_management({"render_working_space": "ACEScg"})
        self.assertEqual(result["status"], "BLOCKED_COLOR_INCOMPLETE")
        self.assertFalse(result["final_pixel_allowed"])

    def test_31_nuke_comp_generator(self):
        text = hfx.generate_nuke_comp(self.tmp_path / "comp")
        self.assertIn("Read_Beauty", text)

    def test_32_ae_davinci_skeleton_generation(self):
        hfx.build_comp_execution(self.tmp_path / "comp")
        self.assertTrue((self.tmp_path / "comp" / "AE_COMP_PROJECT_SKELETON.json").is_file())
        self.assertTrue((self.tmp_path / "comp" / "DAVINCI_NODE_TREE_SKELETON.json").is_file())

    def test_33_aov_auto_wiring(self):
        hfx.build_comp_execution(self.tmp_path / "comp")
        wiring = hfx.read_json(self.tmp_path / "comp" / "AOV_AUTO_WIRING_RULES.json")
        self.assertEqual(wiring["aov_inputs"], hfx.REQUIRED_AOVS)

    def test_34_final_comp_blocker(self):
        result = hfx.build_comp_execution(self.tmp_path / "comp")
        self.assertEqual(result["final"]["status"], "FINAL_COMP_BLOCKED")

    def test_35_thumbnail_generation(self):
        hfx.build_review_dailies(self.tmp_path / "review")
        self.assertTrue((self.tmp_path / "review" / "THUMBNAIL_MANIFEST.json").is_file())

    def test_36_contact_sheet_generation(self):
        hfx.build_review_dailies(self.tmp_path / "review")
        contact = hfx.read_json(self.tmp_path / "review" / "CONTACT_SHEET_MANIFEST.json")
        self.assertEqual(contact["layout"], "grid_4x4")

    def test_37_review_movie_interface(self):
        hfx.build_review_dailies(self.tmp_path / "review")
        movie = hfx.read_json(self.tmp_path / "review" / "REVIEW_MOVIE_MANIFEST.json")
        self.assertFalse(movie["movie_rendered"])

    def test_38_dailies_report(self):
        hfx.build_review_dailies(self.tmp_path / "review")
        report = hfx.read_json(self.tmp_path / "review" / "DAILIES_REPORT.json")
        self.assertEqual(report["status"], "DAILIES_RECORDED")

    def test_39_review_approval_reject_status(self):
        result = hfx.build_review_dailies(self.tmp_path / "review")
        self.assertFalse(result["approval"]["approved"])
        self.assertFalse(result["approval"]["rejected"])

    def test_40_review_evidence_chain(self):
        hfx.build_review_dailies(self.tmp_path / "review")
        chain = hfx.read_json(self.tmp_path / "review" / "REVIEW_EVIDENCE_CHAIN.json")
        self.assertTrue(chain["chain"])

    def test_41_final_pixel_approval_blockers(self):
        result = hfx.validate_final_pixel({}, self.tmp_path / "final")
        self.assertEqual(result["report"]["status"], "FINAL_PIXEL_APPROVAL_BLOCKED")
        self.assertFalse(result["ready"]["emitted"])

    def test_42_final_pixel_ready_emission_only_when_all_checks_pass(self):
        result = hfx.validate_final_pixel(
            {
                "exr_outputs_pass": True,
                "aov_completeness_pass": True,
                "comp_output_pass": True,
                "color_management_pass": True,
                "resource_license_pass": True,
                "review_approval_pass": True,
            },
            self.tmp_path / "final",
        )
        self.assertTrue(result["ready"]["emitted"])
        self.assertEqual(result["report"]["status"], hfx.FINAL_READY_STATE)

    def test_43_delivery_manifest(self):
        hfx.validate_delivery_package({}, self.tmp_path / "delivery")
        self.assertTrue((self.tmp_path / "delivery" / "DELIVERY_MANIFEST.json").is_file())

    def test_44_delivery_package_validator(self):
        result = hfx.validate_delivery_package({"checksum": True}, self.tmp_path / "delivery")
        self.assertEqual(result["validation"]["status"], "DELIVERY_BLOCKED")

    def test_45_client_public_delivery_blocker(self):
        result = hfx.validate_delivery_package({}, self.tmp_path / "delivery")
        self.assertEqual(result["blocker"]["status"], "CLIENT_PUBLIC_DELIVERY_BLOCKED")

    def test_46_master_pipeline_seal_binding_all_12_layer_seals(self):
        master = hfx.materialize_all(REPO_ROOT)
        self.assertEqual(master["bound_layer_count"], 12)
        self.assertEqual(len(master["layer_seals"]), 12)
        self.assertFalse(master["final_pixels_authorized"])
        for seal in master["layer_seals"]:
            self.assertTrue((REPO_ROOT / seal["seal_path"]).is_file())

    def test_no_core12_release_hip_files_modified_by_branch(self):
        changed = os_changed_files()
        modified_hips = [
            path
            for path in changed
            if path.startswith("assets/houdini/hfx_factory_core12/") and path.endswith(".hip")
        ]
        self.assertEqual(modified_hips, [])


def os_changed_files():
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.splitlines()


if __name__ == "__main__":
    unittest.main()
