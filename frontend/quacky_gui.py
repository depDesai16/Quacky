from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel
)
from cardwidget import CardWidget
from draw_icon import draw_icon
from quacky_model import ModelWindow


class QuackyGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.model_visible = False
        self._old_pos = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(1040, 420, 500, 500)

        self.model_window = ModelWindow()
        self.model_window.move(1040, 88) # default position

        self.build_ui()


    #### UI Construction

    def build_ui(self):
        root = self.build_root()
        card_layout = self.build_card()
        title_bar, tb_layout = self.build_title_bar()
        icon_lbl = self.build_icon_label()
        mini_btn = self.build_minimize_button()
        exit_btn = self.build_exit_button()

        tb_layout.addWidget(icon_lbl)
        tb_layout.addStretch()
        tb_layout.addWidget(mini_btn)
        tb_layout.addWidget(exit_btn)
        card_layout.addWidget(title_bar)

        self.chat_display = self.build_chat_display()
        card_layout.addWidget(self.chat_display, 1)

        input_bar = self.build_input_row()
        ib_layout = QHBoxLayout(input_bar)
        ib_layout.setContentsMargins(12, 12, 12, 12)
        ib_layout.setSpacing(8)

        self.mic_btn = self.build_mic_button()
        self.input_field = self.build_input_field()
        send_btn = self.build_send_button()

        ib_layout.addWidget(self.mic_btn)
        ib_layout.addWidget(self.input_field, 1)
        ib_layout.addWidget(send_btn)
        card_layout.addWidget(input_bar)
        root.addWidget(self.card)


    #### UI Component Builders

    def build_root(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)
        return root

    def build_card(self):
        self.card = CardWidget()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        return card_layout

    def build_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet("background: transparent;")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(14, 0, 10, 0)
        return title_bar, tb_layout

    def build_icon_label(self):
        icon = draw_icon()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon.pixmap(32, 32))
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setStyleSheet("background: transparent;")
        return icon_lbl

    def build_minimize_button(self):
        mini_btn = QPushButton("—")
        mini_btn.setFixedSize(28, 28)
        mini_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666688;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.45); color: #e8e8e8; }
        """)
        mini_btn.clicked.connect(self.hide)
        return mini_btn

    def build_exit_button(self):
        exit_btn = QPushButton("✕")
        exit_btn.setFixedSize(28, 28)
        exit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666688;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(255, 80, 80, 0.45); color: #ff5555; }
        """)
        exit_btn.clicked.connect(QApplication.instance().quit)
        return exit_btn

    def build_chat_display(self):
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #e8e8e8;
                border: none;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 10px 14px;
            }
            QScrollBar:vertical {
                background: transparent; width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 215, 0, 0.25); border-radius: 2px;
            }
        """)
        self.chat_display.setPlaceholderText("Quacky is ready to chat…")
        return self.chat_display

    def build_input_row(self):
        input_bar = QWidget()
        input_bar.setStyleSheet("background: transparent;")
        return input_bar

    def build_mic_button(self):
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setCheckable(True)
        self.mic_btn.setToolTip("Mute / Unmute microphone")
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 215, 0, 0.12);
                border: 1px solid rgba(255, 215, 0, 0.75);
                border-radius: 18px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 215, 0, 0.22);
            }
            QPushButton:checked {
                background: rgba(255, 60, 60, 0.25);
                border-color: rgba(255, 60, 60, 0.6);
            }
        """)
        self.mic_btn.toggled.connect(self.on_mic_toggle)
        return self.mic_btn

    def build_input_field(self):
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message…")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 215, 0, 0.75);
                border-radius: 8px;
                color: #e0e0f0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 6px 12px;
            }
            QLineEdit:focus {
                border-color: rgba(255, 215, 0, 0.75);
                background: rgba(255, 255, 255, 0.09);
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        return self.input_field

    def build_send_button(self):
        send_btn = QPushButton("➤")
        send_btn.setFixedSize(36, 36)
        send_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 215, 0, 0.18);
                border: 1px solid rgba(255, 215, 0, 0.75);
                border-radius: 18px;
                color: #e8e8e8;
                font-size: 15px;
            }
            QPushButton:hover {
                background: rgba(255, 215, 0, 0.32);
            }
            QPushButton:pressed {
                background: rgba(255, 215, 0, 0.45);
            }
        """)
        send_btn.clicked.connect(self.send_message)
        return send_btn


    #### Slots

    def set_model_visible(self, visible: bool):
        if visible:
            self.model_window.show()
        else:
            self.model_window.hide()

    def set_speechtospeech_enabled(self, enabled: bool):
        self.speechtospeech_enabled = enabled

    def on_mic_toggle(self, muted: bool):
        if muted:
            self.mic_btn.setText("🔇")
            self.mic_btn.setToolTip("Microphone muted")
        else:
            self.mic_btn.setText("🎙")
            self.mic_btn.setToolTip("Mute microphone")

    def send_message(self):
        text = self.input_field.text().strip()
        quack_text = "Quacky is thinking..." # Placeholder response until LLM response
        if not text:
            return
        
        self.chat_display.append(
            f'<span style="color:#66ccff;font-weight:bold;">You:</span> '
            f'<span style="color:#e8e8e8;">{text}</span>'
            f'<br><span style="color:#FFD700;font-weight:bold;">Quacky:</span> {quack_text}'
        )
        self.input_field.clear()
        # LLM hook goes here


    #### Drag Support

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._old_pos = None