# Workspace Hygiene and Naming Guide v1

## Naming

- branch naming should remain specific and reviewable
- docs naming should reflect the asset type and purpose
- example file naming should include `sample`, `template`, or `form` as appropriate
- report naming should stay deterministic and descriptive
- generated output naming should remain stable for tests

## What Must Not Be Committed

- no secrets
- no raw dumps
- no temporary extraction folders
- no repomix output committed unless explicitly requested
- no accidental desktop-local paths in committed docs unless intentionally documented as operator-local examples
