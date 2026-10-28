import os
import re
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import numpy as np
import cv2
from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import tesserocr
    from tesserocr import PyTessBaseAPI, RIL
except ImportError:
    tesserocr = None
    PyTessBaseAPI = None
    RIL = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

PaddleOCR = None

from app.config import settings

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
TESSDATA_DIR = BACKEND_DIR / "tessdata"

TESSERACT_NOT_INSTALLED_ERROR = """
Tesseract OCR is not installed or language data is missing.
Please install Tesseract and Hindi traineddata:

Windows:
  1. Download the installer from UB-Mannheim:
     https://github.com/UB-Mannheim/tesseract/wiki
  2. Install Tesseract to 'C:\\Program Files\\Tesseract-OCR' or set TESSERACT_CMD in .env
  3. Ensure 'eng.traineddata' and 'hin.traineddata' are placed in the 'tessdata' folder.

macOS:
  brew install tesseract
  brew install tesseract-lang

Linux (Ubuntu/Debian):
  sudo apt-get update
  sudo apt-get install -y tesseract-ocr tesseract-ocr-hin
"""


@dataclass
class OcrWord:
    text: str
    conf: float
    bbox: List[int]  # [x1, y1, x2, y2]

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "conf": float(self.conf), "bbox": [int(x) for x in self.bbox]}


@dataclass
class OcrResult:
    text: str
    mean_confidence: float
    language: str  # "en", "hi", or "mixed"
    words: List[Dict[str, Any]] = field(default_factory=list)


def deskew_image(gray: np.ndarray) -> np.ndarray:
    """Estimate skew using Otsu threshold and minAreaRect and rotate image if skewed."""
    try:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return gray

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # Only deskew if significant skew (> 0.5 degrees and < 45 degrees)
        if 0.5 < abs(angle) < 45.0:
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
    except Exception:
        pass
    return gray


def preprocess_image(image_input: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
    """Pre-processing with OpenCV: grayscale, deskew, denoise, adaptive contrast/threshold.
    Keeps the original image untouched; returns a processed copy.
    """
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        if img is None:
            pil_img = Image.open(image_input)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, Image.Image):
        img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    else:
        img = image_input.copy()

    # 1. Grayscale
    if len(img.shape) == 3 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif len(img.shape) == 3 and img.shape[2] == 4:
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    else:
        gray = img.copy()

    # 2. Deskew
    deskewed = deskew_image(gray)

    # 3. Denoise
    try:
        denoised = cv2.fastNlMeansDenoising(deskewed, None, h=7, templateWindowSize=7, searchWindowSize=21)
    except Exception:
        denoised = cv2.medianBlur(deskewed, 3)

    # 4. Adaptive contrast / threshold
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # Return high-contrast enhanced image suitable for OCR
    return enhanced


def detect_script(text: str) -> str:
    """Detect dominant script per page (count Devanagari vs Latin characters).
    Returns 'en', 'hi', or 'mixed'.
    """
    devanagari_count = sum(1 for c in text if "\u0900" <= c <= "\u097f")
    latin_count = sum(1 for c in text if ("a" <= c <= "z") or ("A" <= c <= "Z"))
    total = devanagari_count + latin_count

    if total == 0:
        return "en"

    deva_ratio = devanagari_count / total
    latin_ratio = latin_count / total

    if deva_ratio >= 0.70:
        return "hi"
    elif latin_ratio >= 0.70:
        return "en"
    else:
        return "mixed"


def load_images(image_path: str) -> List[np.ndarray]:
    """Accept PNG, JPG, and PDF (convert PDF pages 1-3 to images using PyMuPDF)."""
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {image_path}")

    ext = p.suffix.lower()
    if ext == ".pdf":
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) is required to process PDF files.")
        doc = fitz.open(image_path)
        images = []
        for i, page in enumerate(doc):
            if i >= 3:
                break
            zoom = 150 / 72.0  # 150 DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            images.append(img)
        doc.close()
        return images
    else:
        img = cv2.imread(image_path)
        if img is None:
            pil_img = Image.open(image_path)
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return [img]


# Singleton instances for OCR engines
_tesserocr_api = None
_paddle_ocr_engine = None


def get_tesserocr_api() -> Optional[Any]:
    global _tesserocr_api
    if _tesserocr_api is not None:
        return _tesserocr_api
    if tesserocr is not None:
        tessdata_path = str(TESSDATA_DIR) if TESSDATA_DIR.exists() else None
        try:
            if tessdata_path:
                _tesserocr_api = PyTessBaseAPI(path=tessdata_path, lang="eng+hin")
            else:
                _tesserocr_api = PyTessBaseAPI(lang="eng+hin")
            return _tesserocr_api
        except Exception:
            try:
                if tessdata_path:
                    _tesserocr_api = PyTessBaseAPI(path=tessdata_path, lang="eng")
                else:
                    _tesserocr_api = PyTessBaseAPI(lang="eng")
                return _tesserocr_api
            except Exception:
                pass
    return None


