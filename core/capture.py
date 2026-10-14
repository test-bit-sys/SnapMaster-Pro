import ctypes
from ctypes import wintypes
import mss
from PIL import Image, ImageGrab
import win32gui
import win32con
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice

# Ensure high DPI awareness on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def get_virtual_geometry():
    """Get total virtual screen boundaries (left, top, width, height)."""
    user32 = ctypes.windll.user32
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return x, y, w, h

def pil_to_qpixmap(pil_img):
    """Converts a PIL Image to a PyQt6 QPixmap."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)

def qpixmap_to_pil(pixmap):
    """Converts a PyQt6 QPixmap to a PIL Image."""
    qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    width = qimg.width()
    height = qimg.height()
    ptr = qimg.bits()
    ptr.setsize(height * width * 4)
    arr = bytes(ptr)
    return Image.frombuffer("RGBA", (width, height), arr, "raw", "RGBA", 0, 1)

def copy_to_clipboard(pixmap_or_pil):
    """Copies an image directly to the system clipboard."""
    if isinstance(pixmap_or_pil, Image.Image):
        pixmap = pil_to_qpixmap(pixmap_or_pil)
    else:
        pixmap = pixmap_or_pil
    clipboard = QGuiApplication.clipboard()
    if clipboard:
        clipboard.setPixmap(pixmap)

def capture_full_desktop():
    """Captures all connected monitors as one combined virtual desktop image."""
    with mss.mss() as sct:
        # Monitor 0 in mss is always the virtual bounding box for all monitors
        mon = sct.monitors[0]
        sct_img = sct.grab(mon)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img, (mon["left"], mon["top"], mon["width"], mon["height"])

def capture_primary_monitor():
    """Captures the primary monitor."""
    with mss.mss() as sct:
        mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        sct_img = sct.grab(mon)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img, (mon["left"], mon["top"], mon["width"], mon["height"])

def get_window_bounds(hwnd):
    """Gets true window bounds without invisible drop-shadow margins."""
    rect = wintypes.RECT()
    try:
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if hr == 0:
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        pass
    
    # Fallback to standard window rect
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return left, top, right - left, bottom - top
    except Exception:
        return 0, 0, 0, 0

def capture_active_window():
    """Captures the currently active foreground window."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return capture_primary_monitor()

    # Minimize our own app window effect if active
    left, top, w, h = get_window_bounds(hwnd)
    if w <= 0 or h <= 0:
        return capture_primary_monitor()

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": w, "height": h}
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img, (left, top, w, h)

def get_window_at_point(x, y):
    """Finds top-level window at given screen coordinates."""
    point = wintypes.POINT(x, y)
    hwnd = ctypes.windll.user32.WindowFromPoint(point)
    if not hwnd:
        return None, (0, 0, 0, 0), ""
    
    # Get top-level ancestor
    root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
    if root_hwnd:
        hwnd = root_hwnd
        
    title = win32gui.GetWindowText(hwnd)
    bounds = get_window_bounds(hwnd)
    return hwnd, bounds, title
