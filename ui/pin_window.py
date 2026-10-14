from PyQt6.QtWidgets import QWidget, QMenu, QApplication, QFileDialog
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QPixmap, QCursor, QAction
from core.capture import pil_to_qpixmap, copy_to_clipboard
from core.history import history

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
            }
        """)

        act_copy = menu.addAction("📋 نسخ إلى الحافظة")
        act_save = menu.addAction("💾 حفظ باسم...")
        menu.addSeparator()

        opacity_menu = menu.addMenu("👁️ الشفافية")
        for val, label in [(1.0, "100%"), (0.75, "75%"), (0.50, "50%"), (0.30, "30%")]:
            act = opacity_menu.addAction(label)
            act.triggered.connect(lambda ch, v=val: self.set_custom_opacity(v))

        menu.addSeparator()
        act_close = menu.addAction("❌ إغلاق (Esc)")

        chosen = menu.exec(global_pos)
        if chosen == act_copy:
            copy_to_clipboard(self.original_pixmap)
        elif chosen == act_save:
            self.save_as()
        elif chosen == act_close:
            self.close()

    def set_custom_opacity(self, val):
        self.opacity = val
        self.setWindowOpacity(val)
        self.update()

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ لقطة الشاشة", "Screenshot_Pinned.png", "PNG (*.png);;JPG (*.jpg)"
        )
        if path:
            self.original_pixmap.save(path)
