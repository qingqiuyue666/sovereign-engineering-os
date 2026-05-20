"""Workspace overlay for stale or unavailable runtime projections."""

from __future__ import annotations

from apps.ui import QFrame, QLabel, QVBoxLayout, Qt
from apps.ui.read_models import RuntimeSnapshot


class SyncLostOverlay(QFrame):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SyncLostOverlay")
        self._bound_controls: list[tuple[object, bool]] = []
        self._sync_lost = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)
        self.title = QLabel("SYSTEM SYNC LOST", self)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = QLabel("Read-only navigation remains available. Action controls are locked.", self)
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
    ) -> None:
        if action_controls:
            self.bind_action_controls(action_controls)
        self.set_sync_lost(snapshot.is_sync_lost())

    def set_sync_lost(self, lost: bool) -> None:
        self._sync_lost = bool(lost)
        self.setVisible(self._sync_lost)
        for control, originally_enabled in self._bound_controls:
            if hasattr(control, "setEnabled"):
                control.setEnabled(False if self._sync_lost else originally_enabled)
        if self._sync_lost:
            self.raise_()

    def is_sync_lost(self) -> bool:
        return self._sync_lost
