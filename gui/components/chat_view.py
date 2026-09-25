import html
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QPushButton, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QCursor

class SuggestionChip(QPushButton):
    def __init__(self, text, icon="✦", parent=None):
        super().__init__(f"{icon}  {text}", parent)
        self.raw_text = text
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #c4b5fd;
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 14px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.2);
                border-color: #8b5cf6;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(139, 92, 246, 0.35);
            }
        """)

class UserMessageWidget(QWidget):
    def __init__(self, text, timestamp=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        
        layout.addStretch(1)
        
        bubble_container = QFrame()
        bubble_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #7c3aed);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
        """)
        bubble_layout = QVBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(16, 10, 16, 10)
        bubble_layout.setSpacing(4)
        
        # Message text
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500; line-height: 1.4;")
        bubble_layout.addWidget(text_label)
        
        # Time stamp
        time_str = timestamp or datetime.datetime.now().strftime("%I:%M %p")
        meta_label = QLabel(time_str)
        meta_label.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 10px; font-weight: 400;")
        meta_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        bubble_layout.addWidget(meta_label)
        
        layout.addWidget(bubble_container)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

class AiMessageWidget(QWidget):
    def __init__(self, text, timestamp=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Avatar badge
        avatar = QLabel("✦")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #06b6d4, stop:1 #8b5cf6);
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                border-radius: 16px;
            }
        """)
        layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignTop)
        
        bubble_container = QFrame()
        bubble_container.setStyleSheet("""
            QFrame {
                background-color: #151c2c;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """)
        bubble_layout = QVBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(6)
        
        # Sender name & meta header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QLabel("DHATRI")
        name_label.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        header_layout.addWidget(name_label)
        
        time_str = timestamp or datetime.datetime.now().strftime("%I:%M %p")
        meta_label = QLabel(time_str)
        meta_label.setStyleSheet("color: #64748b; font-size: 10px;")
        header_layout.addWidget(meta_label)
        
        header_layout.addStretch(1)
        
        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(45, 20)
        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                border: none;
                border-radius: 4px;
                font-size: 10px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """)
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(text, copy_btn))
        header_layout.addWidget(copy_btn)
        
        bubble_layout.addLayout(header_layout)
        
        # Message text
        text_label = QLabel()
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Format text to look clean
        escaped_text = html.escape(text).replace("\n", "<br>")
        text_label.setText(f"<div style='color: #e2e8f0; font-size: 14px; line-height: 1.5;'>{escaped_text}</div>")
        bubble_layout.addWidget(text_label)
        
        layout.addWidget(bubble_container, stretch=1)
        layout.addStretch(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _copy_to_clipboard(self, text, btn):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        btn.setText("Copied!")
        QTimer.singleShot(1500, lambda: btn.setText("Copy"))

class SystemNoticeWidget(QWidget):
    def __init__(self, text, icon="ℹ️", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        
        layout.addStretch(1)
        pill = QLabel(f"{icon}  {text}")
        pill.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.04);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 4px 14px;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        layout.addWidget(pill)
        layout.addStretch(1)

class ThinkingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        
        avatar = QLabel("✦")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                background: #1e293b;
                color: #a78bfa;
                font-size: 14px;
                border-radius: 15px;
                border: 1px solid rgba(167, 139, 250, 0.4);
            }
        """)
        layout.addWidget(avatar)
        
        self.status_label = QLabel("Dhatri is thinking...")
        self.status_label.setStyleSheet("color: #a78bfa; font-size: 13px; font-style: italic;")
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        
        self.dots = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(400)

    def _animate(self):
        self.dots = (self.dots + 1) % 4
        self.status_label.setText("Dhatri is thinking" + "." * self.dots)

