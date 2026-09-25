import math
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QLinearGradient, 
    QPainterPath, QBrush
)

class AiOrbWidget(QWidget):
    """
    A futuristic, high-tech animated AI Orb and audio-reactive visualizer.
    States:
        - "STANDBY": Idle state, gentle breathing glow.
        - "WAKEWORD": Listening for wake word ("Dhatri").
        - "RECORDING": Actively recording user speech; reacts to real-time RMS volume.
        - "PROCESSING": Transcribing audio / LLM thinking; rotating cyber-rings.
        - "SPEAKING": Assistant speaking via TTS; harmonic voice waves.
    """
    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.compact = compact
        self.state = "STANDBY"
        self.rms = 0.0
        self.smoothed_rms = 0.0
        
        # Animation phase variables
        self.time = 0.0
        self.angle_fast = 0.0
        self.angle_slow = 0.0
        self.pulse_phase = 0.0
        self.ripple_phases = [0.0, 0.33, 0.66]
        
        # Timer for 60 FPS animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(16)  # ~60 fps
        
        if compact:
            self.setFixedSize(54, 54)
        else:
            self.setMinimumSize(90, 90)

    @pyqtSlot(float)
    def update_rms(self, rms: float):
        """Update live audio microphone RMS level (0.0 to 1.0+)."""
        self.rms = max(0.0, rms)

    @pyqtSlot(str)
    def update_state(self, state: str):
        """Update current AI interaction state."""
        self.state = state.upper()
        self.update()

    def _animate_step(self):
        self.time += 0.03
        self.angle_fast = (self.angle_fast + 4.0) % 360.0
        self.angle_slow = (self.angle_slow + 1.5) % 360.0
        
        # Smooth RMS volume interpolation (spring/decay easing)
        target_rms = min(1.0, self.rms * 12.0)
        if target_rms > self.smoothed_rms:
            self.smoothed_rms += (target_rms - self.smoothed_rms) * 0.4
        else:
            self.smoothed_rms += (target_rms - self.smoothed_rms) * 0.12
            
        # Update ripple rings
        for i in range(len(self.ripple_phases)):
            self.ripple_phases[i] = (self.ripple_phases[i] + 0.025) % 1.0
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        center = QPointF(w / 2.0, h / 2.0)
        min_dim = min(w, h)
        
        base_radius = min_dim * (0.24 if self.compact else 0.22)
        
        if self.state == "RECORDING":
            self._paint_recording(painter, center, base_radius)
        elif self.state == "PROCESSING":
            self._paint_processing(painter, center, base_radius)
        elif self.state == "SPEAKING":
            self._paint_speaking(painter, center, base_radius)
        elif self.state == "WAKEWORD":
            self._paint_wakeword(painter, center, base_radius)
        else: # STANDBY / IDLE
            self._paint_idle(painter, center, base_radius)

    def _paint_core_orb(self, painter: QPainter, center: QPointF, radius: float, 
                        core_color: QColor, rim_color: QColor, glow_alpha=120):
        """Draws the 3D-styled luminous sphere core."""
        # Outer ambient glow
        glow_grad = QRadialGradient(center, radius * 2.2)
        glow_c = QColor(core_color)
        glow_c.setAlpha(int(glow_alpha))
        glow_grad.setColorAt(0.0, glow_c)
        glow_grad.setColorAt(0.5, QColor(rim_color.red(), rim_color.green(), rim_color.blue(), int(glow_alpha * 0.35)))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius * 2.2, radius * 2.2)

        # Luminous Sphere Body
        # Offset highlight towards top-left to give authentic 3D sphere depth
        highlight_center = QPointF(center.x() - radius * 0.3, center.y() - radius * 0.3)
        sphere_grad = QRadialGradient(highlight_center, radius * 1.4)
        sphere_grad.setColorAt(0.0, QColor(255, 255, 255, 240))  # Specular bright spot
        sphere_grad.setColorAt(0.2, rim_color)                   # High-energy rim
        sphere_grad.setColorAt(0.7, core_color)                  # Deep core body
        sphere_grad.setColorAt(1.0, QColor(10, 12, 24, 250))     # Dark edge horizon
        
        painter.setBrush(QBrush(sphere_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.drawEllipse(center, radius, radius)

    def _paint_idle(self, painter: QPainter, center: QPointF, base_radius: float):
        breath = (math.sin(self.time * 2.0) + 1.0) / 2.0
        cur_radius = base_radius * (0.92 + 0.08 * breath)
        
        core_c = QColor(99, 102, 241)   # Indigo
        rim_c = QColor(139, 92, 246)    # Violet
        
        # Subtle ambient breathing ring
        ring_r = cur_radius * (1.3 + 0.15 * breath)
        ring_pen = QPen(QColor(139, 92, 246, int(50 + 40 * breath)), 1.5)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, ring_r, ring_r)
        
        self._paint_core_orb(painter, center, cur_radius, core_c, rim_c, glow_alpha=70 + 30 * breath)

    def _paint_wakeword(self, painter: QPainter, center: QPointF, base_radius: float):
        breath = (math.sin(self.time * 3.0) + 1.0) / 2.0
        cur_radius = base_radius * (0.95 + 0.1 * breath)
        
        core_c = QColor(14, 165, 233)   # Sky Blue
        rim_c = QColor(56, 189, 248)    # Cyan
        
        # Dual pulsing radar rings
        for i, offset in enumerate([0.0, 0.5]):
            phase = (self.time * 0.4 + offset) % 1.0
            r = cur_radius + phase * base_radius * 1.4
            alpha = int((1.0 - phase) * 110)
            painter.setPen(QPen(QColor(56, 189, 248, alpha), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, r, r)
            
        self._paint_core_orb(painter, center, cur_radius, core_c, rim_c, glow_alpha=90 + 40 * breath)

    def _paint_recording(self, painter: QPainter, center: QPointF, base_radius: float):
        # Dynamically scales with microphone sound level
        audio_boost = self.smoothed_rms * 1.5
        cur_radius = base_radius * (1.0 + 0.35 * min(1.0, audio_boost))
        
        core_c = QColor(244, 63, 94)    # Neon Rose / Coral
        rim_c = QColor(251, 113, 133)   # Vibrant Pink
        
        # Audio reactive ripples radiating outward
        for phase in self.ripple_phases:
            ring_r = cur_radius + phase * base_radius * (2.2 + audio_boost * 1.8)
            alpha = int((1.0 - phase) * (140 + int(self.smoothed_rms * 100)))
            alpha = max(0, min(255, alpha))
            
            pen_width = max(1.5, 3.5 * (1.0 - phase) * (1.0 + audio_boost))
            painter.setPen(QPen(QColor(244, 63, 94, alpha), pen_width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, ring_r, ring_r)
            
        # Vibrant secondary cyan ripple for energy contrast
        contrast_r = cur_radius * (1.25 + 0.4 * self.smoothed_rms)
        painter.setPen(QPen(QColor(56, 189, 248, 160), 2.0))
        painter.drawEllipse(center, contrast_r, contrast_r)
        
        self._paint_core_orb(painter, center, cur_radius, core_c, rim_c, glow_alpha=160 + int(audio_boost * 80))

    def _paint_processing(self, painter: QPainter, center: QPointF, base_radius: float):
        core_c = QColor(168, 85, 247)   # Purple
        rim_c = QColor(236, 72, 153)    # Pink
        
        cur_radius = base_radius * 0.95
        
        # Futuristic orbital gyroscopic rings
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Ring 1: Fast rotation
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle_fast)
        rect_ring1 = QPointF(0, 0)
        ring1_w = cur_radius * 2.2
        ring1_h = cur_radius * 1.1
        painter.setPen(QPen(QColor(0, 240, 255, 180), 2.0))
        painter.drawEllipse(rect_ring1, ring1_w / 2.0, ring1_h / 2.0)
        
        # Satellite particle on Ring 1
        sat_x = (ring1_w / 2.0)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(0, 240, 255), 1))
        painter.drawEllipse(QPointF(sat_x, 0), 3.5, 3.5)
        painter.restore()
        
        # Ring 2: Slower reverse counter-rotation
        painter.save()
        painter.translate(center)
        painter.rotate(-self.angle_slow)
        ring2_w = cur_radius * 1.2
        ring2_h = cur_radius * 2.3
        painter.setPen(QPen(QColor(236, 72, 153, 160), 2.0))
        painter.drawEllipse(QPointF(0, 0), ring2_w / 2.0, ring2_h / 2.0)
        painter.restore()
        
        self._paint_core_orb(painter, center, cur_radius, core_c, rim_c, glow_alpha=130)

    def _paint_speaking(self, painter: QPainter, center: QPointF, base_radius: float):
        # AI Voice synthesis waves
        core_c = QColor(16, 185, 129)   # Emerald Green / Mint
        rim_c = QColor(52, 211, 153)
        
        cur_radius = base_radius * (1.0 + 0.12 * math.sin(self.time * 6.0))
        
        # Voice harmonic waves
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i, harmonic in enumerate([1.0, 1.4, 1.8]):
            wave_amp = math.sin(self.time * 5.0 * harmonic + i) * 6.0
            r = cur_radius * (1.15 + 0.25 * i) + wave_amp
            alpha = int(180 / (i + 1.2))
            painter.setPen(QPen(QColor(16, 185, 129, alpha), 2.0))
            painter.drawEllipse(center, r, r)
            
        self._paint_core_orb(painter, center, cur_radius, core_c, rim_c, glow_alpha=150)
