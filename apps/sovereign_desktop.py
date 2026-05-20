"""qasync-driven native desktop control plane for Sovereign Engineering OS."""

from __future__ import annotations

import asyncio
import json
import platform
import resource
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kernel.os_engine.database import OSDatabase
from kernel.os_engine.job_projection import ProjectedJobState
from kernel.os_engine.sqlite_artifact_store import SQLiteArtifactRecord, SQLiteArtifactStore
from kernel.os_engine.sqlite_job_queue import SQLiteJobQueue
from kernel.os_engine.worker_registry import build_default_worker_registry

try:
    from PySide6.QtCore import Qt, Signal, Slot
    from PySide6.QtGui import QCloseEvent, QFont
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QComboBox,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    import qasync
    from qasync import asyncSlot

    PYSIDE6_AVAILABLE = True
except Exception as _qt_import_error:  # pragma: no cover - exercised on GUI hosts.
    PYSIDE6_AVAILABLE = False
    qasync = None  # type: ignore[assignment]
    _QT_IMPORT_EXCEPTION = _qt_import_error

    class _MissingQtType:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("PySide6 and qasync are required to start the desktop GUI") from _QT_IMPORT_EXCEPTION

    class _SignalShim:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def connect(self, *_args: object, **_kwargs: object) -> None:
            pass

        def emit(self, *_args: object, **_kwargs: object) -> None:
            pass

    class _QtFlagShim:
        AlignRight = 0
        AlignVCenter = 0
        ItemIsEnabled = 0
        ItemIsSelectable = 0
        TextSelectableByMouse = 0

    class _QtShim:
        AlignmentFlag = _QtFlagShim
        ItemFlag = _QtFlagShim
        TextInteractionFlag = _QtFlagShim

    def Slot(*_args: object, **_kwargs: object) -> object:
        def decorator(function: object) -> object:
            return function

        return decorator

    def asyncSlot(*_args: object, **_kwargs: object) -> object:
        def decorator(function: object) -> object:
            return function

        return decorator

    Qt = _QtShim
    Signal = _SignalShim
    QCloseEvent = _MissingQtType
    QFont = _MissingQtType
    QApplication = _MissingQtType
    QAbstractItemView = _MissingQtType
    QComboBox = _MissingQtType
    QFormLayout = _MissingQtType
    QGridLayout = _MissingQtType
    QGroupBox = _MissingQtType
    QHBoxLayout = _MissingQtType
    QHeaderView = _MissingQtType
    QLabel = _MissingQtType
    QLineEdit = _MissingQtType
    QMainWindow = _MissingQtType
    QPlainTextEdit = _MissingQtType
    QPushButton = _MissingQtType
    QSpinBox = _MissingQtType
    QStatusBar = _MissingQtType
    QTabWidget = _MissingQtType
    QTableWidget = _MissingQtType
    QTableWidgetItem = _MissingQtType
    QVBoxLayout = _MissingQtType
    QWidget = _MissingQtType


__all__ = ["PYSIDE6_AVAILABLE", "SovereignDesktopWindow", "main"]

APP_TITLE = "Sovereign Engineering OS - Native Control Plane"
UI_MEMORY_BUDGET_MB = 150
MAX_TABLE_ROWS = 300
REFRESH_SECONDS = 2.0


def _runtime_root() -> Path:
    return Path.home() / ".sovereign_engineering_os"


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _current_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(usage) / (1024 * 1024)
    return float(usage) / 1024


