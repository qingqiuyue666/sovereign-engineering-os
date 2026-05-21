# Sovereign Console UI Skill v1

Use this repository-local skill for every future Sovereign Console UI task.
Before editing UI code, tests, or visual docs, read and apply
`docs/ui/sovereign_console_ui_design_system_contract_v1.md`.

## Skill Goal

Keep Sovereign Console on one stable product path:

Sovereign Console = Apple Mission Control Workspace.

The UI must feel like a macOS professional desktop control surface inspired by
Finder, Xcode, Raycast, and Apple Mission Control. It must remain local-first,
mission-centered, high-density, readable, and calm.

## Required First Pass

For any UI request:

1. Verify that the work fits one of the five primary entries.
2. Keep Workspace as the default surface.
3. Route old page concepts into their absorbed homes.
4. Preserve the canonical shell: 200px sidebar, flexible workspace, 280px
   inspector, compact top System Pulse, collapsed bottom Black Box.
5. Preserve the execution boundary: GUI issues gated intents only.

## Primary Navigation

Only these first-level entries are allowed:

1. Workspace
2. Runs
3. Artifacts
4. Reviews
5. Settings

Old first-level concepts are absorbed:

- Dashboard into Workspace
- Job Queue into Runs
- HFX Factory into Workspace Mission section
- HFX_008 Landing Chain into Workspace Current Mission Card
- Context Packs into Workspace command/actions
- System Health into Settings
- Human Review into Reviews
- Failure Quarantine into Reviews
- Artifact Store into Artifacts
- Asset Library into Artifacts
- Boundaries into Settings

## Visual Decisions

Use the contract tokens exactly. The normal app is light gray and white:
`#F5F5F7`, `#ECECEE`, `#FFFFFF`, `#F2F2F7`, `#D1D1D6`,
`#1D1D1F`, `#6E6E73`, `#86868B`.

Dark UI is limited to the compact Black Box with `#0D0D0D`, `#E5E5EA`, and
`#8E8E93`.

Status colors are `#0A84FF`, `#30D158`, `#FF9F0A`, `#FF453A`, `#00A6A6`, and
`#7D5FFF`.

Use system font for UI. Use monospace only for IDs, logs, and technical values.
Use the 8px / 16px / 24px spacing grid.

## Component Checklist

Workspace must include the large Raycast/Codex-style Command Bar, degraded
banner when needed, Current Mission Card, HFX_008 Energy Chain, Recent Runs,
Recent Artifacts, Pending Reviews, Quarantine summary, and context packet quick
actions.

Current Mission Card must show HFX_008 Energy Shockwave, status chip, next
action, blocked reason, latest run, latest artifact, review state,
final_claim_allowed, and a compact HFX chain.

Inspector default state must never be empty. It shows selection guidance,
Runtime Mode, Sync State, Policy: Local-only, and Gates state.

Black Box is collapsed by default as `Black Box · 0 warnings · Show`, expands
only to 120-140px, and uses structured rows:

`timestamp | severity | object_id | event_type | message`

## HFX Chain

Use this exact stage sequence:

Topology Audit
→ Proof Artifact
→ Validation
→ Human Review
→ Summary
→ Claim Gate

Keep the visual treatment small: nodes, thin connector lines, subtle status
glow, and downstream dimming only.

## Sync And Labels

Startup without runtime projection is Degraded, not Lost. Show:

`Runtime projection unavailable. Read-only workspace is active.`

`运行时投影不可用。当前为只读工作台。`

Required bilingual display labels include Workspace / 工作台, Runs / 运行,
Artifacts / 产物, Reviews / 审查, Settings / 设置, Command / 命令,
Current Mission / 当前任务, Next Action / 下一步动作, Read-only Workspace /
只读工作台, Runtime projection unavailable / 运行时投影不可用, Black Box /
黑匣子, Event Stream / 事件流, Local-only / 仅本地, Actions Locked / 操作已锁定,
Degraded / 降级, and Lost / 丢失.

Canonical internal event/status codes remain English.

## Hard Rejections

Reject UI directions that turn Sovereign Console into a mobile app, web app,
SaaS dashboard, chatbot clone, plugin marketplace, raw Qt form, database admin
panel, black sci-fi concept screen, cyberpunk console, game HUD, or scattered
menu collection.

Reject raw QFormLayout mission dumps, raw QPushButton navigation stacks,
QGraphicsView node editors, drag/drop node graphs, huge dark regions, debug
label strips, and unbounded event streams.

## Execution Boundary

The GUI is read-model + gated intent issuer only. It must not directly run
subprocesses, launch Houdini, call ComfyUI, call DaVinci, create network clients,
mutate SQLite job state, mutate artifact storage, delete or overwrite files,
upload files, route around runtime gates, route around the human review gate, or
claim production closure.

Boundary check: directly run subprocesses is forbidden.

All action concepts must route through:

`GUI -> OS Runtime Facade -> SQLite Job Queue -> Worker Registry -> Worker -> Artifact Store -> Event Log -> Human Review Gate -> GUI Projection`
