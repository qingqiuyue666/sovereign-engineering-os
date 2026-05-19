# HFX_025 Render Comp Proof Checklist

| Field | Value |
| --- | --- |
| asset_id | HFX_025 |
| asset_name | Character Energy Field |
| proof_package_status | package_created |
| shot_proof_status | package_created |
| render_proof_status | package_created |
| comp_proof_status | package_created |
| review_status | package_created |
| acceptance_decision | pending_execution |
| final_claim_allowed | false |

## Render Checklist
- [ ] Execute the render proof in the Houdini/render environment.
- [ ] Record render settings, pass list, frame range, artifact names, and hashes.
- [ ] Keep failed, missing, or partial renders in a blocked proof state.
- [ ] Do not promote render status from package_created until real artifacts exist.

## Comp Review Checklist
- [ ] Review alpha, holdout, lightwrap, contact, distortion, glow, and integration behavior where applicable.
- [ ] Record reviewer, decision, rejection reasons, and acceptance notes.
- [ ] Block acceptance when render or comp artifacts are missing.
- [ ] Keep final_claim_allowed false until shot, render, and comp proof are accepted.

## Status
- render_proof_status: package_created
- comp_proof_status: package_created
- review_status: package_created
- actual execution remains pending.
