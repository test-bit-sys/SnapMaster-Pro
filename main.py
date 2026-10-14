import sys
import os
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer

from ui.styles import DARK_THEME
from ui.main_window import MainWindow
from ui.overlay import SnippingOverlay
from ui.editor_window import EditorWindow
from ui.pin_window import PinWindow
from ui.history_dialog import HistoryDialog
from ui.settings_dialog import SettingsDialog
from ui.tray import SystemTrayManager
from core.hotkeys import hotkeys
from core.config import config
from core.history import history
from core.capture import copy_to_clipboard

class SnapMasterApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("SnapMaster Pro")
        self.app.setOrganizationName("SnapMaster")
        self.app.setStyle("Fusion")
        self.app.setStyleSheet(DARK_THEME)

        icon_path = str(BASE_DIR / "assets" / "icon.png")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))

        # Windows
        self.main_window = MainWindow()
        self.overlay = SnippingOverlay()
        self.editor = EditorWindow()
        self.tray = SystemTrayManager()
        self.pinned_windows = []

        self.connect_signals()
        self.start_services()

    def connect_signals(self):
        # Main Window
        self.main_window.request_region_capture.connect(self.start_region_capture)
        self.main_window.request_editor.connect(self.open_editor)
        self.main_window.request_pin.connect(self.create_pin_window)
        self.main_window.request_history.connect(self.open_history)
        self.main_window.request_settings.connect(self.open_settings)

        # Overlay
        self.overlay.capture_completed.connect(self.on_overlay_captured)
        self.overlay.capture_cancelled.connect(self.on_overlay_cancelled)
        self.overlay.pin_requested.connect(self.create_pin_window)

        # Editor
        self.editor.pin_requested.connect(self.create_pin_window)

        # Tray
        self.tray.sig_capture_region.connect(self.start_region_capture)
        self.tray.sig_capture_full.connect(self.main_window.trigger_fullscreen_capture)
        self.tray.sig_capture_window.connect(self.main_window.trigger_window_capture)
        self.tray.sig_open_history.connect(self.open_history)
        self.tray.sig_open_settings.connect(self.open_settings)
        self.tray.sig_open_folder.connect(self.main_window.open_screenshots_folder)
        self.tray.sig_show_main.connect(self.show_main_window)
        self.tray.sig_quit.connect(self.quit_app)

        # Global Hotkeys
        hotkeys.sig_capture_region.connect(self.start_region_capture)
        hotkeys.sig_capture_full.connect(self.main_window.trigger_fullscreen_capture)
        hotkeys.sig_capture_window.connect(self.main_window.trigger_window_capture)

    def start_services(self):
        self.tray.show()
        try:
            hotkeys.start()
        except Exception as e:
            print(f"[Hotkeys] Error initializing hotkeys: {e}")

    def show_main_window(self):
        self.main_window.showNormal()
        self.main_window.activateWindow()

    def start_region_capture(self):
        # Hide main window briefly to not capture it
        if self.main_window.isVisible():
            self.main_window.hide()
            QTimer.singleShot(200, self.overlay.start_capture)
        else:
            self.overlay.start_capture()

    def on_overlay_captured(self, pil_image):
        if not pil_image:
            return

        if config.get("auto_copy_clipboard", True):
            copy_to_clipboard(pil_image)

        if config.get("auto_save", True):
            history.save_image(pil_image)

        if config.get("open_editor_after_capture", True):
            self.open_editor(pil_image)
        else:
            self.tray.notify("SnapMaster Pro", "تم التقاط وحفظ لقطة الشاشة بنجاح!")

    def on_overlay_cancelled(self):
        # If main window was open before, restore it
        pass

    def open_editor(self, pil_image):
        self.editor.load_image(pil_image)

    def create_pin_window(self, pil_image):
        pin_win = PinWindow(pil_image)
        self.pinned_windows.append(pin_win)

    def open_history(self):
        dlg = HistoryDialog(self.main_window)
        dlg.open_in_editor.connect(self.open_editor)
        dlg.exec()

    def open_settings(self):
        dlg = SettingsDialog(self.main_window)
        dlg.exec()

    def quit_app(self):
        hotkeys.stop()
        self.app.quit()

    def run(self):
        self.main_window.show()
        return self.app.exec()

if __name__ == "__main__":
    app = SnapMasterApp()
    sys.exit(app.run())
