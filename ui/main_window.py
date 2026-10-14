import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QComboBox, QCheckBox, QMessageBox, QSpacerItem,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap
from core.config import config
from core.capture import (
    capture_full_desktop, capture_active_window, copy_to_clipboard
)
from core.history import history
from core.sound import play_shutter
from ui.toast import get_toast

class MainWindow(QMainWindow):
    request_region_capture = pyqtSignal()
    request_editor = pyqtSignal(object)  # Emits PIL Image
    request_pin = pyqtSignal(object)     # Emits PIL Image
    request_history = pyqtSignal()
    request_settings = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnapMaster Pro - Ultimate Screen Capture Studio")
        self.setFixedSize(680, 560)

        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.png")
        self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Header Banner
        self.create_header(main_layout)

        # 2. Main Capture Cards Grid
        self.create_capture_cards(main_layout)

        # 3. Quick Links Row (History, Folder, Settings)
        self.create_quick_bar(main_layout)

        # 4. Footer Status & Options
        self.create_footer(main_layout)

        # Countdown Timer for delayed capture
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.on_countdown_tick)
        self.remaining_seconds = 0
        self.delayed_capture_mode = "region"

    def create_header(self, parent_layout):
        header_frame = QFrame()
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Logo / Icon
        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.png")
        logo_lbl = QLabel()
        pix = QPixmap(icon_path).scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_lbl.setPixmap(pix)
        h_layout.addWidget(logo_lbl)

        # Titles
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("SnapMaster Pro")
        title_lbl.setObjectName("HeaderTitle")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        title_box.addWidget(title_lbl)

        sub_lbl = QLabel("Ultimate screen capture, annotation & smart OCR studio for Windows")
        sub_lbl.setObjectName("HeaderSubtitle")
        sub_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(sub_lbl)
        h_layout.addLayout(title_box)

        h_layout.addStretch()

        # Version Pill
        ver_lbl = QLabel("v1.0.0")
        ver_lbl.setStyleSheet("background: #1e293b; color: #38bdf8; font-weight: bold; border-radius: 12px; padding: 4px 12px; border: 1px solid #334155;")
        h_layout.addWidget(ver_lbl)

        parent_layout.addWidget(header_frame)

    def create_capture_cards(self, parent_layout):
        grid = QGridLayout()
        grid.setSpacing(14)

        # Card 1: Capture Region (Primary Hero)
        self.btn_region = self.create_hero_card(
            "✂️", "Region Snip", "Select any custom area with live pixel magnifier",
            config.get("hotkey_region", "Ctrl+Shift+S"),
            gradient="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #38bdf8)"
        )
        self.btn_region.clicked.connect(self.request_region_capture.emit)
        grid.addWidget(self.btn_region, 0, 0)

        # Card 2: Fullscreen
        self.btn_fullscreen = self.create_hero_card(
            "🖥️", "Fullscreen", "Instant capture of all connected monitors",
            config.get("hotkey_full", "Ctrl+Shift+F"),
            gradient="#1e293b"
        )
        self.btn_fullscreen.clicked.connect(self.trigger_fullscreen_capture)
        grid.addWidget(self.btn_fullscreen, 0, 1)

        # Card 3: Active Window
        self.btn_window = self.create_hero_card(
            "🪟", "Active Window", "Capture clean foreground window without drop shadows",
            config.get("hotkey_window", "Ctrl+Shift+W"),
            gradient="#1e293b"
        )
        self.btn_window.clicked.connect(self.trigger_window_capture)
        grid.addWidget(self.btn_window, 1, 0)

        # Card 4: Delayed Capture
        self.card_delay = self.create_delay_card()
        grid.addWidget(self.card_delay, 1, 1)

        parent_layout.addLayout(grid)

    def create_hero_card(self, icon, title, desc, shortcut, gradient):
        btn = QPushButton()
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn.setMinimumHeight(115)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        border_color = "#334155" if gradient == "#1e293b" else "transparent"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {gradient};
                border: 1px solid {border_color};
                border-radius: 14px;
                padding: 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                border: 1px solid #38bdf8;
            }}
            QPushButton:pressed {{
                opacity: 0.9;
            }}
        """)

        layout = QVBoxLayout(btn)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        top_row.addWidget(icon_lbl)

        top_row.addStretch()

        badge_lbl = QLabel(shortcut.upper())
        badge_lbl.setStyleSheet("background: rgba(15, 23, 42, 0.6); color: #f8fafc; font-size: 10px; font-weight: bold; border-radius: 6px; padding: 3px 8px;")
        top_row.addWidget(badge_lbl)
        layout.addLayout(top_row)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; background: transparent;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1; background: transparent;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        return btn

    def create_delay_card(self):
        frame = QFrame()
        frame.setObjectName("DashboardCard")
        frame.setMinimumHeight(115)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon_lbl = QLabel("⏱️")
        icon_lbl.setStyleSheet("font-size: 24px;")
        top_row.addWidget(icon_lbl)

        title_lbl = QLabel("Timed Delay")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Controls row
        ctrl_row = QHBoxLayout()
        self.cmb_delay = QComboBox()
        self.cmb_delay.addItems(["3 Seconds", "5 Seconds", "10 Seconds"])
        ctrl_row.addWidget(self.cmb_delay)

        self.btn_start_delay = QPushButton("Start Timer 🚀")
        self.btn_start_delay.setStyleSheet("""
            QPushButton {
                background: #6366f1; color: #ffffff; font-weight: bold; border-radius: 8px; padding: 6px 14px;
            }
            QPushButton:hover { background: #4f46e5; }
        """)
        self.btn_start_delay.clicked.connect(self.start_delayed_capture)
        ctrl_row.addWidget(self.btn_start_delay)

        layout.addLayout(ctrl_row)
        return frame

    def create_quick_bar(self, parent_layout):
        bar = QHBoxLayout()
        bar.setSpacing(10)

        btn_ocr = QPushButton("🔍 Quick OCR")
        btn_ocr.setObjectName("SecondaryActionButton")
        btn_ocr.setToolTip("Select an area and extract text instantly")
        btn_ocr.clicked.connect(self.request_region_capture.emit)
        bar.addWidget(btn_ocr)

        btn_hist = QPushButton("🖼️ History")
        btn_hist.setObjectName("SecondaryActionButton")
        btn_hist.clicked.connect(self.request_history.emit)
        bar.addWidget(btn_hist)

        btn_folder = QPushButton("📁 Screenshots Folder")
        btn_folder.setObjectName("SecondaryActionButton")
        btn_folder.clicked.connect(self.open_screenshots_folder)
        bar.addWidget(btn_folder)

        btn_settings = QPushButton("⚙️ Settings")
        btn_settings.setObjectName("SecondaryActionButton")
        btn_settings.clicked.connect(self.request_settings.emit)
        bar.addWidget(btn_settings)

        parent_layout.addLayout(bar)

    def create_footer(self, parent_layout):
        footer_frame = QFrame()
        footer_frame.setStyleSheet("background: #1e293b; border-radius: 10px; padding: 8px 14px;")
        f_layout = QHBoxLayout(footer_frame)

        self.chk_auto_copy = QCheckBox("Auto Copy to Clipboard")
        self.chk_auto_copy.setChecked(config.get("auto_copy_clipboard", True))
        self.chk_auto_copy.toggled.connect(lambda v: config.set("auto_copy_clipboard", v))
        f_layout.addWidget(self.chk_auto_copy)

        self.chk_open_ed = QCheckBox("Always Open Editor")
        self.chk_open_ed.setChecked(config.get("open_editor_after_capture", True))
        self.chk_open_ed.toggled.connect(lambda v: config.set("open_editor_after_capture", v))
        f_layout.addWidget(self.chk_open_ed)

        f_layout.addStretch()

        self.lbl_status = QLabel("Ready to capture")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-weight: bold;")
        f_layout.addWidget(self.lbl_status)

        parent_layout.addWidget(footer_frame)

    def start_delayed_capture(self):
        text = self.cmb_delay.currentText()
        seconds = 3 if "3" in text else (5 if "5" in text else 10)
        self.remaining_seconds = seconds
        self.btn_start_delay.setEnabled(False)
        self.lbl_status.setText(f"Capturing in {self.remaining_seconds}s...")
        self.countdown_timer.start()

    def on_countdown_tick(self):
        self.remaining_seconds -= 1
        if self.remaining_seconds > 0:
            self.lbl_status.setText(f"Capturing in {self.remaining_seconds}s...")
            self.btn_start_delay.setText(f"{self.remaining_seconds}s...")
        else:
            self.countdown_timer.stop()
            self.btn_start_delay.setEnabled(True)
            self.btn_start_delay.setText("Start Timer 🚀")
            self.lbl_status.setText("Ready to capture")
            self.request_region_capture.emit()

    def trigger_fullscreen_capture(self):
        self.hide()
        QTimer.singleShot(250, self._do_fullscreen)

    def _do_fullscreen(self):
        img, _ = capture_full_desktop()
        self.handle_completed_capture(img)

    def trigger_window_capture(self):
        self.hide()
        QTimer.singleShot(250, self._do_window)

    def _do_window(self):
        img, _ = capture_active_window()
        self.handle_completed_capture(img)

    def handle_completed_capture(self, pil_image):
        if not pil_image:
            self.show()
            return
        play_shutter()

        if config.get("auto_copy_clipboard", True):
            copy_to_clipboard(pil_image)

        if config.get("auto_save", True):
            history.save_image(pil_image)

        if config.get("open_editor_after_capture", True):
            self.request_editor.emit(pil_image)
        else:
            if config.get("enable_toast", True):
                from ui.toast import get_toast
                get_toast().show_message(
                    "SnapMaster Pro",
                    "Screenshot captured and saved! 📸",
                    action_text="Open Editor",
                    action_cb=lambda: self.request_editor.emit(pil_image)
                )
            self.show()

    def open_screenshots_folder(self):
        path = config.get("save_dir", str(Path.home() / "Pictures" / "Screenshots"))
        Path(path).mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def closeEvent(self, event):
        if config.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            if not getattr(self, "_tray_notified", False):
                self._tray_notified = True
                if config.get("enable_toast", True):
                    get_toast().show_message(
                        "SnapMaster Pro",
                        "Running in background. Press Ctrl+Shift+S or click tray icon.",
                        action_text="Show",
                        action_cb=self.showNormal
                    )
        else:
            event.accept()
            QApplication.quit()
