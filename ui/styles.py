"""
Modern Dark Theme Design System for SnapMaster Pro
"""

DARK_THEME = """
QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
    font-size: 13px;
}

/* Main Dashboard Card */
QFrame#DashboardCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #1e2436);
    border: 1px solid #334155;
    border-radius: 14px;
}

QFrame#DashboardCard:hover {
    border: 1px solid #38bdf8;
}

/* Action Buttons (Large) */
QPushButton#PrimaryActionButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #38bdf8);
    color: #ffffff;
    font-weight: 700;
    font-size: 14px;
    border: none;
    border-radius: 12px;
    padding: 14px 24px;
    text-align: center;
}

QPushButton#PrimaryActionButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #0284c7);
}

QPushButton#PrimaryActionButton:pressed {
    background: #4338ca;
}

/* Secondary Button */
QPushButton#SecondaryActionButton {
    background-color: #1e293b;
    color: #f1f5f9;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 18px;
}

QPushButton#SecondaryActionButton:hover {
    background-color: #334155;
    border: 1px solid #64748b;
    color: #38bdf8;
}

QPushButton#SecondaryActionButton:pressed {
    background-color: #0f172a;
}

/* Toolbar Buttons */
QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px;
    color: #cbd5e1;
}

QToolButton:hover {
    background-color: #334155;
    border: 1px solid #475569;
    color: #ffffff;
}

QToolButton:checked {
    background-color: #38bdf8;
    color: #0f172a;
    border: 1px solid #0284c7;
    font-weight: bold;
}

/* Labels */
QLabel {
    background: transparent;
}

QLabel#HeaderTitle {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
}

QLabel#HeaderSubtitle {
    font-size: 12px;
    color: #94a3b8;
}

QLabel#SectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #38bdf8;
    margin-top: 4px;
}

/* Inputs & ComboBoxes */
QLineEdit, QComboBox, QSpinBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f8fafc;
    selection-background-color: #38bdf8;
    selection-color: #0f172a;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: 1px solid #334155;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    selection-background-color: #38bdf8;
    selection-color: #0f172a;
    color: #f8fafc;
    border-radius: 6px;
    outline: none;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #334155;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #38bdf8;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #38bdf8;
    border: 2px solid #ffffff;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #f8fafc;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #1e293b;
}

QCheckBox::indicator:checked {
    background-color: #38bdf8;
    border: 1px solid #38bdf8;
    image: none;
}

/* ScrollBar */
QScrollBar:vertical {
    background: #0f172a;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #ffffff;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}

/* Dialogs */
QDialog {
    background-color: #0f172a;
}
"""
