import os
from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject

class SystemTrayManager(QObject):
    sig_capture_region = pyqtSignal()
    sig_capture_full = pyqtSignal()
    sig_capture_window = pyqtSignal()
    sig_open_history = pyqtSignal()
    sig_open_settings = pyqtSignal()
    sig_open_folder = pyqtSignal()
    sig_show_main = pyqtSignal()
    sig_quit = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.png")
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("SnapMaster Pro - تصوير الشاشة الاحترافي")

        self.setup_menu()
        self.tray_icon.activated.connect(self.on_activated)

    def setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
            }
        """)

        act_region = menu.addAction("✂️ تصوير منطقة مخصصة")
        act_region.triggered.connect(self.sig_capture_region.emit)

        act_ocr = menu.addAction("🔍 استخراج نص فوري (OCR)")
        act_ocr.triggered.connect(self.sig_capture_region.emit)

        act_full = menu.addAction("🖥️ تصوير كامل الشاشة")
        act_full.triggered.connect(self.sig_capture_full.emit)

        act_win = menu.addAction("🪟 تصوير النافذة النشطة")
        act_win.triggered.connect(self.sig_capture_window.emit)

        menu.addSeparator()

        act_hist = menu.addAction("🖼️ سجل اللقطات...")
        act_hist.triggered.connect(self.sig_open_history.emit)

        act_folder = menu.addAction("📁 فتح مجلد الحفظ")
        act_folder.triggered.connect(self.sig_open_folder.emit)

        act_settings = menu.addAction("⚙️ الإعدادات...")
        act_settings.triggered.connect(self.sig_open_settings.emit)

        menu.addSeparator()

        act_show = menu.addAction("🪟 إظهار لوحة التحكم")
        act_show.triggered.connect(self.sig_show_main.emit)

        act_exit = menu.addAction("❌ خروج")
        act_exit.triggered.connect(self.sig_quit.emit)

        self.tray_icon.setContextMenu(menu)

    def show(self):
        self.tray_icon.show()

    def on_activated(self, reason):
        # Double click triggers region capture
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.sig_capture_region.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.sig_show_main.emit()

    def notify(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2500)
