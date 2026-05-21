"""Visual-only coding activity panel for the Sovereign Console workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from apps.ui import QFrame, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget
from apps.ui.anime_micro_fx import (
    AnimeFxIntensity,
    AnimeFxState,
    AnimeStatusDot,
    CommandAura,
    GateVisualState,
    REQUIRED_TEST_GATES,
    SpeedLineHint,
    SweatDropMarker,
    TestGateStamp,
    TestGateStatus,
    TinySparkle,
    effective_anime_fx_intensity,
    normalize_test_gate_status,
)
from apps.ui.i18n import UiText
from apps.ui.motion import SyncState
from apps.ui.read_models import RuntimeSnapshot


class CodingActivityState(str, Enum):
    IDLE = "Idle"
    THINKING = "Thinking"
    READING = "Reading"
    CODING = "Coding"
    TESTING = "Testing"
    WRITING_REPORT = "Writing Report"
    WAITING_REVIEW = "Waiting Review"
    FAILED = "Failed"
    STAGE_COMPLETE = "Stage Complete"


CODING_ACTIVITY_STATES: tuple[str, ...] = tuple(state.value for state in CodingActivityState)
CODE_VISUALIZATION_CONTRACT: tuple[str, ...] = (
    "code block area",
    "file pill",
    "diff-like rows",
    "+ rows in success green",
    "- rows in muted red",
    "current line highlight",
    "cursor placeholder",
    "monospace font",
    "visualization only",
)
MISSION_THREAD_CARDS: tuple[str, ...] = (
    "User command placeholder",
    "AI planning card",
    "Coding activity card",
    "Test gate card",
    "Artifact/review summary card",
    "Final report placeholder card",
)

ACTIVITY_MESSAGE_KEYS: dict[CodingActivityState, str] = {
    CodingActivityState.IDLE: "coding_activity.message.idle",
    CodingActivityState.THINKING: "coding_activity.message.thinking",
    CodingActivityState.READING: "coding_activity.message.reading",
    CodingActivityState.CODING: "coding_activity.message.coding",
    CodingActivityState.TESTING: "coding_activity.message.testing",
    CodingActivityState.WRITING_REPORT: "coding_activity.message.writing_report",
    CodingActivityState.WAITING_REVIEW: "coding_activity.message.waiting_review",
    CodingActivityState.FAILED: "coding_activity.message.failed",
    CodingActivityState.STAGE_COMPLETE: "coding_activity.message.stage_complete",
}

STATE_LABEL_KEYS: dict[CodingActivityState, str] = {
    CodingActivityState.IDLE: "coding_activity.state.idle",
    CodingActivityState.THINKING: "coding_activity.state.thinking",
    CodingActivityState.READING: "coding_activity.state.reading",
    CodingActivityState.CODING: "coding_activity.state.coding",
    CodingActivityState.TESTING: "coding_activity.state.testing",
    CodingActivityState.WRITING_REPORT: "coding_activity.state.writing_report",
    CodingActivityState.WAITING_REVIEW: "coding_activity.state.waiting_review",
    CodingActivityState.FAILED: "coding_activity.state.failed",
    CodingActivityState.STAGE_COMPLETE: "coding_activity.state.stage_complete",
}


@dataclass(frozen=True, slots=True)
class DiffPreviewRow:
    marker: str
    text: str
    current: bool = False

    def normalized_marker(self) -> str:
        if self.marker in {"+", "-", " "}:
            return self.marker
        if self.marker.lower() in {"add", "added", "success"}:
            return "+"
        if self.marker.lower() in {"remove", "removed", "delete"}:
            return "-"
        return " "

    def display_text(self) -> str:
        return f"{self.normalized_marker()} {self.text}"


@dataclass(frozen=True, slots=True)
class CodingActivitySnapshot:
    state: CodingActivityState | str
    current_action: str
    current_file: str = ""
    active_worker: str = ""
    activity_message: str = ""
    diff_preview: tuple[DiffPreviewRow, ...] = field(default_factory=tuple)
    test_gate_summary: tuple[GateVisualState, ...] = field(default_factory=tuple)
    safe_status: str = "Read-only projection; no repo mutation from GUI"

    def normalized_state(self) -> CodingActivityState:
        return normalize_coding_activity_state(self.state)


def normalize_coding_activity_state(value: str | CodingActivityState | None) -> CodingActivityState:
    if isinstance(value, CodingActivityState):
        return value
    normalized = str(value or "").strip().lower().replace("_", " ")
    mapping = {
        "idle": CodingActivityState.IDLE,
        "thinking": CodingActivityState.THINKING,
        "reading": CodingActivityState.READING,
        "coding": CodingActivityState.CODING,
        "testing": CodingActivityState.TESTING,
        "writing report": CodingActivityState.WRITING_REPORT,
        "writing_report": CodingActivityState.WRITING_REPORT,
        "waiting review": CodingActivityState.WAITING_REVIEW,
        "waiting_review": CodingActivityState.WAITING_REVIEW,
        "failed": CodingActivityState.FAILED,
        "stage complete": CodingActivityState.STAGE_COMPLETE,
        "stage_complete": CodingActivityState.STAGE_COMPLETE,
    }
    return mapping.get(normalized, CodingActivityState.IDLE)


def default_diff_preview() -> tuple[DiffPreviewRow, ...]:
    return (
        DiffPreviewRow(" ", "class WorkspaceMissionThread:", current=False),
        DiffPreviewRow("-", "    show_static_dashboard_card()", current=False),
        DiffPreviewRow("+", "    show_coding_activity_panel()", current=False),
        DiffPreviewRow("+", "    render_test_gate_summary()", current=True),
        DiffPreviewRow(" ", "    cursor = visual_only_placeholder", current=False),
    )


def default_test_gates(status: str | TestGateStatus = TestGateStatus.PENDING) -> tuple[GateVisualState, ...]:
    resolved = normalize_test_gate_status(status)
    return tuple(GateVisualState(name=gate, status=resolved) for gate in REQUIRED_TEST_GATES)


def demo_coding_activity_snapshot() -> CodingActivitySnapshot:
    return CodingActivitySnapshot(
        state=CodingActivityState.CODING,
        current_action="Writing bounded changes",
        current_file="apps/ui/coding_activity_panel.py",
        active_worker="local-ui-projection",
        activity_message="Writing bounded changes",
        diff_preview=default_diff_preview(),
        test_gate_summary=default_test_gates(TestGateStatus.PENDING),
    )


def activity_from_snapshot(snapshot: RuntimeSnapshot) -> CodingActivitySnapshot:
    latest_run = snapshot.latest_jobs[0] if snapshot.latest_jobs else None
    if latest_run is None:
        return CodingActivitySnapshot(
            state=CodingActivityState.IDLE,
            current_action="Observe runtime",
            activity_message="No active run. The engine is quiet.",
            diff_preview=default_diff_preview(),
            test_gate_summary=default_test_gates(TestGateStatus.PENDING),
        )
    status = latest_run.status.lower()
    if "failed" in status or "quarantined" in status:
        state = CodingActivityState.FAILED
        message = "Failure isolated. Evidence preserved."
        gates = default_test_gates(TestGateStatus.FAILED)
    elif "review" in status:
        state = CodingActivityState.WAITING_REVIEW
        message = "Waiting for human review."
        gates = default_test_gates(TestGateStatus.PENDING)
    elif "running" in status:
        state = CodingActivityState.TESTING
        message = "Running validation gates."
        gates = default_test_gates(TestGateStatus.RUNNING)
    elif "complete" in status or "succeeded" in status:
        state = CodingActivityState.STAGE_COMPLETE
        message = "Stage complete. Awaiting next gate."
        gates = (
            GateVisualState("Unit Tests", TestGateStatus.OK, "Projected gate passed"),
            GateVisualState("Schemas", TestGateStatus.OK, "Projected gate passed"),
            GateVisualState("Acceptance", TestGateStatus.PENDING, "Awaiting human-readable proof"),
            GateVisualState("make ci", TestGateStatus.PENDING, "Not claimed by UI"),
        )
    else:
        state = CodingActivityState.THINKING
        message = "Planning execution path."
        gates = default_test_gates(TestGateStatus.PENDING)
    return CodingActivitySnapshot(
        state=state,
        current_action=snapshot.next_required_action,
        current_file="apps/ui/workspace_page.py",
        active_worker=latest_run.worker or "read-model projection",
        activity_message=message,
        diff_preview=default_diff_preview(),
        test_gate_summary=gates,
    )


class TestGatePanel(QFrame):
    """Visual validation gate chips with bounded status stamps."""

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("TestGatePanel")
        self.setProperty("role", "gatePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        self.title = QLabel(self.text.tr("test_gate.title"), self)
        self.title.setProperty("role", "eyebrow")
        layout.addWidget(self.title)
        self.stamp_row = QHBoxLayout()
        self.stamp_row.setSpacing(6)
        layout.addLayout(self.stamp_row)
        self.summary = QLabel(self.text.tr("test_gate.unknown"), self)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self._stamps: list[TestGateStamp] = []
        self._gates: tuple[GateVisualState, ...] = ()
        self.render_gates(default_test_gates())

    def render_gates(self, gates: tuple[GateVisualState, ...] | list[GateVisualState]) -> None:
        normalized = _normalize_gate_sequence(tuple(gates))
        for stamp in self._stamps:
            stamp.setParent(None)
        self._stamps = []
        self._gates = normalized
        for gate in normalized:
            stamp = TestGateStamp(gate, self)
            self._stamps.append(stamp)
            self.stamp_row.addWidget(stamp)
        self.summary.setText(_gate_summary_text(normalized))

    def gate_names(self) -> tuple[str, ...]:
        return tuple(gate.name for gate in self._gates)

    def gate_statuses(self) -> tuple[str, ...]:
        return tuple(gate.normalized_status().value for gate in self._gates)

    def supported_gate_states(self) -> tuple[str, ...]:
        return tuple(status.value for status in TestGateStatus)

    def ok_stamp_count(self) -> int:
        return sum(1 for stamp in self._stamps if stamp.is_ok_stamped())

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("test_gate.title"))


class CodingActivityPanel(QFrame):
    """Shows what the AI coding worker is doing, using safe projected data."""

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("CodingActivityPanel")
        self.setProperty("role", "metricCard")
        self._snapshot = demo_coding_activity_snapshot()
        self._anime_fx_intensity = AnimeFxIntensity.STANDARD

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.status_dot = AnimeStatusDot(self, state=AnimeFxState.CODING)
        self.title = QLabel(self.text.tr("coding_activity.title"), self)
        self.title.setProperty("role", "eyebrow")
        self.state_label = QLabel("", self)
        self.state_label.setObjectName("CodingActivityState")
        header.addWidget(self.status_dot)
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.state_label)
        layout.addLayout(header)

        meta = QGridLayout()
        meta.setSpacing(6)
        self.action_label = QLabel("", self)
        self.action_label.setWordWrap(True)
        self.file_label = QLabel("", self)
        self.file_label.setObjectName("CodingActivityFilePill")
        self.worker_label = QLabel("", self)
        self.safe_label = QLabel("", self)
        self.safe_label.setObjectName("CodingActivitySafeStatus")
        meta.addWidget(_eyebrow(self.text.tr("coding_activity.current_action"), self), 0, 0)
        meta.addWidget(self.action_label, 0, 1)
        meta.addWidget(_eyebrow(self.text.tr("coding_activity.current_file"), self), 1, 0)
        meta.addWidget(self.file_label, 1, 1)
        meta.addWidget(_eyebrow(self.text.tr("coding_activity.active_worker"), self), 2, 0)
        meta.addWidget(self.worker_label, 2, 1)
        meta.addWidget(_eyebrow(self.text.tr("coding_activity.safe_status"), self), 3, 0)
        meta.addWidget(self.safe_label, 3, 1)
        layout.addLayout(meta)

        self.message_label = QLabel("", self)
        self.message_label.setObjectName("CodingActivityMessage")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.code_frame = QFrame(self)
        self.code_frame.setObjectName("CodingCodeBlock")
        code_layout = QVBoxLayout(self.code_frame)
        code_layout.setContentsMargins(10, 8, 10, 8)
        code_layout.setSpacing(2)
        self.code_rows_layout = QVBoxLayout()
        self.code_rows_layout.setSpacing(1)
        code_layout.addLayout(self.code_rows_layout)
        footer = QHBoxLayout()
        self.speed_line = SpeedLineHint(self.code_frame)
        self.cursor_label = QLabel("| cursor", self.code_frame)
        self.cursor_label.setObjectName("CodingCursorPlaceholder")
        footer.addWidget(self.speed_line)
        footer.addStretch(1)
        footer.addWidget(self.cursor_label)
        code_layout.addLayout(footer)
        layout.addWidget(self.code_frame)

        self.gate_panel = TestGatePanel(self, language=language)
        layout.addWidget(self.gate_panel)

        fx_row = QHBoxLayout()
        self.sparkle = TinySparkle(self)
        self.sweat_drop = SweatDropMarker(self)
        fx_row.addWidget(self.sparkle)
        fx_row.addWidget(self.sweat_drop)
        fx_row.addStretch(1)
        layout.addLayout(fx_row)

        self._row_labels: list[QLabel] = []
        self.render_activity(self._snapshot)

    def render_activity(
        self,
        snapshot: CodingActivitySnapshot,
        *,
        anime_fx_intensity: str | AnimeFxIntensity = AnimeFxIntensity.STANDARD,
        memory_pressure: str = "Nominal",
        sync_state: str | SyncState = SyncState.HEALTHY,
    ) -> None:
        self._snapshot = snapshot
        self._anime_fx_intensity = effective_anime_fx_intensity(
            anime_fx_intensity,
            memory_pressure=memory_pressure,
            sync_state=sync_state,
        )
        state = snapshot.normalized_state()
        self.state_label.setText(self.text.tr(STATE_LABEL_KEYS[state]))
        self.action_label.setText(snapshot.current_action or "--")
        self.file_label.setText(snapshot.current_file or "--")
        self.worker_label.setText(snapshot.active_worker or "--")
        self.safe_label.setText(snapshot.safe_status)
        self.message_label.setText(snapshot.activity_message or self.text.tr(ACTIVITY_MESSAGE_KEYS[state]))
        self.status_dot.set_state(_fx_state_for_activity(state), intensity=self._anime_fx_intensity)
        self.speed_line.setVisible(state is CodingActivityState.CODING)
        self.speed_line.set_intensity(self._anime_fx_intensity)
        self.sparkle.setVisible(state is CodingActivityState.STAGE_COMPLETE)
        self.sparkle.set_intensity(self._anime_fx_intensity)
        self.sweat_drop.set_failed(state is CodingActivityState.FAILED)
        self.gate_panel.render_gates(snapshot.test_gate_summary or default_test_gates())
        self._render_code_rows(snapshot.diff_preview or default_diff_preview())

    def supported_states(self) -> tuple[str, ...]:
        return CODING_ACTIVITY_STATES

    def code_visualization_contract(self) -> tuple[str, ...]:
        return CODE_VISUALIZATION_CONTRACT

    def rendered_activity(self) -> dict[str, str]:
        return {
            "state": self.state_label.text(),
            "current_action": self.action_label.text(),
            "current_file": self.file_label.text(),
            "active_worker": self.worker_label.text(),
            "activity_message": self.message_label.text(),
            "safe_status": self.safe_label.text(),
        }

    def rendered_code_lines(self) -> tuple[str, ...]:
        return tuple(label.text() for label in self._row_labels)

    def diff_markers(self) -> tuple[str, ...]:
        return tuple(row.normalized_marker() for row in (self._snapshot.diff_preview or default_diff_preview()))

    def test_gate_names(self) -> tuple[str, ...]:
        return self.gate_panel.gate_names()

    def test_gate_statuses(self) -> tuple[str, ...]:
        return self.gate_panel.gate_statuses()

    def effective_anime_fx_intensity(self) -> str:
        return self._anime_fx_intensity.value

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("coding_activity.title"))
        self.gate_panel.apply_language(language)
        self.render_activity(
            self._snapshot,
            anime_fx_intensity=self._anime_fx_intensity,
        )

    def _render_code_rows(self, rows: tuple[DiffPreviewRow, ...]) -> None:
        for label in self._row_labels:
            label.setParent(None)
        self._row_labels = []
        for index, row in enumerate(rows):
            label = QLabel(row.display_text(), self.code_frame)
            label.setObjectName(f"CodingDiffRow_{index}")
            label.setProperty("diffMarker", row.normalized_marker())
            label.setProperty("currentLine", row.current)
            label.setWordWrap(False)
            self.code_rows_layout.addWidget(label)
            self._row_labels.append(label)


def _normalize_gate_sequence(gates: tuple[GateVisualState, ...]) -> tuple[GateVisualState, ...]:
    by_name = {gate.name: gate for gate in gates}
    return tuple(by_name.get(name, GateVisualState(name=name)) for name in REQUIRED_TEST_GATES)


def _gate_summary_text(gates: tuple[GateVisualState, ...]) -> str:
    counts = {status.value: 0 for status in TestGateStatus}
    for gate in gates:
        counts[gate.normalized_status().value] += 1
    return " | ".join(f"{key}: {value}" for key, value in counts.items() if value)


def _fx_state_for_activity(state: CodingActivityState) -> AnimeFxState:
    mapping = {
        CodingActivityState.THINKING: AnimeFxState.THINKING,
        CodingActivityState.READING: AnimeFxState.THINKING,
        CodingActivityState.CODING: AnimeFxState.CODING,
        CodingActivityState.TESTING: AnimeFxState.TESTING,
        CodingActivityState.WRITING_REPORT: AnimeFxState.CODING,
        CodingActivityState.WAITING_REVIEW: AnimeFxState.WAITING,
        CodingActivityState.FAILED: AnimeFxState.FAILED,
        CodingActivityState.STAGE_COMPLETE: AnimeFxState.PASSED,
        CodingActivityState.IDLE: AnimeFxState.WAITING,
    }
    return mapping[state]


def _eyebrow(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setProperty("role", "eyebrow")
    return label
