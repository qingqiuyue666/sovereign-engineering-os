"""HFX_008 landing chain read-only state view."""

from __future__ import annotations

from apps.ui import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from apps.ui.energy_widgets import EnergyLine, EnergyState, normalize_energy_state
from apps.ui.i18n import UiText, localize_status
from apps.ui.motion import MotionIntensity
from apps.ui.read_models import RuntimeSnapshot

HFX_008_CHAIN_STAGES: tuple[str, ...] = (
    "Topology Audit",
    "Proof Artifact",
    "Artifact Validation",
    "Human Review",
    "Materialization Summary",
    "Final Claim Gate",
)

_STAGE_KEYS: dict[str, str] = {
    "Topology Audit": "hfx.topology_audit",
    "Proof Artifact": "hfx.proof_artifact",
    "Artifact Validation": "hfx.artifact_validation",
    "Human Review": "hfx.human_review",
    "Materialization Summary": "hfx.materialization_summary",
    "Final Claim Gate": "hfx.final_claim_gate",
}


class HfxLandingChainPage(QWidget):
    def __init__(
        self,
        parent: object | None = None,
        *,
        language: str = "en",
        motion_intensity: MotionIntensity = MotionIntensity.STANDARD,
    ) -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.motion_intensity = motion_intensity
        self._stage_statuses: dict[str, str] = _default_stage_statuses()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.hfx_landing_chain"), self)
        self.title.setObjectName("HfxLandingChainTitle")
        layout.addWidget(self.title)

        chain_layout = QHBoxLayout()
        chain_layout.setSpacing(6)
        self._stage_labels: dict[str, QLabel] = {}
        self._status_labels: dict[str, QLabel] = {}
        self._connectors: list[EnergyLine] = []
        for index, stage in enumerate(HFX_008_CHAIN_STAGES):
            card, stage_label, status_label = _stage_card(self.text.tr(_STAGE_KEYS[stage]))
            self._stage_labels[stage] = stage_label
            self._status_labels[stage] = status_label
            chain_layout.addWidget(card)
            if index < len(HFX_008_CHAIN_STAGES) - 1:
                connector = EnergyLine(state=EnergyState.IDLE, motion_intensity=motion_intensity, parent=self)
                self._connectors.append(connector)
                chain_layout.addWidget(connector)
        layout.addLayout(chain_layout)

        self.summary = QLabel("", self)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addStretch(1)
        self.render_stage_statuses(self._stage_statuses)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        statuses = _default_stage_statuses()
        statuses["Topology Audit"] = "Dry Run Complete"
        statuses["Proof Artifact"] = "Ready for Review" if snapshot.latest_artifacts_count else "Blocked: Missing Visual Proof"
        statuses["Artifact Validation"] = "Requires Human Review"
        statuses["Human Review"] = "Requires Human Review"
        statuses["Materialization Summary"] = "Materialization Required"
        statuses["Final Claim Gate"] = "Blocked: Human Review Required"
        self.render_stage_statuses(statuses)
        self.summary.setText(snapshot.hfx_008_landing_summary)

    def render_stage_statuses(self, statuses: dict[str, str]) -> None:
        self._stage_statuses = dict(statuses)
        blocked_seen = False
        connector_states: list[EnergyState] = []
        for stage in HFX_008_CHAIN_STAGES:
            status = self._stage_statuses.get(stage, "Not Started")
            if blocked_seen:
                status = "Blocked: Placeholder Guide"
                self._stage_statuses[stage] = status
            self._status_labels[stage].setText(localize_status(status, self.text.language))
            state = normalize_energy_state(status)
            if state in {EnergyState.FAILED, EnergyState.BLOCKED}:
                blocked_seen = True
            if stage != HFX_008_CHAIN_STAGES[-1]:
                connector_states.append(state)
        for connector, state in zip(self._connectors, connector_states, strict=True):
            connector.set_state(state)

    def stage_names(self) -> tuple[str, ...]:
        return HFX_008_CHAIN_STAGES

    def stage_statuses(self) -> dict[str, str]:
        return dict(self._stage_statuses)

    def connector_states(self) -> tuple[str, ...]:
        return tuple(connector.state.value for connector in self._connectors)

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.hfx_landing_chain"))
        for stage, label in self._stage_labels.items():
            label.setText(self.text.tr(_STAGE_KEYS[stage]))
        self.render_stage_statuses(self._stage_statuses)


def _stage_card(title: str) -> tuple[QFrame, QLabel, QLabel]:
    card = QFrame()
    card.setProperty("role", "metricCard")
    card.setMinimumWidth(128)
    card.setMinimumHeight(96)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 8, 10, 8)
    stage_label = QLabel(title, card)
    stage_label.setProperty("role", "eyebrow")
    stage_label.setWordWrap(True)
    status_label = QLabel("--", card)
    status_label.setWordWrap(True)
    layout.addWidget(stage_label)
    layout.addWidget(status_label)
    layout.addStretch(1)
    return card, stage_label, status_label


def _default_stage_statuses() -> dict[str, str]:
    return {
        "Topology Audit": "Ready for Review",
        "Proof Artifact": "Ready for Review",
        "Artifact Validation": "Requires Human Review",
        "Human Review": "Requires Human Review",
        "Materialization Summary": "Materialization Required",
        "Final Claim Gate": "Blocked: Human Review Required",
    }
