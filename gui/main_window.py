import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSlot, QKeyCombination
from PyQt6.QtGui import QKeySequence, QShortcut

from gui.styles import DARK_THEME_QSS
from gui.components.header_bar import HeaderBar
from gui.components.chat_view import ChatView
from gui.components.input_bar import InputBar
from gui.components.vision_panel import VisionPanel
from gui.components.diagnostics_dialog import DiagnosticsDialog
from gui.components.visualizer_overlay import VisualizerOverlay
from gui.threads.listen_thread import ListenThread
from gui.threads.speak_thread import SpeakThread
from gui.threads.video_thread import VideoThread
from gui.vision_window import VisionWindow
from brain.core import process_prompt

class MainWindow(QMainWindow):
    """
    Upgraded, modern, cyber-minimalist desktop interface for Project Dhatri.
    Features:
      - Reactive AI Orb & Header status indicators
      - Integrated collapsible Camera HUD & detachable Vision Window
      - Modern chat bubbles with suggestion chips & markdown typography
      - Floating capsule input bar with Enter-to-send and hands-free voice mode
      - Dynamic real-time soundwave and voice-state feedback
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Dhatri — Multi-Modal Offline AI")
        self.resize(1180, 820)
        self.setMinimumSize(850, 600)

        # Apply dark theme design system
        self.setStyleSheet(DARK_THEME_QSS)

        # Central Root Container
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)

        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sleek Navigation & Header Bar
        self.header_bar = HeaderBar()
        self.header_bar.vision_toggled.connect(self.toggle_vision)
        self.header_bar.listen_toggled.connect(self.toggle_listen)
        self.header_bar.mute_toggled.connect(self.toggle_mute)
        self.header_bar.clear_chat_clicked.connect(self.handle_clear_chat)
        self.header_bar.diagnostics_clicked.connect(self.show_diagnostics)
        root_layout.addWidget(self.header_bar)

        # 2. Main Content Splitter / Workspace (Chat + Integrated Vision)
        self.content_container = QWidget()
        content_layout = QHBoxLayout(self.content_container)
        content_layout.setContentsMargins(16, 12, 16, 8)
        content_layout.setSpacing(14)

        # Left Column: Chat Area
        self.chat_view = ChatView()
        self.chat_view.suggestion_clicked.connect(self.handle_suggestion_clicked)
        content_layout.addWidget(self.chat_view, stretch=1)

        # Right Column: Integrated Vision HUD Panel
        self.vision_panel = VisionPanel()
        self.vision_panel.detach_requested.connect(self.pop_out_vision)
        self.vision_panel.close_requested.connect(lambda: self.header_bar.set_vision_checked(False))
        self.vision_panel.hide()  # Hidden by default
        content_layout.addWidget(self.vision_panel, stretch=0)

        root_layout.addWidget(self.content_container, stretch=1)

        # 3. Bottom Capsule Input Bar
        self.input_bar = InputBar()
        self.input_bar.send_requested.connect(self.handle_user_prompt)
        root_layout.addWidget(self.input_bar)

        # 4. Subtle Ambient Visualizer Overlay (draws non-intrusive sound ripples)
        self.visualizer = VisualizerOverlay(self.chat_view)
        self.visualizer.hide()

        # Keyboard Shortcuts
        self._setup_shortcuts()

        # Subsystems & Background Threads
        self.vision_window = None
        self.video_thread = None
        self.listen_thread = None
        self.current_listen_state = "WAKEWORD"

        # Initialize and launch Speak Thread
        self.speak_thread = SpeakThread()
        self.speak_thread.speaking_started.connect(self._on_speaking_started)
        self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
        self.speak_thread.start()

        # Start listening by default (hands-free wake word armed)
        self.start_listen()

    def _setup_shortcuts(self):
        # Ctrl+V: Toggle Vision
        QShortcut(QKeySequence("Ctrl+V"), self, activated=lambda: self.header_bar.vision_btn.toggle())
        # Ctrl+M: Toggle Mute
        QShortcut(QKeySequence("Ctrl+M"), self, activated=lambda: self.header_bar.mute_btn.toggle())
        # Ctrl+L: Clear Chat
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.handle_clear_chat)
        # F1 or Ctrl+I: Diagnostics
        QShortcut(QKeySequence("F1"), self, activated=self.show_diagnostics)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self.show_diagnostics)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep visualizer overlay mapped over the chat area
        if self.visualizer:
            self.visualizer.setGeometry(self.chat_view.rect())

    # --- Vision Microservice Controls ---
    def toggle_vision(self, checked: bool):
        if checked:
            self.start_vision()
        else:
            self.stop_vision()

    def start_vision(self):
        # Create and start video thread if not running
        if not self.video_thread:
            self.video_thread = VideoThread()
            self.video_thread.change_pixmap_signal.connect(self.vision_panel.update_image)
            self.video_thread.start()
            
        if self.vision_window and self.vision_window.isVisible():
            # If already popped out, keep window visible
            self.vision_window.show()
        else:
            self.vision_panel.show()
            
        self.chat_view.add_system_notice("Vision Camera Stream Active (YOLOv11 + Face ID)", "👁️")

    def stop_vision(self):
        if self.vision_panel:
            self.vision_panel.hide()
            self.vision_panel.set_offline_state()
            
        if self.vision_window:
            self.vision_window.close()
            self.vision_window = None

        if self.video_thread and self.video_thread.isRunning():
            try:
                self.video_thread.change_pixmap_signal.disconnect()
            except Exception:
                pass
            self.video_thread.stop()
            self.video_thread = None

    def pop_out_vision(self):
        """Detach camera HUD into standalone window."""
        self.vision_panel.hide()
        if not self.vision_window:
            self.vision_window = VisionWindow(thread=self.video_thread)
            self.vision_window.window_closed.connect(self._on_vision_window_closed)
        self.vision_window.show()

    def _on_vision_window_closed(self):
        self.vision_window = None
        # Snap back to integrated panel if vision is still enabled
        if self.header_bar.vision_btn.isChecked():
            self.vision_panel.show()
            if self.video_thread:
                self.video_thread.change_pixmap_signal.connect(self.vision_panel.update_image)

    # --- Listening Microservice Controls ---
    def toggle_listen(self, checked: bool):
        if checked:
            self.start_listen()
            self.chat_view.add_system_notice("Microphone armed for wake word 'Dhatri'", "🎙️")
        else:
            self.stop_listen()
            self.chat_view.add_system_notice("Microphone listening stopped", "🔇")

    def start_listen(self):
        self.visualizer.show()
        self.visualizer.setGeometry(self.chat_view.rect())
        self.listen_thread = ListenThread()
        self.listen_thread.state_signal.connect(self.handle_listen_state)
        self.listen_thread.rms_signal.connect(self.handle_listen_rms)
        self.listen_thread.text_signal.connect(self.handle_transcription)
        self.listen_thread.start()

    def stop_listen(self):
        self.visualizer.hide()
        self.header_bar.update_state("STANDBY")
        self.input_bar.update_audio_state("STANDBY")
        if self.listen_thread and self.listen_thread.isRunning():
            self.listen_thread.stop()
            self.listen_thread = None

    @pyqtSlot(str)
    def handle_listen_state(self, state: str):
        self.current_listen_state = state
        self.header_bar.update_state(state)
        self.input_bar.update_audio_state(state)
        self.visualizer.update_state(state)

        if state.upper() == "RECORDING":
            self.chat_view.add_system_notice("Wake word recognized! Listening to speech...", "🔴")
        elif state.upper() == "PROCESSING":
            self.chat_view.show_thinking()

    @pyqtSlot(float)
    def handle_listen_rms(self, rms: float):
        self.header_bar.update_rms(rms)
        self.visualizer.update_rms(rms)

    @pyqtSlot(str)
    def handle_transcription(self, text: str):
        """Handle incoming speech transcribed by Faster-Whisper."""
        self.chat_view.hide_thinking()
        text = text.strip()
        if not text:
            return

        if self.input_bar.is_auto_send_enabled():
            # Seamless hands-free voice mode
            self.handle_user_prompt(text)
        else:
            # Place in input box for manual review
            self.input_bar.set_input_text(text)

    # --- Speech Synthesis (Speak Microservice) ---
    def toggle_mute(self, checked: bool):
        self.speak_thread.set_muted(checked)
        if checked:
            self.chat_view.add_system_notice("Voice synthesis muted", "🔇")
        else:
            self.chat_view.add_system_notice("Voice synthesis enabled", "🔊")

    @pyqtSlot()
    def _on_speaking_started(self):
        self.header_bar.update_state("SPEAKING")
        self.visualizer.update_state("SPEAKING")

    @pyqtSlot()
    def _on_speaking_finished(self):
        self.header_bar.update_state(self.current_listen_state)
        self.visualizer.update_state(self.current_listen_state)

    # --- Chat & Prompt Processing ---
    @pyqtSlot(str)
    def handle_suggestion_clicked(self, prompt: str):
        self.handle_user_prompt(prompt)

    @pyqtSlot(str)
    def handle_user_prompt(self, text: str):
        text = text.strip()
        if not text:
            return

        # 1. Render User Message
        self.chat_view.add_user_message(text)
        self.chat_view.show_thinking()
        self.header_bar.update_state("PROCESSING")

        # 2. Process Prompt via Brain Microservice
        response = self._generate_response(text)
        if not response:
            self.chat_view.hide_thinking()
            self.header_bar.update_state(self.current_listen_state)
            return

        # 3. Render Assistant Response
        self.chat_view.add_ai_message(response)
        self.header_bar.update_state(self.current_listen_state)

        # 4. Speak aloud via TTS engine
        self.speak_thread.speak(response)

    def _generate_response(self, text: str) -> str:
        """
        Processes prompt through the brain microservice.
        The brain returns the response (echoing the input for now),
        which is then spoken aloud by the speak microservice.
        """
        return process_prompt(text)

    def handle_clear_chat(self):
        self.chat_view.clear_chat()

    def show_diagnostics(self):
        diag = DiagnosticsDialog(self)
        diag.exec()

    def closeEvent(self, event):
        self.stop_vision()
        self.stop_listen()
        if self.speak_thread:
            self.speak_thread.stop()
        event.accept()
