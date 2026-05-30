# Workspace Cleanup Policy V1

External review required: yes.

This policy keeps readiness workspaces reproducible after local and CI runs.

## Workspace Cleanup

Before starting a wave and after post-merge validation, run `git status
--short`. The expected end state is a clean tracked-file workspace.

## Tracked Files

Tracked files must be changed only for the active wave. Unrelated tracked
changes are treated as operator-owned unless the task explicitly says
otherwise.

## Temporary Files

Temporary files belong in tool-managed temp locations or ignored build
directories. Benchmark temp workspaces must be created outside tracked
evidence paths and removed by the command that created them.

## Secret Material

Do not read, copy, print, or persist secret material during cleanup. Cleanup
must not inspect `.env` content, keychains, credential files, or token stores.

## Verification

Cleanup verification is `git status --short`, followed by the relevant
validator if generated artifacts changed.
