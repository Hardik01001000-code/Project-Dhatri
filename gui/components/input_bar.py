from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QTextEdit, QPushButton, QFrame, QLabel, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QKeyEvent, QCursor, QFont

class AutoGrowTextEdit(QTextEdit):
    send_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatInput")
        self.setPlaceholderText("Message Dhatri, ask anything, or say 'Dhatri'...")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAcceptRichText(False)
        self.setFixedHeight(40)
        self.textChanged.connect(self._adjust_height)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter: Insert newline
                super().keyPressEvent(event)
            else:
                # Enter without Shift: Send
                text = self.toPlainText().strip()
                if text:
                    self.send_requested.emit(text)
                    self.clear()
                event.accept()
                return
        else:
            super().keyPressEvent(event)

    def _adjust_height(self):
        doc_height = int(self.document().size().height())
        # Clamp height between 40px and 120px
        new_height = max(40, min(120, doc_height + 12))
        if self.height() != new_height:
            self.setFixedHeight(new_height)

class InputBar(QWidget):
    send_requested = pyqtSignal(str)
    auto_send_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)
        
        # Capsule container frame
        self.capsule = QFrame()
        self.capsule.setObjectName("inputCapsule")
        capsule_layout = QHBoxLayout(self.capsule)
        capsule_layout.setContentsMargins(14, 6, 8, 6)
        capsule_layout.setSpacing(10)
        
        # Leading status icon (Mic dot)
        self.status_icon = QLabel("🎙️")
        self.status_icon.setStyleSheet("font-size: 16px; color: #94a3b8;")
        self.status_icon.setToolTip("Listening for wake word 'Dhatri'")
        capsule_layout.addWidget(self.status_icon)
        
        # Text input
        self.text_input = AutoGrowTextEdit()
        self.text_input.send_requested.connect(self._handle_send)
        capsule_layout.addWidget(self.text_input, stretch=1)
        
        # Auto-send voice toggle button
        self.auto_send_btn = QPushButton("Auto-Send: ON")
        self.auto_send_btn.setCheckable(True)
        self.auto_send_btn.setChecked(True)
        self.auto_send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.auto_send_btn.setToolTip("Hands-free Mode: Automatically sends messages transcribed from speech")
        self.auto_send_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.25);
            }
            QPushButton:!checked {
                background: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                border-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.auto_send_btn.toggled.connect(self._on_auto_send_toggle)
        capsule_layout.addWidget(self.auto_send_btn)
        
        # Send Button
        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_btn.setToolTip("Send Message (Enter)")
        self.send_btn.clicked.connect(self._on_send_clicked)
        capsule_layout.addWidget(self.send_btn)
        
        layout.addWidget(self.capsule)

    def _on_auto_send_toggle(self, checked: bool):
        if checked:
            self.auto_send_btn.setText("Auto-Send: ON")
        else:
            self.auto_send_btn.setText("Auto-Send: OFF")
        self.auto_send_toggled.emit(checked)

    def is_auto_send_enabled(self) -> bool:
        return self.auto_send_btn.isChecked()

    def set_input_text(self, text: str):
        self.text_input.setPlainText(text)
        cursor = self.text_input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_input.setTextCursor(cursor)
        self.text_input.setFocus()

    def _on_send_clicked(self):
        text = self.text_input.toPlainText().strip()
        if text:
            self._handle_send(text)
            self.text_input.clear()

    def _handle_send(self, text: str):
        self.send_requested.emit(text)

    def update_audio_state(self, state: str):
        """Update leading mic indicator based on listening state."""
        state = state.upper()
        if state == "RECORDING":
            self.status_icon.setText("🔴")
            self.status_icon.setToolTip("Recording speech...")
        elif state == "PROCESSING":
            self.status_icon.setText("⚡")
            self.status_icon.setToolTip("Transcribing / Processing speech...")
        elif state == "WAKEWORD":
            self.status_icon.setText("🎙️")
            self.status_icon.setToolTip("Listening for wake word 'Dhatri'")
        else:
            self.status_icon.setText("💤")
            self.status_icon.setToolTip("Microphone Standby")
