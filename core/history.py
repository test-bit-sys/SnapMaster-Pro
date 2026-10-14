import os
import json
import time
from datetime import datetime
from pathlib import Path
from PIL import Image
from core.config import config
from core.sound import play_shutter

class HistoryManager:
    def __init__(self):
        self.history_file = Path.home() / ".snapmaster" / "history.json"
        self.items = []
        self.load()

    def load(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
                    # Filter out non-existent files
                    self.items = [item for item in self.items if os.path.exists(item.get("path", ""))]
            except Exception as e:
                print(f"[History] Error loading history: {e}")
                self.items = []

    def save(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.items[-200:], f, indent=2, ensure_ascii=False)  # keep last 200
        except Exception as e:
            print(f"[History] Error saving history: {e}")

    def add_entry(self, file_path, width, height):
        entry = {
            "path": str(file_path),
            "filename": os.path.basename(file_path),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "width": width,
            "height": height
        }
        self.items.insert(0, entry)
        self.save()
        return entry

    def save_image(self, pil_image, custom_filename=None, folder=None):
        """Saves a PIL Image to disk according to config and logs it."""
        play_shutter()
        save_dir = Path(folder or config.get("save_dir", str(Path.home() / "Pictures" / "Screenshots")))
        save_dir.mkdir(parents=True, exist_ok=True)

        fmt = config.get("file_format", "PNG").upper()
        ext = ".png" if fmt == "PNG" else (".jpg" if fmt in ("JPEG", "JPG") else ".webp")

        if custom_filename:
            filename = custom_filename if custom_filename.endswith(ext) else f"{custom_filename}{ext}"
        else:
            pattern = config.get("filename_pattern", "Screenshot_%Y%m%d_%H%M%S")
            time_str = datetime.now().strftime(pattern)
            filename = f"{time_str}{ext}"
            
        full_path = save_dir / filename
        # Ensure unique name if exists
        counter = 1
        stem = full_path.stem
        while full_path.exists():
            full_path = save_dir / f"{stem}_{counter}{ext}"
            counter += 1

        # Convert to RGB if saving JPEG
        if fmt in ("JPEG", "JPG") and pil_image.mode in ("RGBA", "P"):
            rgb_img = Image.new("RGB", pil_image.size, (255, 255, 255))
            if pil_image.mode == "RGBA":
                rgb_img.paste(pil_image, mask=pil_image.split()[3])
            else:
                rgb_img.paste(pil_image)
            rgb_img.save(full_path, "JPEG", quality=95)
        else:
            pil_image.save(full_path, fmt)

        return self.add_entry(full_path, pil_image.width, pil_image.height)

    def delete_item(self, path):
        self.items = [i for i in self.items if i.get("path") != path]
        self.save()
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"[History] Error deleting file {path}: {e}")

    def clear(self):
        self.items = []
        self.save()

history = HistoryManager()
