# HFX v006 HDA Interface Rulebook

Status: HFX_V006_HDA_INTERFACE_RULEBOOK_READY

Purpose:
Define the exact HDA interface mapping before actual Houdini Digital Asset creation.

v006 does not create final .hda files.
v006 creates:
- HDA parameter interface maps
- internal node mapping contracts
- output node alias contracts
- cache/export parameter contracts
- validation rules for future HDA packaging

Final .hda creation is deferred until v007.

---

## Required HDA Interface Groups

Every HDA candidate must expose the following folders:

1. 00_GLOBAL
2. 01_INPUT
3. 02_TIMING
4. 03_SHAPE
5. 04_MOTION
6. 05_LOOKDEV
7. 06_OUTPUT
8. 07_DEBUG

---

## Required Public Parameters

### 00_GLOBAL
- asset_id
- asset_version
- shot_scale
- intensity
- seed
- enable_preview
- enable_cache
- enable_export

### 01_INPUT
- input_mode
- attach_target
- world_tx
- world_ty
- world_tz
- world_rx
- world_ry
- world_rz
- input_curve_path
- ground_proxy_path
- collision_proxy_path

### 02_TIMING
- trigger_frame
- frame_start
- frame_end
- duration_frames
- attack
- decay_start
- time_offset

### 03_SHAPE
- primary_scale
- secondary_scale
- radius_start
- radius_end
- width
- density
- turbulence

### 04_MOTION
- outward_speed
- upward_speed
- wind_x
- wind_y
- wind_z
- gravity
- expansion_speed

### 05_LOOKDEV
- color_r
- color_g
- color_b
- emission_strength
- glow_width
- opacity
- material_mode

### 06_OUTPUT
- output_main
- output_layer_a
- output_layer_b
- output_layer_c
- cache_path
- export_path
- export_format

### 07_DEBUG
- show_guides
- show_sources
- show_bounds
- show_debug_layers
- debug_output_mode

---

## Locked Output Aliases

All HDA candidates must publish stable output aliases:

- OUT_MAIN
- OUT_RENDER
- OUT_CACHE
- OUT_DEBUG
- OUT_LAYER_A
- OUT_LAYER_B
- OUT_LAYER_C
- OUT_LAYER_D where required
- OUT_LAYER_E where required

Internal v003 output names may remain unchanged.
The HDA layer must map stable aliases to internal nodes.

---

## v006 Pass Marker

Final pass marker:

HFX_V006_HDA_INTERFACE_SPEC_PASS
