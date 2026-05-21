# Sovereign Console UI Design System Contract v1

Status: binding local repository contract.

This contract is the source of truth for future Sovereign Console UI work. It is
not a mockup, implementation ticket, backend design, or visual exploration. Any
UI branch that conflicts with this document is out of contract even when the code
is technically functional.

## Product Direction

Sovereign Console = Apple Mission Control Workspace.

The product is a macOS professional desktop app: a unified command workspace,
local-first production OS control surface, and mission-centered operator surface.
It is Apple/Finder/Xcode/Raycast-inspired, high-density but readable, and calm
under degraded runtime conditions.

Approved visual posture:

- light-gray Apple base
- white mission cards
- compact macOS-style sidebar
- large command bar
- inspector as a steady detail surface
- dark compact Black Box only
- subtle Houdini procedural energy only inside HFX mission chain/status feedback

Rejected product identities:

- mobile app
- web app
- SaaS dashboard
- chatbot clone
- plugin marketplace
- raw Qt form
- database admin panel
- black sci-fi concept screen
- cyberpunk console
- game HUD
- scattered menu collection

## Top-Level IA Contract

Top-level navigation must always remain exactly:

CANONICAL_PRIMARY_NAVIGATION:
1. Workspace
2. Runs
3. Artifacts
4. Reviews
5. Settings

No sixth primary entry is allowed. No page may promote an absorbed operational
concern back into first-level navigation.

Forbidden first-level nav entries:

- Dashboard
- Job Queue
- HFX Factory
- HFX_008 Landing Chain
- Context Packs
- Human Review
- Failure Quarantine
- Artifact Store
- Asset Library
- System Health
- Boundaries

Absorption rule:

| Old first-level concept | Required location |
| --- | --- |
| Dashboard | Workspace |
| Job Queue | Runs |
| HFX Factory | Workspace Mission section |
| HFX_008 Landing Chain | Workspace Current Mission Card |
| Context Packs | Workspace command/actions |
| System Health | Settings |
| Human Review | Reviews |
| Failure Quarantine | Reviews |
| Artifact Store | Artifacts |
| Asset Library | Artifacts |
| Boundaries | Settings |

## Canonical Layout Contract

This is the only approved shell layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ macOS titlebar / compact System Pulse chips                  │
├──────────────┬───────────────────────────────┬───────────────┤
│ Sidebar      │ Workspace                     │ Inspector     │
│ 200px        │ flexible                      │ 280px         │
│              │                               │               │
│ Workspace    │ Large Command Bar             │ No Selection  │
│ Runs         │                               │ / Selection   │
│ Artifacts    │ Degraded Banner if needed     │ Details       │
│ Reviews      │                               │               │
│ Settings     │ Current Mission Card          │ Runtime       │
│              │ HFX_008 Energy Shockwave      │ Sync          │
│              │ HFX Energy Chain              │ Policy        │
│              │                               │ Gates         │
│              │ Recent Runs / Artifacts       │               │
│              │ Pending Reviews / Quarantine  │               │
├──────────────┴───────────────────────────────┴───────────────┤
│ Black Box · 0 warnings · Last event · Show                    │
└──────────────────────────────────────────────────────────────┘
```

Required spatial rules:

- Sidebar fixed around 200px.
- Inspector fixed around 280px.
- Workspace flexible.
- Black Box collapsed by default.
- Event Stream must not dominate the app.
- System Pulse must be compact chips, not debug label strips.
- Workspace default page.
- Command Bar visually dominant.
- Current Mission Card is the hero object.

## Visual System Contract

Base design tokens:

| Token | Value |
| --- | --- |
| app background | `#F5F5F7` |
| sidebar background | `#ECECEE` |
| workspace background | `#F5F5F7` |
| card background | `#FFFFFF` |
| inspector background | `#F2F2F7` |
| border | `#D1D1D6` |
| primary text | `#1D1D1F` |
| secondary text | `#6E6E73` |
| muted label | `#86868B` |

Dark technical tokens are allowed only for the compact Black Box:

| Token | Value |
| --- | --- |
| black box background | `#0D0D0D` |
| log text | `#E5E5EA` |
| log muted | `#8E8E93` |

Status tokens:

| Status | Value |
| --- | --- |
| running blue | `#0A84FF` |
| success green | `#30D158` |
| warning orange | `#FF9F0A` |
| failure red | `#FF453A` |
| artifact teal | `#00A6A6` |
| context purple | `#7D5FFF` |

Typography:

