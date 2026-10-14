"""
SnapMaster Pro - Windows Autostart Manager
Configures the app to run in the background upon Windows boot via the Windows Registry.
"""

import sys
import os
from pathlib import Path

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    winreg = None
    WINREG_AVAILABLE = False

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SnapMasterPro"

def is_autostart_enabled() -> bool:
    if not WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[Autostart] Check error: {e}")
        return False

def set_autostart(enable: bool) -> bool:
    if not WINREG_AVAILABLE:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                if getattr(sys, "frozen", False):
                    # Compiled PyInstaller exe
                    cmd = f'"{sys.executable}" --minimized'
                else:
                    # Python source execution
                    main_script = Path(__file__).resolve().parent.parent / "main.py"
                    python_exe = sys.executable
                    # If pythonw.exe exists, use it for silent background boot without a console window
                    pythonw = Path(python_exe).parent / "pythonw.exe"
                    exec_path = str(pythonw) if pythonw.exists() else python_exe
                    cmd = f'"{exec_path}" "{main_script}" --minimized'

                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                return True
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
                return True
    except Exception as e:
        print(f"[Autostart] Configuration error: {e}")
        return False