def get_paddle_ocr_engine() -> Optional[Any]:
    global _paddle_ocr_engine
    if _paddle_ocr_engine is not None:
        return _paddle_ocr_engine
    try:
        from paddleocr import PaddleOCR
        os.environ["FLAGS_use_mkldnn"] = "0"
        _paddle_ocr_engine = PaddleOCR(
            enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        return _paddle_ocr_engine
    except Exception:
        return None


def run_ocr_page_tesserocr(processed_img: np.ndarray, api: Any) -> tuple[str, float, list[dict]]:
    pil_img = Image.fromarray(processed_img)
    api.SetImage(pil_img)
    text = api.GetUTF8Text()
    conf = float(api.MeanTextConf()) / 100.0  # scale to 0.0 - 1.0

    words = []
    api.Recognize()
    it = api.GetIterator()
    if it is not None:
        while True:
            w_text = it.GetUTF8Text(RIL.WORD)
            if w_text:
                w_conf = float(it.Confidence(RIL.WORD)) / 100.0
                bbox = list(it.BoundingBox(RIL.WORD))
                words.append({
                    "text": w_text.strip(),
                    "conf": max(0.0, min(1.0, w_conf)),
                    "bbox": bbox,
                })
            if not it.Next(RIL.WORD):
                break

    return text, max(0.0, min(1.0, conf)), words


def run_ocr_page_pytesseract(processed_img: np.ndarray) -> tuple[str, float, list[dict]]:
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    pil_img = Image.fromarray(processed_img)
    tessdata_arg = f'--tessdata-dir "{TESSDATA_DIR}"' if TESSDATA_DIR.exists() else ""
    data = pytesseract.image_to_data(
        pil_img,
        lang="eng+hin",
        output_type=pytesseract.Output.DICT,
        config=tessdata_arg,
    )

    text_parts = []
    conf_list = []
    words = []

    n_boxes = len(data["text"])
    for i in range(n_boxes):
        w_text = data["text"][i].strip()
        try:
            conf_val = float(data["conf"][i])
        except (ValueError, TypeError):
            conf_val = -1.0

        if w_text:
            text_parts.append(w_text)
            if conf_val >= 0:
                c = conf_val / 100.0
                conf_list.append(c)
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                words.append({
                    "text": w_text,
                    "conf": max(0.0, min(1.0, c)),
                    "bbox": [x, y, x + w, y + h],
                })

    mean_conf = sum(conf_list) / len(conf_list) if conf_list else 0.85
    full_text = " ".join(text_parts)
    return full_text, mean_conf, words


def run_ocr_page_paddleocr(processed_img: np.ndarray, engine: Any) -> tuple[str, float, list[dict]]:
    results = list(engine.predict(processed_img))
    if not results:
        return "", 0.0, []

    item = results[0]
    rec_texts = item.get("rec_texts", [])
    rec_scores = item.get("rec_scores", [])
    rec_boxes = item.get("rec_boxes", [])

    full_text = "\n".join(rec_texts)
    mean_conf = float(np.mean(rec_scores)) if len(rec_scores) > 0 else 0.0

    words = []
    for t, s, b in zip(rec_texts, rec_scores, rec_boxes):
        if hasattr(b, "tolist"):
            b = b.tolist()
        words.append({
            "text": str(t).strip(),
            "conf": float(s),
            "bbox": [int(x) for x in b] if isinstance(b, (list, tuple)) else [],
        })

    return full_text, max(0.0, min(1.0, mean_conf)), words


def run_ocr(image_path: str) -> OcrResult:
    """Run OCR on the given image or PDF file.
    Preprocesses with OpenCV (copy only), runs Tesseract (or PaddleOCR fallback),
    computes confidence, script detection, and words with bounding boxes.
    """
    images = load_images(image_path)
    if not images:
        return OcrResult(text="", mean_confidence=0.0, language="en", words=[])

    # Check available OCR engine
    tess_api = get_tesserocr_api()
    use_pytesseract = False
    if tess_api is None and pytesseract is not None:
        try:
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            pytesseract.get_tesseract_version()
            use_pytesseract = True
        except Exception:
            use_pytesseract = False

    paddle_engine = None
    if tess_api is None and not use_pytesseract:
        paddle_engine = get_paddle_ocr_engine()
        if paddle_engine is None:
            raise RuntimeError(TESSERACT_NOT_INSTALLED_ERROR)

    all_texts = []
    all_confs = []
    all_words = []

    for img in images:
        processed = preprocess_image(img)
        if tess_api is not None:
            page_text, page_conf, page_words = run_ocr_page_tesserocr(processed, tess_api)
        elif use_pytesseract:
            page_text, page_conf, page_words = run_ocr_page_pytesseract(processed)
        else:
            page_text, page_conf, page_words = run_ocr_page_paddleocr(processed, paddle_engine)

        all_texts.append(page_text)
        all_confs.append(page_conf)
        all_words.extend(page_words)

    combined_text = "\n\n".join(all_texts)
    mean_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0
    lang = detect_script(combined_text)

    return OcrResult(
        text=combined_text,
        mean_confidence=round(mean_conf, 4),
        language=lang,
        words=all_words,
    )
