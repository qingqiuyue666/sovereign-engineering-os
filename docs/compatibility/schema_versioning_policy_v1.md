# Schema Versioning Policy V1

External review required: yes.

This policy defines compatibility rules for SEOS contract documents and the
frozen schema pack.

## Version Fields

JSON Schema files use `schema_version`. Public contract documents use
`contract_version`. The current frozen schema pack is `v11-slice1`, exposed by
`kernel/schemas/__init__.py` as `SCHEMA_FREEZE_TAG`.

## Compatibility Rules

A backward-compatible change is additive, documented, and accepted by old
readers without changing existing field meaning. A forward-compatible reader
may ignore documented optional fields but must reject unknown fields where the
contract says to reject unknown fields.

## Breaking Change

A breaking change changes required fields, field meaning, identity semantics,
receipt digest inputs, replay behavior, or failure behavior. Breaking changes
require a new version token, a migration mapping, and external review before
they are used as readiness evidence.

## Additive Change

An additive change may add optional fields only when the compatibility rule is
explicit, deterministic replay remains stable, and the version tuple hash can
distinguish the producer and policy versions.

## Deprecation Window

Deprecation requires a documented deprecation window, replacement field,
reader behavior, and removal condition. Removal before the window closes is a
breaking change.

## Migration Mapping

Migration mapping must be deterministic and auditable. It must preserve old
receipt ids, replay ids, evidence ids, or provide a documented mapping from old
ids to new ids.

## Fail Closed

Unsupported schema_version or contract_version values must fail closed. No
silent downgrade is allowed. Validators must report the unsupported version
instead of assuming compatibility.

No silent downgrade is permitted for schema or contract readers.

## Validation

Compatibility validation is performed by
`scripts/schema_compatibility_check_v1.py` and the matching tracer-bullet test.
The check confirms `v11-slice1`, contract compatibility sections, migration
requirements, and CI/Makefile wiring.
