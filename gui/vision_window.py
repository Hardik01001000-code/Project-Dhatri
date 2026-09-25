from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from gui.threads.video_thread import VideoThread

class VisionWindow(QMainWindow):
    window_closed = pyqtSignal()

    def __init__(self, thread=None):
        super().__init__()
        self.setWindowTitle("Dhatri — Vision HUD")
        self.resize(720, 540)
        self.setMinimumSize(480, 360)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0e17;
            }
            QWidget {
                background-color: #0b0e17;
                color: #e2e8f0;
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }
            QFrame#hudHeader {
                background-color: #121826;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QLabel#video_label {
                background-color: #05070a;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Sleek Top HUD Header
        hud_header = QFrame()
        hud_header.setObjectName("hudHeader")
        header_layout = QHBoxLayout(hud_header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        
        live_dot = QLabel("● LIVE FEED")
        live_dot.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        header_layout.addWidget(live_dot)
        
        title_label = QLabel("YOLOv11 Object Detection & dlib Face Recognition")
        title_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        
        self.layout.addWidget(hud_header)

        # Video Canvas
        self.video_label = QLabel()
        self.video_label.setObjectName("video_label")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("Acquiring video stream...")
        self.video_label.setStyleSheet("color: #64748b; font-size: 14px;")
        self.layout.addWidget(self.video_label, stretch=1)

        # Manage thread: either passed from main window or create new
        self.own_thread = thread is None
        if self.own_thread:
            self.thread = VideoThread()
            self.thread.change_pixmap_signal.connect(self.update_image)
            self.thread.start()
        else:
            self.thread = thread
            self.thread.change_pixmap_signal.connect(self.update_image)

    @pyqtSlot(QImage)
    def update_image(self, qt_img: QImage):
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            try:
                self.thread.change_pixmap_signal.disconnect(self.update_image)
            except Exception:
                pass
            if self.own_thread:
                self.thread.stop()
                self.thread = None
        self.window_closed.emit()
        event.accept()
