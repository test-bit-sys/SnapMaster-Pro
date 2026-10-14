import os
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "save_dir": str(Path.home() / "Pictures" / "Screenshots"),
    "file_format": "PNG",  # PNG, JPEG, WEBP
    "filename_pattern": "Screenshot_%Y%m%d_%H%M%S",
    "auto_copy_clipboard": True,
    "auto_save": True,
    "open_editor_after_capture": True,
    "play_shutter_sound": True,
    "minimize_to_tray": True,
    "magnifier_enabled": True,
    "magnifier_zoom": 5,
    "hotkey_region": "ctrl+shift+s",
    "hotkey_full": "ctrl+shift+f",
    "hotkey_window": "ctrl+shift+w",
    "theme": "dark"
}

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".snapmaster"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.data = DEFAULT_CONFIG.copy()
        self.load()
        # Ensure default screenshot directory exists
        try:
            Path(self.data["save_dir"]).mkdir(parents=True, exist_ok=True)
        except Exception:
            self.data["save_dir"] = str(Path.cwd() / "Screenshots")
            Path(self.data["save_dir"]).mkdir(parents=True, exist_ok=True)

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"[Config] Error loading configuration: {e}")

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving configuration: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

# Global singleton
config = ConfigManager()
