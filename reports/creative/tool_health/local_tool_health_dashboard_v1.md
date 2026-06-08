# SEOS Local Tool Health Dashboard

- Mode: `public`
- Read-only: `True`
- DCC or AI tools launched: `False`
- Proprietary tools required for default CI: `[]`

## Summary

| Metric | Value |
| --- | ---: |
| tool_count | 13 |
| ready_or_detected_count | 7 |
| smoke_passed_count | 4 |
| available_but_untested_count | 2 |
| requires_user_launch_count | 1 |
| config_required_count | 4 |
| missing_count | 2 |
| blocked_count | 6 |

## Tool Health

| Tool | Status | Version | Configured path | Smoke capability | Next fix action |
| --- | --- | --- | --- | --- | --- |
| Python runtime | `FOUND_AND_SMOKE_PASSED` | `3.13.0` | `<local-path:python>` | SMOKE_PASSED_BY_DISCOVERY | Ready for gated local production use. |
| Python dependencies | `FOUND_AND_SMOKE_PASSED` | `present 1/1` | `-` | SMOKE_PASSED_BY_DISCOVERY | Ready for gated local production use. |
| macOS host | `FOUND_AND_SMOKE_PASSED` | `macOS-fixture` | `-` | SMOKE_PASSED_BY_DISCOVERY | Ready for gated local production use. |
| Apple Silicon | `FOUND_AND_SMOKE_PASSED` | `-` | `-` | SMOKE_PASSED_BY_DISCOVERY | Ready for gated local production use. |
| Git CLI | `FOUND_BUT_UNTESTED` | `-` | `<local-path:git>` | PATH_DETECTED_NO_SMOKE_RUN | Run an operator-approved smoke check before production execution. |
| FFmpeg CLI | `FOUND_BUT_UNTESTED` | `-` | `<local-path:ffmpeg>` | PATH_DETECTED_NO_SMOKE_RUN | Run an operator-approved smoke check before production execution. |
| Houdini / hython | `NOT_FOUND` | `-` | `-` | NOT_RUN_ENV_NOT_FOUND | Install the tool, add it to PATH, or configure an explicit local path. |
| ComfyUI | `CONFIG_REQUIRED` | `-` | `-` | NOT_RUN_CONFIG_REQUIRED | Configure ComfyUI path or service settings before running ComfyUI jobs. |
| Blender | `FOUND_BUT_REQUIRES_USER_LAUNCH` | `-` | `<local-path:Blender.app>` | CONFIG_DETECTED_APP_NOT_LAUNCHED | Launch or configure the app, then rerun the doctor before execution. |
| After Effects | `CONFIG_REQUIRED` | `-` | `-` | NOT_RUN_CONFIG_REQUIRED | Configure the local install or scripting path before adapter smoke tests. |
| DaVinci Resolve | `CONFIG_REQUIRED` | `-` | `-` | NOT_RUN_CONFIG_REQUIRED | Configure the local install or scripting path before adapter smoke tests. |
| Unreal Engine | `CONFIG_REQUIRED` | `-` | `-` | NOT_RUN_CONFIG_REQUIRED | Configure the local install or scripting path before adapter smoke tests. |
| ZBrush | `NOT_FOUND` | `-` | `-` | NOT_RUN_ENV_NOT_FOUND | Install the tool, add it to PATH, or configure an explicit local path. |

## Python Dependency Details

| Package | Status | Version |
| --- | --- | --- |
| `openpyxl` | `FOUND` | `3.1-fixture` |

## Next Actions

- Houdini / hython: Install the tool, add it to PATH, or configure an explicit local path.
- ComfyUI: Configure ComfyUI path or service settings before running ComfyUI jobs.
- After Effects: Configure the local install or scripting path before adapter smoke tests.
- DaVinci Resolve: Configure the local install or scripting path before adapter smoke tests.
- Unreal Engine: Configure the local install or scripting path before adapter smoke tests.
- ZBrush: Install the tool, add it to PATH, or configure an explicit local path.

## Safety

- Tool-health dashboard generation does not launch DCC or AI tools.
- Tool-health dashboard generation does not check out licenses.
- Missing tools remain unavailable evidence, not failures hidden as success.
- Default CI does not require Houdini, Blender, Unreal, DaVinci Resolve, After Effects, ZBrush, or ComfyUI.
