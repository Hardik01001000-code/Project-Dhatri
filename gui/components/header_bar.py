from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCursor
from gui.components.ai_orb import AiOrbWidget

class HeaderBar(QFrame):
    vision_toggled = pyqtSignal(bool)
    listen_toggled = pyqtSignal(bool)
    mute_toggled = pyqtSignal(bool)
    clear_chat_clicked = pyqtSignal()
    diagnostics_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setFixedHeight(68)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(14)

        # Left: Interactive Compact AI Orb
        self.orb = AiOrbWidget(compact=True)
        layout.addWidget(self.orb)

        # Brand Titles
        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)
        brand_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        self.title_label = QLabel("DHATRI")
        self.title_label.setObjectName("brandTitle")
        title_row.addWidget(self.title_label)
        
        self.badge_label = QLabel("OFFLINE AI")
        self.badge_label.setStyleSheet("""
            background: rgba(139, 92, 246, 0.15);
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 4px;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 6px;
            letter-spacing: 0.5px;
        """)
        title_row.addWidget(self.badge_label)
        title_row.addStretch(1)
        brand_box.addLayout(title_row)

        # Status Pill
        self.status_pill = QLabel("● READY")
        self.status_pill.setStyleSheet("""
            color: #10b981;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        brand_box.addWidget(self.status_pill)
        layout.addLayout(brand_box)

        layout.addStretch(1)

        # Action Buttons (Right)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Vision Toggle
        self.vision_btn = QPushButton("👁️ Vision: OFF")
        self.vision_btn.setObjectName("visionToggleBtn")
        self.vision_btn.setCheckable(True)
        self.vision_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vision_btn.setToolTip("Toggle Live Object Detection & Face Recognition (Ctrl+V)")
        self.vision_btn.toggled.connect(self._on_vision_toggled)
        btn_layout.addWidget(self.vision_btn)

        # Listening Toggle
        self.listen_btn = QPushButton("🎙️ Mic: ON")
        self.listen_btn.setObjectName("listenToggleBtn")
        self.listen_btn.setCheckable(True)
        self.listen_btn.setChecked(True)
        self.listen_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.listen_btn.setToolTip("Toggle Wake Word & Microphone Listening (Ctrl+Space)")
        self.listen_btn.toggled.connect(self._on_listen_toggled)
        btn_layout.addWidget(self.listen_btn)

        # Mute Toggle
        self.mute_btn = QPushButton("🔊 Voice: ON")
        self.mute_btn.setObjectName("muteToggleBtn")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mute_btn.setToolTip("Toggle TTS Voice Output (Ctrl+M)")
        self.mute_btn.toggled.connect(self._on_mute_toggled)
        btn_layout.addWidget(self.mute_btn)

        # Clear Chat Button
        self.clear_btn = QPushButton("🧹 Clear")
        self.clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_btn.setToolTip("Clear Conversation History (Ctrl+L)")
        self.clear_btn.clicked.connect(self.clear_chat_clicked.emit)
        btn_layout.addWidget(self.clear_btn)

        # Diagnostics HUD Button
        self.diag_btn = QPushButton("⚡ Diagnostics")
        self.diag_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.diag_btn.setToolTip("Show System Microservices & GPU Diagnostics (F1)")
        self.diag_btn.clicked.connect(self.diagnostics_clicked.emit)
        btn_layout.addWidget(self.diag_btn)

        layout.addLayout(btn_layout)

    def _on_vision_toggled(self, checked: bool):
        self.vision_btn.setText("👁️ Vision: ON" if checked else "👁️ Vision: OFF")
        self.vision_toggled.emit(checked)

    def set_vision_checked(self, checked: bool):
        self.vision_btn.blockSignals(True)
        self.vision_btn.setChecked(checked)
        self.vision_btn.setText("👁️ Vision: ON" if checked else "👁️ Vision: OFF")
        self.vision_btn.blockSignals(False)

    def _on_listen_toggled(self, checked: bool):
        self.listen_btn.setText("🎙️ Mic: ON" if checked else "🎙️ Mic: OFF")
        self.listen_toggled.emit(checked)

    def _on_mute_toggled(self, checked: bool):
        self.mute_btn.setText("🔇 Mute: ON" if checked else "🔊 Voice: ON")
        self.mute_toggled.emit(checked)

    def update_state(self, state: str):
        state = state.upper()
        self.orb.update_state(state)
        
        if state == "RECORDING":
            self.status_pill.setText("● RECORDING SPEECH...")
            self.status_pill.setStyleSheet("color: #f43f5e; font-size: 11px; font-weight: 700;")
        elif state == "PROCESSING":
            self.status_pill.setText("● PROCESSING...")
            self.status_pill.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 700;")
        elif state == "SPEAKING":
            self.status_pill.setText("● SPEAKING...")
            self.status_pill.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 700;")
        elif state == "WAKEWORD":
            self.status_pill.setText("● LISTENING FOR 'DHATRI'")
            self.status_pill.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        else: # STANDBY
            self.status_pill.setText("● STANDBY")
            self.status_pill.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700;")

    def update_rms(self, rms: float):
        self.orb.update_rms(rms)
