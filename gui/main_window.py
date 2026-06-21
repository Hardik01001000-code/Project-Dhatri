from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap

from gui.components.visualizer_overlay import VisualizerOverlay
from gui.threads.listen_thread import ListenThread
from gui.threads.speak_thread import SpeakThread
from gui.vision_window import VisionWindow
from brain.core import process_prompt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Companion")
        self.resize(1024, 768)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Nunito', 'Segoe UI', -apple-system, sans-serif;
            }
            QPushButton {
                background-color: #313244;
                border: 2px solid #cba6f7;
                border-radius: 20px;
                padding: 10px 20px;
                color: #cdd6f4;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #f5c2e7;
            }
            QPushButton:pressed {
                background-color: #585b70;
                border-color: #f38ba8;
            }
            QPushButton:checked {
                background-color: #313244;
                border: 2px solid #89b4fa;
                color: #89b4fa;
            }
            QPushButton:checked:hover {
                background-color: #45475a;
                border-color: #89dceb;
            }
            QLabel#video_label {
                background-color: #11111b;
                border: 2px solid #313244;
                border-radius: 12px;
                font-size: 20px;
                color: #a6adc8;
            }
            QTextEdit {
                background-color: #181825;
                border: 2px solid #313244;
                border-radius: 12px;
                padding: 12px;
                color: #cdd6f4;
                font-size: 15px;
            }
            QTextEdit:focus {
                border: 2px solid #cba6f7;
            }
            /* Styling scrollbars for cuteness */
            QScrollBar:vertical {
                border: none;
                background: #181825;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #cba6f7;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #f5c2e7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(20)

        # Top Bar
        self.top_bar_layout = QHBoxLayout()
        
        self.vision_btn = QPushButton("Vision: OFF")
        self.vision_btn.setCheckable(True)
        self.vision_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vision_btn.clicked.connect(self.toggle_vision)
        self.top_bar_layout.addWidget(self.vision_btn)

        self.listen_btn = QPushButton("Listening: OFF")
        self.listen_btn.setCheckable(True)
        self.listen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.listen_btn.clicked.connect(self.toggle_listen)
        self.top_bar_layout.addWidget(self.listen_btn)

        self.mute_btn = QPushButton("Mute: OFF")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.top_bar_layout.addWidget(self.mute_btn)

        self.top_bar_layout.addStretch()
        self.main_layout.addLayout(self.top_bar_layout)

        # Chat Display Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumSize(640, 480)
        self.main_layout.addWidget(self.chat_display, stretch=1)

        # Bottom Input Area
        self.bottom_input_layout = QHBoxLayout()

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type a prompt here or say the wake word...")
        self.text_input.setMaximumHeight(100)
        self.bottom_input_layout.addWidget(self.text_input)

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.handle_send_prompt)
        self.send_btn.setMinimumHeight(100)
        self.bottom_input_layout.addWidget(self.send_btn)

        self.main_layout.addLayout(self.bottom_input_layout)

        # Overlay Visualizer
        self.visualizer = VisualizerOverlay(self.central_widget)
        self.visualizer.hide()

        # Windows & Threads
        self.vision_window = None
        self.listen_thread = None
        self.speak_thread = SpeakThread()
        self.speak_thread.start()

        # --- Default States ---
        # User requested Listening to be ON by default
        self.listen_btn.setChecked(True)
        self.listen_btn.setText("Listening: ON")
        self.start_listen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep visualizer directly over the chat display
        geo = self.chat_display.geometry()
        self.visualizer.setGeometry(geo)

    def toggle_vision(self, checked):
        if checked:
            self.vision_btn.setText("Vision: ON")
            self.start_video()
        else:
            self.vision_btn.setText("Vision: OFF")
            self.stop_video()

    def start_video(self):
        if not self.vision_window:
            self.vision_window = VisionWindow()
        self.vision_window.show()

    def stop_video(self):
        if self.vision_window:
            self.vision_window.close()
            self.vision_window = None

    def toggle_listen(self, checked):
        if checked:
            self.listen_btn.setText("Listening: ON")
            self.start_listen()
        else:
            self.listen_btn.setText("Listening: OFF")
            self.stop_listen()

    def toggle_mute(self, checked):
        if checked:
            self.mute_btn.setText("Mute: ON")
            self.speak_thread.set_muted(True)
        else:
            self.mute_btn.setText("Mute: OFF")
            self.speak_thread.set_muted(False)

    def start_listen(self):
        self.visualizer.show()
        self.listen_thread = ListenThread()
        self.listen_thread.state_signal.connect(self.visualizer.update_state)
        self.listen_thread.rms_signal.connect(self.visualizer.update_rms)
        self.listen_thread.text_signal.connect(self.handle_transcription)
        self.listen_thread.start()

    def stop_listen(self):
        self.visualizer.hide()
        if self.listen_thread and self.listen_thread.isRunning():
            self.listen_thread.stop()
            self.listen_thread = None

    @pyqtSlot(str)
    def handle_transcription(self, text):
        current_text = self.text_input.toPlainText()
        if current_text:
            self.text_input.setPlainText(current_text + "\n" + text)
        else:
            self.text_input.setPlainText(text)
        
        scrollbar = self.text_input.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @pyqtSlot()
    def handle_send_prompt(self):
        text = self.text_input.toPlainText().strip()
        if text:
            user_html = f"""
            <div align="right" style="margin-top: 10px; margin-bottom: 10px;">
                <table style="border-collapse: collapse; float: right;"><tr>
                    <td style="background-color: #f5c2e7; color: #11111b; padding: 10px 15px; border-radius: 15px; font-weight: bold; font-family: 'Nunito', sans-serif;">
                        {text}
                    </td>
                </tr></table>
            </div>
            """
            self.chat_display.append(user_html)
            response = process_prompt(text)
            ai_html = f"""
            <div align="left" style="margin-top: 10px; margin-bottom: 10px;">
                <table style="border-collapse: collapse; float: left;"><tr>
                    <td style="background-color: #89b4fa; color: #11111b; padding: 10px 15px; border-radius: 15px; font-weight: bold; font-family: 'Nunito', sans-serif;">
                        {response}
                    </td>
                </tr></table>
            </div>
            <br>
            """
            self.chat_display.append(ai_html)
            self.speak_thread.speak(response)
            self.text_input.clear()

    def closeEvent(self, event):
        self.stop_video()
        self.stop_listen()
        if self.speak_thread:
            self.speak_thread.stop()
        event.accept()
