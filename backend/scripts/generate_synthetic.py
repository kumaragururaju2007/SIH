import argparse
import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import qrcode
from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas import ApplicationManifest, DocumentManifest, SyntheticManifest

# Constants
PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754
DEFAULT_MIN_AREA_SQM = 10000.0
REFERENCE_SUBMISSION_DATE = "2025-06-01"

# Font Cache
_FONT_CACHE: Dict[Tuple[int, bool, bool], ImageFont.FreeTypeFont] = {}


def get_font(size: int, bold: bool = False, hindi: bool = False) -> ImageFont.FreeTypeFont:
    """Load and cache fonts for English and Devanagari Hindi."""
    key = (size, bold, hindi)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    if hindi:
        # Check bundled asset font first
        assets_font = BACKEND_DIR / "assets" / "fonts" / "NotoSansDevanagari-Regular.ttf"
        if assets_font.exists():
            try:
                font = ImageFont.truetype(str(assets_font), size)
                _FONT_CACHE[key] = font
                return font
            except Exception:
                pass

        # Check system fonts on Windows and Linux
        system_fonts = [
            r"C:\Windows\Fonts\NotoSansDevanagari-Regular.ttf",
            r"C:\Windows\Fonts\Nirmala.ttc",
            r"C:\Windows\Fonts\mangal.ttf",
            r"C:\Windows\Fonts\aparaj.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        ]
        for path in system_fonts:
            if Path(path).exists():
                try:
                    font = ImageFont.truetype(path, size)
                    _FONT_CACHE[key] = font
                    return font
                except Exception:
                    continue

        # If font not found, print warning and fall back to English
        print("WARNING: Noto Sans Devanagari font not found. Falling back to English default font.")
        return get_font(size, bold=bold, hindi=False)

    # English font
    candidates = (
        [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )

    for path in candidates:
        if Path(path).exists():
            try:
                font = ImageFont.truetype(path, size)
                _FONT_CACHE[key] = font
                return font
            except Exception:
                continue

    try:
        font = ImageFont.truetype("arial.ttf", size)
        _FONT_CACHE[key] = font
        return font
    except Exception:
        font = ImageFont.load_default()
        _FONT_CACHE[key] = font
        return font


def compute_sha256(file_path: Path) -> str:
    """Compute sha256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ---------------- Document Drawing Helpers ----------------

def draw_official_seal(draw: ImageDraw.ImageDraw, center_x: int, center_y: int, radius: int = 70, is_hindi: bool = False):
    """Draw a circular official authority stamp/seal."""
    seal_color = (165, 35, 35)  # Official deep crimson
    # Outer ring
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        outline=seal_color,
        width=3,
    )
    # Inner ring
    inner_r = radius - 8
    draw.ellipse(
        [center_x - inner_r, center_y - inner_r, center_x + inner_r, center_y + inner_r],
        outline=seal_color,
        width=1,
    )
    # Center text
    font_seal = get_font(size=14, bold=True, hindi=is_hindi)
    if is_hindi:
        t1, t2, t3 = "राजकीय मुहर", "★ अधिकृत ★", "सत्यमेव जयते"
    else:
        t1, t2, t3 = "OFFICIAL SEAL", "★ VERIFIED ★", "GOVT. APPROVED"

    bbox1 = draw.textbbox((0, 0), t1, font=font_seal)
    bbox2 = draw.textbbox((0, 0), t2, font=font_seal)
    bbox3 = draw.textbbox((0, 0), t3, font=font_seal)

    draw.text((center_x - (bbox1[2] - bbox1[0]) // 2, center_y - 28), t1, font=font_seal, fill=seal_color)
    draw.text((center_x - (bbox2[2] - bbox2[0]) // 2, center_y - 8), t2, font=font_seal, fill=seal_color)
    draw.text((center_x - (bbox3[2] - bbox3[0]) // 2, center_y + 12), t3, font=font_seal, fill=seal_color)


def draw_signature(draw: ImageDraw.ImageDraw, start_x: int, base_y: int, title: str, is_hindi: bool = False):
    """Draw an authorized officer signature line with a cursive flourish."""
    line_length = 260
    draw.line([start_x, base_y, start_x + line_length, base_y], fill=(30, 40, 60), width=2)

    # Stylized cursive signature squiggle
    curve_points = [
        (start_x + 25, base_y - 15),
        (start_x + 55, base_y - 35),
        (start_x + 85, base_y - 10),
        (start_x + 115, base_y - 45),
        (start_x + 155, base_y - 20),
        (start_x + 195, base_y - 30),
        (start_x + 235, base_y - 12),
    ]
    for i in range(len(curve_points) - 1):
        draw.line([curve_points[i], curve_points[i + 1]], fill=(15, 30, 85), width=2)

    font_sig = get_font(size=16, bold=True, hindi=is_hindi)
    label = "सक्षम प्राधिकारी (Authorized Signatory)" if is_hindi else "Authorized Signatory"
    draw.text((start_x + 35, base_y + 8), label, font=font_sig, fill=(40, 50, 70))

    font_title = get_font(size=14, bold=False, hindi=is_hindi)
    draw.text((start_x + 20, base_y + 30), title, font=font_title, fill=(70, 80, 100))


def create_base_page(
    authority: str,
    department: str,
    document_title: str,
    qr_data: Optional[str] = None,
    is_hindi: bool = False,
) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    """Render base official A4 page with header, borders, QR code, and synthetic footer."""
    image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), color=(252, 252, 254))
    draw = ImageDraw.Draw(image)

    # 1. Outer & Inner Borders
    draw.rectangle([50, 50, PAGE_WIDTH - 50, PAGE_HEIGHT - 50], outline=(25, 45, 80), width=3)
    draw.rectangle([60, 60, PAGE_WIDTH - 60, PAGE_HEIGHT - 60], outline=(190, 205, 225), width=1)

    # 2. Header
    font_auth = get_font(size=26, bold=True, hindi=is_hindi)
    font_dept = get_font(size=20, bold=False, hindi=is_hindi)
    font_title = get_font(size=24, bold=True, hindi=is_hindi)

    bbox_auth = draw.textbbox((0, 0), authority, font=font_auth)
    auth_x = (PAGE_WIDTH - (bbox_auth[2] - bbox_auth[0])) // 2
    draw.text((auth_x, 90), authority, font=font_auth, fill=(20, 35, 70))

    bbox_dept = draw.textbbox((0, 0), department, font=font_dept)
    dept_x = (PAGE_WIDTH - (bbox_dept[2] - bbox_dept[0])) // 2
    draw.text((dept_x, 130), department, font=font_dept, fill=(45, 60, 90))

    draw.line([120, 175, PAGE_WIDTH - 120, 175], fill=(180, 195, 215), width=2)

    # Title Banner Box
    title_box = [160, 200, PAGE_WIDTH - 160, 260]
    draw.rounded_rectangle(title_box, radius=8, fill=(238, 244, 252), outline=(175, 195, 225), width=1)
    bbox_title = draw.textbbox((0, 0), document_title, font=font_title)
    title_x = (PAGE_WIDTH - (bbox_title[2] - bbox_title[0])) // 2
    draw.text((title_x, 215), document_title, font=font_title, fill=(15, 30, 65))

    # 3. QR Code (Top Right)
    if qr_data:
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_img = qr_img.resize((130, 130), Image.Resampling.NEAREST)

        qr_x, qr_y = PAGE_WIDTH - 210, 80
        image.paste(qr_img, (qr_x, qr_y))
        draw.rectangle([qr_x - 3, qr_y - 3, qr_x + 133, qr_y + 133], outline=(180, 195, 215), width=1)

        font_qr = get_font(size=11, bold=True, hindi=is_hindi)
        lbl = "स्कैन सत्यापन" if is_hindi else "SCAN TO VERIFY"
        bbox_qr = draw.textbbox((0, 0), lbl, font=font_qr)
        lbl_x = qr_x + (130 - (bbox_qr[2] - bbox_qr[0])) // 2
        draw.text((lbl_x, qr_y + 136), lbl, font=font_qr, fill=(80, 95, 120))

    # 4. Mandatory Footer
    footer_text = (
        "*** SPECIMEN - SYNTHETIC DATA - NOT A VALID OFFICIAL DOCUMENT - FOR PROTOTYPE USE ONLY ***"
    )
    font_footer = get_font(size=16, bold=True, hindi=False)
    bbox_footer = draw.textbbox((0, 0), footer_text, font=font_footer)
    footer_x = (PAGE_WIDTH - (bbox_footer[2] - bbox_footer[0])) // 2
    draw.text((footer_x, PAGE_HEIGHT - 90), footer_text, font=font_footer, fill=(195, 30, 30))

    return image, draw


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    line_spacing: int = 8,
) -> int:
    """Draws multi-line text wrapped within max_width."""
    words = text.split(" ")
    lines: List[str] = []
    current_line: List[str] = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    curr_y = y
    for line in lines:
        draw.text((x, curr_y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        curr_y += max(bbox[3] - bbox[1], 22) + line_spacing
    return curr_y



def render_table_of_fields(
    draw: ImageDraw.ImageDraw,
    fields: List[Tuple[str, str, str]],  # (field_key, display_label, display_value)
    start_y: int = 330,
    is_hindi: bool = False,
) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Renders fields in an alternating-shaded official table.
    Returns a dictionary of bounding boxes for each field's value cell: {field_key: (x1, y1, x2, y2)}.
    """
    table_x1 = 110
    col_split = 460
    table_x2 = PAGE_WIDTH - 110

    font_label = get_font(size=20, bold=True, hindi=is_hindi)
    font_val = get_font(size=20, bold=False, hindi=is_hindi)

    current_y = start_y
    field_bboxes: Dict[str, Tuple[int, int, int, int]] = {}

    for idx, (field_key, label, val_text) in enumerate(fields):
        # Calculate row height based on content
        is_multiline = "\n" in val_text or len(val_text) > 48
        row_height = 80 if is_multiline else 58

        row_bg = (248, 250, 254) if idx % 2 == 0 else (255, 255, 255)
        # Background
        draw.rectangle([table_x1, current_y, table_x2, current_y + row_height], fill=row_bg, outline=(205, 215, 230), width=1)
        # Split line
        draw.line([col_split, current_y, col_split, current_y + row_height], fill=(205, 215, 230), width=1)

        # Label text
        draw.text((table_x1 + 18, current_y + 16), label, font=font_label, fill=(35, 50, 75))

        # Value text and value cell bbox
        val_x = col_split + 18
        val_y = current_y + 16
        draw.text((val_x, val_y), val_text, font=font_val, fill=(20, 25, 40))

        # Record exact bounding box of the value cell area for tampering
        field_bboxes[field_key] = (col_split + 4, current_y + 4, table_x2 - 4, current_y + row_height - 4)

        current_y += row_height

    return field_bboxes


# ---------------- Document Generators ----------------

def render_fire_safety_certificate(data: Dict[str, Any], has_qr: bool = True) -> Tuple[Image.Image, Dict[str, Tuple[int, int, int, int]]]:
    """Generate Fire Safety Certificate."""
    qr_data = (
        f"CERT:{data['certificate_number']}|AUTH:{data['issuing_authority']}|EXP:{data['valid_until']}"
        if has_qr
        else None
    )
    image, draw = create_base_page(
        authority="STATE GOVERNMENT - DEPARTMENT OF FIRE & RESCUE SERVICES",
        department="DIRECTORATE OF DISASTER MANAGEMENT & FIRE SAFETY",
        document_title="NO OBJECTION CERTIFICATE (N.O.C.) - FIRE & LIFE SAFETY",
        qr_data=qr_data,
        is_hindi=False,
    )

    fields = [
        ("certificate_number", "Certificate Number:", str(data["certificate_number"])),
        ("institution_name", "Institution / Occupier:", str(data["institution_name"])),
        ("address", "Site Address:", str(data["address"])),
        ("issued_date", "Date of Inspection / Issue:", str(data["issued_date"])),
        ("valid_until", "Valid Up To:", str(data["valid_until"])),
        ("issuing_authority", "Issuing Fire Authority:", str(data["issuing_authority"])),
    ]

    bboxes = render_table_of_fields(draw, fields, start_y=350, is_hindi=False)

    # Narrative paragraph
    font_body = get_font(size=18, bold=False, hindi=False)
    p_text = (
        "This is to certify that the institutional building premises have been inspected by the competent "
        "fire safety officers and all prescribed fire protection systems, fire extinguishers, emergency exits, "
        "and water storage hydrants comply with National Building Code (NBC) norms for educational occupancy."
    )
    draw_wrapped_text(draw, p_text, x=115, y=780, max_width=1010, font=font_body, fill=(45, 55, 75))

    # Seal and Signature
    draw_official_seal(draw, center_x=300, center_y=1380, radius=75, is_hindi=False)
    draw_signature(draw, start_x=820, base_y=1380, title=f"Chief Fire Officer / {data['issuing_authority']}", is_hindi=False)

    return image, bboxes


def render_land_document(data: Dict[str, Any], language: str = "en", has_qr: bool = True) -> Tuple[Image.Image, Dict[str, Tuple[int, int, int, int]]]:
    """Generate Land Title & Ownership Document in English or Hindi."""
    is_hindi = language == "hi"
    qr_data = f"LAND_REG:{data['registration_number']}|AREA:{data['area_sqm']}" if has_qr else None

    if is_hindi:
        authority = "महाराष्ट्र शासन - भूमि एवं राजस्व विभाग"
        department = "कार्यालय उप-पंजीयक एवं भू-अभिलेख प्रभाग"
        doc_title = "भूमि स्वत्व एवं स्वामित्व पंजीकरण प्रमाण पत्र"
        sig_title = "सक्षम प्राधिकारी / उप-पंजीयक"
        fields = [
            ("registration_number", "पंजीकरण संख्या:", str(data["registration_number"])),
            ("owner_name", "पंजीकृत स्वामी का नाम:", str(data["owner_name"])),
            ("plot_number", "भूखंड / खसरा संख्या:", str(data["plot_number"])),
            ("area_sqm", "कुल क्षेत्रफल (वर्ग मीटर):", f"{data['area_sqm']:,} वर्ग मीटर"),
            ("village_or_locality", "ग्राम / राजस्व क्षेत्र:", str(data["village_or_locality"])),
            ("registration_date", "पंजीकरण दिनांक:", str(data["registration_date"])),
        ]
        narrative = (
            "प्रमाणित किया जाता है कि उपर्युक्त वर्णित भूमि का पूर्ण एवं अविवादित स्वत्व एवं भौतिक स्वामित्व "
            "संबंधित शैक्षणिक न्यास/संस्थान के नाम पर विधिवत पंजीकृत है और भूमि किसी भी प्रकार के प्रभार से मुक्त है।"
        )
    else:
        authority = "REVENUE DEPARTMENT - LAND RECORDS & TITLE DIVISION"
        department = "OFFICE OF THE SUB-REGISTRAR OF ASSURANCES"
        doc_title = "CERTIFICATE OF LAND TITLE & PROPERTY REGISTRATION"
        sig_title = "Sub-Registrar / Competent Revenue Authority"
        fields = [
            ("registration_number", "Registration Deed No:", str(data["registration_number"])),
            ("owner_name", "Registered Owner / Entity:", str(data["owner_name"])),
            ("plot_number", "Plot / Survey Number:", str(data["plot_number"])),
            ("area_sqm", "Total Land Area (sq.m):", f"{data['area_sqm']:,} sq.m"),
            ("village_or_locality", "Locality / Revenue Circle:", str(data["village_or_locality"])),
            ("registration_date", "Deed Registration Date:", str(data["registration_date"])),
        ]
        narrative = (
            "This is to certify that the aforementioned piece and parcel of land has been registered under "
            "perpetual ownership/registered conveyance for educational campus development and is contiguous, "
            "unencumbered, and free from any legal claims or litigations."
        )

    image, draw = create_base_page(
        authority=authority,
        department=department,
        document_title=doc_title,
        qr_data=qr_data,
        is_hindi=is_hindi,
    )

    bboxes = render_table_of_fields(draw, fields, start_y=350, is_hindi=is_hindi)

    font_body = get_font(size=18, bold=False, hindi=is_hindi)
    draw_wrapped_text(draw, narrative, x=115, y=780, max_width=1010, font=font_body, fill=(45, 55, 75))

    draw_official_seal(draw, center_x=300, center_y=1380, radius=75, is_hindi=is_hindi)
    draw_signature(draw, start_x=820, base_y=1380, title=sig_title, is_hindi=is_hindi)

    return image, bboxes


def render_trust_registration(data: Dict[str, Any], has_qr: bool = True) -> Tuple[Image.Image, Dict[str, Tuple[int, int, int, int]]]:
    """Generate Public Trust Registration Certificate."""
    qr_data = f"TRUST_REG:{data['registration_number']}|TRUST:{data['trust_name']}" if has_qr else None

    image, draw = create_base_page(
        authority="GOVERNMENT OF INDIA - CHARITY COMMISSIONER OFFICE",
        department="REGISTRY OF PUBLIC TRUSTS & CHARITABLE SOCIETIES",
        document_title="CERTIFICATE OF PUBLIC CHARITABLE TRUST REGISTRATION",
        qr_data=qr_data,
        is_hindi=False,
    )

    trustees_text = ", ".join(data["trustee_names"])
    fields = [
        ("registration_number", "Trust Registration No:", str(data["registration_number"])),
        ("trust_name", "Name of the Trust:", str(data["trust_name"])),
        ("registered_date", "Registration Date:", str(data["registered_date"])),
        ("trustee_names", "Governing Trustees:", trustees_text),
        ("registered_address", "Registered Office Address:", str(data["registered_address"])),
    ]

    bboxes = render_table_of_fields(draw, fields, start_y=350, is_hindi=False)

    font_body = get_font(size=18, bold=False, hindi=False)
    p_text = (
        "It is hereby certified that the Public Educational & Charitable Trust named herein has this day been duly "
        "registered under the Public Trusts Act with non-profit educational and philanthropic objectives in force."
    )
    draw_wrapped_text(draw, p_text, x=115, y=780, max_width=1010, font=font_body, fill=(45, 55, 75))

    draw_official_seal(draw, center_x=300, center_y=1380, radius=75, is_hindi=False)
    draw_signature(draw, start_x=820, base_y=1380, title="Registrar of Public Trusts / Charity Commissioner", is_hindi=False)

    return image, bboxes


# ---------------- Tampering & Degradation ----------------

def tamper_text_region(
    image: Image.Image,
    bbox: Tuple[int, int, int, int],
    new_text: str,
    is_hindi: bool = False,
) -> Tuple[Image.Image, List[int]]:
    """
    Covers the original text and redraws new text with a slightly different font size,
    anti-aliasing, and background tone, then re-saves as JPEG at a lower quality and converts back to PNG.
    """
    img_copy = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img_copy)
    x1, y1, x2, y2 = bbox

    # 1. Fill bbox with slightly mismatched background tone (subtle discoloration)
    draw.rectangle([x1, y1, x2, y2], fill=(240, 244, 248), outline=(225, 230, 235))

    # 2. Redraw new text with slightly modified size, tone, and slight vertical offset
    font = get_font(size=23, bold=True, hindi=is_hindi)
    text_x = x1 + 14
    text_y = y1 + 14
    draw.text((text_x, text_y), new_text, font=font, fill=(10, 15, 38))

    # 3. Save patch to JPEG at lower quality (55) and paste back onto document
    patch = img_copy.crop((x1, y1, x2, y2))
    buf = io.BytesIO()
    patch.save(buf, format="JPEG", quality=55)
    buf.seek(0)
    patch_q = Image.open(buf).convert("RGB")

    tampered_img = image.copy().convert("RGB")
    tampered_img.paste(patch_q, (x1, y1))

    return tampered_img, [x1, y1, x2, y2]


def degrade_scan(image: Image.Image, angle: float = 1.8) -> Image.Image:
    """
    Simulates a poor quality scanner: small rotation, Gaussian blur, noise,
    contrast reduction, and a subtle lighting shadow gradient.
    """
    # 1. Small rotation
    rotated = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(245, 245, 242))

    # 2. Gaussian blur
    blurred = rotated.filter(ImageFilter.GaussianBlur(radius=0.85))

    # 3. Add noise
    noise = Image.effect_noise(blurred.size, 14).convert("RGB")
    noisy = Image.blend(blurred, noise, 0.04)

    # 4. Contrast & Brightness adjustment
    contrasted = ImageEnhance.Contrast(noisy).enhance(0.85)
    dimmed = ImageEnhance.Brightness(contrasted).enhance(0.96)

    # 5. Shadow gradient
    width, height = dimmed.size
    gradient = Image.new("L", (1, height))
    for y in range(height):
        val = int(255 - (y / height) * 26)  # 255 at top down to 229 at bottom
        gradient.putpixel((0, y), val)
    grad_full = gradient.resize((width, height), Image.Resampling.BILINEAR).convert("RGB")
    final_scan = ImageChops.multiply(dimmed, grad_full)

    return final_scan