def _table_item(text: object, *, align_right: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    if align_right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return item


class QueueTab(QWidget):
    """Thin queue submission surface; worker processes are never started here."""

    submit_requested = Signal(str, str, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.job_type = QComboBox(self)
        self.job_type.setEditable(False)
        self.max_runtime = QSpinBox(self)
        self.max_runtime.setRange(5, 86_400)
        self.max_runtime.setValue(600)
        self.max_runtime.setSuffix(" s")
        self.memory_limit = QSpinBox(self)
        self.memory_limit.setRange(64, 262_144)
        self.memory_limit.setValue(4096)
        self.memory_limit.setSuffix(" MB")

        self.inputs = QPlainTextEdit(self)
        self.inputs.setObjectName("JsonEditor")
        self.inputs.setMaximumHeight(132)
        self.inputs.setPlainText('{\n  "command": ["git", "status", "--short"]\n}')

        self.submit = QPushButton("Submit Job", self)
        self.submit.setObjectName("PrimaryButton")
        self.refresh = QPushButton("Refresh", self)
        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(900)
        self.log.setObjectName("Console")

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            ["Job ID", "Status", "Worker", "Artifacts", "Review", "Final Claim", "Events"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        form = QFormLayout()
        form.addRow("Worker", self.job_type)
        form.addRow("Max Runtime", self.max_runtime)
        form.addRow("Memory Limit", self.memory_limit)

        controls = QGroupBox("Admission", self)
        controls.setLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.refresh)
        buttons.addWidget(self.submit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(controls)
        layout.addWidget(QLabel("Inputs JSON", self))
        layout.addWidget(self.inputs)
        layout.addLayout(buttons)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(QLabel("Queue Events", self))
        layout.addWidget(self.log)

        self.submit.clicked.connect(self._emit_submit)

    def set_job_types(self, job_types: list[str]) -> None:
        self.job_type.clear()
        self.job_type.addItems(job_types)

    def append_log(self, message: str) -> None:
        self.log.appendPlainText(f"{_utc_stamp()} {message}")

    def render_jobs(self, jobs: list[ProjectedJobState]) -> None:
        visible = sorted(jobs, key=lambda job: job.job_id, reverse=True)[:MAX_TABLE_ROWS]
        self.table.setRowCount(len(visible))
        for row, job in enumerate(visible):
            self.table.setItem(row, 0, _table_item(job.job_id))
            self.table.setItem(row, 1, _table_item(job.current_status))
            self.table.setItem(row, 2, _table_item(job.worker_name or ""))
            self.table.setItem(row, 3, _table_item(len(job.artifact_ids), align_right=True))
            self.table.setItem(row, 4, _table_item("required" if job.human_review_required else "not required"))
            self.table.setItem(row, 5, _table_item("allowed" if job.final_claim_allowed else "blocked"))
            self.table.setItem(row, 6, _table_item(job.event_count, align_right=True))

    @Slot()
    def _emit_submit(self) -> None:
        self.submit_requested.emit(
            self.job_type.currentText(),
            self.inputs.toPlainText(),
            int(self.max_runtime.value()),
            int(self.memory_limit.value()),
        )


class ArtifactTab(QWidget):
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Filter artifacts")
        self.refresh = QPushButton("Refresh", self)
        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            ["Artifact ID", "Job ID", "Review", "Quarantine", "Size", "SHA-256", "Local Path"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        top = QHBoxLayout()
        top.addWidget(self.search, stretch=1)
        top.addWidget(self.refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addWidget(self.table, stretch=1)

        self.refresh.clicked.connect(self.refresh_requested.emit)
        self.search.textChanged.connect(self._apply_filter)

    def render_artifacts(self, artifacts: list[SQLiteArtifactRecord]) -> None:
        visible = sorted(artifacts, key=lambda artifact: artifact.created_at, reverse=True)[:MAX_TABLE_ROWS]
        self.table.setRowCount(len(visible))
        for row, artifact in enumerate(visible):
            self.table.setItem(row, 0, _table_item(artifact.artifact_id))
            self.table.setItem(row, 1, _table_item(artifact.job_id))
            self.table.setItem(row, 2, _table_item(artifact.review_status))
            self.table.setItem(row, 3, _table_item(artifact.quarantine_status))
            self.table.setItem(row, 4, _table_item(artifact.size_bytes, align_right=True))
            self.table.setItem(row, 5, _table_item(artifact.sha256))
            self.table.setItem(row, 6, _table_item(str(artifact.local_path)))
        self._apply_filter(self.search.text())

    @Slot(str)
    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self.table.rowCount()):
            row_text = " ".join(
                self.table.item(row, column).text().lower()
                for column in range(self.table.columnCount())
                if self.table.item(row, column) is not None
            )
            self.table.setRowHidden(row, bool(needle) and needle not in row_text)


class ResourceTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.rss = QLabel("0 MB", self)
        self.budget = QLabel(f"{UI_MEMORY_BUDGET_MB} MB", self)
        self.queue_depth = QLabel("0", self)
        self.active_jobs = QLabel("0", self)
        self.terminal_jobs = QLabel("0", self)
        self.artifact_root = QLabel("", self)
        self.db_path = QLabel("", self)
        self.python = QLabel(sys.version.split()[0], self)
        self.platform = QLabel(platform.platform(), self)
        for label in (
            self.rss,
            self.budget,
            self.queue_depth,
            self.active_jobs,
            self.terminal_jobs,
            self.artifact_root,
            self.db_path,
            self.python,
            self.platform,
        ):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        form = QFormLayout()
        form.addRow("UI Max RSS", self.rss)
        form.addRow("UI Budget", self.budget)
        form.addRow("Queued Jobs", self.queue_depth)
        form.addRow("Active Jobs", self.active_jobs)
        form.addRow("Terminal Jobs", self.terminal_jobs)
        form.addRow("Artifact Root", self.artifact_root)
        form.addRow("Catalog DB", self.db_path)
        form.addRow("Python", self.python)
        form.addRow("Host", self.platform)

        group = QGroupBox("Local Resource Envelope", self)
        group.setLayout(form)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(group)
        layout.addStretch(1)

    def render(self, *, jobs: list[ProjectedJobState], artifact_store: SQLiteArtifactStore) -> None:
        counts = Counter(job.current_status for job in jobs)
        active = counts.get("running", 0)
        queued = counts.get("pending", 0) + counts.get("admitted", 0)
        terminal = counts.get("succeeded", 0) + counts.get("failed", 0) + counts.get("quarantined", 0)
        rss_mb = _current_rss_mb()
        self.rss.setText(f"{rss_mb:.1f} MB")
        self.rss.setObjectName("DangerText" if rss_mb > UI_MEMORY_BUDGET_MB else "OkText")
        self.queue_depth.setText(str(queued))
        self.active_jobs.setText(str(active))
        self.terminal_jobs.setText(str(terminal))
        self.artifact_root.setText(str(artifact_store.artifact_root))
        self.db_path.setText(str(artifact_store.database.db_path))


class DesktopOsEngineFacade:
    """Passive desktop-facing facade over the event-sourced OS engine core."""

    def __init__(self, *, repo_root: Path, runtime_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.runtime_root = runtime_root.expanduser().resolve()
        self.database = OSDatabase(root=self.runtime_root, db_path=self.runtime_root / "os_engine.sqlite3")
        self.queue = SQLiteJobQueue(self.database)
        self.artifact_store = SQLiteArtifactStore(
            database=self.database,
            artifact_root=self.runtime_root / "artifacts",
        )
        self.registry = build_default_worker_registry()

    def initialize(self) -> None:
        self.database.initialize()
        self.artifact_store.initialize()

    def registered_job_types(self) -> list[str]:
        return self.registry.registered_types()

    async def submit(
        self,
        *,
        job_type: str,
        inputs: dict[str, Any],
        max_runtime: int,
        memory_limit: int,
    ) -> ProjectedJobState:
        return await asyncio.to_thread(
            self.submit_job_request,
            job_type=job_type,
            inputs=inputs,
            max_runtime=max_runtime,
            memory_limit=memory_limit,
        )

    def submit_job_request(
        self,
        *,
        job_type: str,
        inputs: dict[str, Any],
        max_runtime: int,
        memory_limit: int,
    ) -> ProjectedJobState:
        if not self.registry.has_type(job_type):
            raise ValueError(f"unregistered job type blocked: {job_type}")
        adapter = self.registry.get(job_type)
        job_id = f"gui_job_{uuid.uuid4().hex}"
        manifest = {
            "inputs": inputs,
            "max_runtime_seconds": int(max_runtime),
            "memory_limit_mb": int(memory_limit),
            "request_source": "desktop_control_plane",
        }
        self.queue.create_job(
            job_id=job_id,
            job_type=job_type,
            input_manifest=manifest,
            output_dir=str(inputs.get("output_dir", "")),
            human_review_required=bool(getattr(adapter, "human_review_required", False))
            or bool(inputs.get("human_review_required", False)),
            dry_run=bool(inputs.get("dry_run", False)),
            local_only=True,
        )
        self.queue.admit_job(job_id)
        self.queue.select_worker(job_id, worker_name=str(getattr(adapter, "name", job_type)))
        self.queue.enqueue_job(job_id)
        return self.queue.get_job_state(job_id)

    def list_job_states(self) -> list[ProjectedJobState]:
        return self.queue.list_jobs()

    def list_artifact_records(self) -> list[SQLiteArtifactRecord]:
        return self.artifact_store.list_artifacts()


class SovereignDesktopWindow(QMainWindow):
    """Native control plane backed by the passive event-sourced queue facade."""

    def __init__(self, repo_root: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repo_root = (repo_root or _repo_root_from_here()).resolve()
        self.runtime_root = _runtime_root()
        self.os_engine = DesktopOsEngineFacade(repo_root=self.repo_root, runtime_root=self.runtime_root)
        self.queue = self.os_engine
        self.artifact_store = self.os_engine.artifact_store
        self.registry = self.os_engine.registry
        self._refresh_task: asyncio.Task[None] | None = None
        self._shutting_down = False

        self.setWindowTitle(APP_TITLE)
        self.resize(1260, 820)
        self.setFont(QFont("Inter", 11))

        self.tabs = QTabWidget(self)
        self.queue_tab = QueueTab(self)
        self.artifact_tab = ArtifactTab(self)
        self.resource_tab = ResourceTab(self)
        self.tabs.addTab(self.queue_tab, "Job Orchestration Queue")
        self.tabs.addTab(self.artifact_tab, "Local Artifact Explorer")
        self.tabs.addTab(self.resource_tab, "System Resource Monitor")
        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Booting local-first control plane")
        self._apply_theme()

        self.queue_tab.set_job_types(self.os_engine.registered_job_types())
        self.queue_tab.submit_requested.connect(self._submit_job)
        self.queue_tab.refresh.clicked.connect(self._refresh_now)
        self.artifact_tab.refresh_requested.connect(self._refresh_now)

    async def boot(self) -> None:
        await asyncio.to_thread(self.os_engine.initialize)
        self._refresh_task = asyncio.create_task(self._refresh_loop(), name="desktop-refresh-loop")
        self.statusBar().showMessage("Ready - passive event-sourced control plane online")
        await self._refresh_all()

    async def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        for task in (self._refresh_task,):
            if task is not None:
                task.cancel()

    @asyncSlot(str, str, int, int)
    async def _submit_job(
        self,
        job_type: str,
        raw_inputs: str,
        max_runtime: int,
        memory_limit: int,
    ) -> None:
        try:
            decoded = json.loads(raw_inputs or "{}")
            if not isinstance(decoded, dict):
                raise ValueError("inputs JSON must decode to an object")
            inputs: dict[str, Any] = decoded
            job = await self.queue.submit(
                job_type=job_type,
                inputs=inputs,
                max_runtime=int(max_runtime),
                memory_limit=int(memory_limit),
            )
        except Exception as exc:
            self.queue_tab.append_log(f"admission rejected: {exc}")
            self.statusBar().showMessage(f"Admission rejected: {exc}")
            return
        self.queue_tab.append_log(f"submitted {job.job_id} for durable materialization")
        self.statusBar().showMessage(f"Submitted {job.job_id}")
        await self._refresh_all()

    @asyncSlot()
    async def _refresh_now(self) -> None:
        await self._refresh_all()

    async def _refresh_loop(self) -> None:
        while True:
            await self._refresh_all()
            await asyncio.sleep(REFRESH_SECONDS)

    async def _refresh_all(self) -> None:
        jobs = await asyncio.to_thread(self.os_engine.list_job_states)
        artifacts = await asyncio.to_thread(self.os_engine.list_artifact_records)
        self.queue_tab.render_jobs(jobs)
        self.artifact_tab.render_artifacts(artifacts)
        self.resource_tab.render(jobs=jobs, artifact_store=self.artifact_store)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API.
        if not self._shutting_down:
            asyncio.create_task(self.shutdown())
        event.accept()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #111418;
                color: #d9e2ec;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #2a323c;
                border-radius: 6px;
                margin-top: 16px;
                padding: 14px;
                color: #aebdcb;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
                background: #171c22;
                border: 1px solid #2d3742;
                border-radius: 5px;
                padding: 7px;
                selection-background-color: #2d6cdf;
            }
            QPlainTextEdit#Console, QPlainTextEdit#JsonEditor {
                font-family: "SF Mono", Menlo, monospace;
                font-size: 12px;
            }
            QTableWidget {
                background: #151a20;
                alternate-background-color: #101419;
                border: 1px solid #29313b;
                gridline-color: #26303a;
            }
            QHeaderView::section {
                background: #1b222b;
                color: #9fb1c2;
                border: 0;
                border-right: 1px solid #29313b;
                padding: 7px;
            }
            QPushButton {
                background: #232c36;
                border: 1px solid #34414f;
                border-radius: 5px;
                padding: 8px 13px;
            }
            QPushButton:hover {
                background: #2d3945;
            }
            QPushButton#PrimaryButton {
                background: #2d6cdf;
                border-color: #3f7ff0;
                color: #f8fbff;
            }
            QTabBar::tab {
                background: #171c22;
                border: 1px solid #29313b;
                padding: 10px 18px;
            }
            QTabBar::tab:selected {
                background: #232c36;
                color: #ffffff;
            }
            QLabel#DangerText {
                color: #ff7a7a;
            }
            QLabel#OkText {
                color: #67d39b;
            }
            """
        )


def main(argv: list[str] | None = None) -> int:
    if not PYSIDE6_AVAILABLE or qasync is None:
        raise RuntimeError("PySide6 and qasync are required to run apps.sovereign_desktop")
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_TITLE)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = SovereignDesktopWindow()
    window.show()
    loop.create_task(window.boot())
    app.aboutToQuit.connect(lambda: loop.create_task(window.shutdown()))
    with loop:
        loop.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
