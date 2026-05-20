# Sovereign Console UI Engineering Spec v1

## Product Concept

Sovereign Console is the native desktop command-and-observe surface for the local Sovereign Engineering OS runtime. The console is a unified production workspace: mission-centered, compact, local-first, and strict about the line between observed state and real execution.

The console is not a chatbot, web frontend, node editor, or menu collection. The product IA has five primary domains:

- Workspace
- Runs
- Artifacts
- Reviews
- Settings

## Design Direction

The visual direction is a quiet native workspace with compact professional hierarchy. Design tokens:

- main background: `#ECECEE`
- card/table background: `#FFFFFF`
- technical panel background: `#0D0D0D`
- running blue: `#0066CC`
- success green: `#34C759`
- warning orange: `#FF9500`
- fatal red: `#FF3B30`

## Runtime Boundary

The GUI is a read-model and command-issuer only. Real work remains behind:

`GUI -> OS Runtime Facade -> SQLite Job Queue -> Worker Registry -> Worker -> Artifact Store -> Event Log -> Human Review Gate -> GUI Projection`

Widgets may display runtime projection, jobs, artifacts, reviews, quarantine state, event stream rows, mission state, and disabled command intents. Widgets must not directly start processes, launch creative tools, mutate SQLite job state, mutate artifact storage, upload files, delete or overwrite files, claim production outcomes, or route around the human gate.

## App Shell

The app is one `QMainWindow` with:

- Reduced left rail containing exactly Workspace, Runs, Artifacts, Reviews, Settings.
- Compact System Pulse chips at the top.
- Central `QStackedWidget` workspace.
- Designed right Inspector.
- Collapsed bottom Event Stream / Black Box.

Workspace is the default startup page.

## Workspace

Workspace is the primary mission surface. It contains the current mission card, command intent placeholder, next required action, compact HFX_008 landing chain, recent runs, recent artifacts, pending review count, quarantine count, local runtime status, degraded sync banner, and context packet quick actions.

The default mission is `HFX_008 Energy Shockwave`.

Mission card fields:

- mission_id
- mission_name
- mission_type
- status
- final_claim_allowed
- blocked_reason
- next_action
- latest_artifact
- latest_run
- required_resource_state
- human_review_state

The compact HFX_008 chain is:

`Topology Audit -> Proof Artifact -> Validation -> Human Review -> Summary -> Claim Gate`

Context packet actions live here as disabled or facade-routed intents: Gemini packet, Codex task packet, Claude review packet, HFX dry-run intent, latest artifact inspection, and navigation handoffs.

## Runs

Runs absorbs the old job queue, worker status, event trail, and execution state. The page uses `QTableView` with `QAbstractTableModel`; `QTableWidget` is not used for refreshed data.

Runs displays run ID, type, status chip, worker, creation time, runtime, event count, artifact count, human review requirement, and failure reason. Cancel and retry controls are intent placeholders only unless the OS Runtime Facade admits them.

## Artifacts

Artifacts absorbs Artifact Store and Asset Library. It is an artifact observatory with a table projection, preview placeholder, checksum, size, local path alias, review status, quarantine status, `safe_to_publish`, `local_only`, asset library placeholder, and resource intake placeholder.

Artifact controls do not open, upload, mutate, delete, overwrite, or publish files unless a safe runtime route is added.

## Reviews

Reviews absorbs Human Review and Failure Quarantine. It has segmented sections:

- Pending Reviews
- Rejected
- Quarantined
- Failures

Reviews displays review list, selected artifact preview placeholder, gated approve/reject/quarantine controls, reject reason validation, quarantine state, failure reason, traceback dark panel, event trail, recommended fix, and final-claim warning.

## Settings

Settings absorbs Settings / Boundaries and System Health. It has sections:

- Runtime
- Language
- Motion
- Boundaries
- Paths
- Workers
- Publishing
- System Health

Settings displays language Auto / English / Chinese, motion intensity Minimal / Standard / High Energy, local-only mode, external network disabled, asset root path, artifact root path, allowed workers, dangerous action gates, human review gates, publish policy, GitHub summary-only policy, memory, WAL state, DB connection state, last smoke result, last CI result, and warnings.

## Sync States

Sync has three states:

- Healthy: full read projection is available.
- Degraded: runtime projection is unavailable at startup or before any known healthy projection. The UI remains readable, navigation remains available, and action controls are locked. The banner says `Runtime projection unavailable. Read-only workspace is active.`
- Lost: a previously healthy projection becomes stale or unavailable. Action controls remain locked and the overlay says `SYSTEM SYNC LOST — ACTIONS LOCKED`.

Startup with no runtime projection must be Degraded, not Lost.

## Event Stream

The Event Stream / Black Box is compact and collapsed by default. Expanded height is approximately 120px. Rows are structured with severity, timestamp, event type, object ID, and message. Rows are capped to prevent unbounded memory growth. Canonical event types remain English because they are audit data.

## System Pulse

The System Pulse is grouped chips, not raw debug labels. It displays Runtime, WAL, Runs, Workers, Memory, Warnings, Sync, and Next Action.

## Inspector

The right Inspector supports no selection, selected mission, selected run, selected artifact, selected review, selected failure, and selected setting/boundary. The no-selection state says:

`Select a run, artifact, review, or mission stage to inspect.`

Chinese:

`选择运行、产物、审查或任务阶段以查看详情。`

## Localization

Localization covers display labels only. Canonical event types, status codes, audit payloads, and human-entered review reasons remain unchanged.

Required IA labels include Workspace / 工作台, Runs / 运行, Artifacts / 产物, Reviews / 审查, Settings / 设置, Mission / 任务, Current Mission / 当前任务, Next Required Action / 下一步必需动作, Event Stream / 事件流, Black Box / 黑匣子, Pending Reviews / 待审查, Quarantined / 已隔离, Failures / 失败, Boundaries / 边界, Local-only / 仅本地, and External network disabled / 外部网络已禁用.

## Motion

Motion remains subtle and state-driven: mission chain line, status chip glow, warning badge pulse, event intent feedback, artifact placeholder glow, review seal, and quarantine stripe. Motion must never block reading or change business state.
