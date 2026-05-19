# HFX Gold Asset Standard

| Field | Value |
| --- | --- |
| standard_id | hfx-gold-asset-standard-v1 |
| repository_url | https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os |
| main_commit | d13e9aa8f65c8b64d3da08b9a55ff5087b87beb3 |
| gold_status_decision | gold_allowed |
| policy_version | hfx-gold-asset-standard-v1 |
| code_version | 0.1.0 |
| content_hash | sha256:724db65f9c68a4cf0f431c288c03c48dd50ea071b0433a4213f6717a2c2947e5 |
| observed_at | not_provided |

## Hard Gates
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
- rollback_or_quarantine_route_exists: true
- shot_binding_exists: true
- validation_report_exists: true

## Gate Definitions
- checksum_exists: Checksum evidence exists.
- external_asset_dependencies_declared: External asset dependency posture is declared.
- input_contract_documented: Inputs and per-shot derivation contract are documented.
- known_limitations_documented: Known limitations are explicit.
- manifest_exists: Release/package manifest exists.
- no_fake_film_grade_claim: No film-grade/final-pixel claim is made without evidence.
- no_unlicensed_third_party_raw_asset_dependency: No unlicensed raw third-party dependency is required.
- no_zero_byte_critical_files: Critical source, manifest, and validation files are non-empty.
- output_pass_contract_documented: Outputs, passes, and comp handoff are documented.
- parameter_interface_documented: Artist/operator parameters are documented.
- preview_proof_exists: Preview proof exists without claiming final pixels.
- real_hip_or_hda_exists: A real HIP/HDA reusable source exists in the repository.
- render_comp_report_exists: Render/comp contract or report exists.
- rollback_or_quarantine_route_exists: Rollback, quarantine, or derive-only route exists.
- shot_binding_exists: Shot binding or shot-bound template exists.
- validation_report_exists: Validation report exists and is tied to the asset.

## Standard Notes
- A real HIP/HDA reusable source exists in the repository.
- Critical source, manifest, and validation files are non-empty.
- Artist/operator parameters are documented.
- Inputs and per-shot derivation contract are documented.
- Outputs, passes, and comp handoff are documented.
- Preview proof exists without claiming final pixels.
- Validation report exists and is tied to the asset.
- Release/package manifest exists.
- Checksum evidence exists.
- Shot binding or shot-bound template exists.
- Render/comp contract or report exists.
- Known limitations are explicit.
- Rollback, quarantine, or derive-only route exists.
- External asset dependency posture is declared.
- No unlicensed raw third-party dependency is required.
- No film-grade/final-pixel claim is made without evidence.

## Blocked Claims
- Gold status is blocked if any gate is false.
- Film-grade or final-pixel status is blocked unless independent evidence exists.
- Unlicensed third-party raw assets block gold status.

## Claim Rule
Gold status cannot be claimed unless every hard gate is true.
