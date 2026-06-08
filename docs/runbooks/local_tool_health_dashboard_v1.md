# Local Tool Health Dashboard v1 Runbook

## Purpose

Use SEOS to inspect the local creative workstation before attempting real DCC,
AI, video, or asset-processing work. The dashboard is a truthful availability
report: it can show that a tool is found, missing, config-required, found but
untested, or found but requiring manual app launch. It does not launch DCC or AI
tools and does not check out licenses.

## Command

```bash
python3 seos.py creative tool-health-dashboard \
  --mode public \
  --output-json reports/creative/tool_health/local_tool_health_dashboard.json \
  --output-md reports/creative/tool_health/local_tool_health_dashboard.md \
  --output-html reports/creative/tool_health/local_tool_health_dashboard.html
```

Use `--mode public` for sanitized artifacts. Use `--mode local` only for
operator-private reports when local paths are needed for setup work.

Alias:

```bash
python3 seos.py creative dashboard tool-health \
  --mode public \
  --output-md reports/creative/tool_health/local_tool_health_dashboard.md
```

## What It Reports

- Python runtime and Python project dependency imports.
- Git and FFmpeg command-line availability.
- Houdini/hython, ComfyUI, Blender, After Effects, DaVinci Resolve, Unreal
  Engine, and ZBrush availability.
- Version when the current discovery layer can detect one without launching the
  tool.
- Sanitized configured path when a path is known.
- Smoke capability:
  - `SMOKE_PASSED_BY_DISCOVERY`
  - `PATH_DETECTED_NO_SMOKE_RUN`
  - `CONFIG_DETECTED_APP_NOT_LAUNCHED`
  - `NOT_RUN_CONFIG_REQUIRED`
  - `NOT_RUN_ENV_NOT_FOUND`
  - `NOT_RUN_LICENSE_BLOCKED`
- Next fix action for every missing or blocked tool.

## Safety Boundary

The dashboard:

- reads local PATH, project dependency metadata, and safe app-location hints;
- does not mutate project files except for explicit output report paths;
- does not launch Houdini, Blender, ComfyUI, Unreal, After Effects, DaVinci, or
  ZBrush;
- does not submit network requests to ComfyUI;
- does not check out licenses;
- does not claim tool execution success;
- does not require proprietary tools in default CI.

## Operator Review

1. Install or configure missing command-line tools first if a workflow needs
   them.
2. For `FOUND_BUT_UNTESTED`, run a human-approved smoke before production use.
3. For `FOUND_BUT_REQUIRES_USER_LAUNCH`, open or configure the application
   manually, then rerun the dashboard.
4. For `CONFIG_REQUIRED`, set the required local path or service configuration
   before running any adapter.
5. Treat `NOT_FOUND` as unavailable evidence, not as a hidden success.

## Validation

```bash
make creative-tool-health-dashboard-check
python3 seos.py creative tool-health-dashboard \
  --mode public \
  --doctor-json tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json \
  --output-md reports/creative/tool_health/local_tool_health_dashboard.md
python3 seos.py creative doctor
git diff --check
```
