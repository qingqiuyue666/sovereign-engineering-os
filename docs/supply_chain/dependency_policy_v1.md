# Dependency Policy V1

Dependencies must be intentionally reviewed before addition or upgrade.

Policy requirements:

- explain why the dependency is needed
- prefer standard library or existing local helpers when sufficient
- record runtime versus test-only use
- pin or bound versions where practical
- avoid heavy dependencies unless already present or explicitly justified
- run `make ci` after dependency changes
- document residual dependency risk in the PR

Current CI installs only the standard Python runtime dependencies needed by the
existing repository checks. Fresh-venv smoke uses no-index editable install
flags for the project itself.
