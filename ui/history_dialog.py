import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QMessageBox, QFrame, QSplitter, QLineEdit,
    QTextEdit, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PIL import Image
from core.history import history
from core.capture import copy_to_clipboard
from core.ocr_engine import extract_text_from_image
from ui.toast import get_toast

class HistoryDialog(QDialog):
    open_in_editor = pyqtSignal(object)  # Emits PIL Image

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("سجل لقطات الشاشة السابقة - SnapMaster Pro")
        self.resize(840, 540)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("🖼️ سجل لقطات الشاشة الحديثة")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        top_bar.addWidget(title)

        top_bar.addSpacing(16)

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 تصفية اللقطات بالاسم أو التاريخ...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #38bdf8; }
        """)
        self.txt_search.textChanged.connect(self.filter_list)
        top_bar.addWidget(self.txt_search, stretch=1)

        top_bar.addSpacing(12)

        btn_clear = QPushButton("🧹 مسح السجل")
        btn_clear.setStyleSheet("""
            QPushButton {
                background: #1e293b; color: #f43f5e; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #334155; }
        """)
        btn_clear.clicked.connect(self.on_clear_history)
        top_bar.addWidget(btn_clear)
        layout.addLayout(top_bar)

        # Main Splitter: Left list, Right preview & details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(80, 60))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background-color: #334155;
            }
            QListWidget::item:selected {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
            }
        """)
        self.list_widget.currentRowChanged.connect(self.on_item_selected)
        splitter.addWidget(self.list_widget)

        # Preview & Actions Panel
        preview_panel = QFrame()
        preview_panel.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px;")
        p_layout = QVBoxLayout(preview_panel)

        self.preview_label = QLabel("اختر لقطة من القائمة لمعاينتها")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: #0f172a; border-radius: 6px; min-height: 220px;")
        p_layout.addWidget(self.preview_label, stretch=1)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #94a3b8; font-size: 12px; margin: 8px 0; line-height: 1.4;")
        p_layout.addWidget(self.info_label)

        # Action Buttons Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)

        self.btn_edit = QPushButton("✏️ المحرر")
        self.btn_edit.setStyleSheet(self.btn_style("#6366f1", "#ffffff"))
        self.btn_edit.setToolTip("فتح اللقطة في محرر الشروحات")
        self.btn_edit.clicked.connect(self.on_open_editor)
        actions_row.addWidget(self.btn_edit)

        self.btn_ocr = QPushButton("🔍 استخراج النص")
        self.btn_ocr.setStyleSheet(self.btn_style("#0284c7", "#ffffff"))
        self.btn_ocr.setToolTip("استخراج النصوص من هذه اللقطة عبر تقنية OCR")
        self.btn_ocr.clicked.connect(self.on_ocr_item)
        actions_row.addWidget(self.btn_ocr)

        self.btn_copy = QPushButton("📋 نسخ")
        self.btn_copy.setStyleSheet(self.btn_style("#10b981", "#ffffff"))
        self.btn_copy.setToolTip("نسخ الصورة إلى الحافظة")
        self.btn_copy.clicked.connect(self.on_copy_image)
        actions_row.addWidget(self.btn_copy)

        self.btn_folder = QPushButton("📁 المجلد")
        self.btn_folder.setStyleSheet(self.btn_style("#334155", "#f8fafc"))
        self.btn_folder.setToolTip("تحديد الملف في مستكشف Windows")
        self.btn_folder.clicked.connect(self.on_open_folder)
        actions_row.addWidget(self.btn_folder)

        self.btn_del = QPushButton("🗑️ حذف")
        self.btn_del.setStyleSheet(self.btn_style("#f43f5e", "#ffffff"))
        self.btn_del.setToolTip("حذف اللقطة")
        self.btn_del.clicked.connect(self.on_delete_item)
        actions_row.addWidget(self.btn_del)

        p_layout.addLayout(actions_row)
        splitter.addWidget(preview_panel)
        splitter.setSizes([340, 480])
        layout.addWidget(splitter)

        self.refresh_list()

    def btn_style(self, bg, fg):
        return f"""
            QPushButton {{
                background-color: {bg}; color: {fg}; font-weight: bold; border-radius: 6px; padding: 8px 10px; font-size: 11px; border: none;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """

    def refresh_list(self):
        self.list_widget.clear()
        history.load()
        query = self.txt_search.text().strip().lower()

        for item in history.items:
            path = item.get("path")
            if os.path.exists(path):
                name = item.get("filename", os.path.basename(path))
                time_str = item.get("timestamp", "")
                if query and (query not in name.lower() and query not in time_str.lower()):
                    continue

                text = f"{name}\n{time_str}"
                list_item = QListWidgetItem(text)
                try:
                    pix = QPixmap(path)
                    if not pix.isNull():
                        thumb = pix.scaled(80, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        list_item.setIcon(QIcon(thumb))
                except Exception:
                    pass
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.list_widget.addItem(list_item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        else:
            self.preview_label.setText("لا توجد لقطات شاشة مطابقة للبحث.")
            self.info_label.setText("")

    def filter_list(self):
        self.refresh_list()

    def on_item_selected(self, row):
        if row < 0 or row >= self.list_widget.count():
            return
        item_data = self.list_widget.item(row).data(Qt.ItemDataRole.UserRole)
        path = item_data.get("path")
        if os.path.exists(path):
            pix = QPixmap(path)
            scaled = pix.scaled(
                400, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)

            size_kb = item_data.get("size_bytes", 0) / 1024.0
            dim = f"{item_data.get('width', pix.width())} × {item_data.get('height', pix.height())} px"
            self.info_label.setText(
                f"📄 الملف: {item_data.get('filename')}\n"
                f"📐 الأبعاد: {dim} | 💾 الحجم: {size_kb:.1f} KB\n"
                f"🕒 التاريخ: {item_data.get('timestamp')}"
            )

    def current_item_path(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            item_data = self.list_widget.item(row).data(Qt.ItemDataRole.UserRole)
            return item_data.get("path")
        return None

    def on_open_editor(self):
        path = self.current_item_path()
        if path and os.path.exists(path):
            pil_img = Image.open(path)
            self.open_in_editor.emit(pil_img)
            self.accept()

    def on_ocr_item(self):
        path = self.current_item_path()
        if not path or not os.path.exists(path):
            return
        try:
            pil_img = Image.open(path)
            res = extract_text_from_image(pil_img)
            if len(res) == 3:
                success, text, eng = res
            else:
                success, text = res
                eng = "Auto"

            dlg = QDialog(self)
            dlg.setWindowTitle("استخراج النص (OCR) - SnapMaster Pro")
            dlg.resize(540, 400)
            dlg.setStyleSheet("background-color: #0f172a; color: #ffffff;")
            dlg_lay = QVBoxLayout(dlg)

            title_lbl = QLabel(f"النصوص المستخرجة عبر {eng}:" if success else "معلومات OCR:")
            title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
            dlg_lay.addWidget(title_lbl)

            txt_edit = QTextEdit()
            txt_edit.setPlainText(text)
            txt_edit.setStyleSheet("background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; font-size: 13px; padding: 10px;")
            dlg_lay.addWidget(txt_edit)

            btn_box = QHBoxLayout()
            btn_copy = QPushButton("📋 نسخ النص")
            btn_copy.setStyleSheet("background: #38bdf8; color: #0f172a; font-weight: bold; border-radius: 6px; padding: 8px 16px;")
            btn_copy.clicked.connect(lambda: (QApplication.clipboard().setText(txt_edit.toPlainText()), get_toast().show_message("SnapMaster Pro", "تم نسخ النص بنجاح! 📋")))
            btn_box.addWidget(btn_copy)

            btn_close = QPushButton("إغلاق")
            btn_close.setStyleSheet("background: #334155; color: #ffffff; border-radius: 6px; padding: 8px 16px;")
            btn_close.clicked.connect(dlg.accept)
            btn_box.addWidget(btn_close)

            dlg_lay.addLayout(btn_box)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "خطأ OCR", f"حدث خطأ أثناء معالجة الصورة:\n{e}")

    def on_copy_image(self):
        path = self.current_item_path()
        if path and os.path.exists(path):
            pix = QPixmap(path)
            copy_to_clipboard(pix)
            get_toast().show_message("SnapMaster Pro", "تم نسخ الصورة إلى الحافظة بنجاح! 📋")

    def on_open_folder(self):
        path = self.current_item_path()
        if path and os.path.exists(path):
            subprocess.run(["explorer", "/select,", os.path.normpath(path)])

    def on_delete_item(self):
        path = self.current_item_path()
        if path:
            ret = QMessageBox.question(
                self, "تأكيد الحذف", f"هل أنت متأكد من حذف هذه اللقطة نهائياً من القرص؟\n{os.path.basename(path)}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                history.delete_item(path)
                self.refresh_list()

    def on_clear_history(self):
        ret = QMessageBox.question(
            self, "تأكيد المسح", "هل أنت متأكد من مسح سجل اللقطات؟ (لن يتم حذف ملفات الصور من القرص)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            history.clear()
            self.refresh_list()
