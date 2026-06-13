# Playbooks

Reusable execution playbooks live here. They are operational checklists for
repeatable repository workflows, not new SEIS strategy layers.

## Index

- `pr-stack-migration-v1.md` - reconcile dirty stacked PRs, preserve PR-owned
  changes, remove lower-stack duplicates, rerun checks, and stop at the human
  merge gate.

## Use

Start with the current repository state. Use a playbook only when it matches
the current bottleneck. Record evidence in the relevant checkpoint or final
report.
