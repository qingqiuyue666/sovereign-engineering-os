# AI Proposal Review Checklist V1

AI-generated proposals must be reviewed as untrusted suggestions.

Review requirements:

- confirm the proposal does not bypass approval gates
- confirm the proposal does not introduce provider execution
- confirm the proposal does not read secrets or private local paths
- confirm tests fail closed when evidence is missing
- confirm any patch is minimal and linked to a validation command
- confirm no global recognition or external certification claim is introduced
- confirm the operator can explain residual risk before merge

An AI proposal cannot approve itself, merge itself, publish a release, move a
tag, or become execution authority.
