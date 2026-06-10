"""Workspace overlay for stale or unavailable runtime projections."""

from __future__ import annotations

from apps.ui import QFrame, QLabel, QVBoxLayout, Qt
from apps.ui.i18n import UiText
from apps.ui.motion import SyncState, resolve_sync_state, risky_actions_locked
from apps.ui.read_models import RuntimeSnapshot


class SyncLostOverlay(QFrame):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("SyncLostOverlay")
        self._bound_controls: list[tuple[object, bool]] = []
        self._sync_state = SyncState.HEALTHY
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)
        self.title = QLabel(self.text.tr("sync.lost.title"), self)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = QLabel(self.text.tr("sync.lost.detail"), self)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.detail)
        layout.addStretch(1)
        self.setVisible(False)

    def bind_action_controls(self, controls: tuple[object, ...] | list[object]) -> None:
        for control in controls:
            already_bound = any(existing is control for existing, _enabled in self._bound_controls)
            if not already_bound and hasattr(control, "isEnabled"):
                self._bound_controls.append((control, bool(control.isEnabled())))

    def apply_snapshot(
        self,
        snapshot: RuntimeSnapshot,
        *,
        action_controls: tuple[object, ...] | list[object] = (),
        had_healthy_projection: bool = False,
    ) -> None:
        if action_controls:
            self.bind_action_controls(action_controls)
        self.set_sync_state(resolve_sync_state(snapshot, had_healthy_projection=had_healthy_projection))

    def set_sync_lost(self, lost: bool) -> None:
        self.set_sync_state(SyncState.LOST if lost else SyncState.HEALTHY)

    def set_sync_state(self, state: SyncState | str) -> None:
        self._sync_state = SyncState(state) if not isinstance(state, SyncState) else state
        self.setProperty("syncState", self._sync_state.value)
        self.setVisible(self._sync_state is SyncState.LOST)
        if self._sync_state is SyncState.LOST:
            self.title.setText(self.text.tr("sync.lost.title"))
            self.detail.setText(self.text.tr("sync.lost.detail"))
        elif self._sync_state is SyncState.DEGRADED:
            self.title.setText(self.text.tr("sync.degraded.title"))
            self.detail.setText(self.text.tr("sync.degraded.detail"))
        for control, originally_enabled in self._bound_controls:
            if hasattr(control, "setEnabled"):
                control.setEnabled(False if risky_actions_locked(self._sync_state) else originally_enabled)
        if self._sync_state is SyncState.LOST:
            self.style().unpolish(self)
            self.style().polish(self)
            self.raise_()

    def is_sync_lost(self) -> bool:
        return self._sync_state is SyncState.LOST

    def sync_state(self) -> str:
        return self._sync_state.value

    def actions_locked(self) -> bool:
        return risky_actions_locked(self._sync_state)

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.set_sync_state(self._sync_state)
