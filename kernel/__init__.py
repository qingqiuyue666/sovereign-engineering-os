"""
Kernel package root.

Authority boundary per v11 §24.3, §25.2, §31:
- kernel holds truth / approval / seal / evidence barriers
- nothing outside kernel may mutate authority state
- only the narrow eight-stage signable path is authorized in phase 1:
  Context -> Inference -> PatchProposal -> Validation -> Review -> Approval
  -> Revision Seal -> Evidence
"""
