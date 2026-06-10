# SEOS Optional Adapter Contracts V1

- Mode: `public`
- Read-only: `True`
- DCC or AI tools launched: `False`
- Default CI requires proprietary tools: `False`

## Summary

| Metric | Value |
| --- | ---: |
| adapter_count | 5 |
| execution_supported_count | 0 |
| ready_for_manual_dry_run_count | 1 |
| config_required_count | 3 |
| env_not_found_count | 1 |
| contract_only_count | 0 |

## Contracts

| Adapter | Status | Discovery | Execution | Next local proof |
| --- | --- | --- | --- | --- |
| Blender | `READY_FOR_MANUAL_DRY_RUN` | `FOUND_BUT_REQUIRES_USER_LAUNCH` | `CONTRACT_ONLY` | fixed blender --background smoke script that writes version and scene summary JSON |
| After Effects | `CONFIG_REQUIRED` | `CONFIG_REQUIRED` | `CONTRACT_ONLY` | fixed aerender or app-version smoke with no arbitrary JSX and no project mutation |
| DaVinci Resolve | `CONFIG_REQUIRED` | `CONFIG_REQUIRED` | `CONTRACT_ONLY` | read-only Resolve scripting smoke that reports version and project access without rendering |
| Unreal Engine | `CONFIG_REQUIRED` | `CONFIG_REQUIRED` | `CONTRACT_ONLY` | fixed UnrealEditor commandlet help/version smoke with no project save |
| ZBrush | `ENV_NOT_FOUND` | `NOT_FOUND` | `CONTRACT_ONLY` | manual export handoff verification; no default automated ZBrush runner |

## Adapter Details

### Blender

- Adapter: `blender`
- Current level: `LEVEL_2_SMOKE_TEST`
- Summary: Background Python smoke and staged preview contracts only.
- Supports execute: `False`
- Required operator inputs: blender executable path, blend file or generated fixture scene, output root
- Existing artifacts: creative/adapters/blender/adapter.py, creative/adapters/blender/background_runner.py, creative/adapters/blender/preview_render.py, creative/adapters/blender/asset_check.py
- Risk notes: addon side effects, GPU/headless instability, long render runtime

### After Effects

- Adapter: `after_effects`
- Current level: `LEVEL_1_DRY_RUN`
- Summary: Aerender and JSX contract planning only.
- Supports execute: `False`
- Required operator inputs: After Effects app path, approved fixture project, output root
- Existing artifacts: creative/adapters/after_effects/adapter.py, creative/adapters/after_effects/aerender_contract.py, creative/adapters/after_effects/jsx_contract.py, creative/adapters/after_effects/plugin_dependency_check.py
- Risk notes: GUI launch side effects, plugin licensing, project/plugin compatibility

### DaVinci Resolve

- Adapter: `davinci`
- Current level: `LEVEL_1_DRY_RUN`
- Summary: Scripting and render-job manifest contracts only.
- Supports execute: `False`
- Required operator inputs: Resolve scripting availability, project or timeline manifest, delivery output root
- Existing artifacts: creative/adapters/davinci/adapter.py, creative/adapters/davinci/scripting_contract.py, creative/adapters/davinci/project_manifest.py, creative/adapters/davinci/render_job_manifest.py
- Risk notes: GUI session dependence, project database mutation, codec/license availability

### Unreal Engine

- Adapter: `unreal`
- Current level: `LEVEL_1_DRY_RUN`
- Summary: Commandlet, Sequencer, and MRQ manifest contracts only.
- Supports execute: `False`
- Required operator inputs: UnrealEditor path, uproject path, map or sequence identifier, output root
- Existing artifacts: creative/adapters/unreal/adapter.py, creative/adapters/unreal/commandlet_contract.py, creative/adapters/unreal/mrq_manifest.py, creative/adapters/unreal/sequencer_manifest.py
- Risk notes: project upgrade prompts, shader compilation runtime, plugin/license mismatch

### ZBrush

- Adapter: `zbrush`
- Current level: `LEVEL_0_REGISTRY_ONLY`
- Summary: Registry, export-manifest, and manual handoff contracts only.
- Supports execute: `False`
- Required operator inputs: sculpt registry entry, export manifest, manual handoff checklist
- Existing artifacts: creative/adapters/zbrush/adapter.py, creative/adapters/zbrush/sculpt_registry.py, creative/adapters/zbrush/export_manifest.py, creative/adapters/zbrush/handoff_checklist.py
- Risk notes: limited stable headless automation, manual save/export risk, license/UI dependence

## Safety

- These contracts do not launch DCC applications.
- These contracts do not submit render, generation, import, export, or commandlet jobs.
- These contracts do not install plugins, download models, or use external networks.
- Future runners require separate approval-gated slices and real local evidence.

## Next Actions

- Blender: review contract and run only manual dry-run/handoff steps.
- After Effects: configure local path or scripting settings before any smoke runner.
- DaVinci Resolve: configure local path or scripting settings before any smoke runner.
- Unreal Engine: configure local path or scripting settings before any smoke runner.
- ZBrush: install or expose the tool before adapter smoke work.
