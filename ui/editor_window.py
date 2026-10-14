import os
import math
import webbrowser
import urllib.parse
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageFilter
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QToolButton,
    QColorDialog, QFileDialog, QMessageBox, QLabel, QSlider, QComboBox,
    QScrollArea, QInputDialog, QDialog, QTextEdit, QPushButton, QFrame,
    QButtonGroup, QSizePolicy, QToolTip
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QIcon, QPixmap, QImage,
    QPainterPath, QKeySequence, QShortcut, QPolygon
)
from core.capture import pil_to_qpixmap, qpixmap_to_pil, copy_to_clipboard
from core.history import history
from core.config import config
from core.ocr_engine import extract_text_from_image, is_ocr_available
from ui.toast import get_toast

# Tool definitions
TOOL_SELECT = "select"
TOOL_ARROW = "arrow"
TOOL_RECT = "rect"
TOOL_CIRCLE = "circle"
TOOL_LINE = "line"
TOOL_PEN = "pen"
TOOL_HIGHLIGHT = "highlight"
TOOL_BLUR = "blur"
TOOL_TEXT = "text"
TOOL_STEP = "step"
TOOL_STAMP = "stamp"
TOOL_CROP = "crop"

class AnnotationItem:
    def __init__(self, tool, color, width, fill=False):
        self.tool = tool
        self.color = QColor(color)
        self.width = width
        self.fill = fill
        self.points = []
        self.rect = QRect()
        self.text = ""
        self.step_number = 1
        self.stamp_char = "✓"
        self.cached_blur_pixmap = None

