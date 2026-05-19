# HFX_015 Portal Ring Closure

| Field | Value |
| --- | --- |
| closure_id | hfx-015-production-candidate-closure-v1 |
| asset_id | HFX_015 |
| asset_name | Portal Ring |
| repository_url | https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os |
| main_commit | d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3 |
| closure_status | production_candidate |
| policy_version | hfx-asset-closure-v1 |
| code_version | 0.1.0 |
| content_hash | sha256:bf4d085747c25dcc8d49b7423e16492ab47e598e1a0f204e529fee3828587895 |
| observed_at | not_provided |

## Evidence Gates
- checksum_exists: true
- external_asset_dependencies_declared: true
- input_contract_documented: true
- known_limitations_documented: true
- manifest_exists: true
- no_fake_film_grade_claim: true
- no_unlicensed_third_party_raw_asset_dependency: true
- no_zero_byte_critical_files: true
- output_pass_contract_documented: true
- parameter_interface_documented: true
- preview_proof_exists: true
- real_hip_or_hda_exists: true
- render_comp_report_exists: true
- rollback_or_quarantine_route_exists: false
- shot_binding_exists: true
- validation_report_exists: true

## Missing Gates
- rollback_or_quarantine_route_exists

## Evidence Notes
- Portal Ring has internal preview, mid, final candidate HIP, validation, shot-bound template, and render/comp contract evidence.
- Gold status is not claimed because an explicit rollback or quarantine route is not yet present in the closure evidence.
- The final asset seal records all_houdini_fx_top_tier_complete as false, so this remains a production candidate.

## Boundary Conditions
- no_houdini_launch
- no_hython_execution
- no_render_execution
- no_hip_or_hda_mutation
- no_external_raw_asset_commit

## Gold Rule
gold_complete is allowed only when every HFX gold asset gate is true.