def save_pdf_with_metadata(
    img: Image.Image,
    pdf_path: Path,
    creator: str,
    producer: str,
    creation_date_str: str,
    mod_date_str: str,
) -> Dict[str, str]:
    """Save PIL Image as PDF and embed Creator, Producer, CreationDate, ModDate metadata."""
    img.save(pdf_path, "PDF")
    try:
        import fitz
        doc = fitz.open(pdf_path)
        meta = {
            "creator": creator,
            "producer": producer,
            "creationDate": creation_date_str,
            "modDate": mod_date_str,
        }
        doc.set_metadata(meta)
        doc.save(pdf_path, incremental=True, encryption=0)
        doc.close()
    except Exception as e:
        print(f"Warning: could not set PDF metadata for {pdf_path}: {e}")

    return {
        "creator": creator,
        "producer": producer,
        "creationDate": creation_date_str,
        "modDate": mod_date_str,
    }


# ---------------- Contact Sheet Generator ----------------

def generate_contact_sheet(
    doc_records: List[Dict[str, Any]],
    output_path: Path,
):
    """
    Creates a master contact sheet showing one thumbnail per document,
    labelled with app_id and document type.
    """
    cols = 6
    rows = math.ceil(len(doc_records) / cols)
    thumb_w = 248
    thumb_h = 350
    header_h = 32
    cell_w = thumb_w
    cell_h = thumb_h + header_h
    pad_x = 24
    pad_y = 24
    margin = 40
    title_bar_h = 90

    total_w = margin * 2 + cols * cell_w + (cols - 1) * pad_x
    total_h = margin * 2 + title_bar_h + rows * cell_h + (rows - 1) * pad_y

    sheet = Image.new("RGB", (total_w, total_h), color=(240, 243, 248))
    draw = ImageDraw.Draw(sheet)

    # Title Bar
    draw.rectangle([margin, margin, total_w - margin, margin + title_bar_h - 15], fill=(25, 45, 80))
    title_font = get_font(size=28, bold=True)
    sub_font = get_font(size=16, bold=False)
    draw.text((margin + 25, margin + 15), "AICTE Document Validation System - Synthetic Dataset Contact Sheet", font=title_font, fill=(255, 255, 255))
    draw.text((margin + 25, margin + 50), f"Total Documents: {len(doc_records)} across 13 Applications | Deterministic Ground Truth Verification", font=sub_font, fill=(200, 215, 235))

    font_badge = get_font(size=14, bold=True)

    for idx, doc in enumerate(doc_records):
        c = idx % cols
        r = idx // cols

        x = margin + c * (cell_w + pad_x)
        y = margin + title_bar_h + r * (cell_h + pad_y)

        # Badge color based on status
        if doc.get("tampered"):
            badge_bg = (215, 55, 55)  # Red for tampered
            status_tag = "TAMPERED"
        elif doc.get("is_poor_scan"):
            badge_bg = (115, 120, 130)  # Gray for degraded
            status_tag = "POOR SCAN"
        elif doc.get("language") == "hi":
            badge_bg = (25, 135, 84)  # Green for Hindi
            status_tag = "HINDI"
        elif not doc.get("has_qr"):
            badge_bg = (220, 100, 25)  # Orange for no QR
            status_tag = "NO QR"
        else:
            badge_bg = (40, 65, 105)  # Navy for clean
            status_tag = "CLEAN"

        # Draw header bar
        draw.rectangle([x, y, x + cell_w, y + header_h], fill=badge_bg)
        caption = f"{doc['app_id']}: {doc['doc_type']} [{status_tag}]"
        draw.text((x + 6, y + 7), caption, font=font_badge, fill=(255, 255, 255))

        # Paste thumbnail
        try:
            with Image.open(doc["png_path"]) as thumb_src:
                thumb = thumb_src.resize((thumb_w, thumb_h), Image.Resampling.BILINEAR)
                sheet.paste(thumb, (x, y + header_h))
                draw.rectangle([x, y + header_h, x + thumb_w, y + cell_h], outline=(190, 200, 215), width=1)
        except Exception as e:
            draw.rectangle([x, y + header_h, x + thumb_w, y + cell_h], fill=(220, 220, 220))
            draw.text((x + 10, y + header_h + 20), f"Error loading image:\n{e}", font=font_badge, fill=(180, 0, 0))

    sheet.save(output_path, "PNG")
    print(f"Contact sheet saved to: {output_path}")


