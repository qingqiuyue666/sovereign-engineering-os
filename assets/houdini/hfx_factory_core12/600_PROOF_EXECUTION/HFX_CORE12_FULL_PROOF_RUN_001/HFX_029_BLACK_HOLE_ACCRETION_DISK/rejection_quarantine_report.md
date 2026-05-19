# HFX_029 Rejection Quarantine Report

| Field | Value |
| --- | --- |
| asset_id | HFX_029 |
| asset_name | Black Hole Accretion Disk |
| proof_package_status | package_created |
| shot_proof_status | package_created |
| render_proof_status | package_created |
| comp_proof_status | package_created |
| review_status | package_created |
| acceptance_decision | pending_execution |
| final_claim_allowed | false |

## Rejection Criteria
- Missing shot execution receipt.
- Missing render artifact manifest.
- Missing comp review artifact.
- Hash mismatch, manifest disagreement, unsafe completion claim, or unlicensed dependency.

## Quarantine Trigger
- Unlicensed external asset dependency, unsafe proof claim, corrupted artifact record, or missing required proof artifact.

## Rollback Trigger
- Proof artifact mismatch, failed review, missing accepted render/comp evidence, or promotion state disagreement.

## Current Route Decision
- quarantine_decision: not_triggered_pending_execution
- rollback_decision: not_triggered_pending_execution
