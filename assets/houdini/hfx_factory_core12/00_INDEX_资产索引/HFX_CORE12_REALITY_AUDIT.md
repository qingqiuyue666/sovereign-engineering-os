# HFX Core12 Reality Audit

| Field | Value |
| --- | --- |
| audit_id | hfx-core12-reality-audit-v1 |
| repository_url | https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os |
| main_commit | d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3 |
| source_root | assets/houdini/hfx_factory_core12 |
| policy_version | hfx-core12-reality-audit-v1 |
| code_version | 0.1.0 |
| content_hash | sha256:c2f8932b6e7dc9f7e3dc8412c3dcf948e1180533dac02e9cd19c0d70fc403c82 |
| observed_at | not_provided |

## Asset Reality Table
| asset_id | asset_name | source_files_present | hip_files_present | hda_files_present | preview_docs_present | preview_manifests_present | mid_tier_present | final_tier_present | validation_reports_present | sha256_manifest_present | shot_binding_present | render_or_comp_report_present | empty_file_count | large_file_count_over_50mb | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HFX_008 | Energy Shockwave | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | gold_candidate |
| HFX_015 | Portal Ring | yes | yes | no | yes | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | gold_candidate |
| HFX_016 | Heat Distortion | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_021 | Pyro Explosion | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_025 | Character Energy Field | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_027 | Summoning Portal Gate | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_028 | Space Rift Tear | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_029 | Black Hole Accretion Disk | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_033 | Glow Emission Pass | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_036 | Alpha Holdout Matte | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_037 | Lightwrap Rim Interaction | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |
| HFX_038 | Contact Shadow Ground Integration | yes | yes | no | no | yes | yes | yes | yes | yes | yes | yes | 0 | 0 | production_candidate |

## Status Rules

## Rules
- gold_candidate requires reusable HIP/HDA evidence, preview proof, validation, non-empty files, shot binding, and render/comp report evidence.
- production_candidate requires real HIP/HDA evidence plus validation.
- partial_candidate requires local real asset files while final proof remains incomplete.
- shell_only is reserved for reports/manifests without real asset files.
- blocked is used for missing critical files, empty critical files, or unsafe evidence conditions.
