"""Human Review page with gated intent controls only."""

from __future__ import annotations

from apps.ui import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget
from apps.ui.energy_widgets import QuarantineStripe, ReviewSeal
from apps.ui.i18n import UiText
from apps.ui.read_models import ArtifactRow, RuntimeSnapshot

MIN_REJECT_REASON_LENGTH = 5

HUMAN_REVIEW_FIELDS: tuple[str, ...] = (
    "pending reviews list",
    "preview placeholder",
    "metadata panel",
    "approve button",
    "reject button",
    "reject reason field",
    "quarantine button",
    "final claim warning",
)


class HumanReviewPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self._facade_actions_enabled = False
        self._reject_reason = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.human_review"), self)
        self.title.setObjectName("HumanReviewTitle")
        layout.addWidget(self.title)

        body = QHBoxLayout()
        self.pending_reviews = QLabel("--", self)
        self.pending_reviews.setObjectName("PendingReviewsList")
        self.pending_reviews.setWordWrap(True)
        body.addWidget(_panel(self.text.tr("review.pending"), self.pending_reviews), stretch=1)

        self.preview = QLabel(self.text.tr("common.preview_placeholder"), self)
        self.preview.setObjectName("HumanReviewPreview")
        self.preview.setWordWrap(True)
        body.addWidget(_panel(self.text.tr("common.preview_placeholder"), self.preview), stretch=1)

        self.metadata = QLabel("artifact_id: --\njob_id: --\nreview_status: --", self)
        self.metadata.setObjectName("HumanReviewMetadata")
        self.metadata.setWordWrap(True)
        body.addWidget(_panel(self.text.tr("common.metadata"), self.metadata), stretch=1)
        layout.addLayout(body, stretch=1)

        self.reject_reason_label = QLabel(self.text.tr("review.reason"), self)
        self.reject_reason_label.setProperty("role", "eyebrow")
        self.reject_reason_editor = QPlainTextEdit(self)
        self.reject_reason_editor.setObjectName("RejectReasonField")
        self.reject_reason_editor.setMaximumHeight(70)
        text_changed = getattr(self.reject_reason_editor, "textChanged", None)
        if hasattr(text_changed, "connect"):
            text_changed.connect(self._reason_editor_changed)
        layout.addWidget(self.reject_reason_label)
        layout.addWidget(self.reject_reason_editor)

        controls = QHBoxLayout()
        self.approve_button = QPushButton(self.text.tr("review.approve"), self)
        self.reject_button = QPushButton(self.text.tr("review.reject"), self)
        self.quarantine_button = QPushButton(self.text.tr("review.quarantine"), self)
        for button in (self.approve_button, self.reject_button, self.quarantine_button):
            button.setToolTip(self.text.tr("common.disabled_until_facade"))
            button.setEnabled(False)
            controls.addWidget(button)
        controls.addStretch(1)
        layout.addLayout(controls)

        markers = QHBoxLayout()
        self.review_seal = ReviewSeal(self)
        self.quarantine_stripe = QuarantineStripe(self)
        markers.addWidget(self.review_seal)
        markers.addWidget(self.quarantine_stripe)
        layout.addLayout(markers)

        self.final_claim_warning = QLabel(self.text.tr("review.final_claim_warning"), self)
        self.final_claim_warning.setObjectName("FinalClaimWarning")
        self.final_claim_warning.setWordWrap(True)
        layout.addWidget(self.final_claim_warning)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        pending = tuple(artifact for artifact in snapshot.latest_artifacts if artifact.review_status in {"needs_review", "new"})
        self.render_pending_reviews(pending)

    def render_pending_reviews(self, artifacts: tuple[ArtifactRow, ...]) -> None:
        if not artifacts:
            self.pending_reviews.setText("No pending reviews")
            self.metadata.setText("artifact_id: --\njob_id: --\nreview_status: --")
            return
        self.pending_reviews.setText("\n".join(f"{artifact.artifact_id} | {artifact.review_status}" for artifact in artifacts))
        first = artifacts[0]
        self.metadata.setText(
            "\n".join(
                (
                    f"artifact_id: {first.artifact_id}",
                    f"job_id: {first.job_id}",
                    f"artifact_type: {first.artifact_type}",
                    f"review_status: {first.review_status}",
                    f"safe_to_publish: {first.safe_to_publish}",
                )
            )
        )

    def set_reject_reason(self, reason: str) -> None:
        self._reject_reason = str(reason)
        if hasattr(self.reject_reason_editor, "setPlainText") and self.reject_reason_editor.toPlainText() != self._reject_reason:
            self.reject_reason_editor.setPlainText(self._reject_reason)
        self._update_action_state()

    def reject_reason_is_valid(self) -> bool:
        return len(self._reject_reason.strip()) >= MIN_REJECT_REASON_LENGTH

    def set_facade_actions_enabled(self, enabled: bool) -> None:
        self._facade_actions_enabled = bool(enabled)
        self._update_action_state()

    def action_controls(self) -> tuple[QPushButton, ...]:
        return (self.approve_button, self.reject_button, self.quarantine_button)

    def required_fields(self) -> tuple[str, ...]:
        return HUMAN_REVIEW_FIELDS

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.human_review"))
        self.reject_reason_label.setText(self.text.tr("review.reason"))
        self.approve_button.setText(self.text.tr("review.approve"))
        self.reject_button.setText(self.text.tr("review.reject"))
        self.quarantine_button.setText(self.text.tr("review.quarantine"))
        self.final_claim_warning.setText(self.text.tr("review.final_claim_warning"))
        for button in self.action_controls():
            button.setToolTip(self.text.tr("common.disabled_until_facade"))

    def _reason_editor_changed(self) -> None:
        self._reject_reason = self.reject_reason_editor.toPlainText()
        self._update_action_state()

    def _update_action_state(self) -> None:
        self.approve_button.setEnabled(self._facade_actions_enabled)
        self.quarantine_button.setEnabled(self._facade_actions_enabled)
        self.reject_button.setEnabled(self._facade_actions_enabled and self.reject_reason_is_valid())


def _panel(title: str, content: QWidget) -> QFrame:
    panel = QFrame()
    panel.setProperty("role", "metricCard")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 10, 12, 10)
    label = QLabel(title, panel)
    label.setProperty("role", "eyebrow")
    layout.addWidget(label)
    layout.addWidget(content)
    layout.addStretch(1)
    return panel
