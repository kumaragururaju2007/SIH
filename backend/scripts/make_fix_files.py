"""
AICTE Document Validation System - Demo Fixtures Generator for Phase C (Fix & Recheck)

Generates:
1. data/fixes/A05_corrected_land.png & .pdf (owner name matches Vanguard Educational Trust)
2. data/fixes/A05_bad_fix_land.png & .pdf (still mismatches, remaining issue)
3. data/fixes/A03_corrected_fire.png & .pdf (current, valid fire certificate)
"""

import sys
from pathlib import Path
from PIL import Image

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ROOT_DIR = BACKEND_DIR.parent
FIXES_DIR = ROOT_DIR / "data" / "fixes"
FIXES_DIR.mkdir(parents=True, exist_ok=True)

from scripts.generate_synthetic import (
    render_land_document,
    render_fire_safety_certificate,
    save_pdf_with_metadata,
)


def generate_fixes():
    print(f"Generating Phase C fix demo files in: {FIXES_DIR}")

    # 1. A05 Corrected Land Document (Owner matches Vanguard Educational Trust)
    a05_corr_data = {
        "registration_number": "LD-2021-A05-441",
        "owner_name": "Vanguard Educational Trust",
        "plot_number": "Plot No. 41/A, Sector 4",
        "area_sqm": 11500,
        "village_or_locality": "Revenue Circle, Gujarat",
        "registration_date": "2021-03-22",
    }
    img_a05_corr, _ = render_land_document(a05_corr_data, language="en", has_qr=True)
    png_a05_corr = FIXES_DIR / "A05_corrected_land.png"
    pdf_a05_corr = FIXES_DIR / "A05_corrected_land.pdf"
    img_a05_corr.save(str(png_a05_corr), "PNG")
    save_pdf_with_metadata(
        img_a05_corr,
        pdf_a05_corr,
        creator="Synthetic Authority PDF Engine",
        producer="Synthetic Issuer System",
        creation_date_str="D:20210322100000Z",
        mod_date_str="D:20210322100000Z",
    )
    print(f"  [OK] Saved {png_a05_corr.name} & {pdf_a05_corr.name}")

    # 2. A05 Bad Fix Land Document (Owner still mismatches trust: Girish Sharma)
    a05_bad_data = {
        "registration_number": "LD-2021-A05-441",
        "owner_name": "Girish Sharma",
        "plot_number": "Plot No. 41/A, Sector 4",
        "area_sqm": 11500,
        "village_or_locality": "Revenue Circle, Gujarat",
        "registration_date": "2021-03-22",
    }
    img_a05_bad, _ = render_land_document(a05_bad_data, language="en", has_qr=True)
    png_a05_bad = FIXES_DIR / "A05_bad_fix_land.png"
    pdf_a05_bad = FIXES_DIR / "A05_bad_fix_land.pdf"
    img_a05_bad.save(str(png_a05_bad), "PNG")
    save_pdf_with_metadata(
        img_a05_bad,
        pdf_a05_bad,
        creator="Synthetic Authority PDF Engine",
        producer="Synthetic Issuer System",
        creation_date_str="D:20210322100000Z",
        mod_date_str="D:20210322100000Z",
    )
    print(f"  [OK] Saved {png_a05_bad.name} & {pdf_a05_bad.name}")

    # 3. A03 Corrected Fire Safety Certificate (Valid until 2027)
    a03_corr_data = {
        "certificate_number": "FS-2025-A03-901",
        "institution_name": "National Institute of Science & Technology",
        "address": "Survey No. 42, Knowledge Park, Tamil Nadu - 400001",
        "issued_date": "2025-01-10",
        "valid_until": "2027-01-09",
        "issuing_authority": "Tamil Nadu Fire & Rescue Services Directorate",
    }
    img_a03_corr, _ = render_fire_safety_certificate(a03_corr_data, has_qr=True)
    png_a03_corr = FIXES_DIR / "A03_corrected_fire.png"
    pdf_a03_corr = FIXES_DIR / "A03_corrected_fire.pdf"
    img_a03_corr.save(str(png_a03_corr), "PNG")
    save_pdf_with_metadata(
        img_a03_corr,
        pdf_a03_corr,
        creator="Synthetic Authority PDF Engine",
        producer="Synthetic Issuer System",
        creation_date_str="D:20250110100000Z",
        mod_date_str="D:20250110100000Z",
    )
    print(f"  [OK] Saved {png_a03_corr.name} & {pdf_a03_corr.name}")


if __name__ == "__main__":
    generate_fixes()
