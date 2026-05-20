"""Single-window Sovereign Console Phase 1 shell."""

from __future__ import annotations

from collections.abc import Callable

from apps.ui import QFrame, QLabel, QHBoxLayout, QMainWindow, QStackedWidget, QTimer, QVBoxLayout, QWidget, Slot
from apps.ui.dashboard_page import DashboardPage
from apps.ui.job_queue_page import JobQueuePage
from apps.ui.live_event_stream import LiveEventStream
from apps.ui.navigation_rail import NavigationRail
from apps.ui.read_models import RuntimeSnapshot, fake_phase1_snapshot
from apps.ui.right_inspector import RightInspector
from apps.ui.sync_lost_overlay import SyncLostOverlay
from apps.ui.system_pulse_bar import SystemPulseBar
from apps.ui.theme import application_stylesheet

SnapshotProvider = Callable[[], RuntimeSnapshot]


class SovereignConsoleMainWindow(QMainWindow):
    """Native app shell that only reads projections and displays metadata."""

    def __init__(self, *, snapshot_provider: SnapshotProvider | None = None, parent: object | None = None) -> None:
        super().__init__(parent)
        self.snapshot_provider = snapshot_provider or fake_phase1_snapshot
        self.setWindowTitle("Sovereign Console")
        self.resize(1320, 820)
        self.setStyleSheet(application_stylesheet())

        self.pulse_bar = SystemPulseBar(self)
        self.navigation = NavigationRail(self)
        self.workspace = QStackedWidget(self)
        self.dashboard_page = DashboardPage(self.workspace)
        self.job_queue_page = JobQueuePage(self.workspace)
        self.inspector = RightInspector(self)
        self.event_stream = LiveEventStream(self)

        self._page_indexes: dict[str, int] = {}
        self._add_page("dashboard", self.dashboard_page)
        self._add_page("job_queue", self.job_queue_page)
        for page_id in (
            "system_health",
            "hfx_factory",
            "context_packs",
            "human_review",
            "failure_quarantine",
            "artifact_store",
            "asset_library",
            "settings",
        ):
            self._add_page(page_id, _placeholder_page(page_id))

        self.workspace_frame = QFrame(self)
        workspace_layout = QVBoxLayout(self.workspace_frame)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.workspace)
        self.sync_lost_overlay = SyncLostOverlay(self.workspace_frame)
        self.sync_lost_overlay.bind_action_controls(self.job_queue_page.action_controls())

        content = QFrame(self)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.navigation)
        content_layout.addWidget(self.workspace_frame, stretch=1)
        content_layout.addWidget(self.inspector)

        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.pulse_bar)
        root_layout.addWidget(content, stretch=1)
        root_layout.addWidget(self.event_stream)
        self.setCentralWidget(root)

        self.navigation.page_selected.connect(self.show_page)
        self.job_queue_page.job_selected.connect(self.inspector.show_job)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1_000)
        self.refresh_timer.timeout.connect(self.refresh_snapshot)
        self.refresh_timer.start()
        self.refresh_snapshot()

    @Slot(str)
    def show_page(self, page_id: str) -> None:
        index = self._page_indexes.get(page_id)
        if index is not None:
            self.workspace.setCurrentIndex(index)
            self.navigation.select_page(page_id, emit=False)

    @Slot()
    def refresh_snapshot(self) -> None:
        snapshot = self.snapshot_provider()
        self.pulse_bar.render_snapshot(snapshot)
        self.dashboard_page.render_snapshot(snapshot)
        self.job_queue_page.render_snapshot(snapshot)
        self.event_stream.render_snapshot(snapshot)
        self.sync_lost_overlay.apply_snapshot(snapshot)
        self._position_overlay()

    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt API.
        super().resizeEvent(event)
        self._position_overlay()

    def _position_overlay(self) -> None:
        self.sync_lost_overlay.setGeometry(self.workspace_frame.rect())

    def _add_page(self, page_id: str, widget: QWidget) -> None:
        self._page_indexes[page_id] = self.workspace.addWidget(widget)


def _placeholder_page(page_id: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(18, 18, 18, 18)
    title = QLabel(page_id.replace("_", " ").title(), page)
    label = QLabel("Placeholder: Phase 2", page)
    label.setObjectName("Phase2Placeholder")
    layout.addWidget(title)
    layout.addWidget(label)
    layout.addStretch(1)
    return page
