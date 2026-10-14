import os
import shutil
from pathlib import Path

try:
    import pytesseract
except ImportError:
    pytesseract = None

# Common Windows install paths for Tesseract OCR
CANDIDATE_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
]

def find_tesseract():
    if not pytesseract:
        return None
    # Check if in PATH
    if shutil.which("tesseract"):
        return "tesseract"
    for p in CANDIDATE_PATHS:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return p
    return None

def is_ocr_available():
    return find_tesseract() is not None

def extract_text_from_image(pil_image, lang="eng+ara"):
    """Extracts text from PIL Image using OCR."""
    cmd = find_tesseract()
    if not cmd:
        return (
            False,
            "لم يتم العثور على محرك Tesseract OCR على النظام.\n\n"
            "لتفعيل ميزة استخراج النصوص (OCR):\n"
            "1. قم بتحميل Tesseract OCR لنظام Windows.\n"
            "2. ثبّته في المسار الافتراضي: C:\\Program Files\\Tesseract-OCR\n"
            "3. أعد تشغيل البرنامج وسيعمل التعرف على النصوص تلقائياً!"
        )
    try:
        # Try both Arabic and English or default
        try:
            text = pytesseract.image_to_string(pil_image, lang=lang)
        except Exception:
            # Fallback to default language
            text = pytesseract.image_to_string(pil_image)
        return True, text.strip()
    except Exception as e:
        return False, f"حدث خطأ أثناء معالجة الصورة عبر OCR:\n{str(e)}"
