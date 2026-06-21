import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen

class VisualizerOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.rms = 0.0
        self.smoothed_rms = 0.0
        self.state = "WAKEWORD" # WAKEWORD, RECORDING, PROCESSING
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(33) # ~30fps update for smoother animation
        self.phase = 0.0

    @pyqtSlot(float)
    def update_rms(self, rms):
        self.rms = rms

    @pyqtSlot(str)
    def update_state(self, state):
        self.state = state

    def paintEvent(self, event):
        if self.state == "WAKEWORD":
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        base_radius = 40
        
        if self.state == "PROCESSING":
            self.phase += 0.15 # Smoother pulse phase
            pulse = (np.sin(self.phase) + 1) / 2
            # Pastel Purple breathing
            color = QColor(203, 166, 247, int(100 + 100 * pulse)) # Mauve
            painter.setBrush(color)
            # Glowing outline
            glow = QColor(203, 166, 247, int(50 + 50 * pulse))
            painter.setPen(QPen(glow, 6))
            radius = base_radius + int(10 * pulse)
            painter.drawEllipse(center, radius, radius)
            return

        # RECORDING State
        # Smooth interpolation for bounciness
        target_rms = min(1.0, self.rms * 15)
        self.smoothed_rms += (target_rms - self.smoothed_rms) * 0.3 # Easing
        
        dynamic_radius = base_radius + int(self.smoothed_rms * 80)
        
        # Outer rings (Glowing neon pastel)
        painter.setPen(QPen(QColor(137, 180, 250, 100), 3)) # Soft Blue
        painter.drawEllipse(center, dynamic_radius, dynamic_radius)
        
        painter.setPen(QPen(QColor(245, 194, 231, 80), 5)) # Soft Pink
        painter.drawEllipse(center, dynamic_radius + 15, dynamic_radius + 15)
        
        painter.setPen(QPen(QColor(166, 227, 161, 40), 8)) # Mint Green
        painter.drawEllipse(center, dynamic_radius + 30, dynamic_radius + 30)
        
        # Base circle
        painter.setBrush(QColor(137, 180, 250, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, base_radius, base_radius)
