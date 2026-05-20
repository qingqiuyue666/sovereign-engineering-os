"""Status chip lexicon and delegate for job queue tables."""

from __future__ import annotations

from apps.ui import QColor, PYSIDE6_AVAILABLE, QPainter, QPen, QRect, QStyledItemDelegate, Qt

ALLOWED_STATUS_LABELS: tuple[str, ...] = (
    "Not Started",
    "Pending",
    "Running",
    "Succeeded",
    "Failed",
    "Quarantined",
    "Requires Human Review",
    "Blocked: Missing Resource",
    "Blocked: Missing Visual Proof",
    "Blocked: Human Review Required",
    "Blocked: Placeholder Guide",
    "Dry Run Complete",
    "Materialization Required",
    "Materialized Valid",
    "Materialized Stale",
    "Ready for Real Run",
    "Ready for Review",
)

STATUS_COLORS: dict[str, tuple[str, str]] = {
    "Not Started": ("#86868B", "#F5F5F7"),
    "Pending": ("#6E6E73", "#F5F5F7"),
    "Running": ("#0066CC", "#E7F0FB"),
    "Succeeded": ("#34C759", "#EAF8EE"),
    "Failed": ("#FF3B30", "#FFECEB"),
    "Quarantined": ("#FF9500", "#FFF4E5"),
    "Requires Human Review": ("#7D5FFF", "#F0EDFF"),
    "Blocked: Missing Resource": ("#FF9500", "#FFF4E5"),
    "Blocked: Missing Visual Proof": ("#FF9500", "#FFF4E5"),
    "Blocked: Human Review Required": ("#7D5FFF", "#F0EDFF"),
    "Blocked: Placeholder Guide": ("#86868B", "#F5F5F7"),
    "Dry Run Complete": ("#00A6A6", "#E8FAFA"),
    "Materialization Required": ("#0066CC", "#E7F0FB"),
    "Materialized Valid": ("#34C759", "#EAF8EE"),
    "Materialized Stale": ("#FF9500", "#FFF4E5"),
    "Ready for Real Run": ("#0066CC", "#E7F0FB"),
    "Ready for Review": ("#7D5FFF", "#F0EDFF"),
}


def normalize_status_label(value: object) -> str:
    text = str(value or "").strip()
    if text in ALLOWED_STATUS_LABELS:
        return text
    lowered = text.lower()
    mapping = {
        "created": "Not Started",
        "admitted": "Pending",
        "pending": "Pending",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "quarantined": "Quarantined",
        "requires_human_review": "Requires Human Review",
        "human_review_required": "Requires Human Review",
        "materialization_required": "Materialization Required",
        "materialized_valid": "Materialized Valid",
        "materialized_stale": "Materialized Stale",
    }
    return mapping.get(lowered, "Blocked: Placeholder Guide")


def status_chip_colors(value: object) -> tuple[str, str]:
    label = normalize_status_label(value)
    return STATUS_COLORS.get(label, STATUS_COLORS["Blocked: Placeholder Guide"])


class StatusChipDelegate(QStyledItemDelegate):
    """Compact QStyledItemDelegate that paints strict status labels as chips."""

    def paint(self, painter: QPainter, option: object, index: object) -> None:  # type: ignore[override]
        if not PYSIDE6_AVAILABLE:
            return
        raw = index.data(Qt.ItemDataRole.DisplayRole)  # type: ignore[attr-defined]
        label = normalize_status_label(raw)
        foreground, background = status_chip_colors(label)
        painter.save()
        rect = option.rect.adjusted(8, 5, -8, -5)  # type: ignore[attr-defined]
        chip = QRect(rect.left(), rect.top(), min(rect.width(), 230), rect.height())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(foreground)))
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(chip, 6, 6)
        painter.setPen(QColor(foreground))
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    def displayText(self, value: object, _locale: object) -> str:  # noqa: N802 - Qt API.
        return normalize_status_label(value)
