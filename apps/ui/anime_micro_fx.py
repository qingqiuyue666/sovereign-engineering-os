"""Bounded anime-inspired micro effects for coding activity surfaces.

The objects in this module are visual-only Qt widgets and small contract
helpers. They never execute commands, mutate project state, or depend on
external assets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from apps.ui import QFrame, QHBoxLayout, QLabel, QVBoxLayout
from apps.ui.motion import SyncState, VisualSeverity, classify_memory_pressure


class AnimeFxIntensity(str, Enum):
    OFF = "Off"
    MINIMAL = "Minimal"
    STANDARD = "Standard"
    PLAYFUL = "Playful"


class AnimeFxState(str, Enum):
    THINKING = "Thinking"
    CODING = "Coding"
    TESTING = "Testing"
    PASSED = "Passed"
    FAILED = "Failed"
    WAITING = "Waiting"


class TestGateStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    OK = "OK"
    FAILED = "Failed"
    SKIPPED = "Skipped"


REQUIRED_TEST_GATES: tuple[str, ...] = ("Unit Tests", "Schemas", "Acceptance", "make ci")
ANIME_FX_INTENSITY_OPTIONS: tuple[str, ...] = tuple(intensity.value for intensity in AnimeFxIntensity)
ANIME_STATUS_DOT_STATES: tuple[str, ...] = tuple(state.value for state in AnimeFxState)
TEST_GATE_STATES: tuple[str, ...] = tuple(status.value for status in TestGateStatus)
ANIME_MICRO_FX_CONTRACT: tuple[str, ...] = (
    "local coding and testing states only",
    "no copyrighted anime character references",
    "no anime girl character art",
    "no mascot takeover",
    "no full-screen speed lines",
    "no heavy particles",
    "no screen shake",
    "no cyberpunk drift",
    "no game HUD drift",
    "small bounded professional workspace accents",
)


@dataclass(frozen=True, slots=True)
class GateVisualState:
    name: str
    status: TestGateStatus | str = TestGateStatus.PENDING
    summary: str = ""

    def normalized_status(self) -> TestGateStatus:
        return normalize_test_gate_status(self.status)


def normalize_anime_fx_intensity(value: str | AnimeFxIntensity | None) -> AnimeFxIntensity:
    if isinstance(value, AnimeFxIntensity):
        return value
    normalized = str(value or "").strip().lower().replace("_", " ")
    mapping = {
        "off": AnimeFxIntensity.OFF,
        "minimal": AnimeFxIntensity.MINIMAL,
        "standard": AnimeFxIntensity.STANDARD,
        "playful": AnimeFxIntensity.PLAYFUL,
    }
    return mapping.get(normalized, AnimeFxIntensity.STANDARD)


def effective_anime_fx_intensity(
    requested: str | AnimeFxIntensity | None,
    *,
    memory_pressure: str = "Nominal",
    sync_state: str | SyncState = SyncState.HEALTHY,
) -> AnimeFxIntensity:
    normalized = normalize_anime_fx_intensity(requested)
    if normalized is AnimeFxIntensity.OFF:
        return AnimeFxIntensity.OFF
    resolved_sync = SyncState(sync_state) if not isinstance(sync_state, SyncState) else sync_state
    if resolved_sync is SyncState.LOST:
        return AnimeFxIntensity.MINIMAL
    if classify_memory_pressure(memory_pressure) is VisualSeverity.FATAL:
        return AnimeFxIntensity.MINIMAL
    return normalized


def normalize_test_gate_status(value: str | TestGateStatus | None) -> TestGateStatus:
    if isinstance(value, TestGateStatus):
        return value
    normalized = str(value or "").strip().lower().replace("_", " ")
    mapping = {
        "pending": TestGateStatus.PENDING,
        "running": TestGateStatus.RUNNING,
        "ok": TestGateStatus.OK,
        "passed": TestGateStatus.OK,
        "pass": TestGateStatus.OK,
        "failed": TestGateStatus.FAILED,
        "fail": TestGateStatus.FAILED,
        "skipped": TestGateStatus.SKIPPED,
        "skip": TestGateStatus.SKIPPED,
    }
    return mapping.get(normalized, TestGateStatus.PENDING)


def anime_fx_enabled(intensity: str | AnimeFxIntensity | None) -> bool:
    return normalize_anime_fx_intensity(intensity) is not AnimeFxIntensity.OFF


class AnimeStatusDot(QFrame):
    """Tiny expression dot for coding state without character art."""

    def __init__(
        self,
        parent: object | None = None,
        *,
        state: str | AnimeFxState = AnimeFxState.WAITING,
        intensity: str | AnimeFxIntensity = AnimeFxIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("AnimeStatusDot")
        self.dot = QLabel("", self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.dot)
        self.setFixedSize(18, 18)
        self._state = AnimeFxState.WAITING
        self._intensity = AnimeFxIntensity.STANDARD
        self.set_state(state, intensity=intensity)

    def set_state(
        self,
        state: str | AnimeFxState,
        *,
        intensity: str | AnimeFxIntensity | None = None,
    ) -> None:
        self._state = _normalize_fx_state(state)
        if intensity is not None:
            self._intensity = normalize_anime_fx_intensity(intensity)
        glyphs = {
            AnimeFxState.THINKING: "...",
            AnimeFxState.CODING: ">",
            AnimeFxState.TESTING: "?",
            AnimeFxState.PASSED: "OK",
            AnimeFxState.FAILED: "!",
            AnimeFxState.WAITING: ".",
        }
        self.dot.setText("" if self._intensity is AnimeFxIntensity.OFF else glyphs[self._state])
        self.setProperty("fxState", self._state.value)
        self.setProperty("fxIntensity", self._intensity.value)
        self.style().unpolish(self)
        self.style().polish(self)

    def supported_states(self) -> tuple[str, ...]:
        return ANIME_STATUS_DOT_STATES

    def state(self) -> str:
        return self._state.value


class SpeedLineHint(QFrame):
    """Subtle local speed-line hint for the active code row."""

    def __init__(
        self,
        parent: object | None = None,
        *,
        intensity: str | AnimeFxIntensity = AnimeFxIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SpeedLineHint")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        self.line_label = QLabel("", self)
        layout.addWidget(self.line_label)
        self.set_intensity(intensity)

    def set_intensity(self, intensity: str | AnimeFxIntensity) -> None:
        self._intensity = normalize_anime_fx_intensity(intensity)
        self.line_label.setText("" if self._intensity in {AnimeFxIntensity.OFF, AnimeFxIntensity.MINIMAL} else "///")
        self.setProperty("fxIntensity", self._intensity.value)

    def is_local_only(self) -> bool:
        return True


class TinySparkle(QFrame):
    """One to three tiny success marks for saved or passed local states."""

    def __init__(
        self,
        parent: object | None = None,
        *,
        intensity: str | AnimeFxIntensity = AnimeFxIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TinySparkle")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sparkle_label = QLabel("", self)
        layout.addWidget(self.sparkle_label)
        self.set_intensity(intensity)

    def set_intensity(self, intensity: str | AnimeFxIntensity) -> None:
        self._intensity = normalize_anime_fx_intensity(intensity)
        glyphs = {
            AnimeFxIntensity.OFF: "",
            AnimeFxIntensity.MINIMAL: "*",
            AnimeFxIntensity.STANDARD: "* *",
            AnimeFxIntensity.PLAYFUL: "* * *",
        }
        self.sparkle_label.setText(glyphs[self._intensity])
        self.setProperty("fxIntensity", self._intensity.value)

    def max_marks(self) -> int:
        return 3


class SweatDropMarker(QFrame):
    """Tiny warning/failure marker, kept local to the failed chip."""

    def __init__(self, parent: object | None = None, *, failed: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("SweatDropMarker")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.marker = QLabel("", self)
        layout.addWidget(self.marker)
        self.set_failed(failed)

    def set_failed(self, failed: bool) -> None:
        self._failed = bool(failed)
        self.marker.setText("!" if self._failed else "")
        self.setProperty("failed", self._failed)

    def is_failed(self) -> bool:
        return self._failed


class TestGateStamp(QFrame):
    """Validation gate chip with an optional gentle OK stamp."""

    def __init__(self, gate: GateVisualState, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TestGateStamp")
        self.gate = gate
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(1)
        self.name_label = QLabel(gate.name, self)
        self.name_label.setProperty("role", "eyebrow")
        self.status_label = QLabel("", self)
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        self.set_gate(gate)

    def set_gate(self, gate: GateVisualState) -> None:
        self.gate = gate
        status = gate.normalized_status()
        self.name_label.setText(gate.name)
        self.status_label.setText("OK stamp" if status is TestGateStatus.OK else status.value)
        self.setProperty("gateStatus", status.value)
        self.setProperty("gateName", gate.name)
        self.style().unpolish(self)
        self.style().polish(self)

    def is_ok_stamped(self) -> bool:
        return self.gate.normalized_status() is TestGateStatus.OK


class CommandAura(QFrame):
    """Subtle command-bar border aura for focus, Thinking, or Coding states."""

    def __init__(
        self,
        parent: object | None = None,
        *,
        intensity: str | AnimeFxIntensity = AnimeFxIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CommandAura")
        self._active = False
        self._intensity = normalize_anime_fx_intensity(intensity)
        self.set_aura(False, intensity=self._intensity)

    def set_aura(
        self,
        active: bool,
        *,
        intensity: str | AnimeFxIntensity | None = None,
    ) -> None:
        if intensity is not None:
            self._intensity = normalize_anime_fx_intensity(intensity)
        self._active = bool(active and self._intensity is not AnimeFxIntensity.OFF)
        self.setProperty("auraActive", self._active)
        self.setProperty("fxIntensity", self._intensity.value)
        self.style().unpolish(self)
        self.style().polish(self)

    def aura_active(self) -> bool:
        return self._active


def _normalize_fx_state(state: str | AnimeFxState) -> AnimeFxState:
    if isinstance(state, AnimeFxState):
        return state
    normalized = str(state or "").strip().lower().replace("_", " ")
    mapping = {
        "thinking": AnimeFxState.THINKING,
        "coding": AnimeFxState.CODING,
        "testing": AnimeFxState.TESTING,
        "passed": AnimeFxState.PASSED,
        "ok": AnimeFxState.PASSED,
        "failed": AnimeFxState.FAILED,
        "waiting": AnimeFxState.WAITING,
    }
    return mapping.get(normalized, AnimeFxState.WAITING)
