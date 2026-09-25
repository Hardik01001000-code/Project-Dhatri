"""
Project Dhatri - Modern Dark Cyber-Glass Design System & Stylesheets
"""

DARK_THEME_QSS = """
/* Global Window & Base Widgets */
QMainWindow, QWidget#centralWidget {
    background-color: #0b0e17;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
}

QWidget {
    outline: none;
}

/* Glass Panels & Containers */
QFrame#cardPanel, QFrame#sidebarPanel {
    background-color: #121826;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
}

QFrame#headerBar {
    background-color: rgba(18, 24, 38, 0.85);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 4px 0 4px 0;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #8b5cf6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

/* Buttons */
QPushButton {
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 8px 16px;
}

QPushButton:hover {
    color: #ffffff;
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
}

QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.12);
}

/* Active / Checked Button States */
QPushButton:checked {
    color: #ffffff;
    background-color: rgba(139, 92, 246, 0.2);
    border: 1px solid #8b5cf6;
}

QPushButton:checked:hover {
    background-color: rgba(139, 92, 246, 0.3);
    border: 1px solid #a78bfa;
}

/* Specific Action Pill Buttons */
QPushButton#visionToggleBtn:checked {
    color: #38bdf8;
    background-color: rgba(56, 189, 248, 0.18);
    border: 1px solid #38bdf8;
}

QPushButton#listenToggleBtn:checked {
    color: #a78bfa;
    background-color: rgba(139, 92, 246, 0.22);
    border: 1px solid #8b5cf6;
}

QPushButton#muteToggleBtn:checked {
    color: #fb7185;
    background-color: rgba(251, 113, 133, 0.2);
    border: 1px solid #fb7185;
}

/* Primary Accent Send Button */
QPushButton#sendBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
    color: #ffffff;
    border: none;
    border-radius: 20px;
    font-size: 14px;
    font-weight: bold;
    padding: 0px;
}

QPushButton#sendBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #7c3aed);
}

QPushButton#sendBtn:pressed {
    background: #4338ca;
}

QPushButton#sendBtn:disabled {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.05);
}

/* Input Bar Capsule */
QFrame#inputCapsule {
    background-color: #151c2c;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
}

QFrame#inputCapsule:focus-within {
    border: 1px solid #8b5cf6;
    background-color: #171f32;
}

/* Text Input Inside Capsule */
QTextEdit#chatInput {
    background-color: transparent;
    color: #f8fafc;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 14px;
    border: none;
    padding: 6px 4px;
    selection-background-color: #8b5cf6;
    selection-color: #ffffff;
}

/* Labels */
QLabel {
    color: #e2e8f0;
}

QLabel#brandTitle {
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #ffffff;
}

QLabel#brandSubtitle {
    font-size: 10px;
    font-weight: 600;
    color: #818cf8;
    letter-spacing: 1px;
}

/* Tooltips */
QToolTip {
    background-color: #1e2638;
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}
"""

# Palette Constants
COLOR_BG_DARK = "#0b0e17"
COLOR_SURFACE = "#121826"
COLOR_SURFACE_LIGHT = "#182032"
COLOR_CYAN = "#00f0ff"
COLOR_VIOLET = "#8b5cf6"
COLOR_PINK = "#f43f5e"
COLOR_EMERALD = "#10b981"
COLOR_AMBER = "#f59e0b"
COLOR_TEXT_PRIMARY = "#f8fafc"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"
