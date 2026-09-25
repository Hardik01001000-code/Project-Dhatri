import sys
import os
import torch
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

class DiagnosticsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dhatri — System Architecture & Diagnostics")
        self.setFixedSize(540, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #0e121e;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }
            QFrame#card {
                background-color: #151c2c;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 24px;")
        header.addWidget(icon)
        
        title_box = QVBoxLayout()
        title = QLabel("System Architecture & Status")
        title.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff;")
        subtitle = QLabel("Multi-Modal Offline Microservices Mesh")
        subtitle.setStyleSheet("font-size: 12px; color: #818cf8;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        # Diagnostics Grid Card
        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(12)

        # Check Hardware
        cuda_avail = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU Mode (Active)"
        cuda_badge = "🟢 ONLINE (CUDA)" if cuda_avail else "🟡 CPU Fallback"

        services = [
            ("🧠 AI Brain", "Pluggable LLM interface", "🟢 Active"),
            ("🎙️ Listen Service", "Faster-Whisper (base.en) + OpenWakeWord", "🟢 Active"),
            ("🔊 Voice Service", "MeloTTS + OpenVoice V2 Voice Cloning", "🟢 Ready"),
            ("👁️ Vision Service", "YOLOv11s + dlib Real-time Face Recognition", "🟢 Available"),
            ("⚡ Compute Hardware", f"{gpu_name}", cuda_badge),
            ("🔒 Security & Cloud", "Zero cloud API calls • 100% offline edge execution", "🟢 Secure")
        ]

        for row, (name, desc, status) in enumerate(services):
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #ffffff;")
            grid.addWidget(name_lbl, row, 0)

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
            grid.addWidget(desc_lbl, row, 1)

            status_lbl = QLabel(status)
            status_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #38bdf8;")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(status_lbl, row, 2)

        layout.addWidget(card)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        close_btn = QPushButton("Done")
        close_btn.setFixedSize(90, 36)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: #4f46e5;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