# ---------------- Synthetic Dataset Pipeline ----------------

def generate_dataset(output_dir: Path, seed: int = 42) -> SyntheticManifest:
    """
    Main generator pipeline: generates applications A01 - A13, documents (.png and .pdf),
    manifest.json, registry_mock.json, and contact_sheet.png.
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    applications_manifest: List[ApplicationManifest] = []
    registry_mock: Dict[str, Dict[str, Any]] = {
        "fire_safety_certificates": {},
        "land_records": {},
        "trust_registry": {},
    }
    all_doc_records: List[Dict[str, Any]] = []

    # 13 Application Definitions
    scenarios_def = [
        {
            "app_id": "A01",
            "institution_id": 1,
            "institution_name": "Apex Institute of Technology",
            "trust_name": "Apex Educational Foundation",
            "state": "Maharashtra",
            "scenario": "clean, all 3 documents, all consistent, English",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": [],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 12500,
            "land_owner": "Apex Educational Foundation",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A02",
            "institution_id": 2,
            "institution_name": "Horizon Institute of Engineering",
            "trust_name": "Horizon Global Trust",
            "state": "Karnataka",
            "scenario": "missing trust_registration (only 2 documents)",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "verified",
            },
            "expected_issues": ["MISSING:trust_registration"],
            "include_trust": False,
            "fire_expired": False,
            "land_area": 11200,
            "land_owner": "Horizon Global Trust",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A03",
            "institution_id": 3,
            "institution_name": "National Polytechnic College",
            "trust_name": "National Educational Society",
            "state": "Tamil Nadu",
            "scenario": "fire certificate expired (valid_until before the submission date)",
            "expected_labels": {
                "fire_safety_certificate": "needs_verification",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": ["FIRE-EXPIRY"],
            "include_trust": True,
            "fire_expired": True,  # valid_until = 2024-05-15 (submission is 2025-06-01)
            "land_area": 10500,
            "land_owner": "National Educational Society",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A04",
            "institution_id": 4,
            "institution_name": "Pinnacle Institute of Technology",
            "trust_name": "Pinnacle Knowledge Foundation",
            "state": "Maharashtra",
            "scenario": "land area below minimum (6500 sqm)",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "needs_verification",
                "trust_registration": "verified",
            },
            "expected_issues": ["LAND-AREA-MIN"],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 6500,  # below 10,000 sqm
            "land_owner": "Pinnacle Knowledge Foundation",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A05",
            "institution_id": 5,
            "institution_name": "Vanguard Academy of Technical Studies",
            "trust_name": "Vanguard Educational Trust",
            "state": "Gujarat",
            "scenario": "owner name mismatch: land owner_name is a different person from the trust's name",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "inconsistent",
                "trust_registration": "verified",
            },
            "expected_issues": ["XDOC-OWNER-TRUST"],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 11500,
            "land_owner": "Rameshwar Prasad Sharma",  # mismatch with Vanguard Educational Trust
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A06",
            "institution_id": 6,
            "institution_name": "Metro Institute of Science & Technology",
            "trust_name": "Metro Higher Education Trust",
            "state": "Maharashtra",
            "scenario": "tampered fire certificate: valid_until date edited",
            "expected_labels": {
                "fire_safety_certificate": "possible_tampering",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": ["TAMPERED:valid_until"],
            "include_trust": True,
            "fire_expired": True,  # registry has 2024-04-15
            "land_area": 10800,
            "land_owner": "Metro Higher Education Trust",
            "tamper_fire": True,  # document altered to 2026-04-15
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A07",
            "institution_id": 7,
            "institution_name": "Zenith Polytechnic Institute",
            "trust_name": "Zenith Welfare & Research Trust",
            "state": "Maharashtra",
            "scenario": "tampered land document: area_sqm digits edited upward to pass the minimum",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "possible_tampering",
                "trust_registration": "verified",
            },
            "expected_issues": ["TAMPERED:area_sqm"],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 7500,  # registry has 7500
            "land_owner": "Zenith Welfare & Research Trust",
            "tamper_fire": False,
            "tamper_land": True,  # document altered to 12,500
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A08",
            "institution_id": 8,
            "institution_name": "Beacon Engineering College",
            "trust_name": "Beacon Educational Foundation",
            "state": "Karnataka",
            "scenario": "duplicate: reuses the exact fire certificate file and certificate number from A01 for a different institution",
            "expected_labels": {
                "fire_safety_certificate": "inconsistent",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": ["DUPLICATE_OF:A01/fire_safety_certificate"],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 10500,
            "land_owner": "Beacon Educational Foundation",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": "A01",
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A09",
            "institution_id": 9,
            "institution_name": "श्री विनायक प्रौद्योगिकी संस्थान (Shri Vinayak Institute of Technology)",
            "trust_name": "श्री विनायक एजुकेशन ट्रस्ट (Shri Vinayak Education Trust)",
            "state": "Maharashtra",
            "scenario": "clean application where the land document is in Hindi",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": [],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 13000,
            "land_owner": "श्री विनायक एजुकेशन ट्रस्ट",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": True,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A10",
            "institution_id": 10,
            "institution_name": "Silver Oak Institute of Management & Technology",
            "trust_name": "Silver Oak Public Charitable Trust",
            "state": "Gujarat",
            "scenario": "clean content, but every document is a poor scan (slight rotation, blur, noise, lower contrast)",
            "expected_labels": {
                "fire_safety_certificate": "needs_verification",
                "land_document": "needs_verification",
                "trust_registration": "needs_verification",
            },
            "expected_issues": [
                "POOR_SCAN:fire_safety_certificate",
                "POOR_SCAN:land_document",
                "POOR_SCAN:trust_registration",
            ],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 11800,
            "land_owner": "Silver Oak Public Charitable Trust",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": True,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A11",
            "institution_id": 11,
            "institution_name": "Pragati Institute of Advanced Studies",
            "trust_name": "Pragati Educational & Welfare Society",
            "state": "Madhya Pradesh",
            "scenario": "multiple problems: name mismatch + expired certificate + tampered land document (to produce the highest risk)",
            "expected_labels": {
                "fire_safety_certificate": "needs_verification",
                "land_document": "possible_tampering",
                "trust_registration": "verified",
            },
            "expected_issues": [
                "XDOC-OWNER-TRUST",
                "FIRE-EXPIRY",
                "TAMPERED:area_sqm",
            ],
            "include_trust": True,
            "fire_expired": True,  # expired fire cert
            "land_area": 6000,  # below min (registry has 6000)
            "land_owner": "Vikas Narayan Murthy",  # owner mismatch
            "tamper_fire": False,
            "tamper_land": True,  # land tampered to 11000
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": False,
        },
        {
            "app_id": "A12",
            "institution_id": 12,
            "institution_name": "Sai Institute of Technology",
            "trust_name": "Shri Sai Education Trust",
            "state": "Maharashtra",
            "scenario": "minor name variation that should NOT be a conflict (e.g. 'Shri Sai Education Trust' vs 'Sri Sai Education Trust' and 'Shree Sai Educational Trust')",
            "expected_labels": {
                "fire_safety_certificate": "verified",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": [],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 12000,
            "land_owner": "Shree Sai Educational Trust",  # benign phonetic variant
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": True,
            "no_qr_fire": False,
        },
        {
            "app_id": "A13",
            "institution_id": 13,
            "institution_name": "Heritage Institute of Technology",
            "trust_name": "Heritage Educational Mission",
            "state": "Karnataka",
            "scenario": "fire certificate with no QR code (clean otherwise, absent from registry)",
            "expected_labels": {
                "fire_safety_certificate": "needs_verification",
                "land_document": "verified",
                "trust_registration": "verified",
            },
            "expected_issues": [
                "MISSING_QR:fire_safety_certificate",
                "REGISTRY_UNAVAILABLE:fire_safety_certificate",
            ],
            "include_trust": True,
            "fire_expired": False,
            "land_area": 10800,
            "land_owner": "Heritage Educational Mission",
            "tamper_fire": False,
            "tamper_land": False,
            "duplicate_fire_from": None,
            "land_hindi": False,
            "poor_scan": False,
            "name_variation": False,
            "no_qr_fire": True,  # has_qr = False, absent from registry
        },
    ]

    saved_doc_paths: Dict[str, Dict[str, Path]] = {}
    saved_doc_metadata: Dict[str, Dict[str, Dict[str, str]]] = {}

    for sc in scenarios_def:
        app_id = sc["app_id"]
        app_folder = output_dir / app_id
        app_folder.mkdir(parents=True, exist_ok=True)
        saved_doc_paths[app_id] = {}
        saved_doc_metadata[app_id] = {}

        docs_manifest: List[DocumentManifest] = []

        # ==================== 1. Fire Safety Certificate ====================
        fire_cert_no = f"FS-2024-{app_id}-901"
        fire_issued = "2024-04-16"
        # If expired (A03, A06, A11) -> valid_until = 2024-04-15 (prior to submission date 2025-06-01)
        # If clean -> valid_until = 2026-04-15
        fire_valid = "2024-04-15" if sc["fire_expired"] else "2026-04-15"
        fire_auth = f"{sc['state']} Fire & Rescue Services Directorate"

        fire_fields = {
            "certificate_number": fire_cert_no,
            "institution_name": sc["institution_name"],
            "address": f"Survey No. 42, Knowledge Park, {sc['state']} - 400001",
            "issued_date": fire_issued,
            "valid_until": fire_valid,
            "issuing_authority": fire_auth,
        }

        fire_png = app_folder / "fire_safety_certificate.png"
        fire_pdf = app_folder / "fire_safety_certificate.pdf"

        tampered_fire = False
        tampered_fire_bbox: Optional[List[int]] = None

        if sc["duplicate_fire_from"]:
            # A08: Reuse exact file from A01
            src_png = saved_doc_paths[sc["duplicate_fire_from"]]["fire_safety_certificate_png"]
            src_pdf = saved_doc_paths[sc["duplicate_fire_from"]]["fire_safety_certificate_pdf"]
            shutil.copyfile(src_png, fire_png)
            shutil.copyfile(src_pdf, fire_pdf)
            fire_meta = dict(saved_doc_metadata[sc["duplicate_fire_from"]]["fire_safety_certificate"])
            # Re-read field values from A01 for manifest accuracy
            fire_fields = {
                "certificate_number": f"FS-2024-{sc['duplicate_fire_from']}-901",
                "institution_name": "Apex Institute of Technology",
                "address": "Survey No. 42, Knowledge Park, Maharashtra - 400001",
                "issued_date": "2024-04-16",
                "valid_until": "2026-04-15",
                "issuing_authority": "Maharashtra Fire & Rescue Services Directorate",
            }
        else:
            fire_img, fire_bboxes = render_fire_safety_certificate(
                fire_fields, has_qr=not sc["no_qr_fire"]
            )

            if sc["tamper_fire"]:
                # A06: Tamper valid_until from 2024-04-15 to 2026-04-15
                tampered_text = "2026-04-15"
                fire_img, tampered_fire_bbox = tamper_text_region(
                    fire_img, fire_bboxes["valid_until"], tampered_text, is_hindi=False
                )
                tampered_fire = True
                fire_fields["valid_until_displayed"] = tampered_text

            if sc["poor_scan"]:
                fire_img = degrade_scan(fire_img, angle=1.7)

            fire_img.save(fire_png, "PNG")

            if tampered_fire:
                fire_meta = save_pdf_with_metadata(
                    fire_img,
                    fire_pdf,
                    creator="Adobe Photoshop 24.1 (Windows)",
                    producer="Adobe Photoshop 24.1 (Windows)",
                    creation_date_str="D:20240416100000Z",
                    mod_date_str="D:20240521153000Z",
                )
            else:
                fire_meta = save_pdf_with_metadata(
                    fire_img,
                    fire_pdf,
                    creator="Synthetic Authority PDF Engine",
                    producer="Synthetic Issuer System",
                    creation_date_str="D:20240416100000Z",
                    mod_date_str="D:20240416100000Z",
                )

        saved_doc_paths[app_id]["fire_safety_certificate_png"] = fire_png
        saved_doc_paths[app_id]["fire_safety_certificate_pdf"] = fire_pdf
        saved_doc_metadata[app_id]["fire_safety_certificate"] = fire_meta

        # Mock Registry entry for Fire Certificate (A13 is omitted)
        if not sc["no_qr_fire"] and not sc["duplicate_fire_from"]:
            registry_mock["fire_safety_certificates"][fire_cert_no] = {
                "certificate_number": fire_cert_no,
                "institution_name": sc["institution_name"],
                "valid_until": fire_valid,  # Original ground truth date in registry
                "issuing_authority": fire_auth,
                "status": "expired" if sc["fire_expired"] else "valid",
            }

        fire_sha256 = compute_sha256(fire_png)
        docs_manifest.append(
            DocumentManifest(
                doc_type="fire_safety_certificate",
                file_path_png=str(fire_png.relative_to(output_dir.parent.parent)),
                file_path_pdf=str(fire_pdf.relative_to(output_dir.parent.parent)),
                fields=fire_fields,
                language="en",
                has_qr=not sc["no_qr_fire"],
                tampered=tampered_fire,
                tampered_bbox=tampered_fire_bbox,
                sha256=fire_sha256,
                metadata=fire_meta,
            )
        )
        all_doc_records.append({
            "app_id": app_id,
            "doc_type": "fire_safety_certificate",
            "png_path": fire_png,
            "tampered": tampered_fire,
            "is_poor_scan": sc["poor_scan"],
            "language": "en",
            "has_qr": not sc["no_qr_fire"],
        })

        # ==================== 2. Land Document ====================
        land_reg_no = f"LD-2021-{app_id}-441"
        land_plot = f"Plot No. {random.randint(10, 99)}/A, Sector 4"
        land_locality = "Navi Mumbai, Thane" if sc["state"] == "Maharashtra" else f"Revenue Circle, {sc['state']}"
        land_date = "2021-03-22"

        land_fields = {
            "registration_number": land_reg_no,
            "owner_name": sc["land_owner"],
            "plot_number": land_plot,
            "area_sqm": sc["land_area"],
            "village_or_locality": land_locality,
            "registration_date": land_date,
        }

        land_lang = "hi" if sc["land_hindi"] else "en"
        land_img, land_bboxes = render_land_document(land_fields, language=land_lang, has_qr=True)

        tampered_land = False
        tampered_land_bbox: Optional[List[int]] = None

        if sc["tamper_land"]:
            # A07: Tamper area_sqm upward to pass minimum (e.g. 12,500 sq.m)
            tampered_text = "12,500 sq.m" if not sc["land_hindi"] else "१२,५०० वर्ग मीटर"
            if app_id == "A11":
                tampered_text = "11,000 sq.m"
            land_img, tampered_land_bbox = tamper_text_region(
                land_img, land_bboxes["area_sqm"], tampered_text, is_hindi=sc["land_hindi"]
            )
            tampered_land = True
            land_fields["area_sqm_displayed"] = 11000 if app_id == "A11" else 12500

        if sc["poor_scan"]:
            land_img = degrade_scan(land_img, angle=-1.9)

        land_png = app_folder / "land_document.png"
        land_pdf = app_folder / "land_document.pdf"
        land_img.save(land_png, "PNG")

        if tampered_land:
            land_meta = save_pdf_with_metadata(
                land_img,
                land_pdf,
                creator="Adobe Photoshop 24.1 (Windows)",
                producer="Adobe Photoshop 24.1 (Windows)",
                creation_date_str="D:20210322100000Z",
                mod_date_str="D:20210426164500Z",
            )
        else:
            land_meta = save_pdf_with_metadata(
                land_img,
                land_pdf,
                creator="Synthetic Authority PDF Engine",
                producer="Synthetic Issuer System",
                creation_date_str="D:20210322100000Z",
                mod_date_str="D:20210322100000Z",
            )

        saved_doc_paths[app_id]["land_document_png"] = land_png
        saved_doc_paths[app_id]["land_document_pdf"] = land_pdf
        saved_doc_metadata[app_id]["land_document"] = land_meta

        # Mock Registry entry for Land Record (contains true original un-tampered area)
        registry_mock["land_records"][land_reg_no] = {
            "registration_number": land_reg_no,
            "owner_name": sc["land_owner"],
            "plot_number": land_plot,
            "area_sqm": sc["land_area"],  # True original area in registry
            "village_or_locality": land_locality,
            "registration_date": land_date,
            "status": "registered",
        }

        land_sha256 = compute_sha256(land_png)
        docs_manifest.append(
            DocumentManifest(
                doc_type="land_document",
                file_path_png=str(land_png.relative_to(output_dir.parent.parent)),
                file_path_pdf=str(land_pdf.relative_to(output_dir.parent.parent)),
                fields=land_fields,
                language=land_lang,
                has_qr=True,
                tampered=tampered_land,
                tampered_bbox=tampered_land_bbox,
                sha256=land_sha256,
                metadata=land_meta,
            )
        )
        all_doc_records.append({
            "app_id": app_id,
            "doc_type": "land_document",
            "png_path": land_png,
            "tampered": tampered_land,
            "is_poor_scan": sc["poor_scan"],
            "language": land_lang,
            "has_qr": True,
        })

        # ==================== 3. Trust Registration (Optional for A02) ====================
        if sc["include_trust"]:
            trust_reg_no = f"TR-2016-{app_id}-702"
            trustees = ["Dr. Arvind Sharma", "Meena K. Patel", "Suresh Rao"]
            trust_address = f"Corporate Suite 301, Trust Bhavan, {sc['state']} - 400021"
            trust_date = "2016-11-14"

            # A12 uses minor name variation (e.g. "Shri Sai Education Trust" on trust reg)
            trust_name_val = sc["trust_name"]

            trust_fields = {
                "registration_number": trust_reg_no,
                "trust_name": trust_name_val,
                "registered_date": trust_date,
                "trustee_names": trustees,
                "registered_address": trust_address,
            }

            trust_img, _ = render_trust_registration(trust_fields, has_qr=True)

            if sc["poor_scan"]:
                trust_img = degrade_scan(trust_img, angle=2.1)

            trust_png = app_folder / "trust_registration.png"
            trust_pdf = app_folder / "trust_registration.pdf"
            trust_img.save(trust_png, "PNG")

            trust_meta = save_pdf_with_metadata(
                trust_img,
                trust_pdf,
                creator="Synthetic Authority PDF Engine",
                producer="Synthetic Issuer System",
                creation_date_str="D:20161114100000Z",
                mod_date_str="D:20161114100000Z",
            )

            saved_doc_paths[app_id]["trust_registration_png"] = trust_png
            saved_doc_paths[app_id]["trust_registration_pdf"] = trust_pdf
            saved_doc_metadata[app_id]["trust_registration"] = trust_meta

            # Mock Registry entry for Trust Record
            registry_mock["trust_registry"][trust_reg_no] = {
                "registration_number": trust_reg_no,
                "trust_name": trust_name_val,
                "registered_date": trust_date,
                "registered_address": trust_address,
                "trustee_names": trustees,
                "status": "active",
            }

            trust_sha256 = compute_sha256(trust_png)
            docs_manifest.append(
                DocumentManifest(
                    doc_type="trust_registration",
                    file_path_png=str(trust_png.relative_to(output_dir.parent.parent)),
                    file_path_pdf=str(trust_pdf.relative_to(output_dir.parent.parent)),
                    fields=trust_fields,
                    language="en",
                    has_qr=True,
                    tampered=False,
                    tampered_bbox=None,
                    sha256=trust_sha256,
                    metadata=trust_meta,
                )
            )
            all_doc_records.append({
                "app_id": app_id,
                "doc_type": "trust_registration",
                "png_path": trust_png,
                "tampered": False,
                "is_poor_scan": sc["poor_scan"],
                "language": "en",
                "has_qr": True,
            })

        # Assemble ApplicationManifest
        app_manifest = ApplicationManifest(
            app_id=app_id,
            institution_name=sc["institution_name"],
            institution_id=sc["institution_id"],
            application_type="new_institution",
            submission_date=REFERENCE_SUBMISSION_DATE,
            min_area_sqm=DEFAULT_MIN_AREA_SQM,
            scenario=sc["scenario"],
            expected_labels=sc["expected_labels"],
            expected_issues=sc["expected_issues"],
            documents=docs_manifest,
        )
        applications_manifest.append(app_manifest)

    # Assemble and validate master synthetic manifest
    manifest_data = SyntheticManifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        seed=seed,
        min_area_sqm_norm=DEFAULT_MIN_AREA_SQM,
        applications=applications_manifest,
    )

    # Save manifest.json
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_data.model_dump_json(indent=2))
    print(f"Manifest written to: {manifest_path}")

    # Save registry_mock.json
    registry_path = output_dir / "registry_mock.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_mock, f, indent=2, ensure_ascii=False)
    print(f"Registry mock written to: {registry_path}")

    # Generate master contact sheet
    contact_sheet_path = output_dir / "contact_sheet.png"
    generate_contact_sheet(all_doc_records, contact_sheet_path)

    return manifest_data


def main():
    parser = argparse.ArgumentParser(description="AICTE Document Validation System - Synthetic Data Generator")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic output (default: 42)")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Target output directory (default: <workspace>/data/synthetic)",
    )
    args = parser.parse_args()

    if args.output_dir:
        target_dir = Path(args.output_dir).resolve()
    else:
        # Default to data/synthetic at project root
        target_dir = (BACKEND_DIR.parent / "data" / "synthetic").resolve()

    print(f"Generating synthetic dataset with seed={args.seed} into {target_dir}...")
    manifest = generate_dataset(output_dir=target_dir, seed=args.seed)
    total_docs = sum(len(app.documents) for app in manifest.applications)
    print("=" * 60)
    print(f"SUCCESS: Generated {len(manifest.applications)} applications and {total_docs} documents.")
    print("=" * 60)


if __name__ == "__main__":
    main()
