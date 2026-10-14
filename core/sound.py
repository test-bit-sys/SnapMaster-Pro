import os
import threading
from pathlib import Path
from core.config import config

try:
    import winsound
except ImportError:
    winsound = None

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SHUTTER_WAV = str(ASSETS_DIR / "shutter.wav")

def play_shutter():
    """Play camera shutter sound asynchronously if enabled in config."""
    if not config.get("play_shutter_sound", True):
        return
    if winsound and os.path.exists(SHUTTER_WAV):
        try:
            # SND_ASYNC | SND_FILENAME | SND_NODEFAULT
            winsound.PlaySound(SHUTTER_WAV, winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        except Exception as e:
            print(f"[Sound] Error playing shutter sound: {e}")
