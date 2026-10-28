from pathlib import Path
from typing import Optional, Union
import cv2
import numpy as np

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def load_image_cv(image_or_pdf_path: Union[str, Path]) -> Optional[np.ndarray]:
    """Loads an image or the first page of a PDF as a BGR OpenCV numpy array."""
    path = Path(image_or_pdf_path)
    if not path.exists():
        return None

    if path.suffix.lower() == ".pdf":
        if fitz is None:
            return None
        doc = fitz.open(str(path))
        if len(doc) == 0:
            return None
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        return cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

    return cv2.imread(str(path))


def decode_qr(image_path: Union[str, Path]) -> Optional[str]:
    """
    Decodes QR code from an image or PDF using OpenCV QRCodeDetector.
    Tries original image and several scaled / thresholded variants for robustness.
    Returns decoded text string or None if not found.
    """
    img = load_image_cv(image_path)
    if img is None:
        return None

    detector = cv2.QRCodeDetector()

    # 1. Try original image
    val, pts, _ = detector.detectAndDecode(img)
    if val and val.strip():
        return val.strip()

    # 2. Try top-right crop (where QR codes are placed on these documents)
    h, w = img.shape[:2]
    top_right_crop = img[0 : int(h * 0.4), int(w * 0.6) : w]
    val, pts, _ = detector.detectAndDecode(top_right_crop)
    if val and val.strip():
        return val.strip()

    for s in [2.0, 1.5, 0.8]:
        scaled_crop = cv2.resize(top_right_crop, (0, 0), fx=s, fy=s)
        val, pts, _ = detector.detectAndDecode(scaled_crop)
        if val and val.strip():
            return val.strip()

    # 3. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    val, pts, _ = detector.detectAndDecode(gray)
    if val and val.strip():
        return val.strip()

    # 4. Scaled variants (0.75x and 1.25x)
    for scale in [0.75, 1.25]:
        scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        val, pts, _ = detector.detectAndDecode(scaled)
        if val and val.strip():
            return val.strip()

    # 5. Adaptive / binary threshold
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    val, pts, _ = detector.detectAndDecode(thresh)
    if val and val.strip():
        return val.strip()

    return None