class CanvasWidget(QWidget):
    status_updated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_pixmap = None
        self.current_tool = TOOL_ARROW
        self.current_color = QColor(244, 63, 94)  # Coral red default
        self.stroke_width = 4
        self.fill_enabled = False
        self.current_stamp = "✓"
        self.next_step_num = 1

        self.items = []
        self.redo_stack = []
        self.current_item = None
        self.start_pos = None
        self.zoom_level = 1.0

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_base_image(self, pil_image):
        self.base_pixmap = pil_to_qpixmap(pil_image)
        self.items.clear()
        self.redo_stack.clear()
        self.next_step_num = 1
        self.update_canvas_size()
        self.update()

    def update_canvas_size(self):
        if self.base_pixmap:
            w = int(self.base_pixmap.width() * self.zoom_level)
            h = int(self.base_pixmap.height() * self.zoom_level)
            self.setFixedSize(w, h)

    def set_zoom(self, zoom):
        self.zoom_level = max(0.2, min(4.0, zoom))
        self.update_canvas_size()
        self.update()

    def undo(self):
        if self.items:
            popped = self.items.pop()
            if popped.tool == TOOL_STEP and self.next_step_num > 1:
                self.next_step_num -= 1
            self.redo_stack.append(popped)
            self.update()
            self.status_updated.emit("Undo")

    def redo(self):
        if self.redo_stack:
            item = self.redo_stack.pop()
            if item.tool == TOOL_STEP:
                self.next_step_num += 1
            self.items.append(item)
            self.update()
            self.status_updated.emit("Redo")

    def canvas_pos(self, widget_pos):
        """Converts widget position considering zoom level."""
        return QPoint(int(widget_pos.x() / self.zoom_level), int(widget_pos.y() / self.zoom_level))

    def mousePressEvent(self, event):
        if not self.base_pixmap:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.canvas_pos(event.pos())
            self.start_pos = pos

            if self.current_tool == TOOL_STEP:
                item = AnnotationItem(TOOL_STEP, self.current_color, self.stroke_width)
                item.rect = QRect(pos.x() - 15, pos.y() - 15, 30, 30)
                item.step_number = self.next_step_num
                self.next_step_num += 1
                self.items.append(item)
                self.redo_stack.clear()
                self.update()
                return

            if self.current_tool == TOOL_STAMP:
                item = AnnotationItem(TOOL_STAMP, self.current_color, self.stroke_width)
                item.rect = QRect(pos.x() - 16, pos.y() - 16, 32, 32)
                item.stamp_char = self.current_stamp
                self.items.append(item)
                self.redo_stack.clear()
                self.update()
                return

            if self.current_tool == TOOL_TEXT:
                text, ok = QInputDialog.getText(self, "Add Text", "Enter callout text:")
                if ok and text.strip():
                    item = AnnotationItem(TOOL_TEXT, self.current_color, self.stroke_width)
                    item.points = [pos]
                    item.text = text.strip()
                    self.items.append(item)
                    self.redo_stack.clear()
                    self.update()
                return

            # Shape or drawing tools
            item = AnnotationItem(
                self.current_tool, self.current_color, self.stroke_width, self.fill_enabled
            )
            if self.current_tool in (TOOL_PEN, TOOL_HIGHLIGHT):
                item.points = [pos]
            else:
                item.rect = QRect(pos, pos)
            self.current_item = item
            self.update()

    def mouseMoveEvent(self, event):
        pos = self.canvas_pos(event.pos())
        self.status_updated.emit(f"Pos: X={pos.x()}, Y={pos.y()} | Size: {self.base_pixmap.width()}×{self.base_pixmap.height()}")

        if self.current_item and self.start_pos:
            if self.current_tool in (TOOL_PEN, TOOL_HIGHLIGHT):
                self.current_item.points.append(pos)
            elif self.current_tool in (TOOL_ARROW, TOOL_LINE):
                self.current_item.points = [self.start_pos, pos]
            elif self.current_tool in (TOOL_RECT, TOOL_CIRCLE, TOOL_BLUR, TOOL_CROP):
                self.current_item.rect = QRect(self.start_pos, pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.current_item:
            if self.current_tool == TOOL_BLUR and self.current_item.rect.isValid():
                # Precompute blur for this rect
                self.apply_blur_to_item(self.current_item)

            if self.current_tool == TOOL_CROP and self.current_item.rect.isValid():
                # Apply crop immediately
                self.apply_crop(self.current_item.rect)
                self.current_item = None
                self.update()
                return

            self.items.append(self.current_item)
            self.redo_stack.clear()
            self.current_item = None
            self.update()

    def apply_blur_to_item(self, item):
        """Creates pixelated / blurred patch for the given rect."""
        if not self.base_pixmap or item.rect.isEmpty():
            return
        r = item.rect.intersected(self.base_pixmap.rect())
        if r.width() <= 0 or r.height() <= 0:
            return

        cropped = self.base_pixmap.copy(r)
        pil_sub = qpixmap_to_pil(cropped)
        # Apply heavy pixelation / mosaic
        small = pil_sub.resize((max(1, r.width() // 12), max(1, r.height() // 12)), Image.Resampling.NEAREST)
        pixelated = small.resize((r.width(), r.height()), Image.Resampling.NEAREST)
        item.cached_blur_pixmap = pil_to_qpixmap(pixelated)

    def apply_crop(self, crop_rect):
        """Crops base pixmap and resets annotations."""
        if not self.base_pixmap or crop_rect.isEmpty():
            return
        r = crop_rect.intersected(self.base_pixmap.rect())
        if r.width() > 10 and r.height() > 10:
            # Render current items onto image first
            rendered = self.render_final_image()
            cropped_pil = rendered.crop((r.left(), r.top(), r.right(), r.bottom()))
            self.set_base_image(cropped_pil)
            self.status_updated.emit("Image cropped successfully")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.zoom_level, self.zoom_level)

        # 1. Base Image
        if self.base_pixmap:
            painter.drawPixmap(0, 0, self.base_pixmap)

        # 2. Render all completed annotation items
        for item in self.items:
            self.draw_item(painter, item)

        # 3. Render currently active dragging item
        if self.current_item:
            self.draw_item(painter, self.current_item)

    def draw_item(self, painter, item):
        pen = QPen(item.color, item.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

        if item.tool == TOOL_PEN:
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(item.points) - 1):
                painter.drawLine(item.points[i], item.points[i + 1])

        elif item.tool == TOOL_HIGHLIGHT:
            # Translucent pen
            hl_color = QColor(item.color)
            hl_color.setAlpha(90)
            hl_pen = QPen(hl_color, max(item.width * 3, 18), Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
            painter.setPen(hl_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(item.points) - 1):
                painter.drawLine(item.points[i], item.points[i + 1])

        elif item.tool == TOOL_LINE and len(item.points) == 2:
            painter.setPen(pen)
            painter.drawLine(item.points[0], item.points[1])

        elif item.tool == TOOL_ARROW and len(item.points) == 2:
            self.draw_arrow(painter, item.points[0], item.points[1], item.color, item.width)

        elif item.tool == TOOL_RECT:
            painter.setPen(pen)
            painter.setBrush(QBrush(item.color) if item.fill else Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(item.rect, 6, 6)

        elif item.tool == TOOL_CIRCLE:
            painter.setPen(pen)
            painter.setBrush(QBrush(item.color) if item.fill else Qt.BrushStyle.NoBrush)
            painter.drawEllipse(item.rect)

        elif item.tool == TOOL_BLUR:
            if item.cached_blur_pixmap:
                painter.drawPixmap(item.rect.topLeft(), item.cached_blur_pixmap)
            else:
                # Live preview while dragging blur
                painter.setPen(QPen(QColor(100, 116, 139), 1, Qt.PenStyle.DashLine))
                painter.setBrush(QBrush(QColor(15, 23, 42, 180)))
                painter.drawRect(item.rect)

        elif item.tool == TOOL_TEXT and item.points:
            pt = item.points[0]
            font = QFont("Segoe UI", max(12, int(item.width * 3.5)), QFont.Weight.Bold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            tw = metrics.horizontalAdvance(item.text) + 14
            th = metrics.height() + 8
            # Text background badge
            bg_rect = QRect(pt.x(), pt.y(), tw, th)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(15, 23, 42, 210)))
            painter.drawRoundedRect(bg_rect, 6, 6)

            painter.setPen(QPen(item.color))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, item.text)

        elif item.tool == TOOL_STEP:
            r = item.rect
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QBrush(item.color))
            painter.drawEllipse(r)

            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, str(item.step_number))

        elif item.tool == TOOL_STAMP:
            painter.setFont(QFont("Segoe UI Emoji", 20, QFont.Weight.Bold))
            painter.setPen(QPen(item.color))
            painter.drawText(item.rect, Qt.AlignmentFlag.AlignCenter, item.stamp_char)

        elif item.tool == TOOL_CROP:
            # Crop selection mask
            painter.setPen(QPen(QColor(244, 63, 94), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(244, 63, 94, 40)))
            painter.drawRect(item.rect)

    def draw_arrow(self, painter, p1, p2, color, width):
        """Draws sleek directional arrow from p1 to p2 with sharp triangular head."""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 5:
            return

        angle = math.atan2(dy, dx)
        head_len = max(14.0, width * 3.5)
        head_angle = math.pi / 6.0

        # Draw main stem
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

        # Draw arrowhead
        x3 = p2.x() - head_len * math.cos(angle - head_angle)
        y3 = p2.y() - head_len * math.sin(angle - head_angle)
        x4 = p2.x() - head_len * math.cos(angle + head_angle)
        y4 = p2.y() - head_len * math.sin(angle + head_angle)

        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        arrow_head = QPolygon([
            p2,
            QPoint(int(x3), int(y3)),
            QPoint(int(x4), int(y4))
        ])
        painter.drawPolygon(arrow_head)

    def render_final_image(self):
        """Bakes all annotations onto the base image and returns PIL Image."""
        if not self.base_pixmap:
            return None
        result = QPixmap(self.base_pixmap.size())
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, self.base_pixmap)

        for item in self.items:
            self.draw_item(painter, item)

        painter.end()
        return qpixmap_to_pil(result)


