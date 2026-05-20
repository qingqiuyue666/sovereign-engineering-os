# Sovereign Console UI Engineering Spec v1

## Product Concept

Sovereign Console, also called Sovereign C2, is the native desktop command-and-observe surface for the local Sovereign Engineering OS runtime. It is a living production console: quiet enough for repeated operational use, strict enough for governed execution, and always clear about what is observed, what is queued, and what still requires a human.

The console is not a chatbot, web frontend, node graph, or final production surface. Phase 1 delivered the first usable desktop app shell for reading runtime projections. Phase 2 upgrades that shell into the Apple-Native Procedural Console: a PySide6 macOS-oriented production console with localized labels, stronger page coverage, and tightly bounded procedural energy feedback in state surfaces only.

## Design Direction

The visual direction is Apple Native Discipline plus Houdini Procedural Energy. Apple provides the structure: sidebar, toolbar-like pulse, dense tables, right inspector, and compact professional hierarchy. Procedural energy is local and state driven: status glow, connector line, pulse boiler, review seal, quarantine stripe, and sync blackout.

The visual system name is Apple-Native Procedural Console.

It inherits the Phase 1 Light-Dark Hybrid Living Production Console tokens and tightens them into a more Apple-native desktop layout.

Design tokens:

- main background: `#ECECEE`
- card/table background: `#FFFFFF`
- technical panel background: `#0D0D0D`
- border: `#D1D1D6`
- muted label: `#86868B`
- primary text: `#1D1D1F`
- secondary text: `#6E6E73`
- running blue: `#0066CC`
- success green: `#34C759`
- warning orange: `#FF9500`
- fatal red: `#FF3B30`
- artifact teal: `#00A6A6`
- AI/context purple: `#7D5FFF`

Typography uses the system font for normal UI and monospace for IDs, logs, and event lines. Tables use compact row height. Labels are small uppercase. Marketing-scale headings are avoided inside the operational shell.

## Workspace Rule

Phase 1 uses one `QMainWindow` and a single-window workspace. Normal inspection happens in the right inspector; normal navigation happens in the left rail; normal telemetry remains in the bottom stream. Pop-up windows are not used for routine metadata.

## Runtime Boundary

The GUI is a read-model and command-issuer only. It never owns execution. Real work remains behind:

`GUI -> OS Runtime Facade -> SQLite Job Queue -> Worker Registry -> Worker -> Artifact Store -> Event Log -> Human Review Gate -> GUI Status Projection`

Phase 2 command controls are still disabled unless routed through the OS Runtime Facade. The GUI must not directly mutate SQLite, start processes, launch creative tools, delete or overwrite assets, scan heavy file trees, read environment files, or use network calls by default.

Localization covers display labels only. Language options are Auto, English, and Chinese. Auto follows the host language when safely detectable and otherwise falls back to English. Canonical status strings, event_type values, internal enums, audit payloads, and human-entered review reasons remain unchanged.

## System Pulse Bar

The top System Pulse Bar is approximately 36px high and receives an immutable snapshot object. It displays:

- OS Runtime
- SQLite WAL
- Queue Depth
- Workers
- Memory
- Warnings
- Next Required Action

Widgets do not query the database during paint/update. Stale snapshots must switch the shell into sync warning state.

## Navigation Rail

The left navigation rail is approximately 200px wide and grouped as:

- Observe: Dashboard, System Health
- Dispatch: Job Queue, HFX Factory, Context Packs
- Govern: Human Review, Failure Quarantine, Artifact Store, Asset Library
- Settings: Settings

Phase 2 implements Dashboard, System Health, Job Queue, HFX Factory, HFX_008 Landing Chain, Context Packs, Human Review, Failure Quarantine, Artifact Store, and Settings / Boundaries. Asset Library remains out of the Phase 2 navigation.

## Workspace Stack

The center workspace uses `QStackedWidget`. Phase 2 pages are concrete read-only projection widgets. They may show placeholder previews for artifacts or packet outputs, but they do not imply materialized files or completed real-world work.

## Dashboard

Dashboard is read-only. It shows runtime health, SQLite WAL status, queue depth, active jobs, failed jobs, quarantined jobs, latest artifact count, HFX_008 landing summary, desktop smoke summary, ResourceWarning status, memory pressure, next required action, local-only status, and sync health. Values come from fake-safe snapshots or bounded read models.

## Job Queue

Job Queue uses `QTableView` with `QAbstractTableModel`. `QTableWidget` is prohibited for high-frequency or frequently refreshed tables.

Fields:

- job_id
- job_type
- status
- worker
- created_at
- runtime
- event_count
- artifact_count
- human_review_required
- failure_reason

Selecting a job updates the Right Inspector. Cancel/retry intent buttons remain disabled unless a safe facade route is introduced.

## Artifact Store

Artifact Store uses a compact `QTableView` / `QAbstractTableModel` projection of artifact metadata:

- type
- artifact_id
- job_id
- sha256 truncated for display
- size
- review_status
- quarantine_status
- local_only
- safe_to_publish

The preview area is a placeholder and does not open, mutate, delete, overwrite, upload, or publish files. Open-folder controls are disabled unless routed through the OS Runtime Facade.

## HFX Factory

HFX Factory summarizes Core12, HFX_008, topology audit status, proof artifact status, validation status, human review status, resource package status, `final_claim_allowed`, next action, and blocked reason. It does not make final HFX claims; it reports gate state only.

## HFX_008 Landing Chain

HFX_008 Landing Chain is a fixed linear widget:

Topology Audit -> Proof Artifact -> Artifact Validation -> Human Review -> Materialization Summary -> Final Claim Gate

