# Anytype Integration

Anytype support is a neutral object-model adapter. SEOS does not vendor Anytype
source code, depend on the Anytype runtime, or use Anytype as an authority layer.

## Supported Role

- object/type/relation export for operator review
- object-model proposal import
- public-safe digest and relation summary
- local JSON handoff format

## Unsupported Role

- execution authority
- approval or permit source of truth
- bundled Anytype source dependency
- cloud or peer-to-peer sync step
- secret or private asset store

## Runtime Path

```bash
python3 seos.py knowledge export-anytype \
  --workspace .seos-workspace \
  --output reports/knowledge/anytype_object_bundle.json \
  --json

python3 seos.py knowledge import-anytype \
  --source reports/knowledge/anytype_object_bundle.json \
  --output reports/knowledge/anytype_import_record.json \
  --json
```

Import records are `object_model_proposal_only`. They do not create SEOS tasks,
approvals, permits, receipts, or execution authority.
