import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QFileDialog, QGroupBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from core.config import config
from core.hotkeys import hotkeys

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("الإعدادات والتفضيلات - SnapMaster Pro")
        self.resize(560, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                color: #38bdf8;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Storage & Format Group
        grp_storage = QGroupBox("📁 مجلد الحفظ والصيغ")
        lay_storage = QVBoxLayout(grp_storage)

        # Path chooser
        row_path = QHBoxLayout()
        self.txt_path = QLineEdit(config.get("save_dir", ""))
        row_path.addWidget(self.txt_path)
        btn_browse = QPushButton("استعراض...")
        btn_browse.setStyleSheet("background: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px;")
        btn_browse.clicked.connect(self.browse_folder)
        row_path.addWidget(btn_browse)
        lay_storage.addLayout(row_path)

        # Format selector
        row_fmt = QHBoxLayout()
        row_fmt.addWidget(QLabel("صيغة الحفظ الافتراضية:"))
        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems(["PNG", "JPEG", "WEBP"])
        self.cmb_fmt.setCurrentText(config.get("file_format", "PNG").upper())
        row_fmt.addWidget(self.cmb_fmt)
        row_fmt.addStretch()
        lay_storage.addLayout(row_fmt)

        layout.addWidget(grp_storage)

        # 2. Workflow & Automation Group
        grp_flow = QGroupBox("⚙️ سلوك الالتقاط التلقائي")
        lay_flow = QVBoxLayout(grp_flow)

        self.chk_auto_copy = QCheckBox("نسخ لقطة الشاشة إلى الحافظة تلقائياً فور الالتقاط")
        self.chk_auto_copy.setChecked(config.get("auto_copy_clipboard", True))
        lay_flow.addWidget(self.chk_auto_copy)

        self.chk_auto_save = QCheckBox("حفظ لقطة الشاشة في المجلد تلقائياً")
        self.chk_auto_save.setChecked(config.get("auto_save", True))
        lay_flow.addWidget(self.chk_auto_save)

        self.chk_open_editor = QCheckBox("فتح محرر الشروحات تلقائياً بعد تحديد المنطقة")
        self.chk_open_editor.setChecked(config.get("open_editor_after_capture", True))
        lay_flow.addWidget(self.chk_open_editor)

        self.chk_sound = QCheckBox("تشغيل صوت غالق الكاميرا عند التصوير")
        self.chk_sound.setChecked(config.get("play_shutter_sound", True))
        lay_flow.addWidget(self.chk_sound)

        self.chk_tray = QCheckBox("التصغير إلى صينية النظام (System Tray) عند إغلاق النافذة")
        self.chk_tray.setChecked(config.get("minimize_to_tray", True))
        lay_flow.addWidget(self.chk_tray)

        self.chk_magnifier = QCheckBox("تفعيل المكبرة اللحظية (Live Magnifier) أثناء التحديد")
        self.chk_magnifier.setChecked(config.get("magnifier_enabled", True))
        lay_flow.addWidget(self.chk_magnifier)

        layout.addWidget(grp_flow)

        # 3. Hotkeys Group
        grp_hotkeys = QGroupBox("⌨️ اختصارات لوحة المفاتيح العامة (Global Hotkeys)")
        lay_hotkeys = QVBoxLayout(grp_hotkeys)

        row_hk1 = QHBoxLayout()
        row_hk1.addWidget(QLabel("تصوير منطقة مخصصة:"))
        self.txt_hk_region = QLineEdit(config.get("hotkey_region", "ctrl+shift+s"))
        row_hk1.addWidget(self.txt_hk_region)
        lay_hotkeys.addLayout(row_hk1)

        row_hk2 = QHBoxLayout()
        row_hk2.addWidget(QLabel("تصوير كامل الشاشة:"))
        self.txt_hk_full = QLineEdit(config.get("hotkey_full", "ctrl+shift+f"))
        row_hk2.addWidget(self.txt_hk_full)
        lay_hotkeys.addLayout(row_hk2)

        row_hk3 = QHBoxLayout()
        row_hk3.addWidget(QLabel("تصوير النافذة النشطة:"))
        self.txt_hk_win = QLineEdit(config.get("hotkey_window", "ctrl+shift+w"))
        row_hk3.addWidget(self.txt_hk_win)
        lay_hotkeys.addLayout(row_hk3)

        layout.addWidget(grp_hotkeys)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_save = QPushButton("💾 حفظ الإعدادات")
        btn_save.setStyleSheet("""
            QPushButton {
                background: #38bdf8; color: #0f172a; font-weight: bold; border-radius: 6px; padding: 8px 20px;
            }
            QPushButton:hover { background: #0284c7; }
        """)
        btn_save.clicked.connect(self.save_settings)
        btn_box.addWidget(btn_save)

        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setStyleSheet("background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        layout.addLayout(btn_box)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد حفظ الصور", self.txt_path.text())
        if folder:
            self.txt_path.setText(folder)

    def save_settings(self):
        config.set("save_dir", self.txt_path.text().strip())
        config.set("file_format", self.cmb_fmt.currentText())
        config.set("auto_copy_clipboard", self.chk_auto_copy.isChecked())
        config.set("auto_save", self.chk_auto_save.isChecked())
        config.set("open_editor_after_capture", self.chk_open_editor.isChecked())
        config.set("play_shutter_sound", self.chk_sound.isChecked())
        config.set("minimize_to_tray", self.chk_tray.isChecked())
        config.set("magnifier_enabled", self.chk_magnifier.isChecked())

        config.set("hotkey_region", self.txt_hk_region.text().strip())
        config.set("hotkey_full", self.txt_hk_full.text().strip())
        config.set("hotkey_window", self.txt_hk_win.text().strip())

        hotkeys.reload_hotkeys()
        self.settings_saved.emit()
        self.accept()
