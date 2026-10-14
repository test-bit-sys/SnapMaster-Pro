import math
from PyQt6.QtWidgets import QWidget, QApplication, QToolTip
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QCursor, QPixmap, QImage, QPainterPath
)
from core.capture import (
    capture_full_desktop, get_virtual_geometry, get_window_at_point,
    pil_to_qpixmap, qpixmap_to_pil, copy_to_clipboard
)
from core.config import config
from core.history import history

class SnippingOverlay(QWidget):
    capture_completed = pyqtSignal(object)  # Emits PIL Image
    capture_cancelled = pyqtSignal()
    pin_requested = pyqtSignal(object)      # Emits PIL Image
    ocr_requested = pyqtSignal(object)      # Emits PIL Image

    # Resize handle states
    HANDLE_NONE = 0
    HANDLE_TL = 1
    HANDLE_TR = 2
    HANDLE_BL = 3
    HANDLE_BR = 4
    HANDLE_T = 5
    HANDLE_B = 6
    HANDLE_L = 7
    HANDLE_R = 8
    HANDLE_INSIDE = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMouseTracking(True)

        self.virtual_x, self.virtual_y, self.virtual_w, self.virtual_h = get_virtual_geometry()
        self.setGeometry(self.virtual_x, self.virtual_y, self.virtual_w, self.virtual_h)

        self.screen_pixmap = None
        self.screen_pil = None
        self.start_pos = None
        self.curr_pos = None
        self.selection_rect = None
        self.is_dragging = False
        self.active_handle = self.HANDLE_NONE
        self.hovered_window_rect = None
        self.hovered_window_title = ""

        # Magnifier settings
        self.magnifier_enabled = config.get("magnifier_enabled", True)
        self.magnifier_size = 140
        self.magnifier_zoom = config.get("magnifier_zoom", 5)

        # Toolbar rects
        self.toolbar_rect = QRect()
        self.btn_edit_rect = QRect()
        self.btn_copy_rect = QRect()
        self.btn_ocr_rect = QRect()
        self.btn_save_rect = QRect()
        self.btn_pin_rect = QRect()
        self.btn_cancel_rect = QRect()
        self.hovered_btn = None

    def start_capture(self):
        """Grabs desktop and displays overlay."""
        self.screen_pil, _ = capture_full_desktop()
        self.screen_pixmap = pil_to_qpixmap(self.screen_pil)
        self.selection_rect = None
        self.is_dragging = False
        self.active_handle = self.HANDLE_NONE
        self.hovered_window_rect = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.showFullScreen()
        self.activateWindow()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.cancel_capture()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirm_capture()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                self.action_copy()
            elif key == Qt.Key.Key_S:
                self.action_save()
            elif key == Qt.Key.Key_P:
                self.action_pin()
            elif key == Qt.Key.Key_T:
                self.action_ocr()
        elif not self.selection_rect and key in (Qt.Key.Key_Space, Qt.Key.Key_F):
            # Select entire virtual desktop immediately
            self.selection_rect = self.rect()
            self.update()
        elif self.selection_rect:
            # Nudge selection with arrow keys
            step = 10 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
            r = self.selection_rect
            if key == Qt.Key.Key_Left:
                self.selection_rect = r.translated(-step, 0)
            elif key == Qt.Key.Key_Right:
                self.selection_rect = r.translated(step, 0)
            elif key == Qt.Key.Key_Up:
                self.selection_rect = r.translated(0, -step)
            elif key == Qt.Key.Key_Down:
                self.selection_rect = r.translated(0, step)
            self.selection_rect = self.selection_rect.intersected(self.rect())
            self.update()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self.selection_rect:
                self.selection_rect = None
                self.update()
            else:
                self.cancel_capture()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            # Check toolbar click if selection is active
            if self.selection_rect and self.toolbar_rect.contains(pos):
                if self.btn_edit_rect.contains(pos):
                    self.confirm_capture()
                elif self.btn_copy_rect.contains(pos):
                    self.action_copy()
                elif self.btn_ocr_rect.contains(pos):
                    self.action_ocr()
                elif self.btn_save_rect.contains(pos):
                    self.action_save()
                elif self.btn_pin_rect.contains(pos):
                    self.action_pin()
                elif self.btn_cancel_rect.contains(pos):
                    self.cancel_capture()
                return

            if self.selection_rect:
                handle = self.get_handle_at(pos)
                if handle != self.HANDLE_NONE:
                    self.active_handle = handle
                    self.start_pos = pos
                    self.is_dragging = True
                    return

            # Check if clicked on a window boundary before selection
            if not self.selection_rect and self.hovered_window_rect:
                # Snap to hovered window
                self.selection_rect = self.hovered_window_rect.intersected(self.rect())
                self.update()
                return

            # Start new selection
            self.start_pos = pos
            self.curr_pos = pos
            self.is_dragging = True
            self.selection_rect = QRect(pos, pos)
            self.active_handle = self.HANDLE_BR
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.curr_pos = pos

        if self.is_dragging:
            if self.active_handle == self.HANDLE_INSIDE and self.selection_rect:
                dx = pos.x() - self.start_pos.x()
                dy = pos.y() - self.start_pos.y()
                self.selection_rect.translate(dx, dy)
                self.start_pos = pos
            elif self.selection_rect:
                r = self.selection_rect
                if self.active_handle == self.HANDLE_BR:
                    self.selection_rect = QRect(self.start_pos, pos).normalized()
                elif self.active_handle == self.HANDLE_TL:
                    self.selection_rect = QRect(pos, r.bottomRight()).normalized()
                elif self.active_handle == self.HANDLE_TR:
                    self.selection_rect = QRect(QPoint(r.left(), pos.y()), QPoint(pos.x(), r.bottom())).normalized()
                elif self.active_handle == self.HANDLE_BL:
                    self.selection_rect = QRect(QPoint(pos.x(), r.top()), QPoint(r.right(), pos.y())).normalized()
                elif self.active_handle == self.HANDLE_T:
                    self.selection_rect.setTop(pos.y())
                elif self.active_handle == self.HANDLE_B:
                    self.selection_rect.setBottom(pos.y())
                elif self.active_handle == self.HANDLE_L:
                    self.selection_rect.setLeft(pos.x())
                elif self.active_handle == self.HANDLE_R:
                    self.selection_rect.setRight(pos.x())
            self.update()
            return

        # Not dragging: check hover on toolbar
        if self.selection_rect and self.toolbar_rect.contains(pos):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update()
            return

        # Check handle hover
        if self.selection_rect:
            handle = self.get_handle_at(pos)
            self.set_cursor_for_handle(handle)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
            # Detect window under mouse for auto-snapping
            screen_x = pos.x() + self.virtual_x
            screen_y = pos.y() + self.virtual_y
            hwnd, (wx, wy, ww, wh), title = get_window_at_point(screen_x, screen_y)
            if ww > 20 and wh > 20 and hwnd != int(self.winId()):
                self.hovered_window_rect = QRect(wx - self.virtual_x, wy - self.virtual_y, ww, wh)
                self.hovered_window_title = title
            else:
                self.hovered_window_rect = None

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.active_handle = self.HANDLE_NONE
            if self.selection_rect:
                self.selection_rect = self.selection_rect.normalized()
                if self.selection_rect.width() < 5 or self.selection_rect.height() < 5:
                    self.selection_rect = None
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.selection_rect:
            self.confirm_capture()

    def get_handle_at(self, pos):
        if not self.selection_rect:
            return self.HANDLE_NONE
        r = self.selection_rect
        margin = 8
        if QRect(r.left() - margin, r.top() - margin, margin * 2, margin * 2).contains(pos):
            return self.HANDLE_TL
        if QRect(r.right() - margin, r.top() - margin, margin * 2, margin * 2).contains(pos):
            return self.HANDLE_TR
        if QRect(r.left() - margin, r.bottom() - margin, margin * 2, margin * 2).contains(pos):
            return self.HANDLE_BL
        if QRect(r.right() - margin, r.bottom() - margin, margin * 2, margin * 2).contains(pos):
            return self.HANDLE_BR
        if abs(pos.y() - r.top()) <= margin and r.left() < pos.x() < r.right():
            return self.HANDLE_T
        if abs(pos.y() - r.bottom()) <= margin and r.left() < pos.x() < r.right():
            return self.HANDLE_B
        if abs(pos.x() - r.left()) <= margin and r.top() < pos.y() < r.bottom():
            return self.HANDLE_L
        if abs(pos.x() - r.right()) <= margin and r.top() < pos.y() < r.bottom():
            return self.HANDLE_R
        if r.contains(pos):
            return self.HANDLE_INSIDE
        return self.HANDLE_NONE

    def set_cursor_for_handle(self, handle):
        if handle in (self.HANDLE_TL, self.HANDLE_BR):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in (self.HANDLE_TR, self.HANDLE_BL):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in (self.HANDLE_T, self.HANDLE_B):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle in (self.HANDLE_L, self.HANDLE_R):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif handle == self.HANDLE_INSIDE:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw frozen desktop image
        if self.screen_pixmap:
            painter.drawPixmap(0, 0, self.screen_pixmap)

        # 2. Draw dimmed overlay mask outside selection
        dim_color = QColor(10, 15, 29, 140)  # elegant translucent dark slate
        if self.selection_rect and self.selection_rect.isValid() and not self.selection_rect.isEmpty():
            sel = self.selection_rect.normalized()
            # Top rect
            painter.fillRect(0, 0, self.width(), sel.top(), dim_color)
            # Bottom rect
            painter.fillRect(0, sel.bottom() + 1, self.width(), self.height() - sel.bottom() - 1, dim_color)
            # Left rect
            painter.fillRect(0, sel.top(), sel.left(), sel.height(), dim_color)
            # Right rect
            painter.fillRect(sel.right() + 1, sel.top(), self.width() - sel.right() - 1, sel.height(), dim_color)

            # Draw glowing selection border
            border_pen = QPen(QColor(56, 189, 248), 2)  # sky cyan
            painter.setPen(border_pen)
            painter.drawRect(sel)

            # Draw resize handles
            self.draw_handles(painter, sel)

            # Draw dimension badge
            dim_text = f"{sel.width()} × {sel.height()} px"
            self.draw_badge(painter, sel.left(), sel.top() - 28, dim_text)

            # Draw floating quick action bar
            self.draw_action_toolbar(painter, sel)
        else:
            # Full dim
            painter.fillRect(self.rect(), dim_color)

            # Draw hovered window outline if auto-detecting
            if self.hovered_window_rect:
                win_pen = QPen(QColor(99, 102, 241), 2, Qt.PenStyle.DashLine)
                painter.setPen(win_pen)
                painter.drawRect(self.hovered_window_rect)
                if self.hovered_window_title:
                    self.draw_badge(
                        painter,
                        self.hovered_window_rect.left() + 10,
                        self.hovered_window_rect.top() + 10,
                        f"🪟 {self.hovered_window_title[:35]}"
                    )

            # Draw helpful initial guide
            guide_text = "انقر واسحب لتحديد منطقة | اضغط Esc للإلغاء | انقر على أي نافذة لتحديدها فوراً"
            self.draw_guide_bar(painter, guide_text)

        # 3. Draw live magnifier if enabled and not covered
        if self.magnifier_enabled and self.curr_pos:
            self.draw_magnifier(painter, self.curr_pos)

    def draw_handles(self, painter, rect):
        handle_color = QColor(255, 255, 255)
        border_color = QColor(56, 189, 248)
        size = 8
        half = size // 2

        points = [
            rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight(),
            QPoint(rect.center().x(), rect.top()),
            QPoint(rect.center().x(), rect.bottom()),
            QPoint(rect.left(), rect.center().y()),
            QPoint(rect.right(), rect.center().y())
        ]

        for pt in points:
            painter.setPen(QPen(border_color, 2))
            painter.setBrush(QBrush(handle_color))
            painter.drawRoundedRect(pt.x() - half, pt.y() - half, size, size, 2, 2)

    def draw_badge(self, painter, x, y, text):
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        tw = metrics.horizontalAdvance(text) + 16
        th = metrics.height() + 8

        # Bound check
        bx = max(10, min(x, self.width() - tw - 10))
        by = max(10, min(y, self.height() - th - 10))

        # Pill background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
        painter.drawRoundedRect(bx, by, tw, th, 6, 6)

        painter.setPen(QPen(QColor(56, 189, 248)))
        painter.drawText(bx, by, tw, th, Qt.AlignmentFlag.AlignCenter, text)

    def draw_guide_bar(self, painter, text):
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        tw = metrics.horizontalAdvance(text) + 36
        th = 44
        bx = (self.width() - tw) // 2
        by = 50

        # Glassmorphic pill
        painter.setPen(QPen(QColor(56, 189, 248, 180), 1))
        painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
        painter.drawRoundedRect(bx, by, tw, th, 22, 22)

        painter.setPen(QPen(QColor(248, 250, 252)))
        painter.drawText(bx, by, tw, th, Qt.AlignmentFlag.AlignCenter, text)

    def draw_action_toolbar(self, painter, rect):
        """Draws floating quick-actions bar near the selection."""
        tb_width = 286
        tb_height = 42

        # Position below selection, or above if near screen bottom
        bx = rect.right() - tb_width
        by = rect.bottom() + 10
        if by + tb_height > self.height() - 15:
            by = rect.top() - tb_height - 10
        if bx < 10:
            bx = 10
        if bx + tb_width > self.width() - 10:
            bx = self.width() - tb_width - 10

        self.toolbar_rect = QRect(bx, by, tb_width, tb_height)

        # Background pill
        painter.setPen(QPen(QColor(51, 65, 85), 1))
        painter.setBrush(QBrush(QColor(15, 23, 42, 240)))
        painter.drawRoundedRect(self.toolbar_rect, 10, 10)

        # Action Buttons: Edit, Copy, OCR, Save, Pin, Cancel
        btn_w = 42
        btn_h = 32
        spacing = 4
        start_x = bx + 6
        btn_y = by + 5

        buttons = [
            ("btn_edit", "✏️", "تعديل (Enter)"),
            ("btn_copy", "📋", "نسخ (Ctrl+C)"),
            ("btn_ocr", "🔍", "استخراج النص (Ctrl+T)"),
            ("btn_save", "💾", "حفظ (Ctrl+S)"),
            ("btn_pin", "📌", "تثبيت (Ctrl+P)"),
            ("btn_cancel", "❌", "إلغاء (Esc)")
        ]

        curr_x = start_x
        mouse_pos = self.mapFromGlobal(QCursor.pos())

        for name, icon, tooltip in buttons:
            btn_rect = QRect(curr_x, btn_y, btn_w, btn_h)
            setattr(self, f"{name}_rect", btn_rect)

            is_hover = btn_rect.contains(mouse_pos)
            if is_hover:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(56, 189, 248, 80)))
                painter.drawRoundedRect(btn_rect, 6, 6)

            font = QFont("Segoe UI Emoji", 13)
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, icon)

            curr_x += btn_w + spacing

    def draw_magnifier(self, painter, pos):
        """Draws live magnifier with zoomed pixel grid and RGB hex color info."""
        if not self.screen_pixmap:
            return

        size = self.magnifier_size
        zoom = self.magnifier_zoom
        half_src = (size // zoom) // 2

        # Magnifier box placement (flip around cursor to avoid obstruction)
        offset = 25
        mx = pos.x() + offset
        my = pos.y() + offset
        if mx + size > self.width():
            mx = pos.x() - size - offset
        if my + size + 45 > self.height():
            my = pos.y() - size - offset - 45

        # Source rectangle around cursor
        src_rect = QRect(pos.x() - half_src, pos.y() - half_src, half_src * 2, half_src * 2)
        zoomed_pixmap = self.screen_pixmap.copy(src_rect).scaled(
            size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )

        # Get exact pixel color at cursor
        pixel_img = self.screen_pixmap.toImage()
        px = max(0, min(pos.x(), pixel_img.width() - 1))
        py = max(0, min(pos.y(), pixel_img.height() - 1))
        pixel_color = pixel_img.pixelColor(px, py)
        hex_color = pixel_color.name().upper()
        rgb_text = f"RGB: {pixel_color.red()}, {pixel_color.green()}, {pixel_color.blue()}"

        # Draw magnifier frame
        painter.save()
        # Clip rounded rect for lens
        clip_path = QPainterPath()
        clip_path.addRoundedRect(float(mx), float(my), float(size), float(size), 10, 10)
        painter.setClipPath(clip_path)
        painter.drawPixmap(mx, my, zoomed_pixmap)

        # Draw subtle pixel grid
        grid_pen = QPen(QColor(255, 255, 255, 40), 1)
        painter.setPen(grid_pen)
        step = zoom
        for gx in range(mx, mx + size, step):
            painter.drawLine(gx, my, gx, my + size)
        for gy in range(my, my + size, step):
            painter.drawLine(mx, gy, mx + size, gy)

        # Center crosshair / target pixel indicator
        cx = mx + size // 2
        cy = my + size // 2
        painter.setPen(QPen(QColor(244, 63, 94), 2))  # rose red target
        painter.drawRect(cx - step // 2, cy - step // 2, step, step)
        painter.restore()

        # Frame border
        painter.setPen(QPen(QColor(56, 189, 248), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(mx, my, size, size, 10, 10)

        # Info Box below magnifier (Color badge & Coordinates)
        info_h = 42
        info_rect = QRect(mx, my + size + 4, size, info_h)
        painter.setPen(QPen(QColor(51, 65, 85), 1))
        painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
        painter.drawRoundedRect(info_rect, 6, 6)

        # Color preview circle
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(pixel_color))
        painter.drawEllipse(mx + 6, my + size + 10, 14, 14)

        # Color & Position text
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(248, 250, 252)))
        painter.drawText(mx + 26, my + size + 20, hex_color)

        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QPen(QColor(148, 163, 184)))
        painter.drawText(mx + 6, my + size + 36, f"X:{pos.x()} Y:{pos.y()}")
        painter.drawText(mx + 70, my + size + 36, f"W:{self.selection_rect.width() if self.selection_rect else 0}")

    def get_cropped_image(self):
        """Returns the cropped PIL Image based on selection."""
        if not self.selection_rect or not self.screen_pil:
            return None
        r = self.selection_rect.normalized()
        box = (r.left(), r.top(), r.right(), r.bottom())
        return self.screen_pil.crop(box)

    def confirm_capture(self):
        """Completes capture and sends to Editor."""
        img = self.get_cropped_image()
        self.close()
        if img:
            self.capture_completed.emit(img)
        else:
            self.capture_cancelled.emit()

    def action_copy(self):
        """Copies image to clipboard and closes."""
        img = self.get_cropped_image()
        self.close()
        if img:
            copy_to_clipboard(img)
            history.save_image(img)  # Auto-save record

    def action_save(self):
        """Quick saves screenshot to folder."""
        img = self.get_cropped_image()
        self.close()
        if img:
            history.save_image(img)

    def action_pin(self):
        """Pins screenshot to desktop."""
        img = self.get_cropped_image()
        self.close()
        if img:
            self.pin_requested.emit(img)

    def action_ocr(self):
        """Extracts text via OCR and closes."""
        img = self.get_cropped_image()
        self.close()
        if img:
            self.ocr_requested.emit(img)

    def cancel_capture(self):
        self.close()
        self.capture_cancelled.emit()
