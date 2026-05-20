# Sovereign Console UI Engineering Spec v1

## Product Concept

Sovereign Console, also called Sovereign C2, is the native desktop command-and-observe surface for the local Sovereign Engineering OS runtime. It is a living production console: quiet enough for repeated operational use, strict enough for governed execution, and always clear about what is observed, what is queued, and what still requires a human.

The console is not a chatbot, web frontend, node graph, or final production surface. Phase 1 is the first usable desktop app shell for reading runtime projections and issuing future commands through the OS Runtime Facade.

## Design Direction

The visual direction is Light-Dark Hybrid Living Production Console.

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

Phase 1 command controls are disabled or explicitly deferred. The GUI must not directly mutate SQLite, start processes, launch creative tools, delete or overwrite assets, scan heavy file trees, read environment files, or use network calls by default.

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

Only Dashboard and Job Queue are implemented in Phase 1. Every other page must clearly show `Placeholder: Phase 2` and must not imply delivered capability.

## Workspace Stack

The center workspace uses `QStackedWidget`. Phase 1 pages are Dashboard and Job Queue. Deferred sections remain placeholders until their phase arrives.

## Dashboard

Dashboard is read-only in Phase 1. It shows OS runtime status, SQLite WAL status, queue depth, active jobs, failed jobs, quarantined jobs, latest artifact count, HFX_008 landing summary, desktop smoke summary, ResourceWarning status, memory pressure, and next required action. Values come from fake-safe snapshots or bounded read models.

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

Selecting a job updates the Right Inspector. Cancel/retry are Phase 2 controls and remain disabled in Phase 1.

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

Phase 2 may replace this with `QListView` plus `QAbstractListModel`.

## Sync Lost Overlay

The Sync Lost Overlay appears when snapshot age exceeds 2000ms, the read-model reports stale, runtime is unavailable, or database sync is unavailable. It visually shows `SYSTEM SYNC LOST`, locks submit/action controls, allows safe read-only navigation, and clears when a fresh snapshot returns.

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

- command palette
- richer human review UI
- artifact store UI
- failure quarantine UI
- HFX factory UI
- event stream model upgrade
- richer action issuance through the OS Runtime Facade

Phase 3:

- macOS `.app` packaging
- Application Support path policy
- logs path policy
- crash report path policy
- HFX chain custom view
- distribution hardening

macOS packaging, Application Support layout, logs location, crash report location, Command Palette, and HFX chain custom view are deferred.
