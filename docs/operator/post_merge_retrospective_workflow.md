# Post-Merge Retrospective Workflow

## Purpose

The Post-Merge Retrospective workflow turns each completed merge into deterministic long-memory operator knowledge.

## Required Material

- Report ID.
- Repository URL.
- Merge commit.
- Merged branch.
- Merged capabilities.
- Files added, modified, and deleted.
- Tests after merge.
- Risks retained.
- Blocked capabilities preserved.
- Lessons learned.
- Next actions.
- Rollback route.
- Policy version.
- Code version.

## Blocked Capability Boundary

Blocked capabilities must remain preserved. The retrospective must explicitly record that live provider execution, production autonomy, financial execution, trading automation, secret access, raw prompt persistence, and external action execution remain blocked unless a separate authorized governance slice changes that boundary.

## Markdown Output

1. Merge Summary
2. Merged Capabilities
3. Files Changed
4. Tests After Merge
5. Risks Retained
6. Blocked Capabilities Preserved
7. Lessons Learned
8. Next Actions
9. Rollback Route

## Failure Handling

Missing merge commit, merged branch, merged capabilities, tests after merge, rollback route, blocked capability preservation evidence, forbidden sensitive fields, invalid digest fields, caller-supplied content hashes, or non-serializable material fail closed.
