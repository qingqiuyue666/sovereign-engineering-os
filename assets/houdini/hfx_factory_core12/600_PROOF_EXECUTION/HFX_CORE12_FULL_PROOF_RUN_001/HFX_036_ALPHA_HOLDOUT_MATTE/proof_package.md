# HFX_036 Proof Package

| Field | Value |
| --- | --- |
| asset_id | HFX_036 |
| asset_name | Alpha Holdout Matte |
| proof_package_status | package_created |
| shot_proof_status | package_created |
| render_proof_status | package_created |
| comp_proof_status | package_created |
| review_status | package_created |
| acceptance_decision | pending_execution |
| final_claim_allowed | false |
| content_hash | sha256:f49d609befa41d8aa62d87b3dd604a30f4b6b56b72b9881554b2fd59a7dbdc20 |
| observed_at | not_provided |

## Linked Evidence
- promotion_closure_path: assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/HFX_036_ALPHA_HOLDOUT_MATTE/HFX_036_PROMOTION_CLOSURE.json
- rollback_quarantine_route_path: assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_ROLLBACK_QUARANTINE_ROUTES.json
- shot_render_proof_plan_path: assets/houdini/hfx_factory_core12/00_INDEX_资产索引/HFX_CORE12_SHOT_RENDER_PROOF_PLAN.json

## Minimum Shot Proof Checklist
- Bind the promoted asset version to a named proof shot.
- Record camera, frame range, plate or synthetic-plate label, and scale assumptions.
- Record the source HIP/HDA closure path without mutating the source asset.
- Seal the shot receipt with deterministic artifact names and hashes.

## Minimum Render Proof Checklist
- Execute the render proof in the Houdini/render environment.
- Record render settings, pass list, frame range, artifact names, and hashes.
- Keep failed, missing, or partial renders in a blocked proof state.
- Do not promote render status from package_created until real artifacts exist.

## Minimum Comp Review Checklist
- Review alpha, holdout, lightwrap, contact, distortion, glow, and integration behavior where applicable.
- Record reviewer, decision, rejection reasons, and acceptance notes.
- Block acceptance when render or comp artifacts are missing.
- Keep final_claim_allowed false until shot, render, and comp proof are accepted.

## Expected Artifacts
- HFX_036 shot binding receipt with asset version, camera, frame range, and scale notes.
- HFX_036 render proof manifest with artifact paths, pass list, and deterministic hashes.
- HFX_036 comp review record with integration notes and reviewer acceptance decision.

## Missing Proof Artifacts
- actual shot execution receipt
- actual render artifact manifest
- actual comp review artifact
- reviewed acceptance receipt

## Acceptance Criteria
- Shot proof is executed and reviewed for the exact promoted asset.
- Render proof artifact manifest exists and hashes match recorded artifacts.
- Comp review confirms integration behavior and records an explicit acceptance decision.
- Rollback and quarantine route remain active for proof mismatch or unsafe claim.
- No unlicensed external asset dependency is required for acceptance.

## Rejection Criteria
- Missing shot execution receipt.
- Missing render artifact manifest.
- Missing comp review artifact.
- Hash mismatch, manifest disagreement, unsafe completion claim, or unlicensed dependency.

## Quarantine Trigger
Unlicensed external asset dependency, unsafe proof claim, corrupted artifact record, or missing required proof artifact.

## Rollback Trigger
Proof artifact mismatch, failed review, missing accepted render/comp evidence, or promotion state disagreement.

## Current Acceptance Decision
pending_execution