class WelcomeHeroWidget(QWidget):
    suggestion_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 20)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Glowing Emblem
        icon_label = QLabel("✦")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            font-size: 48px;
            color: #38bdf8;
            padding: 4px;
        """)
        layout.addWidget(icon_label)
        
        title_label = QLabel("Project Dhatri")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: 2px;
        """)
        layout.addWidget(title_label)
        
        desc_label = QLabel("Offline Multi-Modal AI Assistant • Vision • Speech • Voice")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 13px; color: #94a3b8; font-weight: 400;")
        layout.addWidget(desc_label)
        
        # Capability badges row
        badge_layout = QHBoxLayout()
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_layout.setSpacing(10)
        
        badges = [
            ("👁️ Vision HUD", "YOLOv11s"),
            ("🎙️ Wake Word", "'Dhatri'"),
            ("🔊 Cloned TTS", "MeloTTS"),
            ("🔒 100% Offline", "Zero Cloud")
        ]
        for title, sub in badges:
            b = QLabel(f"<b>{title}</b> · <span style='color: #64748b;'>{sub}</span>")
            b.setStyleSheet("""
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 11px;
                color: #e2e8f0;
            """)
            badge_layout.addWidget(b)
            
        layout.addLayout(badge_layout)
        layout.addSpacing(16)
        
        # Prompt Suggestions Title
        sug_title = QLabel("Try saying or clicking:")
        sug_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sug_title.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;")
        layout.addWidget(sug_title)
        
        # Suggestion chips grid
        chip_layout = QVBoxLayout()
        chip_layout.setSpacing(8)
        
        chips = [
            ("What can you see right now?", "👁️"),
            ("Introduce yourself and your capabilities", "⚡"),
            ("Who created you and how does your voice work?", "🔊"),
            ("System diagnostics and device status", "📊")
        ]
        
        for text, icon in chips:
            chip = SuggestionChip(text, icon)
            chip.clicked.connect(lambda _, t=text: self.suggestion_selected.emit(t))
            chip_layout.addWidget(chip)
            
        layout.addLayout(chip_layout)

class ChatView(QWidget):
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatView")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Container widget inside scroll area
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.container)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(12)
        
        # Welcome Hero
        self.welcome_hero = WelcomeHeroWidget()
        self.welcome_hero.suggestion_selected.connect(self.suggestion_clicked.emit)
        self.chat_layout.addWidget(self.welcome_hero)
        
        self.chat_layout.addStretch(1)
        
        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)
        
        self.thinking_widget = None
        self.has_messages = False

    def add_user_message(self, text: str):
        if not self.has_messages:
            self.welcome_hero.hide()
            self.has_messages = True
            
        w = UserMessageWidget(text)
        # Insert before stretch
        idx = max(0, self.chat_layout.count() - 1)
        self.chat_layout.insertWidget(idx, w)
        self._scroll_to_bottom()

    def add_ai_message(self, text: str):
        if not self.has_messages:
            self.welcome_hero.hide()
            self.has_messages = True
            
        self.hide_thinking()
        
        w = AiMessageWidget(text)
        idx = max(0, self.chat_layout.count() - 1)
        self.chat_layout.insertWidget(idx, w)
        self._scroll_to_bottom()

    def add_system_notice(self, text: str, icon="ℹ️"):
        if not self.has_messages:
            self.welcome_hero.hide()
            self.has_messages = True
            
        w = SystemNoticeWidget(text, icon)
        idx = max(0, self.chat_layout.count() - 1)
        self.chat_layout.insertWidget(idx, w)
        self._scroll_to_bottom()

    def show_thinking(self):
        if self.thinking_widget is None:
            self.thinking_widget = ThinkingWidget()
            idx = max(0, self.chat_layout.count() - 1)
            self.chat_layout.insertWidget(idx, self.thinking_widget)
            self._scroll_to_bottom()

    def hide_thinking(self):
        if self.thinking_widget is not None:
            self.thinking_widget.deleteLater()
            self.thinking_widget = None

    def clear_chat(self):
        # Remove all message widgets except stretch
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                if widget == self.welcome_hero:
                    continue
                widget.deleteLater()
                
        self.hide_thinking()
        self.welcome_hero.show()
        self.has_messages = False

    def _scroll_to_bottom(self):
        QTimer.singleShot(40, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