class EditorWindow(QMainWindow):
    pin_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnapMaster Pro - Annotation Studio")
        self.setMinimumSize(950, 680)

        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sleek Top Toolbar
        self.create_top_toolbar(main_layout)

        # 2. Scroll area with Canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #0b0f19; border: none;")
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas = CanvasWidget()
        self.canvas.status_updated.connect(self.on_canvas_status)
        self.scroll_area.setWidget(self.canvas)
        main_layout.addWidget(self.scroll_area)

        # 3. Status Bar
        self.status_bar = QLabel("Ready for annotations | Select a tool to begin")
        self.status_bar.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; padding: 6px 14px; font-size: 12px; border-top: 1px solid #334155;"
        )
        main_layout.addWidget(self.status_bar)

        self.setup_shortcuts()

    def create_top_toolbar(self, parent_layout):
        bar_frame = QFrame()
        bar_frame.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155; padding: 4px 10px;")
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(6, 4, 6, 4)
        bar_layout.setSpacing(6)

        # Tool group buttons
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = [
            (TOOL_ARROW, "↘️ Arrow", "Draw directional arrow (A)"),
            (TOOL_RECT, "🔲 Rect", "Draw rectangle (R)"),
            (TOOL_CIRCLE, "⭕ Circle", "Draw ellipse / circle (C)"),
            (TOOL_PEN, "✏️ Pen", "Freehand drawing pen (P)"),
            (TOOL_HIGHLIGHT, "🖍️ Highlight", "Translucent highlighter (H)"),
            (TOOL_BLUR, "💧 Blur", "Mosaic blur to redact sensitive data (B)"),
            (TOOL_TEXT, "🔤 Text", "Add callout text (T)"),
            (TOOL_STEP, "🔢 Steps", "Step counter badge 1, 2, 3 (N)"),
            (TOOL_STAMP, "✓ Stamp", "Quick stamps and markers"),
            (TOOL_CROP, "✂️ Crop", "Crop & trim image canvas (X)"),
        ]

        for tool_id, title, tooltip in tools:
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0f172a;
                    color: #e2e8f0;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #38bdf8;
                }
                QPushButton:checked {
                    background-color: #38bdf8;
                    color: #0f172a;
                    border: 1px solid #0284c7;
                    font-weight: bold;
                }
            """)
            if tool_id == TOOL_ARROW:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=tool_id: self.select_tool(t))
            self.tool_group.addButton(btn)
            bar_layout.addWidget(btn)

        # Separator
        bar_layout.addWidget(self.create_separator())

        # Colors Palette
        color_label = QLabel("Color:")
        color_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        bar_layout.addWidget(color_label)

        palette = [
            ("#f43f5e", "Coral Red"),
            ("#38bdf8", "Sky Blue"),
            ("#10b981", "Emerald Green"),
            ("#f59e0b", "Amber Gold"),
            ("#a855f7", "Purple"),
            ("#ffffff", "White"),
            ("#0f172a", "Black")
        ]

        for c_hex, c_name in palette:
            c_btn = QPushButton()
            c_btn.setFixedSize(22, 22)
            c_btn.setToolTip(c_name)
            c_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c_hex};
                    border: 2px solid #475569;
                    border-radius: 11px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            c_btn.clicked.connect(lambda checked, col=c_hex: self.set_canvas_color(col))
            bar_layout.addWidget(c_btn)

        # Custom Color Picker Button
        pick_btn = QPushButton("🎨")
        pick_btn.setFixedSize(24, 24)
        pick_btn.setToolTip("Choose custom color...")
        pick_btn.setStyleSheet("background: #0f172a; border: 1px solid #475569; border-radius: 6px;")
        pick_btn.clicked.connect(self.choose_custom_color)
        bar_layout.addWidget(pick_btn)

        # Separator
        bar_layout.addWidget(self.create_separator())

        # Stroke Width Slider
        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        bar_layout.addWidget(size_label)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(2, 24)
        self.size_slider.setValue(4)
        self.size_slider.setFixedWidth(80)
        self.size_slider.valueChanged.connect(self.on_stroke_changed)
        bar_layout.addWidget(self.size_slider)

        # Separator
        bar_layout.addWidget(self.create_separator())

        # Action Buttons (Undo, Redo, OCR, Pin, Save, Copy)
        btn_undo = QPushButton("↩️ Undo")
        btn_undo.setStyleSheet(self.secondary_btn_style())
        btn_undo.setToolTip("Undo (Ctrl+Z)")
        btn_undo.clicked.connect(self.canvas.undo)
        bar_layout.addWidget(btn_undo)

        btn_redo = QPushButton("↪️ Redo")
        btn_redo.setStyleSheet(self.secondary_btn_style())
        btn_redo.setToolTip("Redo (Ctrl+Y)")
        btn_redo.clicked.connect(self.canvas.redo)
        bar_layout.addWidget(btn_redo)

        bar_layout.addStretch()

        # OCR Button
        btn_ocr = QPushButton("🔍 Extract Text")
        btn_ocr.setStyleSheet(self.accent_btn_style("#6366f1"))
        btn_ocr.setToolTip("Extract text from image (OCR) (Ctrl+T)")
        btn_ocr.clicked.connect(self.action_ocr)
        bar_layout.addWidget(btn_ocr)

        # Pin Button
        btn_pin = QPushButton("📌 Pin")
        btn_pin.setStyleSheet(self.secondary_btn_style())
        btn_pin.setToolTip("Pin image as floating desktop widget (Ctrl+P)")
        btn_pin.clicked.connect(self.action_pin)
        bar_layout.addWidget(btn_pin)

        # Save As Button
        btn_save = QPushButton("💾 Save As")
        btn_save.setStyleSheet(self.secondary_btn_style())
        btn_save.setToolTip("Save image to file (Ctrl+S)")
        btn_save.clicked.connect(self.action_save_as)
        bar_layout.addWidget(btn_save)

        # Quick Copy Button (Glowing Primary)
        btn_copy = QPushButton("📋 Copy & Close")
        btn_copy.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 7px 16px;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        btn_copy.setToolTip("Copy to clipboard & close (Ctrl+C)")
        btn_copy.clicked.connect(self.action_copy_and_close)
        bar_layout.addWidget(btn_copy)

        parent_layout.addWidget(bar_frame)

    def secondary_btn_style(self):
        return """
            QPushButton {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38bdf8;
            }
        """

    def accent_btn_style(self, color_hex):
        return f"""
            QPushButton {{
                background-color: {color_hex};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """

    def create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #334155; margin: 4px 6px;")
        return sep

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self.action_save_as)
        QShortcut(QKeySequence("Ctrl+C"), self, self.action_copy_and_close)
        QShortcut(QKeySequence("Ctrl+P"), self, self.action_pin)
        QShortcut(QKeySequence("Ctrl+T"), self, self.action_ocr)

        # Tool shortcuts
        QShortcut(QKeySequence("A"), self, lambda: self.select_tool(TOOL_ARROW))
        QShortcut(QKeySequence("R"), self, lambda: self.select_tool(TOOL_RECT))
        QShortcut(QKeySequence("C"), self, lambda: self.select_tool(TOOL_CIRCLE))
        QShortcut(QKeySequence("P"), self, lambda: self.select_tool(TOOL_PEN))
        QShortcut(QKeySequence("H"), self, lambda: self.select_tool(TOOL_HIGHLIGHT))
        QShortcut(QKeySequence("B"), self, lambda: self.select_tool(TOOL_BLUR))
        QShortcut(QKeySequence("T"), self, lambda: self.select_tool(TOOL_TEXT))
        QShortcut(QKeySequence("N"), self, lambda: self.select_tool(TOOL_STEP))
        QShortcut(QKeySequence("X"), self, lambda: self.select_tool(TOOL_CROP))

    def load_image(self, pil_image):
        self.canvas.set_base_image(pil_image)
        self.show()
        self.raise_()
        self.activateWindow()

    def select_tool(self, tool_id):
        self.canvas.current_tool = tool_id
        # Update checkstate in buttons
        for btn in self.tool_group.buttons():
            if tool_id in btn.toolTip():
                btn.setChecked(True)
        self.status_bar.setText(f"Active Tool: {tool_id.upper()}")

    def set_canvas_color(self, hex_color):
        self.canvas.current_color = QColor(hex_color)

    def choose_custom_color(self):
        col = QColorDialog.getColor(self.canvas.current_color, self, "Select Color")
        if col.isValid():
            self.canvas.current_color = col

    def on_stroke_changed(self, val):
        self.canvas.stroke_width = val

    def on_canvas_status(self, text):
        self.status_bar.setText(text)

    def action_copy_and_close(self):
        rendered = self.canvas.render_final_image()
        if rendered:
            copy_to_clipboard(rendered)
            if config.get("auto_save", True):
                history.save_image(rendered)
            if config.get("enable_toast", True):
                get_toast().show_message(
                    "SnapMaster Pro",
                    "Screenshot copied to clipboard! 📋",
                    action_text="Open Folder",
                    action_cb=lambda: os.startfile(config.get("save_dir", ""))
                )
            self.close()

    def action_save_as(self):
        rendered = self.canvas.render_final_image()
        if not rendered:
            return
        default_dir = config.get("save_dir", str(os.path.expanduser("~/Pictures/Screenshots")))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested = os.path.join(default_dir, f"Screenshot_{timestamp}.png")

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            suggested,
            "PNG Image (*.png);;JPEG Image (*.jpg);;WebP Image (*.webp);;PDF Document (*.pdf);;All Files (*.*)"
        )
        if path:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                rendered.convert("RGB").save(path, "PDF")
            else:
                fmt = "PNG" if ext == ".png" else ("JPEG" if ext in (".jpg", ".jpeg") else "WEBP")
                rendered.save(path, fmt)
            history.add_entry(path, rendered.width, rendered.height)
            if config.get("enable_toast", True):
                get_toast().show_message("Saved Successfully", f"Saved to {os.path.basename(path)}")
            else:
                QMessageBox.information(self, "Saved", f"Screenshot saved successfully at:\n{path}")

    def action_pin(self):
        rendered = self.canvas.render_final_image()
        if rendered:
            self.pin_requested.emit(rendered)
            self.close()

    def action_ocr(self):
        rendered = self.canvas.render_final_image()
        if not rendered:
            return
        self.status_bar.setText("Processing OCR text extraction...")
        res = extract_text_from_image(rendered)
        if len(res) == 3:
            success, text, engine_name = res
        else:
            success, text = res
            engine_name = "Auto"

        dlg = QDialog(self)
        dlg.setWindowTitle("Smart Text Extraction (OCR) - SnapMaster Pro")
        dlg.resize(580, 440)
        dlg.setStyleSheet("background-color: #0f172a; color: #ffffff;")
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setContentsMargins(18, 18, 18, 18)
        dlg_layout.setSpacing(12)

        header_row = QHBoxLayout()
        title_lbl = QLabel("Extracted Text from Screenshot:" if success else "OCR Notice:")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8;")
        header_row.addWidget(title_lbl)

        header_row.addStretch()

        engine_badge = QLabel(f"⚡ Engine: {engine_name}")
        engine_badge.setStyleSheet("background: #1e293b; color: #10b981; font-weight: bold; border-radius: 6px; padding: 3px 8px; font-size: 11px; border: 1px solid #334155;")
        header_row.addWidget(engine_badge)
        dlg_layout.addLayout(header_row)

        txt_edit = QTextEdit()
        txt_edit.setPlainText(text)
        txt_edit.setStyleSheet("background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; font-size: 13px; padding: 12px; line-height: 1.5;")
        dlg_layout.addWidget(txt_edit)

        # Counter info
        char_count = len(text)
        word_count = len(text.split())
        info_lbl = QLabel(f"Words: {word_count} | Characters: {char_count}")
        info_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        dlg_layout.addWidget(info_lbl)

        btn_row = QHBoxLayout()
        btn_copy_text = QPushButton("📋 Copy Text")
        btn_copy_text.setStyleSheet("""
            QPushButton {
                background: #38bdf8; color: #0f172a; font-weight: bold; border-radius: 6px; padding: 8px 16px;
            }
            QPushButton:hover { background: #0284c7; }
        """)
        def do_copy():
            QApplication.clipboard().setText(txt_edit.toPlainText())
            get_toast().show_message("SnapMaster Pro", "Extracted text copied to clipboard! 📋")
            btn_copy_text.setText("✅ Copied!")
        btn_copy_text.clicked.connect(do_copy)
        btn_row.addWidget(btn_copy_text)

        btn_search = QPushButton("🌐 Google Search")
        btn_search.setStyleSheet("background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        def do_search():
            q = txt_edit.toPlainText().strip()
            if q:
                url = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
                webbrowser.open(url)
        btn_search.clicked.connect(do_search)
        btn_row.addWidget(btn_search)

        btn_save_txt = QPushButton("💾 Save TXT")
        btn_save_txt.setStyleSheet("background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        def do_save_txt():
            path, _ = QFileDialog.getSaveFileName(dlg, "Save Extracted Text", "Extracted_Text.txt", "Text Files (*.txt)")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt_edit.toPlainText())
                get_toast().show_message("Saved", f"Text saved to {os.path.basename(path)}")
        btn_save_txt.clicked.connect(do_save_txt)
        btn_row.addWidget(btn_save_txt)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background: #334155; color: #ffffff; border-radius: 6px; padding: 8px 16px;")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)

        dlg_layout.addLayout(btn_row)
        dlg.exec()
