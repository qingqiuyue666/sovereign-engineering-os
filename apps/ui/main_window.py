"""Single-window Sovereign Console Phase 2 shell."""

from __future__ import annotations

from collections.abc import Callable

from apps.ui import QFrame, QLabel, QHBoxLayout, QMainWindow, QStackedWidget, QTimer, QVBoxLayout, QWidget, Slot
from apps.ui.artifact_store_page import ArtifactStorePage
from apps.ui.context_packs_page import ContextPacksPage
from apps.ui.dashboard_page import DashboardPage
from apps.ui.failure_quarantine_page import FailureQuarantinePage
from apps.ui.hfx_factory_page import HfxFactoryPage
from apps.ui.hfx_landing_chain_page import HfxLandingChainPage
from apps.ui.human_review_page import HumanReviewPage
from apps.ui.i18n import UiText
from apps.ui.job_queue_page import JobQueuePage
from apps.ui.live_event_stream import LiveEventStream
from apps.ui.motion import MotionIntensity, effective_motion_intensity, resolve_sync_state
from apps.ui.navigation_rail import NavigationRail
from apps.ui.read_models import RuntimeSnapshot, fake_phase1_snapshot
from apps.ui.right_inspector import RightInspector
from apps.ui.settings_page import SettingsPage
from apps.ui.sync_lost_overlay import SyncLostOverlay
from apps.ui.system_health_page import SystemHealthPage
from apps.ui.system_pulse_bar import SystemPulseBar
from apps.ui.theme import application_stylesheet

SnapshotProvider = Callable[[], RuntimeSnapshot]


class SovereignConsoleMainWindow(QMainWindow):
    """Native app shell that only reads projections and displays metadata."""

    def __init__(
        self,
        *,
        snapshot_provider: SnapshotProvider | None = None,
        parent: object | None = None,
        language: str = "auto",
        motion_intensity: MotionIntensity = MotionIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.motion_intensity = motion_intensity
        self.snapshot_provider = snapshot_provider or fake_phase1_snapshot
        self.setWindowTitle(self.text.tr("app.title"))
        self.resize(1320, 820)
        self.setStyleSheet(application_stylesheet())

        self.pulse_bar = SystemPulseBar(self)
        self.navigation = NavigationRail(self, language=self.text.language)
        self.workspace = QStackedWidget(self)
        self.dashboard_page = DashboardPage(self.workspace, language=self.text.language)
        self.job_queue_page = JobQueuePage(self.workspace, language=self.text.language)
        self.system_health_page = SystemHealthPage(self.workspace, language=self.text.language)
        self.hfx_factory_page = HfxFactoryPage(self.workspace, language=self.text.language)
        self.hfx_landing_chain_page = HfxLandingChainPage(
            self.workspace,
            language=self.text.language,
            motion_intensity=motion_intensity,
        )
        self.context_packs_page = ContextPacksPage(self.workspace, language=self.text.language)
        self.human_review_page = HumanReviewPage(self.workspace, language=self.text.language)
        self.failure_quarantine_page = FailureQuarantinePage(self.workspace, language=self.text.language)
        self.artifact_store_page = ArtifactStorePage(self.workspace, language=self.text.language)
        self.settings_page = SettingsPage(self.workspace, language=self.text.language)
        self.inspector = RightInspector(self, language=self.text.language)
        self.event_stream = LiveEventStream(self)

        self._page_indexes: dict[str, int] = {}
        self._add_page("dashboard", self.dashboard_page)
        self._add_page("job_queue", self.job_queue_page)
        self._add_page("system_health", self.system_health_page)
        self._add_page("hfx_factory", self.hfx_factory_page)
        self._add_page("hfx_landing_chain", self.hfx_landing_chain_page)
        self._add_page("context_packs", self.context_packs_page)
        self._add_page("human_review", self.human_review_page)
        self._add_page("failure_quarantine", self.failure_quarantine_page)
        self._add_page("artifact_store", self.artifact_store_page)
        self._add_page("settings", self.settings_page)

        self.workspace_frame = QFrame(self)
        workspace_layout = QVBoxLayout(self.workspace_frame)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.workspace)
        self.sync_lost_overlay = SyncLostOverlay(self.workspace_frame)
        self.sync_lost_overlay.bind_action_controls(self._action_controls())

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
        self.artifact_store_page.artifact_selected.connect(self.inspector.show_artifact)

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
        sync_state = resolve_sync_state(snapshot)
        self.motion_intensity = effective_motion_intensity(
            self.motion_intensity,
            memory_pressure=snapshot.memory_pressure,
            sync_state=sync_state,
        )
        self.pulse_bar.render_snapshot(snapshot)
        self.dashboard_page.render_snapshot(snapshot)
        self.job_queue_page.render_snapshot(snapshot)
        self.system_health_page.render_snapshot(snapshot)
        self.hfx_factory_page.render_snapshot(snapshot)
        self.hfx_landing_chain_page.render_snapshot(snapshot)
        self.context_packs_page.render_snapshot(snapshot)
        self.human_review_page.render_snapshot(snapshot)
        self.failure_quarantine_page.render_snapshot(snapshot)
        self.artifact_store_page.render_snapshot(snapshot)
        self.event_stream.render_snapshot(snapshot)
        self.sync_lost_overlay.apply_snapshot(snapshot)
        self._position_overlay()

    def set_language(self, language: str) -> None:
        self.text.set_language(language)
        self.setWindowTitle(self.text.tr("app.title"))
        for widget in (
            self.navigation,
            self.dashboard_page,
            self.job_queue_page,
            self.system_health_page,
            self.hfx_factory_page,
            self.hfx_landing_chain_page,
            self.context_packs_page,
            self.human_review_page,
            self.failure_quarantine_page,
            self.artifact_store_page,
            self.settings_page,
            self.inspector,
            self.sync_lost_overlay,
        ):
            apply_language = getattr(widget, "apply_language", None)
            if callable(apply_language):
                apply_language(self.text.language)

    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt API.
        super().resizeEvent(event)
        self._position_overlay()

    def _position_overlay(self) -> None:
        self.sync_lost_overlay.setGeometry(self.workspace_frame.rect())

    def _add_page(self, page_id: str, widget: QWidget) -> None:
        self._page_indexes[page_id] = self.workspace.addWidget(widget)

    def _action_controls(self) -> tuple[object, ...]:
        controls: list[object] = []
        for page in (
            self.job_queue_page,
            self.artifact_store_page,
            self.human_review_page,
            self.failure_quarantine_page,
            self.context_packs_page,
        ):
            page_controls = getattr(page, "action_controls", None)
            if callable(page_controls):
                controls.extend(page_controls())
        return tuple(controls)
