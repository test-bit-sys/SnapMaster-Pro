import os
import shutil
from pathlib import Path
from PIL import Image

# Try WinOCR (Windows 10/11 native OCR API - no external install required)
try:
    import winocr
    WINOCR_AVAILABLE = True
except Exception:
    winocr = None
    WINOCR_AVAILABLE = False

# Try PyTesseract
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False

# Common Windows install paths for Tesseract OCR
CANDIDATE_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
]

def find_tesseract():
    if not PYTESSERACT_AVAILABLE or not pytesseract:
        return None
    if shutil.which("tesseract"):
        return "tesseract"
    for p in CANDIDATE_PATHS:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return p
    return None

def is_ocr_available():
    """Checks if either WinOCR or Tesseract OCR is available."""
    return WINOCR_AVAILABLE or (find_tesseract() is not None)

def get_available_engines():
    """Returns list of available OCR engines."""
    engines = []
    if WINOCR_AVAILABLE:
        engines.append("Windows Media OCR (Native Windows API)")
    if find_tesseract():
        engines.append("Tesseract OCR")
    return engines

def extract_text_from_image(pil_image, lang="auto", engine_pref="auto"):
    """
    Extracts text from PIL Image using the best available OCR engine.
    Returns: (success: bool, text: str, engine_name: str)
    """
    if not isinstance(pil_image, Image.Image):
        return False, "Invalid image input.", "None"

    # Pre-process image: convert to RGB if palette or transparent
    img_processed = pil_image
    if img_processed.mode in ("RGBA", "LA", "P"):
        rgb_img = Image.new("RGB", img_processed.size, (255, 255, 255))
        if img_processed.mode == "RGBA":
            rgb_img.paste(img_processed, mask=img_processed.split()[3])
        else:
            rgb_img.paste(img_processed.convert("RGB"))
        img_processed = rgb_img

    # 1. Try Windows Media OCR (Zero Setup, Fast, Native)
    if WINOCR_AVAILABLE and (engine_pref in ("auto", "winocr")):
        try:
            # Try English recognition
            res_en = winocr.recognize_pil_sync(img_processed, "en")
            text_en = res_en.get("text", "").strip() if isinstance(res_en, dict) else getattr(res_en, "text", "").strip()
            
            # Try Arabic recognition
            text_ar = ""
            try:
                res_ar = winocr.recognize_pil_sync(img_processed, "ar")
                text_ar = res_ar.get("text", "").strip() if isinstance(res_ar, dict) else getattr(res_ar, "text", "").strip()
            except Exception:
                pass

            # Combine or pick best
            combined_text = ""
            if text_ar and text_en:
                # If Arabic detected significant text, prioritize or merge
                if len(text_ar) > len(text_en):
                    combined_text = f"{text_ar}\n\n[English text]:\n{text_en}"
                else:
                    combined_text = f"{text_en}\n\n[Arabic text]:\n{text_ar}"
            elif text_ar:
                combined_text = text_ar
            else:
                combined_text = text_en

            if combined_text:
                return True, combined_text, "Windows Media OCR (Native)"
        except Exception as e:
            print(f"[WinOCR] Exception during recognition: {e}")

    # 2. Try Tesseract OCR
    tess_path = find_tesseract()
    if tess_path:
        try:
            try:
                tess_text = pytesseract.image_to_string(img_processed, lang="eng+ara")
            except Exception:
                tess_text = pytesseract.image_to_string(img_processed)

            tess_clean = tess_text.strip()
            if tess_clean:
                return True, tess_clean, "Tesseract OCR"
        except Exception as e:
            print(f"[Tesseract] Exception: {e}")

    # 3. If neither produced text or available
    if not is_ocr_available():
        return (
            False,
            "No OCR engine found on this system.\n\n"
            "Please ensure winocr is installed or install Tesseract OCR to enable text extraction.",
            "None"
        )

    return False, "No recognizable text found in the selected image.", "Auto"
