"""Single-window Sovereign Console unified workspace shell."""

from __future__ import annotations

from collections.abc import Callable

from apps.ui import QFrame, QLabel, QHBoxLayout, QMainWindow, QStackedWidget, QTimer, QVBoxLayout, QWidget, Slot
from apps.ui.anime_micro_fx import AnimeFxIntensity, effective_anime_fx_intensity
from apps.ui.artifacts_page import ArtifactsPage
from apps.ui.i18n import UiText
from apps.ui.live_event_stream import LiveEventStream
from apps.ui.motion import MotionIntensity, SyncState, effective_motion_intensity, resolve_sync_state
from apps.ui.navigation_rail import NavigationRail
from apps.ui.read_models import RuntimeSnapshot, fake_phase1_snapshot
from apps.ui.reviews_page import ReviewsPage
from apps.ui.right_inspector import RightInspector
from apps.ui.runs_page import RunsPage
from apps.ui.settings_page import SettingsPage
from apps.ui.sync_lost_overlay import SyncLostOverlay
from apps.ui.system_pulse_bar import SystemPulseBar
from apps.ui.theme import application_stylesheet
from apps.ui.workspace_page import WorkspacePage

SnapshotProvider = Callable[[], RuntimeSnapshot]


class SovereignConsoleMainWindow(QMainWindow):
    """Native app shell that reads projections and issues only gated intents."""

    def __init__(
        self,
        *,
        snapshot_provider: SnapshotProvider | None = None,
        parent: object | None = None,
        language: str = "auto",
        motion_intensity: MotionIntensity = MotionIntensity.STANDARD,
        anime_fx_intensity: AnimeFxIntensity = AnimeFxIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.motion_intensity = motion_intensity
        self.anime_fx_intensity = anime_fx_intensity
        self.snapshot_provider = snapshot_provider or fake_phase1_snapshot
        self._seen_healthy_projection = False
        self.setWindowTitle(self.text.tr("app.title"))
        self.resize(1320, 820)
        self.setStyleSheet(application_stylesheet())

        self.pulse_bar = SystemPulseBar(self)
        self.navigation = NavigationRail(self, language=self.text.language)
        self.workspace = QStackedWidget(self)
        self.workspace_page = WorkspacePage(self.workspace, language=self.text.language)
        self.runs_page = RunsPage(self.workspace, language=self.text.language)
        self.artifacts_page = ArtifactsPage(self.workspace, language=self.text.language)
        self.reviews_page = ReviewsPage(self.workspace, language=self.text.language)
        self.settings_page = SettingsPage(self.workspace, language=self.text.language)
        self.inspector = RightInspector(self, language=self.text.language)
        self.event_stream = LiveEventStream(self, language=self.text.language)

        self._page_indexes: dict[str, int] = {}
        self._add_page("workspace", self.workspace_page)
        self._add_page("runs", self.runs_page)
        self._add_page("artifacts", self.artifacts_page)
        self._add_page("reviews", self.reviews_page)
        self._add_page("settings", self.settings_page)

        self.workspace_frame = QFrame(self)
        workspace_layout = QVBoxLayout(self.workspace_frame)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.workspace)
        self.sync_lost_overlay = SyncLostOverlay(self.workspace_frame, language=self.text.language)
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
        self.degraded_banner = QLabel(self.text.tr("sync.degraded.detail"), root)
        self.degraded_banner.setObjectName("GlobalDegradedBanner")
        self.degraded_banner.setWordWrap(True)
        self.degraded_banner.setVisible(False)
        root_layout.addWidget(self.pulse_bar)
        root_layout.addWidget(self.degraded_banner)
        root_layout.addWidget(content, stretch=1)
        root_layout.addWidget(self.event_stream)
        self.setCentralWidget(root)

        self.navigation.page_selected.connect(self.show_page)
        self.runs_page.run_selected.connect(self.inspector.show_run)
        self.artifacts_page.artifact_selected.connect(self.inspector.show_artifact)

        self.show_page("workspace")

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
        sync_state = resolve_sync_state(snapshot, had_healthy_projection=self._seen_healthy_projection)
        self.motion_intensity = effective_motion_intensity(
            self.motion_intensity,
            memory_pressure=snapshot.memory_pressure,
            sync_state=sync_state,
        )
        self.anime_fx_intensity = effective_anime_fx_intensity(
            self.anime_fx_intensity,
            memory_pressure=snapshot.memory_pressure,
            sync_state=sync_state,
        )
        self.pulse_bar.render_snapshot(snapshot, sync_state=sync_state)
        self.navigation.render_badges(snapshot)
        self.workspace_page.render_snapshot(snapshot, sync_state=sync_state, anime_fx_intensity=self.anime_fx_intensity)
        self.runs_page.render_snapshot(snapshot)
        self.artifacts_page.render_snapshot(snapshot)
        self.reviews_page.render_snapshot(snapshot)
        self.settings_page.render_snapshot(snapshot)
        self.settings_page.set_anime_fx_intensity(self.anime_fx_intensity)
        self.event_stream.render_snapshot(snapshot)
        self.degraded_banner.setVisible(sync_state is SyncState.DEGRADED)
        self.degraded_banner.setText(self.text.tr("sync.degraded.detail"))
        self.sync_lost_overlay.set_sync_state(sync_state)
        if sync_state is SyncState.HEALTHY:
            self._seen_healthy_projection = True
        self._position_overlay()

    def set_language(self, language: str) -> None:
        self.text.set_language(language)
        self.setWindowTitle(self.text.tr("app.title"))
        self.degraded_banner.setText(self.text.tr("sync.degraded.detail"))
        for widget in (
            self.navigation,
            self.workspace_page,
            self.runs_page,
            self.artifacts_page,
            self.reviews_page,
            self.settings_page,
            self.inspector,
            self.sync_lost_overlay,
            self.event_stream,
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
            self.workspace_page,
            self.runs_page,
            self.artifacts_page,
            self.reviews_page,
        ):
            page_controls = getattr(page, "action_controls", None)
            if callable(page_controls):
                controls.extend(page_controls())
        return tuple(controls)
