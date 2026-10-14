import os
from PyQt6.QtWidgets import (
    QWidget, QMenu, QApplication, QFileDialog, QDialog, QVBoxLayout,
    QLabel, QTextEdit, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap, QCursor, QAction, QPen, QColor
from core.capture import pil_to_qpixmap, qpixmap_to_pil, copy_to_clipboard
from core.history import history
from core.ocr_engine import extract_text_from_image
from ui.toast import get_toast

class PinWindow(QWidget):
    def __init__(self, pil_image, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.original_pixmap = pil_to_qpixmap(pil_image)
        self.current_pixmap = self.original_pixmap
        self.scale_factor = 1.0
        self.opacity = 1.0

        self.drag_position = QPoint()
        self.is_dragging = False

        self.resize(self.original_pixmap.size())
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.opacity)
        painter.drawPixmap(0, 0, self.current_pixmap)

        # Subtle glowing edge border
        painter.setPen(QPen(QColor(56, 189, 248, 120), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        # Double click to close
        self.close()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        modifiers = QApplication.keyboardModifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Zoom / Scale
            zoom_in = delta > 0
            factor = 1.1 if zoom_in else 0.9
            new_scale = max(0.2, min(3.0, self.scale_factor * factor))
            if new_scale != self.scale_factor:
                self.scale_factor = new_scale
                new_w = int(self.original_pixmap.width() * self.scale_factor)
                new_h = int(self.original_pixmap.height() * self.scale_factor)
                self.current_pixmap = self.original_pixmap.scaled(
                    new_w, new_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.resize(new_w, new_h)
                self.update()
        else:
            # Adjust opacity
            step = 0.08 if delta > 0 else -0.08
            self.opacity = max(0.2, min(1.0, self.opacity + step))
            self.setWindowOpacity(self.opacity)
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            copy_to_clipboard(self.original_pixmap)
            get_toast().show_message("SnapMaster Pro", "Image copied to clipboard! 📋")
        else:
            super().keyPressEvent(event)

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: bold;
            }
        """)

        act_copy = menu.addAction("📋 Copy to Clipboard")
        act_ocr = menu.addAction("🔍 Extract Text (OCR)")
        act_save = menu.addAction("💾 Save As...")
        menu.addSeparator()

        opacity_menu = menu.addMenu("👁️ Opacity")
        for val, label in [(1.0, "100%"), (0.75, "75%"), (0.50, "50%"), (0.30, "30%")]:
            act = opacity_menu.addAction(label)
            act.triggered.connect(lambda ch, v=val: self.set_custom_opacity(v))

        menu.addSeparator()
        act_close = menu.addAction("❌ Close (Esc)")

        chosen = menu.exec(global_pos)
        if chosen == act_copy:
            copy_to_clipboard(self.original_pixmap)
            get_toast().show_message("SnapMaster Pro", "Image copied to clipboard! 📋")
        elif chosen == act_ocr:
            self.do_ocr()
        elif chosen == act_save:
            self.save_as()
        elif chosen == act_close:
            self.close()

    def do_ocr(self):
        pil_img = qpixmap_to_pil(self.original_pixmap)
        res = extract_text_from_image(pil_img)
        if len(res) == 3:
            success, text, eng = res
        else:
            success, text = res
            eng = "Auto"

        dlg = QDialog(self)
        dlg.setWindowTitle("Extract Text (OCR)")
        dlg.resize(500, 360)
        dlg.setStyleSheet("background-color: #0f172a; color: #ffffff;")
        dlg_lay = QVBoxLayout(dlg)

        title_lbl = QLabel(f"Extracted Text via {eng}:" if success else "OCR Information:")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        dlg_lay.addWidget(title_lbl)

        txt_edit = QTextEdit()
        txt_edit.setPlainText(text)
        txt_edit.setStyleSheet("background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; font-size: 13px; padding: 10px;")
        dlg_lay.addWidget(txt_edit)

        btn_box = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Text")
        btn_copy.setStyleSheet("background: #38bdf8; color: #0f172a; font-weight: bold; border-radius: 6px; padding: 8px 16px;")
        btn_copy.clicked.connect(lambda: (QApplication.clipboard().setText(txt_edit.toPlainText()), get_toast().show_message("SnapMaster Pro", "Text copied to clipboard! 📋")))
        btn_box.addWidget(btn_copy)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background: #334155; color: #ffffff; border-radius: 6px; padding: 8px 16px;")
        btn_close.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_close)

        dlg_lay.addLayout(btn_box)
        dlg.exec()

    def set_custom_opacity(self, val):
        self.opacity = val
        self.setWindowOpacity(val)
        self.update()

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "Screenshot_Pinned.png", "PNG (*.png);;JPG (*.jpg)"
        )
        if path:
            self.original_pixmap.save(path)
            get_toast().show_message("Saved", f"Screenshot saved to {os.path.basename(path)}")
