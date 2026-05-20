"""Native PySide6 desktop control plane for Sovereign Engineering OS."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import asyncio
import json
import platform
import resource
import sys

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
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

from kernel.ipc.aci_subprocess import CommandResult, run_whitelisted_command
from kernel.ipc.radar_zmq import DEFAULT_RADAR_ENDPOINT, RadarZmqSubscriber
from kernel.ipc.vfx_localhost import (
    DEFAULT_COMFYUI_BASE_URL,
    VfxPromptRequest,
    build_text_to_image_dag,
    submit_prompt,
)

__all__ = ["main", "SovereignDesktopWindow"]

_APP_TITLE = "Sovereign Engineering OS - God-Node Control Plane"
_RAM_BUDGET_MB = 150.0
_MAX_RADAR_ROWS = 200


class AciCommandWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, command_line: str, repo_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._command_line = command_line
        self._repo_root = repo_root

    @Slot()
    def run(self) -> None:
        try:
            result = run_whitelisted_command(
                self._command_line,
                cwd=self._repo_root,
                timeout_seconds=180.0,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)


class VfxSubmitWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        request: VfxPromptRequest,
        endpoint: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._endpoint = endpoint

    @Slot()
    def run(self) -> None:
        try:
            result = asyncio.run(
                submit_prompt(
                    self._request,
                    base_url=self._endpoint,
                    timeout_seconds=12.0,
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)


class CodeAuditTab(QWidget):
    command_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._command = QComboBox(self)
        self._command.setEditable(True)
        self._command.addItems(
            [
                "pytest -q",
                "pytest -q tests/tracer_bullet/test_code_audit_workbench.py",
                "pytest -q tests/tracer_bullet/test_comfyui_workflow_spec.py",
                "ruff check apps kernel tests",
                "git status --short --branch",
                "git diff --stat",
            ]
        )
        self._run_button = QPushButton("Run", self)
        self._run_button.setObjectName("PrimaryButton")
        self._clear_button = QPushButton("Clear", self)
        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(5000)
        self._output.setObjectName("Console")

        command_row = QHBoxLayout()
        command_row.addWidget(QLabel("Command", self))
        command_row.addWidget(self._command, stretch=1)
        command_row.addWidget(self._run_button)
        command_row.addWidget(self._clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(command_row)
        layout.addWidget(self._output, stretch=1)

        self._run_button.clicked.connect(self._emit_command)
        self._clear_button.clicked.connect(self._output.clear)

    def set_running(self, running: bool) -> None:
        self._run_button.setEnabled(not running)
        self._command.setEnabled(not running)
        self._run_button.setText("Running" if running else "Run")

    def append_line(self, line: str) -> None:
        self._output.appendPlainText(line)

    def show_result(self, result: CommandResult) -> None:
        status = "OK" if result.ok else "FAILED"
        header = (
            f"$ {result.command_line}\n"
            f"[{status}] rc={result.returncode} "
            f"elapsed={result.duration_seconds:.2f}s timeout={result.timed_out}\n"
        )
        body = result.combined_output or "<no output>"
        self._output.appendPlainText(f"{header}{body}\n")

    @Slot()
    def _emit_command(self) -> None:
        command = self._command.currentText().strip()
        if command:
            self.command_requested.emit(command)


class VfxFactoryTab(QWidget):
    submit_requested = Signal(object, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._endpoint = QLineEdit(DEFAULT_COMFYUI_BASE_URL, self)
        self._prompt = QPlainTextEdit(self)
        self._prompt.setPlaceholderText("cinematic industrial machine room, volumetric light, high detail")
        self._prompt.setMaximumHeight(92)
        self._negative = QPlainTextEdit(self)
        self._negative.setPlainText(
            "low quality, blurry, text artifacts, watermark, malformed geometry, overexposed highlights"
        )
        self._negative.setMaximumHeight(70)
        self._checkpoint = QLineEdit("sd_xl_base_1.0.safetensors", self)
        self._prefix = QLineEdit("sovereign_vfx", self)

        self._width = _spinbox(64, 4096, 1024, step=64)
        self._height = _spinbox(64, 4096, 1024, step=64)
        self._steps = _spinbox(1, 150, 28)
        self._seed = _spinbox(0, 2_147_483_647, 1337)
        self._cfg = _double_spinbox(0.0, 30.0, 7.0, step=0.25, decimals=2)
        self._denoise = _double_spinbox(0.01, 1.0, 1.0, step=0.05, decimals=2)
        self._sampler = QComboBox(self)
        self._sampler.addItems(["dpmpp_2m", "dpmpp_2m_sde", "euler", "euler_ancestral"])
        self._scheduler = QComboBox(self)
        self._scheduler.addItems(["karras", "normal", "simple", "exponential"])
        self._submit_button = QPushButton("Submit DAG", self)
        self._submit_button.setObjectName("PrimaryButton")
        self._preview_button = QPushButton("Preview JSON", self)
        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(5000)
        self._output.setObjectName("Console")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Endpoint", self._endpoint)
        form.addRow("Prompt", self._prompt)
        form.addRow("Negative", self._negative)
        form.addRow("Checkpoint", self._checkpoint)
        form.addRow("Prefix", self._prefix)

        grid = QGridLayout()
        grid.addWidget(QLabel("Width", self), 0, 0)
        grid.addWidget(self._width, 0, 1)
        grid.addWidget(QLabel("Height", self), 0, 2)
        grid.addWidget(self._height, 0, 3)
        grid.addWidget(QLabel("Steps", self), 1, 0)
        grid.addWidget(self._steps, 1, 1)
        grid.addWidget(QLabel("Seed", self), 1, 2)
        grid.addWidget(self._seed, 1, 3)
        grid.addWidget(QLabel("CFG", self), 2, 0)
        grid.addWidget(self._cfg, 2, 1)
        grid.addWidget(QLabel("Denoise", self), 2, 2)
        grid.addWidget(self._denoise, 2, 3)
        grid.addWidget(QLabel("Sampler", self), 3, 0)
        grid.addWidget(self._sampler, 3, 1)
        grid.addWidget(QLabel("Scheduler", self), 3, 2)
        grid.addWidget(self._scheduler, 3, 3)

        controls = QGroupBox("DAG Controls", self)
        controls.setLayout(grid)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self._preview_button)
        button_row.addWidget(self._submit_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(controls)
        layout.addLayout(button_row)
        layout.addWidget(self._output, stretch=1)

        self._preview_button.clicked.connect(self._preview_json)
        self._submit_button.clicked.connect(self._emit_submit)

    def set_running(self, running: bool) -> None:
        self._submit_button.setEnabled(not running)
        self._preview_button.setEnabled(not running)
        self._submit_button.setText("Submitting" if running else "Submit DAG")

    def show_json(self, payload: dict[str, Any]) -> None:
        self._output.setPlainText(json.dumps(payload, indent=2, sort_keys=True))

    def append_line(self, line: str) -> None:
        self._output.appendPlainText(line)

    def _make_request(self) -> VfxPromptRequest:
        return VfxPromptRequest(
            positive_prompt=self._prompt.toPlainText().strip(),
            negative_prompt=self._negative.toPlainText().strip(),
            checkpoint_name=self._checkpoint.text().strip(),
            width=self._width.value(),
            height=self._height.value(),
            seed=self._seed.value(),
            steps=self._steps.value(),
            cfg=self._cfg.value(),
            sampler_name=self._sampler.currentText(),
            scheduler=self._scheduler.currentText(),
            denoise=self._denoise.value(),
            filename_prefix=self._prefix.text().strip(),
        ).validated()

    @Slot()
    def _preview_json(self) -> None:
        try:
            request = self._make_request()
            self.show_json({"client_id": request.client_id, "prompt": build_text_to_image_dag(request)})
        except Exception as exc:
            self._output.setPlainText(f"Request rejected: {exc}")

    @Slot()
    def _emit_submit(self) -> None:
        try:
            request = self._make_request()
        except Exception as exc:
            self._output.setPlainText(f"Request rejected: {exc}")
            return
        self.submit_requested.emit(request, self._endpoint.text().strip())


class MacroRadarTab(QWidget):
    start_requested = Signal(str)
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._endpoint = QLineEdit(DEFAULT_RADAR_ENDPOINT, self)
        self._start_button = QPushButton("Start", self)
        self._start_button.setObjectName("PrimaryButton")
        self._stop_button = QPushButton("Stop", self)
        self._stop_button.setEnabled(False)
        self._status = QLabel("SUB idle", self)
        self._status.setObjectName("StatusChip")
        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(["Time", "Topic", "Symbol", "Strength", "Event"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("Endpoint", self))
        control_row.addWidget(self._endpoint, stretch=1)
        control_row.addWidget(self._status)
        control_row.addWidget(self._start_button)
        control_row.addWidget(self._stop_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(control_row)
        layout.addWidget(self._table, stretch=1)

        self._start_button.clicked.connect(self._emit_start)
        self._stop_button.clicked.connect(self.stop_requested.emit)

    def set_running(self, running: bool) -> None:
        self._start_button.setEnabled(not running)
        self._stop_button.setEnabled(running)
        self._endpoint.setEnabled(not running)

    @Slot(str)
    def update_status(self, status: str) -> None:
        self._status.setText(status)

    @Slot(dict)
    def add_event(self, event: dict[str, Any]) -> None:
        while self._table.rowCount() >= _MAX_RADAR_ROWS:
            self._table.removeRow(0)
        row = self._table.rowCount()
        self._table.insertRow(row)
        timestamp = datetime.fromtimestamp(float(event.get("received_at", 0.0))).strftime("%H:%M:%S")
        strength = event.get("strength")
        cells = [
            timestamp,
            str(event.get("topic", "")),
            str(event.get("symbol", "")),
            "" if strength is None else f"{float(strength):.2f}",
            str(event.get("event_type", "")),
        ]
        for column, value in enumerate(cells):
            item = QTableWidgetItem(value)
            if bool(event.get("is_strong_signal")):
                item.setForeground(QColor("#f5c542"))
            self._table.setItem(row, column, item)
        self._table.scrollToBottom()

    @Slot()
    def _emit_start(self) -> None:
        endpoint = self._endpoint.text().strip()
        if endpoint:
            self.start_requested.emit(endpoint)


class SovereignDesktopWindow(QMainWindow):
    def __init__(self, repo_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo_root = repo_root.resolve()
        self._aci_thread: QThread | None = None
        self._aci_worker: AciCommandWorker | None = None
        self._vfx_thread: QThread | None = None
        self._vfx_worker: VfxSubmitWorker | None = None
        self._radar_thread: QThread | None = None
        self._radar_worker: RadarZmqSubscriber | None = None

        self.setWindowTitle(_APP_TITLE)
        self.resize(1320, 860)
        self.setMinimumSize(1040, 680)

        self._code_tab = CodeAuditTab(self)
        self._vfx_tab = VfxFactoryTab(self)
        self._radar_tab = MacroRadarTab(self)
        self._tabs = QTabWidget(self)
        self._tabs.addTab(self._code_tab, "Code Audit")
        self._tabs.addTab(self._vfx_tab, "VFX Factory")
        self._tabs.addTab(self._radar_tab, "Macro Radar")

        central = QWidget(self)
        header = self._build_header()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(header)
        central_layout.addWidget(self._tabs, stretch=1)
        self.setCentralWidget(central)

        self._ram_label = QLabel("RSS -- MB", self)
        self._status = QStatusBar(self)
        self._status.addPermanentWidget(self._ram_label)
        self.setStatusBar(self._status)

        self._memory_timer = QTimer(self)
        self._memory_timer.setInterval(2000)
        self._memory_timer.timeout.connect(self._update_memory_label)
        self._memory_timer.start()
        self._update_memory_label()

        self._code_tab.command_requested.connect(self._run_aci_command)
        self._vfx_tab.submit_requested.connect(self._submit_vfx_request)
        self._radar_tab.start_requested.connect(self._start_radar)
        self._radar_tab.stop_requested.connect(self._stop_radar)

    def closeEvent(self, event: Any) -> None:
        self._stop_radar()
        for thread in (self._aci_thread, self._vfx_thread, self._radar_thread):
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(1500)
        event.accept()

    def _build_header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("Header")
        title = QLabel("Sovereign Engineering OS", header)
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Localhost IPC Control Plane", header)
        subtitle.setObjectName("HeaderSubtitle")
        repo_label = QLabel(self._repo_root.as_posix(), header)
        repo_label.setObjectName("RepoPath")

        left = QVBoxLayout()
        left.addWidget(title)
        left.addWidget(subtitle)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.addLayout(left)
        layout.addStretch(1)
        layout.addWidget(repo_label)
        return header

    @Slot(str)
    def _run_aci_command(self, command_line: str) -> None:
        if self._aci_thread is not None and self._aci_thread.isRunning():
            self._code_tab.append_line("ACI proxy is already running a command.")
            return
        self._code_tab.set_running(True)
        self._code_tab.append_line(f"$ {command_line}")
        thread = QThread(self)
        worker = AciCommandWorker(command_line, self._repo_root)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._handle_aci_success)
        worker.failed.connect(self._handle_aci_failure)
        worker.succeeded.connect(lambda _result: thread.quit())
        worker.failed.connect(lambda _message: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_aci_thread)
        self._aci_thread = thread
        self._aci_worker = worker
        thread.start()

    @Slot(object)
    def _handle_aci_success(self, result: CommandResult) -> None:
        self._code_tab.show_result(result)
        self._code_tab.set_running(False)
        self._status.showMessage("Code Audit command completed", 4000)

    @Slot(str)
    def _handle_aci_failure(self, message: str) -> None:
        self._code_tab.append_line(f"Command rejected: {message}")
        self._code_tab.set_running(False)
        self._status.showMessage("Code Audit command rejected", 4000)

    @Slot()
    def _clear_aci_thread(self) -> None:
        self._aci_thread = None
        self._aci_worker = None

    @Slot(object, str)
    def _submit_vfx_request(self, request: VfxPromptRequest, endpoint: str) -> None:
        if self._vfx_thread is not None and self._vfx_thread.isRunning():
            self._vfx_tab.append_line("VFX bridge is already submitting a DAG.")
            return
        self._vfx_tab.set_running(True)
        thread = QThread(self)
        worker = VfxSubmitWorker(request, endpoint)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._handle_vfx_success)
        worker.failed.connect(self._handle_vfx_failure)
        worker.succeeded.connect(lambda _result: thread.quit())
        worker.failed.connect(lambda _message: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_vfx_thread)
        self._vfx_thread = thread
        self._vfx_worker = worker
        thread.start()

    @Slot(object)
    def _handle_vfx_success(self, result: Any) -> None:
        self._vfx_tab.show_json(result.as_dict())
        self._vfx_tab.set_running(False)
        self._status.showMessage("ComfyUI DAG submitted", 4000)

    @Slot(str)
    def _handle_vfx_failure(self, message: str) -> None:
        self._vfx_tab.append_line(f"Submit failed: {message}")
        self._vfx_tab.set_running(False)
        self._status.showMessage("ComfyUI submit failed", 4000)

    @Slot()
    def _clear_vfx_thread(self) -> None:
        self._vfx_thread = None
        self._vfx_worker = None

    @Slot(str)
    def _start_radar(self, endpoint: str) -> None:
        if self._radar_thread is not None and self._radar_thread.isRunning():
            self._radar_tab.update_status("SUB already running")
            return
        try:
            worker = RadarZmqSubscriber(endpoint)
        except Exception as exc:
            self._radar_tab.update_status(f"Rejected: {exc}")
            return
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self._radar_tab.update_status)
        worker.message_received.connect(self._radar_tab.add_event)
        worker.strong_signal_detected.connect(self._handle_strong_signal)
        worker.error_occurred.connect(self._handle_radar_error)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_radar_thread)
        self._radar_thread = thread
        self._radar_worker = worker
        self._radar_tab.set_running(True)
        thread.start()

    @Slot()
    def _stop_radar(self) -> None:
        if self._radar_worker is not None:
            self._radar_worker.stop()

    @Slot(dict)
    def _handle_strong_signal(self, event: dict[str, Any]) -> None:
        symbol = event.get("symbol", "UNKNOWN")
        strength = event.get("strength")
        label = f"STRONG_SIGNAL {symbol}"
        if strength is not None:
            label = f"{label} {float(strength):.2f}"
        self._status.showMessage(label, 6000)

    @Slot(str)
    def _handle_radar_error(self, message: str) -> None:
        self._radar_tab.update_status(message)
        self._status.showMessage(message, 6000)

    @Slot()
    def _clear_radar_thread(self) -> None:
        self._radar_tab.set_running(False)
        self._radar_thread = None
        self._radar_worker = None

    @Slot()
    def _update_memory_label(self) -> None:
        rss_mb = _resident_set_mb()
        self._ram_label.setText(f"RSS {rss_mb:.1f} MB / {_RAM_BUDGET_MB:.0f} MB")
        if rss_mb > _RAM_BUDGET_MB:
            self._ram_label.setStyleSheet("color: #ff6b6b; font-weight: 700;")
        else:
            self._ram_label.setStyleSheet("color: #9bd88f; font-weight: 700;")


def _spinbox(minimum: int, maximum: int, value: int, *, step: int = 1) -> QSpinBox:
    spinbox = QSpinBox()
    spinbox.setRange(minimum, maximum)
    spinbox.setSingleStep(step)
    spinbox.setValue(value)
    return spinbox


def _double_spinbox(
    minimum: float,
    maximum: float,
    value: float,
    *,
    step: float,
    decimals: int,
) -> QDoubleSpinBox:
    spinbox = QDoubleSpinBox()
    spinbox.setRange(minimum, maximum)
    spinbox.setSingleStep(step)
    spinbox.setDecimals(decimals)
    spinbox.setValue(value)
    return spinbox


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resident_set_mb() -> float:
    rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if platform.system() == "Darwin":
        return rss / (1024.0 * 1024.0)
    return rss / 1024.0


def _apply_dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#17191c"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#d5d7db"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#101214"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#20242a"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#252a31"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f0f2f4"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#d5d7db"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#252a31"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e8eaed"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4c9f70"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0f1113"))
    app.setPalette(palette)
    app.setStyleSheet(_STYLESHEET)


_STYLESHEET = """
QWidget {
    background: #17191c;
    color: #d5d7db;
    font-family: "SF Pro Text", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QFrame#Header {
    background: #101214;
    border-bottom: 1px solid #303640;
}
QLabel#HeaderTitle {
    color: #f0f2f4;
    font-size: 20px;
    font-weight: 700;
}
QLabel#HeaderSubtitle {
    color: #8d96a0;
    font-size: 12px;
}
QLabel#RepoPath,
QLabel#StatusChip {
    color: #aab2bd;
    background: #20242a;
    border: 1px solid #343b45;
    border-radius: 6px;
    padding: 6px 10px;
}
QTabWidget::pane {
    border: 0;
}
QTabBar::tab {
    background: #20242a;
    color: #aab2bd;
    border: 1px solid #303640;
    border-bottom: 0;
    padding: 10px 18px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background: #17191c;
    color: #f0f2f4;
    border-top: 2px solid #4c9f70;
}
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox,
QPlainTextEdit,
QTableWidget {
    background: #101214;
    border: 1px solid #343b45;
    border-radius: 6px;
    color: #e8eaed;
    selection-background-color: #4c9f70;
    selection-color: #0f1113;
}
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    min-height: 30px;
    padding-left: 8px;
}
QPlainTextEdit#Console {
    font-family: "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.35;
}
QPushButton {
    background: #282e36;
    border: 1px solid #3a424d;
    border-radius: 6px;
    color: #e8eaed;
    min-height: 30px;
    padding: 0 14px;
}
QPushButton:hover {
    background: #303843;
}
QPushButton:disabled {
    color: #69727d;
    background: #20242a;
}
QPushButton#PrimaryButton {
    background: #3d7b58;
    border-color: #5aa577;
    color: #f5fff8;
    font-weight: 700;
}
QGroupBox {
    border: 1px solid #303640;
    border-radius: 6px;
    margin-top: 18px;
    padding: 14px 10px 10px 10px;
}
QGroupBox::title {
    color: #aab2bd;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QHeaderView::section {
    background: #20242a;
    border: 0;
    border-right: 1px solid #303640;
    color: #aab2bd;
    padding: 7px;
}
QTableWidget {
    gridline-color: #2d333b;
}
QStatusBar {
    background: #101214;
    border-top: 1px solid #303640;
}
"""


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Sovereign Engineering OS")
    app.setApplicationDisplayName("Sovereign Engineering OS")
    app.setStyle("Fusion")
    app.setFont(QFont("SF Pro Text", 13))
    _apply_dark_palette(app)
    window = SovereignDesktopWindow(_repo_root())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
