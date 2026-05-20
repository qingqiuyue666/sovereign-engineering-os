"""qasync-driven native desktop control plane for Sovereign Engineering OS."""

from __future__ import annotations

import asyncio
import json
import platform
import resource
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kernel.os_engine.artifact_store import ArtifactRecord, ArtifactStore
from kernel.os_engine.job_queue import Job, JobQueueManager, JsonFileJobStore
from kernel.os_engine.worker_registry import WorkerContext, build_default_worker_registry

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
            ["Created", "Job ID", "Type", "Status", "Runtime", "Memory", "Error"]
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

    def render_jobs(self, jobs: list[Job]) -> None:
        visible = sorted(jobs, key=lambda job: job.created_at, reverse=True)[:MAX_TABLE_ROWS]
        self.table.setRowCount(len(visible))
        for row, job in enumerate(visible):
            self.table.setItem(row, 0, _table_item(job.created_at.isoformat(timespec="seconds")))
            self.table.setItem(row, 1, _table_item(job.id))
            self.table.setItem(row, 2, _table_item(job.type))
            self.table.setItem(row, 3, _table_item(job.status.value))
            self.table.setItem(row, 4, _table_item(f"{job.max_runtime:.0f}s", align_right=True))
            self.table.setItem(row, 5, _table_item(f"{job.memory_limit_mb} MB", align_right=True))
            self.table.setItem(row, 6, _table_item(job.error or ""))

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

    def render_artifacts(self, artifacts: list[ArtifactRecord]) -> None:
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

    def render(self, *, jobs: list[Job], artifact_store: ArtifactStore) -> None:
        counts = Counter(job.status.value for job in jobs)
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
        self.db_path.setText(str(artifact_store.db_path))


class SovereignDesktopWindow(QMainWindow):
    """Native control plane backed by the brokerless local queue."""

    def __init__(self, repo_root: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repo_root = (repo_root or _repo_root_from_here()).resolve()
        self.runtime_root = _runtime_root()
        self.artifact_store = ArtifactStore.default(repo_root=self.repo_root)
        self.registry = build_default_worker_registry()
        self.job_store = JsonFileJobStore(self.runtime_root / "jobs" / "desktop_jobs.json")
        self.queue: JobQueueManager | None = None
        self._event_task: asyncio.Task[None] | None = None
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

        self.queue_tab.set_job_types(self.registry.registered_types())
        self.queue_tab.submit_requested.connect(self._submit_job)
        self.queue_tab.refresh.clicked.connect(self._refresh_now)
        self.artifact_tab.refresh_requested.connect(self._refresh_now)

    async def boot(self) -> None:
        await asyncio.to_thread(self.artifact_store.initialize)
        context = WorkerContext(
            repo_root=self.repo_root,
            artifact_root=self.artifact_store.artifact_root,
            crash_dir=self.artifact_store.artifact_root / "crashes",
            artifact_store=self.artifact_store,
        )
        self.queue = JobQueueManager(
            registry=self.registry,
            context=context,
            store=self.job_store,
            max_concurrent=1,
        )
        await self.queue.start()
        self._event_task = asyncio.create_task(self._drain_queue_events(), name="desktop-event-drain")
        self._refresh_task = asyncio.create_task(self._refresh_loop(), name="desktop-refresh-loop")
        self.statusBar().showMessage("Ready - brokerless local queue online")
        await self._refresh_all()

    async def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        for task in (self._event_task, self._refresh_task):
            if task is not None:
                task.cancel()
        if self.queue is not None:
            await self.queue.stop()

    @asyncSlot(str, str, int, int)
    async def _submit_job(
        self,
        job_type: str,
        raw_inputs: str,
        max_runtime: int,
        memory_limit: int,
    ) -> None:
        if self.queue is None:
            self.queue_tab.append_log("Queue is not initialized")
            return
        try:
            decoded = json.loads(raw_inputs or "{}")
            if not isinstance(decoded, dict):
                raise ValueError("inputs JSON must decode to an object")
            inputs: dict[str, Any] = decoded
            job = await self.queue.submit(
                job_type=job_type,
                inputs=inputs,
                max_runtime=float(max_runtime),
                memory_limit_mb=int(memory_limit),
            )
        except Exception as exc:
            self.queue_tab.append_log(f"admission rejected: {exc}")
            self.statusBar().showMessage(f"Admission rejected: {exc}")
            return
        self.queue_tab.append_log(f"submitted {job.id} as {job.type}")
        self.statusBar().showMessage(f"Submitted {job.id}")
        await self._refresh_all()

    @asyncSlot()
    async def _refresh_now(self) -> None:
        await self._refresh_all()

    async def _drain_queue_events(self) -> None:
        if self.queue is None:
            return
        while True:
            event = await self.queue.events.get()
            self.queue_tab.append_log(
                f"{event.job_id} {event.previous_status or '-'} -> {event.new_status}: {event.message}"
            )
            await self._refresh_all()

    async def _refresh_loop(self) -> None:
        while True:
            await self._refresh_all()
            await asyncio.sleep(REFRESH_SECONDS)

    async def _refresh_all(self) -> None:
        if self.queue is None:
            return
        jobs = await self.queue.list_jobs()
        artifacts = await asyncio.to_thread(self.artifact_store.list_artifacts)
        self.queue_tab.render_jobs(jobs)
        self.artifact_tab.render_artifacts(artifacts)
        self.resource_tab.render(jobs=jobs, artifact_store=self.artifact_store)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API.
        if self.queue is not None and not self._shutting_down:
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
