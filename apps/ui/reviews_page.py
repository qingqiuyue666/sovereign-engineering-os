"""Reviews view absorbing human review, quarantine, and failure queues."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget
from apps.ui.energy_widgets import QuarantineStripe, ReviewSeal
from apps.ui.i18n import UiText
from apps.ui.read_models import ArtifactRow, JobRow, RuntimeSnapshot

MIN_REJECT_REASON_LENGTH = 5

REVIEWS_SECTIONS: tuple[str, ...] = ("Pending Reviews", "Rejected", "Quarantined", "Failures")

REVIEWS_REQUIRED_FIELDS: tuple[str, ...] = (
    "review list",
    "selected artifact preview placeholder",
    "approve control",
    "reject control",
    "reject reason validation",
    "quarantine state",
    "failure reason",
    "traceback dark panel",
    "event trail",
    "recommended fix",
    "final claim warning",
)


class ReviewsPage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self._facade_actions_enabled = False
        self._reject_reason = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.title = QLabel(self.text.tr("page.reviews"), self)
        self.title.setObjectName("ReviewsTitle")
        layout.addWidget(self.title)

        self.segment_bar = QHBoxLayout()
        self._section_labels: dict[str, QLabel] = {}
        for section, key in (
            ("Pending Reviews", "reviews.pending"),
            ("Rejected", "reviews.rejected"),
            ("Quarantined", "reviews.quarantined"),
            ("Failures", "reviews.failures"),
        ):
            label = QLabel(self.text.tr(key), self)
            label.setObjectName(f"ReviewsSegment_{section.replace(' ', '_')}")
            label.setProperty("role", "eyebrow")
            self._section_labels[section] = label
            panel = QFrame(self)
            panel.setProperty("role", "metricCard")
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(10, 6, 10, 6)
            panel_layout.addWidget(label)
            self.segment_bar.addWidget(panel)
        layout.addLayout(self.segment_bar)

        body = QGridLayout()
        body.setSpacing(10)
        self.review_list = QLabel("--", self)
        self.preview = QLabel(self.text.tr("common.preview_placeholder"), self)
        self.metadata = QLabel("artifact_id: --\nreview_status: --\nquarantine_status: --", self)
        self.quarantine_state = QLabel("--", self)
        self.failure_reason = QLabel("--", self)
        self.event_trail = QLabel("--", self)
        self.recommended_fix = QLabel("Inspect worker evidence and repair input contract", self)
        for widget in (
            self.review_list,
            self.preview,
            self.metadata,
            self.quarantine_state,
            self.failure_reason,
            self.event_trail,
            self.recommended_fix,
        ):
            widget.setWordWrap(True)
        panels = (
            (self.text.tr("reviews.pending"), self.review_list),
            (self.text.tr("common.preview_placeholder"), self.preview),
            (self.text.tr("common.metadata"), self.metadata),
            (self.text.tr("reviews.quarantined"), self.quarantine_state),
            (self.text.tr("failure.failure_reason"), self.failure_reason),
            (self.text.tr("failure.event_trail"), self.event_trail),
            (self.text.tr("failure.recommended_fix"), self.recommended_fix),
        )
        for index, (label, widget) in enumerate(panels):
            body.addWidget(_panel(label, widget), index // 3, index % 3)
        layout.addLayout(body, stretch=1)

        self.traceback_excerpt = QPlainTextEdit(self)
        self.traceback_excerpt.setObjectName("TracebackExcerptPanel")
        self.traceback_excerpt.setReadOnly(True)
        self.traceback_excerpt.setMaximumHeight(94)
        self.traceback_excerpt.setPlainText("traceback excerpt unavailable in read-only projection")
        layout.addWidget(_panel(self.text.tr("failure.traceback_excerpt"), self.traceback_excerpt))

        self.reject_reason_label = QLabel(self.text.tr("review.reason"), self)
        self.reject_reason_label.setProperty("role", "eyebrow")
        self.reject_reason_editor = QPlainTextEdit(self)
        self.reject_reason_editor.setObjectName("ReviewsRejectReasonField")
        self.reject_reason_editor.setMaximumHeight(56)
        text_changed = getattr(self.reject_reason_editor, "textChanged", None)
        if hasattr(text_changed, "connect"):
            text_changed.connect(self._reason_editor_changed)
        layout.addWidget(self.reject_reason_label)
        layout.addWidget(self.reject_reason_editor)

        controls = QHBoxLayout()
        self.approve_button = QPushButton(self.text.tr("review.approve"), self)
        self.reject_button = QPushButton(self.text.tr("review.reject"), self)
        self.quarantine_button = QPushButton(self.text.tr("review.quarantine"), self)
        self.export_bundle_button = QPushButton(self.text.tr("failure.export_bundle"), self)
        for button in (self.approve_button, self.reject_button, self.quarantine_button, self.export_bundle_button):
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
        self.final_claim_warning.setObjectName("ReviewsFinalClaimWarning")
        self.final_claim_warning.setWordWrap(True)
        layout.addWidget(self.final_claim_warning)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        pending = tuple(artifact for artifact in snapshot.latest_artifacts if artifact.review_status in {"needs_review", "new"})
        rejected = tuple(artifact for artifact in snapshot.latest_artifacts if artifact.review_status == "rejected")
        quarantined_artifacts = tuple(artifact for artifact in snapshot.latest_artifacts if artifact.quarantine_status != "clean")
        failed_runs = tuple(job for job in snapshot.latest_jobs if job.status in {"Failed", "Quarantined"})
        self.render_review_state(
            pending=pending,
            rejected=rejected,
            quarantined=quarantined_artifacts,
            failures=failed_runs,
            snapshot=snapshot,
        )

    def render_review_state(
        self,
        *,
        pending: tuple[ArtifactRow, ...],
        rejected: tuple[ArtifactRow, ...],
        quarantined: tuple[ArtifactRow, ...],
        failures: tuple[JobRow, ...],
        snapshot: RuntimeSnapshot,
    ) -> None:
        rows = [f"{artifact.artifact_id} | {artifact.review_status}" for artifact in pending]
        if rejected:
            rows.extend(f"{artifact.artifact_id} | rejected" for artifact in rejected[:3])
        if not rows:
            rows.append("No pending reviews")
        self.review_list.setText("\n".join(rows))
        first = pending[0] if pending else (rejected[0] if rejected else None)
        if first is None:
            self.metadata.setText("artifact_id: --\nreview_status: --\nquarantine_status: --")
        else:
            self.metadata.setText(
                "\n".join(
                    (
                        f"artifact_id: {first.artifact_id}",
                        f"job_id: {first.job_id}",
                        f"review_status: {first.review_status}",
                        f"quarantine_status: {first.quarantine_status}",
                        f"safe_to_publish: {first.safe_to_publish}",
                    )
                )
            )
        self.quarantine_state.setText(
            "\n".join(f"{artifact.artifact_id} | {artifact.quarantine_status}" for artifact in quarantined) or "No quarantined artifacts"
        )
        self.failure_reason.setText(
            "\n".join(
                f"{job.job_id} | {job.failure_reason or job.quarantine_reason or 'Reason not projected'}" for job in failures
            )
            or "No failed runs in current projection"
        )
        self.event_trail.setText("\n".join(event.line() for event in snapshot.latest_events[-5:]) or "--")

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
        return (self.approve_button, self.reject_button, self.quarantine_button, self.export_bundle_button)

    def required_fields(self) -> tuple[str, ...]:
        return REVIEWS_REQUIRED_FIELDS

    def required_sections(self) -> tuple[str, ...]:
        return REVIEWS_SECTIONS

    def absorbed_domains(self) -> tuple[str, ...]:
        return ("Human Review", "Failure Quarantine")

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.reviews"))
        for section, key in (
            ("Pending Reviews", "reviews.pending"),
            ("Rejected", "reviews.rejected"),
            ("Quarantined", "reviews.quarantined"),
            ("Failures", "reviews.failures"),
        ):
            self._section_labels[section].setText(self.text.tr(key))
        self.reject_reason_label.setText(self.text.tr("review.reason"))
        self.approve_button.setText(self.text.tr("review.approve"))
        self.reject_button.setText(self.text.tr("review.reject"))
        self.quarantine_button.setText(self.text.tr("review.quarantine"))
        self.export_bundle_button.setText(self.text.tr("failure.export_bundle"))
        self.final_claim_warning.setText(self.text.tr("review.final_claim_warning"))
        for button in self.action_controls():
            button.setToolTip(self.text.tr("common.disabled_until_facade"))

    def _reason_editor_changed(self) -> None:
        self._reject_reason = self.reject_reason_editor.toPlainText()
        self._update_action_state()

    def _update_action_state(self) -> None:
        self.approve_button.setEnabled(self._facade_actions_enabled)
        self.quarantine_button.setEnabled(self._facade_actions_enabled)
        self.export_bundle_button.setEnabled(self._facade_actions_enabled)
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
    return panel