The view uses fixed node cards and connector lines. Running connectors may be blue, succeeded connectors green, and failed or blocked connectors red or muted. Downstream nodes are greyed by status when upstream state is blocked. It is not a node editor, has no drag/drop, and does not use `QGraphicsView`.

## Human Review

Human Review shows pending reviews, preview placeholder, metadata, approve intent, reject intent, reject reason, quarantine intent, and final-claim warning. Approve and quarantine controls are disabled unless routed safely. Reject intent is additionally gated by a minimum reason length of five characters. Human-entered reasons are not translated.

## Failure Quarantine

Failure Quarantine shows failed jobs, failed worker, failure reason, traceback excerpt in a dark technical panel, event trail, quarantine path, retry allowed/blocked state, recommended fix, and disabled export failure bundle intent.

## Context Packs

Context Packs lists Gemini packet, Codex task packet, Claude review packet, HFX-only packet, desktop-only packet, tests-only packet, and branch diff packet options. It shows token/size budget and generated-packet artifact placeholders. Copy/open controls are disabled unless routed safely.

## System Health

System Health shows memory usage, worker count, active process count, DB connection state, SQLite WAL state, artifact store size, last smoke result, last CI result, warning list, next maintenance task, and sync health. The System Pulse Boiler escalates visual severity for memory pressure and WAL state without creating business-state changes.

## Settings / Boundaries

Settings / Boundaries shows Language: Auto / English / Chinese, Motion Intensity: Minimal / Standard / High Energy, local-only mode, external network disabled, asset root paths, artifact root path, allowed workers, dangerous action gates, human review gates, publish policy, and GitHub summary-only policy. Phase 2 settings can be read-only or in-memory only unless persistence is explicitly added through safe runtime paths.

## Status Chips

Status chips use a `QStyledItemDelegate` or an equivalent testable renderer. The strict status lexicon is:

- Not Started
- Pending
- Running
- Succeeded
- Failed
- Quarantined
- Requires Human Review
- Blocked: Missing Resource
- Blocked: Missing Visual Proof
- Blocked: Human Review Required
- Blocked: Placeholder Guide
- Dry Run Complete
- Materialization Required
- Materialized Valid
- Materialized Stale
- Ready for Real Run
- Ready for Review

The forbidden fake completion labels category covers overclaiming language, not valid runtime states. UI source, default data, and docs must avoid those labels and rely only on the strict lexicon above.

## Right Inspector

The Right Inspector is global and collapsible in later phases. Phase 1 supports:

- no selection state
- selected job state
- selected event state
- selected artifact placeholder state

Selected job metadata includes job_id, job_type, status, worker, event_count, artifact_count, failure_reason, quarantine_reason, human_review_required, and final_claim_allowed when present.

## Live Event Stream

The bottom Live Event Stream uses `QPlainTextEdit` in Phase 1. It is read-only, dark, monospace, and capped with a maximum block count such as 1000. It may display read-model or fake-safe event names including JobCreated, WorkerSelected, ArtifactRecorded, HumanReviewRequested, JobSucceeded, JobQuarantined, MaterializationBlocked, ReviewApproved, and ReviewRejected.

Phase 2 keeps the stream read-only and canonical. Event names are not translated because `event_type` is audit data.

## Sync Lost Overlay

Sync has three display states:

- Healthy: actions may be shown according to their own gate state.
- Degraded: warning is shown, risky actions are disabled, and read-only navigation remains available.
- Lost: the overlay shows `SYSTEM SYNC LOST — ACTIONS LOCKED` and `Runtime projection is stale. Read-only navigation remains available.`

The Chinese Lost display is `系统同步丢失 — 操作已锁定` and `运行时投影已过期。只读导航仍可使用。`

Lost state locks action buttons. Read-only navigation may remain.

## Motion And Procedural Energy

Motion intensity options are Minimal, Standard, and High Energy. Default is Standard. Under high memory pressure or lost sync, effective motion degrades to Minimal. Tests assert enums, color/state mapping, and fallback rules; they do not depend on animation timing.

Phase 2 motion components:

- Input energy foundation: heatline-ready static widget surface.
- HFX Energy Pipeline: status-driven connector rendering.
- System Pulse Boiler: memory/WAL severity indicator.
- Review Seal and Quarantine Stripe: visual markers only.
- Sync Lost Blackout: Healthy/Degraded/Lost display.

Motion must be subtle, local, and state driven. It must never block reading or change business state.

## Threading And Polling

UI updates happen on the Qt main thread. Phase 1 permits `QTimer` to request small bounded snapshots. Optional later probes may emit immutable snapshots from background objects.

Database polling rules:

- use bounded queries with `LIMIT`
- do not perform full-table scans from GUI paths
- do not hold long transactions
- do not read raw environment material
- do not write SQLite from GUI widgets
- no GUI direct subprocess boundary crossing
- do not call direct process APIs from GUI widgets
- do not launch DCC hosts or finishing tools
- do not use network by default

## Phase Split

Phase 1:

- app shell
- System Pulse Bar
- left navigation
- Dashboard
- read-only Job Queue
- Right Inspector
- bottom Live Event Stream
- Status Chip Delegate
- Sync Lost Overlay
- UI engineering spec and tests

Phase 2:

- i18n foundation
- Apple-native visual refinement
- Artifact Store UI
- HFX Factory UI
- HFX_008 Landing Chain HFX chain custom view
- Human Review UI
- Failure Quarantine UI
- Context Packs UI
- System Health UI
- Settings / Boundaries UI
- sync state refinement
- motion safety foundation
- disabled or facade-routed action intents

Phase 3:

- macOS `.app` packaging
- Application Support path policy
- logs path policy
- crash report path policy
- full command palette
- distribution hardening

macOS `.app` packaging, Application Support layout, logs location, crash report location, and full Command Palette remain deferred.
