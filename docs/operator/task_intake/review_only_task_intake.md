# Review-Only Task Intake

## task goal

Perform audit or review without mutating repository-tracked files.

## allowed files

- none for edits
- read-only inspection targets only

## forbidden files

- all repository-tracked files for mutation

## required tests

- only the tests explicitly authorized for read-only validation

## blocked capabilities

- no edits
- no commit
- no push
- no PR creation

## output format

Evidence-first review report.

## rollback expectation

No rollback because no repository mutation is allowed.

## human review requirement

Human review required to convert findings into implementation.
