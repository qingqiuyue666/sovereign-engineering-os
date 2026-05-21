"""Design tokens and style sheets for the Sovereign Console shell."""

from __future__ import annotations

DESIGN_TOKENS: dict[str, str] = {
    "main_background": "#ECECEE",
    "card_background": "#FFFFFF",
    "technical_panel_background": "#0D0D0D",
    "border": "#D1D1D6",
    "muted_label": "#86868B",
    "primary_text": "#1D1D1F",
    "secondary_text": "#6E6E73",
    "running_blue": "#0066CC",
    "success_green": "#34C759",
    "warning_orange": "#FF9500",
    "fatal_red": "#FF3B30",
    "artifact_teal": "#00A6A6",
    "ai_context_purple": "#7D5FFF",
}


def application_stylesheet() -> str:
    return """
    QMainWindow, QWidget {
        background: #ECECEE;
        color: #1D1D1F;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 12px;
        letter-spacing: 0px;
    }
    QLabel[role="eyebrow"] {
        color: #86868B;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
    }
    QFrame#PulseBar {
        background: #FFFFFF;
        border-bottom: 1px solid #D1D1D6;
    }
    QFrame[role="pulseChip"] {
        background: #F7F7F8;
        border: 1px solid #D1D1D6;
        border-radius: 6px;
    }
    QFrame#NavRail {
        background: #F7F7F8;
        border-right: 1px solid #D1D1D6;
    }
    QToolButton {
        border: 0;
        border-radius: 6px;
        padding: 7px 10px;
        text-align: left;
        color: #1D1D1F;
    }
    QToolButton:checked {
        background: #FFFFFF;
        color: #0066CC;
        border: 1px solid #D1D1D6;
    }
    QFrame[role="metricCard"] {
        background: #FFFFFF;
        border: 1px solid #D1D1D6;
        border-radius: 8px;
    }
    QFrame[role="commandBar"] {
        background: #FFFFFF;
        border: 1px solid #C9C9CF;
        border-radius: 8px;
    }
    QFrame[role="commandBar"][auraActive="true"] {
        border: 1px solid #7D5FFF;
    }
    QFrame[role="threadCard"] {
        background: #FFFFFF;
        border: 1px solid #D1D1D6;
        border-radius: 8px;
    }
    QFrame#MissionThreadPanel {
        background: transparent;
        border: 0;
    }
    QLabel#WorkspaceCommandBar {
        color: #1D1D1F;
        font-size: 15px;
        font-weight: 500;
    }
    QLabel#WorkspaceNextAction {
        color: #6E6E73;
        font-size: 11px;
    }
    QFrame#CodingActivityPanel {
        background: #FFFFFF;
        border: 1px solid #D1D1D6;
        border-radius: 8px;
    }
    QLabel#CodingActivityState, QLabel#CodingActivityFilePill {
        color: #1D1D1F;
        background: #F5F5F7;
        border: 1px solid #D1D1D6;
        border-radius: 6px;
        padding: 3px 7px;
    }
    QLabel#CodingActivitySafeStatus {
        color: #2B6F46;
    }
    QFrame#CodingCodeBlock {
        background: #F7F7F8;
        border: 1px solid #D1D1D6;
        border-radius: 7px;
    }
    QFrame#CodingCodeBlock QLabel {
        font-family: "SF Mono", Menlo, Consolas, monospace;
        font-size: 11px;
    }
    QFrame#CodingCodeBlock QLabel[diffMarker="+"] {
        color: #188038;
    }
    QFrame#CodingCodeBlock QLabel[diffMarker="-"] {
        color: #A23A35;
    }
    QFrame#CodingCodeBlock QLabel[currentLine="true"] {
        background: #EAF2FF;
        border-radius: 4px;
        padding: 2px 4px;
    }
    QLabel#CodingCursorPlaceholder {
        color: #0066CC;
    }
    QFrame#AnimeStatusDot {
        background: #F5F5F7;
        border: 1px solid #D1D1D6;
        border-radius: 9px;
    }
    QFrame#AnimeStatusDot[fxState="Passed"] {
        border-color: #30D158;
    }
    QFrame#AnimeStatusDot[fxState="Failed"] {
        border-color: #FF453A;
    }
    QFrame#SpeedLineHint QLabel, QFrame#TinySparkle QLabel {
        color: #7D5FFF;
        font-size: 10px;
    }
    QFrame#SweatDropMarker QLabel {
        color: #FF9F0A;
        font-size: 11px;
        font-weight: 700;
    }
    QFrame#TestGatePanel {
        background: #F7F7F8;
        border: 1px solid #D1D1D6;
        border-radius: 8px;
    }
    QFrame#TestGateStamp {
        background: #FFFFFF;
        border: 1px solid #D1D1D6;
        border-radius: 7px;
    }
    QFrame#TestGateStamp[gateStatus="OK"] {
        border-color: #30D158;
    }
    QFrame#TestGateStamp[gateStatus="Failed"] {
        border-color: #FF453A;
    }
    QLabel#DashboardWarningStrip, QLabel#JobQueueFilterStrip, QLabel#RunsFilterStrip, QLabel#WorkspaceDegradedBanner,
    QLabel#GlobalDegradedBanner {
        background: #FFF4E5;
        color: #6E6E73;
        border: 1px solid #FF9500;
        border-radius: 6px;
        padding: 7px 10px;
    }
    QFrame#ArtifactPreview, QFrame#ArtifactObservatoryPreview {
        background: #FFFFFF;
        border: 1px solid #00A6A6;
        border-radius: 8px;
    }
    QFrame#Inspector {
        background: #FFFFFF;
        border-left: 1px solid #D1D1D6;
    }
    QTableView {
        background: #FFFFFF;
        alternate-background-color: #F7F7F8;
        border: 1px solid #D1D1D6;
        gridline-color: #E5E5EA;
        selection-background-color: #D6E8FA;
        selection-color: #1D1D1F;
    }
    QHeaderView::section {
        background: #F7F7F8;
        color: #6E6E73;
        border: 0;
        border-right: 1px solid #D1D1D6;
        border-bottom: 1px solid #D1D1D6;
        padding: 6px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
    }
    QPushButton {
        background: #FFFFFF;
        border: 1px solid #D1D1D6;
        border-radius: 6px;
        padding: 7px 10px;
    }
    QPushButton:disabled {
        color: #86868B;
        background: #F5F5F7;
    }
    QFrame#LiveEventStreamFrame {
        background: #0D0D0D;
        border-top: 1px solid #1E1E1E;
    }
    QFrame#EventStreamTitleBar, QLabel#EventStreamTitle {
        background: #0D0D0D;
        color: #E5E5EA;
    }
    QPlainTextEdit#LiveEventStream {
        background: #0D0D0D;
        color: #E5E5EA;
        border: 0;
        font-family: "SF Mono", Menlo, Consolas, monospace;
        font-size: 11px;
        selection-background-color: #0066CC;
    }
    QPlainTextEdit#TracebackExcerptPanel {
        background: #0D0D0D;
        color: #F5F5F7;
        border: 1px solid #1E1E1E;
        font-family: "SF Mono", Menlo, Consolas, monospace;
        font-size: 11px;
    }
    QFrame#SystemPulseBoiler {
        background: #FFFFFF;
        border: 1px solid #D1D1D6;
        border-radius: 8px;
    }
    QFrame#SystemPulseBoiler[severity="warning"] {
        border-color: #FF9500;
    }
    QFrame#SystemPulseBoiler[severity="fatal"] {
        border-color: #FF3B30;
    }
    QFrame#ReviewSeal {
        background: #EAF8EE;
        border: 1px solid #34C759;
        border-radius: 8px;
    }
    QFrame#QuarantineStripe {
        background: #FFF4E5;
        border-left: 4px solid #FF9500;
        border-radius: 8px;
    }
    QFrame#SyncLostOverlay {
        background: rgba(13, 13, 13, 215);
        border: 1px solid #FF3B30;
    }
    QFrame#SyncLostOverlay[syncState="Degraded"] {
        background: rgba(255, 244, 229, 235);
        border: 1px solid #FF9500;
    }
    QFrame#SyncLostOverlay QLabel {
        background: transparent;
        color: #FFFFFF;
    }
    QFrame#SyncLostOverlay[syncState="Degraded"] QLabel {
        color: #1D1D1F;
    }
    """
