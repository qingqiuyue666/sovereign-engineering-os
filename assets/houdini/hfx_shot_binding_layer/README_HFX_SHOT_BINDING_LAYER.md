# HFX Factory Shot Binding Layer

Status target: `HFX_SHOT_BINDING_LAYER_GLOBAL_SEAL_PASS`

This layer turns the sealed HFX Factory Core 12 release assets into deterministic per-shot working packages. It derives every generated shot package from the existing release packages under `assets/houdini/hfx_factory_core12/` and copies release HIP files into a shot-local workspace before any shot work begins.

This is not Hollywood final-pixel shot delivery. It does not render OpenEXR sequences. It does not produce final comp. It creates deterministic, auditable, replayable, local-first shot binding packages that can be validated without mutating release HIP files.

## What It Creates

Given a `ShotBindingRequest`, the binder creates:

```text
<output_root>/<project_id>/<sequence_id>/<shot_id>/<take_id>/
  00_request/
  01_source_assets/
  02_shot_hip/
  03_parameters/
  04_render_contract/
  05_comp_contract/
  06_validation/
  07_manifests/
  08_docs/
```

Each enabled asset receives a copied shot HIP, parameter JSON, source-release reference, and binding manifest record. The package records source release HIP SHA-256, copied shot HIP SHA-256, final seal path, and the registry entry snapshot used for binding.

## Hard Boundaries

- Release HIP files under `assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/**/10_release/release_package/hip/*.hip` are never modified.
- Output paths inside `assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE` or `assets/houdini/hfx_factory_core12/500_HFX_FACTORY` are rejected.
- Unknown asset IDs, duplicate asset IDs, invalid frame ranges, missing final seals, and missing release HIP files fail closed.
- Package validation rejects movie/archive side products such as `.mp4`, `.mov`, `.zip`, `.7z`, and `.DS_Store`.

## CLIs

Bind a shot:

```bash
python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_bind_shot.py --request assets/houdini/hfx_shot_binding_layer/examples/shot_request_energy_impact.json
```

Validate a generated package:

```bash
python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_validate_shot_package.py --shot-package /tmp/hfx_shot_binding_output/HFX_DEMO/SEQ010/SH010/TAKE_A
```

Run the layer global seal:

```bash
python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_shot_binding_global_seal.py
```

Run tests and the global seal:

```bash
bash assets/houdini/hfx_shot_binding_layer/tools/run_hfx_shot_binding_tests.sh
```

## Next Layer

The next layer after this is render automation: Houdini batch render orchestration, OpenEXR sequence generation and validation, comp automation, and final-pixel review gates.
