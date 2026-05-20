"""Small, bounded procedural-energy widgets for state feedback."""

from __future__ import annotations

from enum import Enum

from apps.ui import QColor, PYSIDE6_AVAILABLE, QFrame, QLabel, QPainter, QPen, QVBoxLayout, QWidget
from apps.ui.motion import MotionIntensity, VisualSeverity, classify_memory_pressure, classify_wal_status
from apps.ui.theme import DESIGN_TOKENS


class EnergyState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


ENERGY_STATE_COLORS: dict[EnergyState, str] = {
    EnergyState.IDLE: DESIGN_TOKENS["muted_label"],
    EnergyState.RUNNING: DESIGN_TOKENS["running_blue"],
    EnergyState.SUCCEEDED: DESIGN_TOKENS["success_green"],
    EnergyState.FAILED: DESIGN_TOKENS["fatal_red"],
    EnergyState.BLOCKED: DESIGN_TOKENS["border"],
}


class EnergyLine(QWidget):
    """Static connector line. Tests assert state, not timing."""

    def __init__(
        self,
        *,
        state: EnergyState | str = EnergyState.IDLE,
        motion_intensity: MotionIntensity = MotionIntensity.STANDARD,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = normalize_energy_state(state)
        self.motion_intensity = motion_intensity
        self.setMinimumHeight(10)

    def set_state(self, state: EnergyState | str) -> None:
        self.state = normalize_energy_state(state)
        self.update()

    def color(self) -> str:
        return ENERGY_STATE_COLORS[self.state]

    def paintEvent(self, _event: object) -> None:  # noqa: N802 - Qt API.
        if not PYSIDE6_AVAILABLE:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(self.color()))
        pen.setWidth(2 if self.motion_intensity is not MotionIntensity.MINIMAL else 1)
        painter.setPen(pen)
        mid_y = int(self.height() / 2)
        painter.drawLine(0, mid_y, self.width(), mid_y)


class SystemPulseBoiler(QFrame):
    """Compact severity surface for memory and WAL pressure."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SystemPulseBoiler")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        self.memory_label = QLabel("Memory: --", self)
        self.wal_label = QLabel("WAL: --", self)
        layout.addWidget(self.memory_label)
        layout.addWidget(self.wal_label)
        self.memory_severity = VisualSeverity.NORMAL
        self.wal_severity = VisualSeverity.NORMAL

    def render(self, *, memory_pressure: str, wal_status: str) -> None:
        self.memory_severity = classify_memory_pressure(memory_pressure)
        self.wal_severity = classify_wal_status(wal_status)
        self.memory_label.setText(f"Memory: {memory_pressure}")
        self.wal_label.setText(f"WAL: {wal_status}")
        self.setProperty("severity", max((self.memory_severity, self.wal_severity), key=_severity_rank).value)
        self.style().unpolish(self)
        self.style().polish(self)

    def severity_tuple(self) -> tuple[str, str]:
        return (self.memory_severity.value, self.wal_severity.value)


class ReviewSeal(QFrame):
    """Visual marker for approved review state; it carries no write semantics."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReviewSeal")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self.label = QLabel("Review seal placeholder", self)
        layout.addWidget(self.label)


class QuarantineStripe(QFrame):
    """Visual marker for quarantined state; it carries no destructive semantics."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuarantineStripe")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self.label = QLabel("Quarantine stripe placeholder", self)
        layout.addWidget(self.label)


def normalize_energy_state(state: EnergyState | str) -> EnergyState:
    if isinstance(state, EnergyState):
        return state
    normalized = str(state).strip().lower()
    mapping = {
        "pending": EnergyState.IDLE,
        "not started": EnergyState.IDLE,
        "running": EnergyState.RUNNING,
        "succeeded": EnergyState.SUCCEEDED,
        "dry run complete": EnergyState.SUCCEEDED,
        "failed": EnergyState.FAILED,
        "quarantined": EnergyState.FAILED,
        "blocked": EnergyState.BLOCKED,
        "blocked: missing resource": EnergyState.BLOCKED,
        "blocked: missing visual proof": EnergyState.BLOCKED,
        "blocked: human review required": EnergyState.BLOCKED,
        "blocked: placeholder guide": EnergyState.BLOCKED,
    }
    return mapping.get(normalized, EnergyState.BLOCKED)


def _severity_rank(severity: VisualSeverity) -> int:
    return {
        VisualSeverity.NORMAL: 0,
        VisualSeverity.WARNING: 1,
        VisualSeverity.FATAL: 2,
    }[severity]
