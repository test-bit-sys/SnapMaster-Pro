"""
PyInstaller Build Script for SnapMaster Pro
Generates a standalone single-file Windows executable (.exe)
"""

import os
import sys
import subprocess
from pathlib import Path

def build():
    print("=" * 60)
    print("🚀 بدء بناء تطبيق SnapMaster Pro بصيغة Windows Executable (.exe)")
    print("=" * 60)

    base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / "assets" / "icon.ico"
    shutter_path = base_dir / "assets" / "shutter.wav"
    icon_png = base_dir / "assets" / "icon.png"

    # PyInstaller command arguments
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",             # directory distribution (faster startup and reliable)
        "--windowed",           # no console window
        f"--name=SnapMasterPro",
        f"--icon={icon_path}",
        f"--add-data={base_dir / 'assets'};assets",
        f"--add-data={base_dir / 'core'};core",
        f"--add-data={base_dir / 'ui'};ui",
        "--clean",
        str(base_dir / "main.py")
    ]

    print("جاري تنفيذ أمر التجميع...")
    print(" ".join(cmd))
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✅ تم بناء البرنامج بنجاح!")
        print("المجلد الناتج: dist/SnapMasterPro/SnapMasterPro.exe")
        print("=" * 60)
    else:
        print("\n❌ حدث خطأ أثناء عملية البناء.")

if __name__ == "__main__":
    build()
