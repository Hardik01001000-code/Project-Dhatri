import math
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QBrush

class VisualizerOverlay(QWidget):
    """
    Subtle ambient audio-reactive overlay.
    Renders sleek, modern energy ripples with non-intrusive alpha falloff
    so chat text remains completely legible.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.rms = 0.0
        self.smoothed_rms = 0.0
        self.state = "WAKEWORD" # WAKEWORD, RECORDING, PROCESSING, SPEAKING
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16) # 60 FPS
        self.time = 0.0

    @pyqtSlot(float)
    def update_rms(self, rms: float):
        self.rms = max(0.0, rms)

    @pyqtSlot(str)
    def update_state(self, state: str):
        self.state = state.upper()
        self.update()

    def _tick(self):
        self.time += 0.04
        # Smooth interpolation
        target_rms = min(1.0, self.rms * 15.0)
        self.smoothed_rms += (target_rms - self.smoothed_rms) * 0.25
        if self.state in ["RECORDING", "PROCESSING", "SPEAKING"]:
            self.update()

    def paintEvent(self, event):
        if self.state == "WAKEWORD" or self.state == "STANDBY":
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPointF(self.rect().center())
        
        if self.state == "PROCESSING":
            # Subtle futuristic rotating orbit ring
            radius = 50.0
            pulse = (math.sin(self.time * 4.0) + 1.0) / 2.0
            
            painter.setBrush(Qt.BrushStyle.NoBrush)
            pen = QPen(QColor(139, 92, 246, int(40 + 40 * pulse)), 2)
            painter.setPen(pen)
            painter.drawEllipse(center, radius + pulse * 10, radius + pulse * 10)
            return

        if self.state == "RECORDING":
            # Dynamic audio ripples with sleek cyber colors
            base_r = 45.0
            dynamic_r = base_r + self.smoothed_rms * 90.0
            
            # Ambient radial glow behind ripples
            glow = QRadialGradient(center, dynamic_r * 1.5)
            glow.setColorAt(0.0, QColor(244, 63, 94, int(20 + self.smoothed_rms * 40)))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, dynamic_r * 1.5, dynamic_r * 1.5)
            
            # Outer rings
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(244, 63, 94, 90), 2))
            painter.drawEllipse(center, dynamic_r, dynamic_r)
            
            painter.setPen(QPen(QColor(0, 240, 255, 60), 1.5))
            painter.drawEllipse(center, dynamic_r + 20, dynamic_r + 20)
            
            # Core pulse
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(244, 63, 94, int(60 + self.smoothed_rms * 80)))
            painter.drawEllipse(center, base_r, base_r)