- UI uses the system font.
- IDs, logs, and technical values use monospace.
- Labels are small uppercase where a compact label is needed.
- No huge marketing text.
- No raw Qt label strips.

Spacing:

- Use the 8px / 16px / 24px grid.
- Avoid excessive borders.
- Avoid giant black regions.
- Avoid mobile card spacing.
- Avoid thick debug outlines.

## Component Contracts

### Sidebar

Must:

- use exactly five primary entries: Workspace, Runs, Artifacts, Reviews, Settings
- look like a macOS Finder/Xcode sidebar
- support selected state
- support badge slot
- avoid page sprawl

Must not look like a raw QPushButton stack.

### System Pulse

Must show compact chips:

- Runtime
- WAL
- Runs
- Workers
- Memory
- Sync
- Warnings
- Next

Must not look like debug labels.

### Workspace

Workspace is the default page and must include:

- large Raycast/Codex-style Command Bar
- degraded banner if runtime unavailable
- Current Mission Card
- HFX_008 Energy Chain
- Recent Runs
- Recent Artifacts
- Pending Reviews
- Quarantine summary
- Context packet quick actions

### Command Bar

The Command Bar must be visually dominant, 44-52px high, rounded, safe/gated,
and display a clear placeholder. It is an intent surface only. It must not
directly execute work.

Command Bar rule: must not directly execute work.

### Current Mission Card

The Current Mission Card is the hero object. It must show:

- HFX_008 Energy Shockwave
- status chip
- next action
- blocked reason
- latest run
- latest artifact
- review state
- final_claim_allowed
- compact HFX chain

It must not be a raw QFormLayout table dump.

### HFX Chain

Stages:

Topology Audit
→ Proof Artifact
→ Validation
→ Human Review
→ Summary
→ Claim Gate

Allowed visual language:

- small nodes
- thin connector lines
- subtle status glow
- downstream dimming

Forbidden visual language:

- heavy particles
- screen shake
- glass break
- QGraphicsView node editor
- drag/drop node graph

### Inspector

Default state must not be blank. It must show:

- selection guidance
- Runtime Mode
- Sync State
- Policy: Local-only
- Gates state

Default guidance:

`Select a mission, run, artifact, or review to inspect.`

### Black Box

Collapsed default text:

`Black Box · 0 warnings · Show`

Expanded max height: 120-140px.

Rows must be structured as:

`timestamp | severity | object_id | event_type | message`

The Black Box must not grow without bound, take over the workspace, or become
the primary navigation model.

## Sync State Contract

Startup without runtime projection:

- state = Degraded
- no full-screen SYSTEM SYNC LOST overlay
- show calm banner:
  - `Runtime projection unavailable. Read-only workspace is active.`
  - `运行时投影不可用。当前为只读工作台。`

Lost state:

- only if previously healthy runtime becomes stale/lost
- stronger overlay allowed
- actions locked

## I18N Contract

Display labels must include:

| English | Chinese |
| --- | --- |
| Workspace | 工作台 |
| Runs | 运行 |
| Artifacts | 产物 |
| Reviews | 审查 |
| Settings | 设置 |
| Command | 命令 |
| Current Mission | 当前任务 |
| Next Action | 下一步动作 |
| Read-only Workspace | 只读工作台 |
| Runtime projection unavailable | 运行时投影不可用 |
| Black Box | 黑匣子 |
| Event Stream | 事件流 |
| Select a mission, run, artifact, or review to inspect. | 选择任务、运行、产物或审查以查看详情。 |
| Local-only | 仅本地 |
| Actions Locked | 操作已锁定 |
| Degraded | 降级 |
| Lost | 丢失 |

Canonical internal event/status codes remain English.

## Execution Boundary Contract

GUI remains read-model + gated intent issuer only.

GUI must not:

- directly run subprocess
- directly launch Houdini
- directly call ComfyUI
- directly call DaVinci
- directly create network clients
- directly mutate SQLite job queue
- directly mutate artifact store
- delete/overwrite files
- upload files
- bypass OS Runtime
- bypass Job Queue
- bypass Human Review Gate
- claim final completion

All future actions must conceptually route through:

`GUI -> OS Runtime Facade -> SQLite Job Queue -> Worker Registry -> Worker -> Artifact Store -> Event Log -> Human Review Gate -> GUI Projection`

## Contract Use

Future UI tickets must cite this contract before changing layout, navigation,
visual tokens, component behavior, degraded/lost sync behavior, labels, or action
surfaces. The companion skill is
`docs/ui/sovereign_console_ui_skill_v1.md`.
