import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.adapters.creative_adapter_contract import (
    CreativeAdapterFamily,
)
from kernel.personal_ai.adapters.creative_handoff_package import (
    build_creative_handoff_package,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.runtime_delivery_package import (
    build_runtime_delivery_package,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class CreativeHandoffPackageTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_dir = root / "source"
        package_root = root / "handoff_packages"
        delivery_root = root / "delivery_packages"
        source_dir.mkdir()
        package_root.mkdir()
        delivery_root.mkdir()
        source_asset = source_dir / "scene_reference.asset"
        source_asset.write_text(
            "SOURCE_CONTENT_SENTINEL_DO_NOT_COPY",
            encoding="utf-8",
        )
        return source_asset, package_root, delivery_root

    def test_builds_hash_bound_handoff_package_for_all_creative_families(self):
        for family in CreativeAdapterFamily.all():
            with self.subTest(family=family):
                source_asset, package_root, _ = self.build_workspace()
                package_id = family.replace("_", "-") + "-handoff"

                result = build_creative_handoff_package(
                    family,
                    (source_asset,),
                    package_root,
                    package_id=package_id,
                )
                package_manifest = read_json(result.package_manifest_path)
                tool_manifest = read_json(result.tool_manifest_path)

                self.assertTrue(result.complete)
                self.assertTrue(result.required_human_approval)
                self.assertEqual(result.source_asset_count, 1)
                self.assertEqual(package_manifest["family"], family)
                self.assertEqual(
                    package_manifest["source_asset_hashes"][
                        source_asset.as_posix()
                    ],
                    sha256_file(source_asset),
                )
                self.assertFalse(package_manifest["runtime_admitted"])
                self.assertFalse(
                    package_manifest["external_tool_control_performed"]
                )
                self.assertFalse(
                    package_manifest["source_asset_overwrite_performed"]
                )
                self.assertTrue(package_manifest["preview_render_evidence_required"])
                self.assertEqual(tool_manifest["family"], family)
                self.assertGreater(len(tool_manifest["operation_allowlist"]), 0)
                self.assertTrue(
                    tool_manifest["output_target_policy"][
                        "outputs_must_stay_inside_package"
                    ]
                )
                self.assertFalse(
                    tool_manifest["automatic_external_tool_control_allowed"]
                )

    def test_package_does_not_copy_source_asset_contents(self):
        source_asset, package_root, _ = self.build_workspace()

        result = build_creative_handoff_package(
            CreativeAdapterFamily.BLENDER,
            (source_asset,),
            package_root,
            package_id="blender-handoff",
        )

        for artifact_path in (
            result.package_manifest_path,
            result.tool_manifest_path,
            result.instructions_path,
        ):
            self.assertNotIn(
                "SOURCE_CONTENT_SENTINEL_DO_NOT_COPY",
                artifact_path.read_text(encoding="utf-8"),
            )
        self.assertEqual(source_asset.read_text(encoding="utf-8"), "SOURCE_CONTENT_SENTINEL_DO_NOT_COPY")

    def test_rejects_source_overwrite_and_output_escape_targets(self):
        source_asset, package_root, _ = self.build_workspace()

        with self.assertRaisesRegex(ValueError, "must not overwrite source asset"):
            build_creative_handoff_package(
                CreativeAdapterFamily.AFTER_EFFECTS,
                (source_asset,),
                package_root,
                package_id="unsafe-source-target",
                requested_output_targets=(source_asset,),
            )
        self.assertFalse((package_root / "unsafe-source-target").exists())

        with self.assertRaisesRegex(ValueError, "must stay inside"):
            build_creative_handoff_package(
                CreativeAdapterFamily.AFTER_EFFECTS,
                (source_asset,),
                package_root,
                package_id="unsafe-escape-target",
                requested_output_targets=(package_root.parent / "outside.mov",),
            )
        self.assertFalse((package_root / "unsafe-escape-target").exists())

    def test_accepts_package_local_output_targets_and_refuses_package_overwrite(self):
        source_asset, package_root, _ = self.build_workspace()
        requested_target = (
            package_root / "zbrush-handoff" / "handoff_outputs" / "preview.png"
        )

        first = build_creative_handoff_package(
            CreativeAdapterFamily.ZBRUSH,
            (source_asset,),
            package_root,
            package_id="zbrush-handoff",
            requested_output_targets=(requested_target,),
        )

        self.assertEqual(first.output_target_dir, requested_target.parent)
        with self.assertRaisesRegex(ValueError, "already exists"):
            build_creative_handoff_package(
                CreativeAdapterFamily.ZBRUSH,
                (source_asset,),
                package_root,
                package_id="zbrush-handoff",
            )

    def test_rejects_symlink_source_assets(self):
        source_asset, package_root, _ = self.build_workspace()
        symlink_path = source_asset.parent / "linked.asset"
        symlink_path.symlink_to(source_asset)

        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            build_creative_handoff_package(
                CreativeAdapterFamily.UNREAL,
                (symlink_path,),
                package_root,
                package_id="unreal-handoff",
            )

    def test_runtime_delivery_package_includes_handoff_manifests(self):
        source_asset, package_root, delivery_root = self.build_workspace()
        handoff = build_creative_handoff_package(
            CreativeAdapterFamily.COMFYUI,
            (source_asset,),
            package_root,
            package_id="comfyui-handoff",
        )

        delivery = build_runtime_delivery_package(
            handoff.package_dir,
            delivery_root,
            package_id="creative-delivery",
        )
        delivery_manifest = read_json(delivery.runtime_delivery_manifest_path)

        self.assertTrue(delivery.complete)
        self.assertIn("creative_handoff_manifest", delivery.packaged_artifacts)
        self.assertIn("creative_handoff_tool_manifest", delivery.packaged_artifacts)
        self.assertIn("creative_handoff_instructions", delivery.packaged_artifacts)
        self.assertEqual(delivery_manifest["delivery_policy"]["creative_runtime_allowed"], False)


if __name__ == "__main__":
    unittest.main()
