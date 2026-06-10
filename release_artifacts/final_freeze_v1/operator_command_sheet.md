# Operator Command Sheet

## Verify Current HEAD

```bash
git rev-parse HEAD
```

Expected:

```text
e08823385c15be421d6d72819226e418786443e3
```

## Verify Clean Worktree

```bash
git status --short
```

Expected: no output before release ceremony.

## Full Local Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests
make ci
git diff --check
git status --short
```

## Tag Proposal Only

Do not create tag until explicitly approved.

Proposed tag format:

```text
v0.1.0-rc.536+<HEAD_SHA>
```
