# HFX Shot Binding Operator Manual

This manual covers the local-first shot binding layer for the sealed HFX Factory Core 12 reusable assets. The layer creates shot working packages; it does not render pixels or finalize comps.

## Create A Request

Start from one of the examples in `assets/houdini/hfx_shot_binding_layer/examples/`.

Required request fields:

- `project_id`, `sequence_id`, `shot_id`, `take_id`
- `frame_start`, `frame_end`, `fps`
- `plate_path`, `camera_path`, `hdri_path`, `lens_profile_path`
- `output_root`
- `requested_assets`
- `render_target`, `comp_target`
- `notes`

Each requested asset must include:

- `asset_id`
- `enabled`
- `parameter_overrides`
- `dependency_policy`

The binder rejects duplicate asset IDs, unknown asset IDs, empty asset lists, and `frame_end` values earlier than `frame_start`.

## Bind A Shot

Run:

```bash
python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_bind_shot.py --request assets/houdini/hfx_shot_binding_layer/examples/shot_request_energy_impact.json
```

The package is written to:

```text
<output_root>/<project_id>/<sequence_id>/<shot_id>/<take_id>/
```

The binder copies release HIP files into `02_shot_hip/` and writes per-asset parameter JSON into `03_parameters/`. Source release HIPs remain untouched.

## Validate A Shot Package

Run:

```bash
python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_validate_shot_package.py --shot-package /tmp/hfx_shot_binding_output/HFX_DEMO/SEQ010/SH010/TAKE_A
```

Validation verifies the manifest, request snapshot, copied HIPs, source release HIPs, source and copied SHA-256 values, render contract, comp contract, operator guide, validation report, and forbidden side-product file types.

## Run The Global Seal

Run:

```bash
python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_shot_binding_global_seal.py
```

The global seal validates the Core 12 final global seal, schemas, all examples, generated shot packages, and layer manifests. It writes:

- `assets/houdini/hfx_shot_binding_layer/validation/HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.json`
- `assets/houdini/hfx_shot_binding_layer/validation/HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL.md`
- `assets/houdini/hfx_shot_binding_layer/manifests/HFX_SHOT_BINDING_LAYER_MANIFEST.json`
- `assets/houdini/hfx_shot_binding_layer/manifests/HFX_SHOT_BINDING_LAYER_SHA256SUMS.txt`
- `assets/houdini/hfx_shot_binding_layer/manifests/HFX_SHOT_BINDING_LAYER_FILE_TREE.txt`

## Use The Copied HIP Files

Open only the copied HIP files in `02_shot_hip/`. Apply shot-specific changes there and use `03_parameters/` as the authoritative shot parameter record. The source release package path and SHA-256 are recorded in `07_manifests/`.

## What Not To Edit

- Do not edit Core 12 release HIP files.
- Do not write shot output inside `assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE`.
- Do not write shot output inside `assets/houdini/hfx_factory_core12/500_HFX_FACTORY`.
- Do not rewrite final asset seal JSON files.
- Do not edit the source registry to force a shot bind.

## Blocked Claims

This layer does not claim:

- Hollywood final-pixel shot completion
- OpenEXR render completion
- Final comp completion
- Client/public delivery readiness

## Next Production Steps

The next production layer should automate Houdini batch rendering, produce real OpenEXR sequences, validate those EXRs, drive comp automation in Nuke, After Effects, or DaVinci Resolve, and add final-pixel review gates.
