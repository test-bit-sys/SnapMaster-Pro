import os
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor
from pathlib import Path

class ToastNotification(QWidget):
    action_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.setFixedSize(360, 84)

        # Main container widget for styling
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 360, 84)
        self.container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                border: 1px solid #38bdf8;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Icon
        self.icon_lbl = QLabel()
        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_lbl.setPixmap(pix)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.icon_lbl)

        # Texts
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel("SnapMaster Pro")
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8; background: transparent; border: none;")
        text_layout.addWidget(self.title_lbl)

        self.msg_lbl = QLabel("تم نسخ لقطة الشاشة إلى الحافظة بنجاح")
        self.msg_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1; background: transparent; border: none;")
        self.msg_lbl.setWordWrap(True)
        text_layout.addWidget(self.msg_lbl)

        layout.addLayout(text_layout, stretch=1)

        # Action Button (optional)
        self.btn_action = QPushButton("عرض")
        self.btn_action.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
                font-size: 11px;
                border-radius: 6px;
                padding: 6px 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
            }
        """)
        self.btn_action.clicked.connect(self.on_action)
        layout.addWidget(self.btn_action)

        # Close Button
        btn_close = QPushButton("✕")
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                font-size: 12px;
                font-weight: bold;
                border: none;
                padding: 4px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.hide_toast)
        layout.addWidget(btn_close)

        # Timer to auto-hide
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_toast)

        self._action_callback = None

    def show_message(self, title, message, duration=3500, action_text="فتح", action_cb=None):
        self.title_lbl.setText(title)
        self.msg_lbl.setText(message)
        self._action_callback = action_cb

        if action_cb and action_text:
            self.btn_action.setText(action_text)
            self.btn_action.show()
        else:
            self.btn_action.hide()

        # Position at bottom-right of primary screen
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 20
        y = screen.bottom() - self.height() - 20
        self.move(x, y)

        self.show()
        self.raise_()
        self.hide_timer.start(duration)

    def on_action(self):
        if self._action_callback:
            try:
                self._action_callback()
            except Exception as e:
                print(f"[Toast] Error running action: {e}")
        self.hide_toast()

    def hide_toast(self):
        self.hide_timer.stop()
        self.hide()

# Global toast instance
toast = None

def get_toast():
    global toast
    if toast is None:
        toast = ToastNotification()
    return toast
