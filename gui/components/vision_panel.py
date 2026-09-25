from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QImage, QPixmap, QCursor

class VisionPanel(QFrame):
    """
    Sleek, integrated camera HUD panel that docks directly inside the main UI.
    Supports live annotated video feed, status overlays, and a pop-out button.
    """
    detach_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardPanel")
        self.setMinimumWidth(360)
        self.setMaximumWidth(480)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # HUD Header Bar
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)
        
        # Live Indicator
        self.live_indicator = QLabel("● LIVE FEED")
        self.live_indicator.setStyleSheet("""
            color: #ef4444; 
            font-size: 11px; 
            font-weight: 800; 
            letter-spacing: 1px;
        """)
        header.addWidget(self.live_indicator)
        
        # Microservice Tag
        tag = QLabel("YOLOv11 • dlib")
        tag.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        header.addWidget(tag)
        
        header.addStretch(1)
        
        # Pop-out button
        popout_btn = QPushButton("⛶ Pop-out")
        popout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        popout_btn.setToolTip("Detach into standalone window")
        popout_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.12);
            }
        """)
        popout_btn.clicked.connect(self.detach_requested.emit)
        header.addWidget(popout_btn)
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setToolTip("Turn off Vision")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 13px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                color: #ef4444;
                background: rgba(239, 68, 68, 0.15);
            }
        """)
        close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(close_btn)
        
        main_layout.addLayout(header)
        
        # Camera Feed Display Container
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("""
            QFrame {
                background-color: #05070a;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 12px;
            }
        """)
        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(2, 2, 2, 2)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("Connecting camera stream...")
        self.video_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        video_layout.addWidget(self.video_label)
        
        main_layout.addWidget(self.video_frame, stretch=1)
        
        # Footer Status Strip
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 2, 4, 2)
        
        self.status_label = QLabel("Real-time Object & Face Detection")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer.addWidget(self.status_label)
        footer.addStretch(1)
        
        ai_badge = QLabel("Vision AI: Active")
        ai_badge.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")
        footer.addWidget(ai_badge)
        
        main_layout.addLayout(footer)

    @pyqtSlot(QImage)
    def update_image(self, qt_img: QImage):
        """Render received video frame with smooth aspect-ratio scaling."""
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def set_offline_state(self):
        self.video_label.clear()
        self.video_label.setText("Camera Offline")
