"""AI coding mission-thread workspace for Sovereign Console."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from apps.ui.anime_micro_fx import AnimeFxIntensity, CommandAura
from apps.ui.coding_activity_panel import (
    CodingActivityPanel,
    CodingActivityState,
    MISSION_THREAD_CARDS,
    TestGatePanel,
    activity_from_snapshot,
)
from apps.ui.i18n import UiText
from apps.ui.mission_widgets import HFX_008_COMPACT_CHAIN, MISSION_FIELD_KEYS, mission_projection
from apps.ui.motion import SyncState, resolve_sync_state
from apps.ui.read_models import RuntimeSnapshot

WORKSPACE_ACTION_KEYS: tuple[tuple[str, str], ...] = (
    ("generate_gemini_packet", "workspace.generate_gemini"),
    ("generate_codex_task_packet", "workspace.generate_codex"),
    ("generate_claude_review_packet", "workspace.generate_claude"),
    ("start_hfx_008_dry_run", "workspace.start_hfx_dry_run"),
    ("inspect_latest_artifact", "workspace.inspect_latest_artifact"),
    ("open_reviews", "workspace.open_reviews"),
    ("open_runs", "workspace.open_runs"),
    ("open_settings", "workspace.open_settings"),
)

WORKSPACE_REQUIRED_FIELDS: tuple[str, ...] = (
    "current mission",
    "command area",
    "large command bar",
    "mission thread",
    "activity stream",
    "Coding Activity Panel",
    "Test Gate Panel",
    "next required action",
    "HFX_008 compact chain",
    "compact black box/event stream",
    "recent runs",
    "recent artifacts",
    "pending reviews count",
    "quarantined count",
    "local runtime status",
    "degraded sync banner",
    "context packet quick actions",
)

THREAD_CARD_KEYS: tuple[tuple[str, str], ...] = (
    ("User command placeholder", "workspace.user_command_placeholder"),
    ("AI planning card", "workspace.ai_planning_card"),
    ("Coding activity card", "workspace.coding_activity_card"),
    ("Test gate card", "workspace.test_gate_card"),
    ("Artifact/review summary card", "workspace.artifact_review_summary_card"),
    ("Final report placeholder card", "workspace.final_report_placeholder_card"),
)


class WorkspacePage(QWidget):
    """Default AI coding work surface; all data is read projection or disabled intent."""

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.title = QLabel(self.text.tr("page.workspace"), self)
        self.title.setObjectName("WorkspaceTitle")
        layout.addWidget(self.title)

        self.degraded_banner = QLabel(self.text.tr("sync.degraded.detail"), self)
        self.degraded_banner.setObjectName("WorkspaceDegradedBanner")
        self.degraded_banner.setWordWrap(True)
        self.degraded_banner.setVisible(False)
        layout.addWidget(self.degraded_banner)

        self.command_panel = CommandAura(self)
        self.command_panel.setObjectName("WorkspaceCommandPanel")
        self.command_panel.setProperty("role", "commandBar")
        command_layout = QVBoxLayout(self.command_panel)
        command_layout.setContentsMargins(16, 12, 16, 12)
        command_layout.setSpacing(4)
        self.command_label = QLabel(self.text.tr("workspace.command_placeholder"), self.command_panel)
        self.command_label.setObjectName("WorkspaceCommandBar")
        self.command_label.setWordWrap(True)
        self.next_action_label = QLabel("--", self.command_panel)
        self.next_action_label.setObjectName("WorkspaceNextAction")
        self.next_action_label.setWordWrap(True)
        command_layout.addWidget(self.command_label)
        command_layout.addWidget(self.next_action_label)
        layout.addWidget(self.command_panel)

        center = QHBoxLayout()
        center.setSpacing(10)
        self.thread_panel = QFrame(self)
        self.thread_panel.setObjectName("MissionThreadPanel")
        thread_layout = QVBoxLayout(self.thread_panel)
        thread_layout.setContentsMargins(0, 0, 0, 0)
        thread_layout.setSpacing(8)
        self.thread_title = QLabel(
            f"{self.text.tr('workspace.mission_thread')} / {self.text.tr('workspace.activity_stream')}",
            self.thread_panel,
        )
        self.thread_title.setProperty("role", "eyebrow")
        thread_layout.addWidget(self.thread_title)
        self._thread_cards: dict[str, QLabel] = {}
        for card_name, label_key in THREAD_CARD_KEYS:
            card, label = _thread_card(self.text.tr(label_key), self.thread_panel)
            self._thread_cards[card_name] = label
            thread_layout.addWidget(card)
        thread_layout.addStretch(1)
        center.addWidget(self.thread_panel, stretch=2)

        work_column = QVBoxLayout()
        work_column.setSpacing(10)
        self.mission_card = QFrame(self)
        self.mission_card.setObjectName("CurrentMissionCard")
        self.mission_card.setProperty("role", "metricCard")
        mission_layout = QVBoxLayout(self.mission_card)
        mission_layout.setContentsMargins(12, 10, 12, 10)
        self.mission_title = QLabel(self.text.tr("common.current_mission"), self.mission_card)
        self.mission_title.setProperty("role", "eyebrow")
        mission_layout.addWidget(self.mission_title)
        self._mission_values: dict[str, QLabel] = {}
        mission_grid = QGridLayout()
        mission_grid.setSpacing(7)
        for index, field in enumerate(MISSION_FIELD_KEYS):
            label = QLabel(field, self.mission_card)
            label.setProperty("role", "eyebrow")
            value = QLabel("--", self.mission_card)
            value.setWordWrap(True)
            self._mission_values[field] = value
            mission_grid.addWidget(label, index // 2, (index % 2) * 2)
            mission_grid.addWidget(value, index // 2, (index % 2) * 2 + 1)
        mission_layout.addLayout(mission_grid)
        work_column.addWidget(self.mission_card)

        self.coding_activity_panel = CodingActivityPanel(self, language=language)
        work_column.addWidget(self.coding_activity_panel, stretch=2)

        self.test_gate_panel = TestGatePanel(self, language=language)
        work_column.addWidget(self.test_gate_panel)

        self.chain_panel = QFrame(self)
        self.chain_panel.setObjectName("WorkspaceMissionChain")
        self.chain_panel.setProperty("role", "metricCard")
        chain_layout = QVBoxLayout(self.chain_panel)
        chain_layout.setContentsMargins(12, 10, 12, 10)
        self.chain_title = QLabel(self.text.tr("workspace.hfx_008_chain"), self.chain_panel)
        self.chain_title.setProperty("role", "eyebrow")
        self.chain_label = QLabel(" -> ".join(HFX_008_COMPACT_CHAIN), self.chain_panel)
        self.chain_label.setObjectName("HFX008CompactChain")
        self.chain_label.setWordWrap(True)
        chain_layout.addWidget(self.chain_title)
        chain_layout.addWidget(self.chain_label)
        work_column.addWidget(self.chain_panel)
        center.addLayout(work_column, stretch=5)
        layout.addLayout(center, stretch=5)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.recent_runs = QLabel("--", self)
        self.recent_artifacts = QLabel("--", self)
        self.pending_reviews_count = QLabel("0", self)
        self.quarantined_count = QLabel("0", self)
        self.local_runtime_status = QLabel("--", self)
        metric_widgets = (
            ("workspace.recent_runs", self.recent_runs),
            ("workspace.recent_artifacts", self.recent_artifacts),
            ("workspace.pending_reviews_count", self.pending_reviews_count),
            ("workspace.quarantined_count", self.quarantined_count),
            ("workspace.local_runtime_status", self.local_runtime_status),
        )
        self._metric_titles: list[tuple[str, QLabel]] = []
        for index, (key, widget) in enumerate(metric_widgets):
            widget.setWordWrap(True)
            panel, title_label = _panel(self.text.tr(key), widget)
            self._metric_titles.append((key, title_label))
            metrics.addWidget(panel, index // 3, index % 3)
        layout.addLayout(metrics)

        self.actions_panel = QFrame(self)
        self.actions_panel.setObjectName("WorkspaceActions")
        self.actions_panel.setProperty("role", "metricCard")
        actions_layout = QGridLayout(self.actions_panel)
        actions_layout.setContentsMargins(12, 10, 12, 10)
        actions_layout.addWidget(_eyebrow(self.text.tr("workspace.context_packets"), self.actions_panel), 0, 0, 1, 2)
        self._action_buttons: dict[str, QPushButton] = {}
        for index, (action_id, label_key) in enumerate(WORKSPACE_ACTION_KEYS, start=1):
            button = QPushButton(self.text.tr(label_key), self.actions_panel)
            button.setObjectName(f"WorkspaceAction_{action_id}")
            button.setEnabled(False)
            button.setToolTip(self.text.tr("common.disabled_until_facade"))
            self._action_buttons[action_id] = button
            actions_layout.addWidget(button, (index + 1) // 2, (index + 1) % 2)
        layout.addWidget(self.actions_panel)

    def render_snapshot(
        self,
        snapshot: RuntimeSnapshot,
        *,
        sync_state: SyncState | None = None,
        anime_fx_intensity: str | AnimeFxIntensity = AnimeFxIntensity.STANDARD,
    ) -> None:
        state = sync_state or resolve_sync_state(snapshot)
        self.degraded_banner.setVisible(state is SyncState.DEGRADED)
        projection = mission_projection(snapshot)
        for field, value in projection.items():
            self._mission_values[field].setText(str(value))
        self.next_action_label.setText(str(projection["next_action"]))
        self.recent_runs.setText("\n".join(f"{job.job_id} | {job.status}" for job in snapshot.latest_jobs[:4]) or "--")
        self.recent_artifacts.setText(
            "\n".join(f"{artifact.artifact_id} | {artifact.review_status}" for artifact in snapshot.latest_artifacts[:4])
            or "--"
        )
        pending_reviews = sum(1 for artifact in snapshot.latest_artifacts if artifact.review_status in {"needs_review", "new"})
        quarantined_artifacts = sum(1 for artifact in snapshot.latest_artifacts if artifact.quarantine_status != "clean")
        self.pending_reviews_count.setText(str(pending_reviews))
        self.quarantined_count.setText(str(snapshot.quarantined_jobs + quarantined_artifacts))
        self.local_runtime_status.setText(f"{snapshot.runtime_status} | {state.value}")

        activity = activity_from_snapshot(snapshot)
        self.coding_activity_panel.render_activity(
            activity,
            anime_fx_intensity=anime_fx_intensity,
            memory_pressure=snapshot.memory_pressure,
            sync_state=state,
        )
        self.test_gate_panel.render_gates(activity.test_gate_summary)
        self.command_panel.set_aura(
            activity.normalized_state()
            in {CodingActivityState.THINKING, CodingActivityState.CODING, CodingActivityState.TESTING},
            intensity=anime_fx_intensity,
        )

    def required_fields(self) -> tuple[str, ...]:
        return WORKSPACE_REQUIRED_FIELDS

    def mission_fields(self) -> tuple[str, ...]:
        return MISSION_FIELD_KEYS

    def compact_chain_stages(self) -> tuple[str, ...]:
        return HFX_008_COMPACT_CHAIN

    def mission_thread_cards(self) -> tuple[str, ...]:
        return MISSION_THREAD_CARDS

    def action_controls(self) -> tuple[QPushButton, ...]:
        return tuple(self._action_buttons.values())

    def rendered_mission(self) -> dict[str, str]:
        return {field: label.text() for field, label in self._mission_values.items()}

    def command_placeholder(self) -> str:
        return self.command_label.text()

    def coding_activity_states(self) -> tuple[str, ...]:
        return self.coding_activity_panel.supported_states()

    def test_gate_names(self) -> tuple[str, ...]:
        return self.test_gate_panel.gate_names()

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.workspace"))
        self.degraded_banner.setText(self.text.tr("sync.degraded.detail"))
        self.mission_title.setText(self.text.tr("common.current_mission"))
        self.command_label.setText(self.text.tr("workspace.command_placeholder"))
        self.chain_title.setText(self.text.tr("workspace.hfx_008_chain"))
        self.thread_title.setText(f"{self.text.tr('workspace.mission_thread')} / {self.text.tr('workspace.activity_stream')}")
        for card_name, label_key in THREAD_CARD_KEYS:
            self._thread_cards[card_name].setText(self.text.tr(label_key))
        for key, label in self._metric_titles:
            label.setText(self.text.tr(key).upper())
        for action_id, label_key in WORKSPACE_ACTION_KEYS:
            button = self._action_buttons[action_id]
            button.setText(self.text.tr(label_key))
            button.setToolTip(self.text.tr("common.disabled_until_facade"))
        self.coding_activity_panel.apply_language(language)
        self.test_gate_panel.apply_language(language)


def _panel(title: str, content: QWidget) -> tuple[QFrame, QLabel]:
    panel = QFrame()
    panel.setProperty("role", "metricCard")
    panel.setMinimumHeight(76)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 10, 12, 10)
    title_label = QLabel(title.upper(), panel)
    title_label.setProperty("role", "eyebrow")
    layout.addWidget(title_label)
    layout.addWidget(content)
    return panel, title_label


def _thread_card(text: str, parent: QWidget | None = None) -> tuple[QFrame, QLabel]:
    panel = QFrame(parent)
    panel.setProperty("role", "threadCard")
    panel.setMinimumHeight(48)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(10, 8, 10, 8)
    label = QLabel(text, panel)
    label.setWordWrap(True)
    layout.addWidget(label)
    return panel, label


def _eyebrow(text: str, parent: object | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setProperty("role", "eyebrow")
    return label
