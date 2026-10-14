import threading
from PyQt6.QtCore import QObject, pyqtSignal
from core.config import config

try:
    import keyboard
except ImportError:
    keyboard = None

class HotkeyManager(QObject):
    sig_capture_region = pyqtSignal()
    sig_capture_full = pyqtSignal()
    sig_capture_window = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._registered_keys = []
        self._is_running = False

    def start(self):
        if not keyboard or self._is_running:
            return
        self._is_running = True
        self.reload_hotkeys()

    def reload_hotkeys(self):
        if not keyboard:
            return
        self.stop()
        self._is_running = True

        reg_hotkey = config.get("hotkey_region", "ctrl+shift+s")
        full_hotkey = config.get("hotkey_full", "ctrl+shift+f")
        win_hotkey = config.get("hotkey_window", "ctrl+shift+w")

        try:
            if reg_hotkey:
                keyboard.add_hotkey(reg_hotkey, self._on_region)
                self._registered_keys.append(reg_hotkey)
        except Exception as e:
            print(f"[Hotkey] Failed to register region hotkey ({reg_hotkey}): {e}")

        try:
            if full_hotkey:
                keyboard.add_hotkey(full_hotkey, self._on_full)
                self._registered_keys.append(full_hotkey)
        except Exception as e:
            print(f"[Hotkey] Failed to register full hotkey ({full_hotkey}): {e}")

        try:
            if win_hotkey:
                keyboard.add_hotkey(win_hotkey, self._on_window)
                self._registered_keys.append(win_hotkey)
        except Exception as e:
            print(f"[Hotkey] Failed to register window hotkey ({win_hotkey}): {e}")

    def _on_region(self):
        self.sig_capture_region.emit()

    def _on_full(self):
        self.sig_capture_full.emit()

    def _on_window(self):
        self.sig_capture_window.emit()

    def stop(self):
        if not keyboard or not self._is_running:
            return
        try:
            for k in self._registered_keys:
                try:
                    keyboard.remove_hotkey(k)
                except Exception:
                    pass
            self._registered_keys.clear()
        except Exception as e:
            print(f"[Hotkey] Error clearing hotkeys: {e}")
        self._is_running = False

hotkeys = HotkeyManager()
