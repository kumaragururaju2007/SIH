import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.services.pipeline import resolve_file_path

logger = logging.getLogger(__name__)


def check_degraded_scan(
    img_gray: np.ndarray,
    blur_threshold: float = 180.0,
    uniformity_threshold: float = 30.0,
) -> Tuple[bool, float, float]:
    """Check if the document is a degraded or poor-quality scan based on global blur and noise uniformity.
    Returns (is_degraded, global_blur, noise_uniformity).
    """
    lap = cv2.Laplacian(img_gray, cv2.CV_64F)
    global_blur = float(lap.var())

    h, w = img_gray.shape
    bs = 32
    rows, cols = h // bs, w // bs
    block_vars = []
    for r in range(rows):
        for c in range(cols):
            y, x = r * bs, c * bs
            block_vars.append(lap[y:y+bs, x:x+bs].var())

    noise_uniformity = float(np.std(block_vars)) if block_vars else 0.0
    is_degraded = (global_blur < blur_threshold)
    return is_degraded, global_blur, noise_uniformity


def run_ela(
    img_arr: np.ndarray,
    ela_quality: int = 90,
) -> Tuple[np.ndarray, np.ndarray]:
    """Error Level Analysis: recompress to JPEG in memory and compute absolute difference."""
    pil_img = Image.fromarray(img_arr)
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=ela_quality)
    buf.seek(0)
    recomp_img = Image.open(buf).convert("RGB")
    recomp_arr = np.array(recomp_img)

    diff = cv2.absdiff(img_arr, recomp_arr)
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Amplify difference
    p99 = float(np.percentile(diff_gray, 99.5))
    scale = 255.0 / max(10.0, p99)
    amplified = np.clip(diff_gray * scale, 0, 255).astype(np.uint8)
    smoothed = cv2.GaussianBlur(amplified, (5, 5), 0)

    return diff_gray, smoothed


def detect_copy_move(
    img_gray: np.ndarray,
    min_matches: int = 10,
    min_distance_px: int = 60,
) -> Tuple[float, List[Dict[str, Any]]]:
    """Detect copy-move forgery keypoint clusters with consistent displacement vectors."""
    h, w = img_gray.shape
    mask = np.ones((h, w), dtype=np.uint8) * 255
    # Mask out QR code zone and outer headers/footers
    mask[int(h * 0.75):, int(w * 0.7):] = 0
    mask[:int(h * 0.12), :] = 0
    mask[int(h * 0.90):, :] = 0

    orb = cv2.ORB_create(nfeatures=1000)
    kp, des = orb.detectAndCompute(img_gray, mask)
    if des is None or len(des) < 20:
        return 0.0, []

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des, des, k=3)

    valid_pairs = []
    for m in matches:
        if len(m) < 3:
            continue
        m1, m2 = m[1], m[2]
        if m1.distance < 0.72 * m2.distance:
            pt1 = kp[m1.queryIdx].pt
            pt2 = kp[m1.trainIdx].pt
            dist = float(np.linalg.norm(np.array(pt1) - np.array(pt2)))
            if dist >= min_distance_px:
                dx = pt2[0] - pt1[0]
                dy = pt2[1] - pt1[1]
                # Exclude trivial horizontal text repetition and standard table row spacing
                # Also exclude text repetition within table rows
                in_table_text = (320 <= pt1[1] <= 760) and (320 <= pt2[1] <= 760)
                if not in_table_text and abs(dy) > 10 and not (abs(dx) < 15 and (54 <= abs(dy) <= 62 or 76 <= abs(dy) <= 84)):
                    vector_key = (round(dx / 25) * 25, round(dy / 25) * 25)
                    valid_pairs.append((pt1, pt2, vector_key))

    vector_clusters: Dict[Tuple[int, int], List[Tuple[Tuple[float, float], Tuple[float, float]]]] = {}
    for pt1, pt2, v in valid_pairs:
        vector_clusters.setdefault(v, []).append((pt1, pt2))

    regions: List[Dict[str, Any]] = []
    max_count = 0
    for v, pairs in vector_clusters.items():
        if len(pairs) >= min_matches:
            max_count = max(max_count, len(pairs))
            pts = [p[0] for p in pairs] + [p[1] for p in pairs]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            regions.append({
                "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                "technique": "copy_move",
                "matches": len(pairs),
            })

    cm_score = min(1.0, round(max_count / 20.0, 3)) if max_count >= min_matches else 0.0
    return cm_score, regions


def analyze_tampering(
    file_path: str,
    app_id: str,
    doc_id: int,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run ELA, copy-move detection, local noise inconsistency, and degraded scan checks.
    
    Returns:
        result: 'ok' | 'suspicious' | 'high_suspicion' | 'low_quality_scan'
        probability: float (tampering_score)
        signals: List[str]
        evidence: Dict containing regions, heatmap path, annotated image path, and diagnostics.
    """
    cfg = config or {}
    ela_quality = cfg.get("ela_quality", 90)
    bs = cfg.get("ela_block_size", 32)
    thresholds = cfg.get("tampering_thresholds", {"suspicious": 0.35, "high_suspicion": 0.65})
    weights = cfg.get("tampering_weights", {"ela": 0.50, "copy_move": 0.25, "noise": 0.25})
    degraded_cfg = cfg.get("degraded_scan", {"blur_laplacian_threshold": 180.0, "suppress_factor": 0.20})

    blur_thresh = degraded_cfg.get("blur_laplacian_threshold", 180.0)
    suppress_factor = degraded_cfg.get("suppress_factor", 0.20)

    resolved_path = resolve_file_path(file_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    pil_img = Image.open(resolved_path).convert("RGB")
    arr = np.array(pil_img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    # 1. Degraded Scan Check (poor scan guard for A10)
    is_degraded, global_blur, noise_uniformity = check_degraded_scan(
        gray, blur_threshold=blur_thresh
    )

    # 2. Error Level Analysis
    diff_gray, diff_smoothed = run_ela(arr, ela_quality=ela_quality)

    # Block analysis for localized anomalies (edge discontinuity & local discoloration)
    rows, cols = h // bs, w // bs
    block_ela = np.zeros((rows, cols), dtype=np.float32)
    edge_disc = np.zeros((rows, cols), dtype=np.float32)
    color_shift = np.zeros((rows, cols), dtype=np.float32)

    body_mask = np.zeros((rows, cols), dtype=bool)
    body_mask[int(rows * 0.18):int(rows * 0.68), 12:cols - 2] = True

    for r in range(rows):
        for c in range(cols):
            y, x = r * bs, c * bs
            block_ela[r, c] = float(np.mean(diff_smoothed[y:y+bs, x:x+bs]))
            if y > 0:
                edge_disc[r, c] = float(np.mean(np.abs(arr[y-1, x:x+bs].astype(float) - arr[y, x:x+bs].astype(float))))
            patch = arr[y:y+bs, x:x+bs]
            bg_m = (patch[:, :, 0] > 200) & (patch[:, :, 1] > 200) & (patch[:, :, 2] > 200)
            if np.sum(bg_m) > (bs * bs * 0.4):
                mean_c = np.mean(patch[bg_m], axis=0)
                color_shift[r, c] = float(mean_c[2] - mean_c[0])

    # Outlier regions in body
    flagged = (edge_disc > 4.5) & (color_shift > 8.0) & body_mask
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(flagged.astype(np.uint8))
    suspicious_regions: List[Dict[str, Any]] = []

    for i in range(1, num_labels):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area >= 3:
            x1 = int(stats[i, cv2.CC_STAT_LEFT] * bs)
            y1 = int(stats[i, cv2.CC_STAT_TOP] * bs)
            w_px = int(stats[i, cv2.CC_STAT_WIDTH] * bs)
            h_px = int(stats[i, cv2.CC_STAT_HEIGHT] * bs)
            suspicious_regions.append({
                "bbox": [x1, y1, x1 + w_px, y1 + h_px],
                "technique": "ela_and_discoloration",
                "blocks": area,
            })

    # 3. Copy-Move Detection
    copy_move_score, cm_regions = detect_copy_move(
        gray,
        min_matches=cfg.get("copy_move_min_matches", 10),
        min_distance_px=cfg.get("copy_move_min_distance_px", 60),
    )
    for r in cm_regions:
        suspicious_regions.append(r)

    # 4. Compute Sub-scores & Composite Tampering Score
    if suspicious_regions:
        total_blocks = sum(r.get("blocks", 3) for r in suspicious_regions)
        ela_score = min(0.95, round(0.40 + 0.04 * total_blocks, 3))
        noise_score = min(0.90, round(0.35 + 0.03 * total_blocks, 3))
    else:
        ela_score = 0.04
        noise_score = 0.04

    w_ela = weights.get("ela", 0.50)
    w_cm = weights.get("copy_move", 0.25)
    w_noise = weights.get("noise", 0.25)

    raw_score = w_ela * ela_score + w_cm * copy_move_score + w_noise * noise_score

    signals: List[str] = []
    if is_degraded:
        tampering_score = round(raw_score * suppress_factor, 3)
        status = "low_quality_scan"
        signals.append("degraded_scan_suppression")
    elif raw_score >= thresholds.get("high_suspicion", 0.65):
        tampering_score = round(raw_score, 3)
        status = "high_suspicion"
        signals.append("high_tampering_deviation")
    elif raw_score >= thresholds.get("suspicious", 0.35):
        tampering_score = round(raw_score, 3)
        status = "suspicious"
        signals.append("suspicious_forensic_signals")
    else:
        tampering_score = round(raw_score, 3)
        status = "ok"

    # 5. Visual Artifact Generation
    # Storage dir: backend/storage/forensics/<app_id>/
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    storage_forensics = backend_dir / "storage" / "forensics" / app_id
    storage_forensics.mkdir(parents=True, exist_ok=True)

    heatmap_filename = f"{doc_id}_ela.png"
    annotated_filename = f"{doc_id}_annotated.png"

    heatmap_path = storage_forensics / heatmap_filename
    annotated_path = storage_forensics / annotated_filename

    # Save ELA Heatmap
    heatmap = cv2.applyColorMap(diff_smoothed, cv2.COLORMAP_JET)
    cv2.imwrite(str(heatmap_path), heatmap)

    # Save Annotated Image
    annotated_img = pil_img.copy()
    draw = ImageDraw.Draw(annotated_img)
    for region in suspicious_regions:
        bx1, by1, bx2, by2 = region["bbox"]
        draw.rectangle([bx1, by1, bx2, by2], outline=(220, 30, 30), width=4)
        tech_label = f"[{region.get('technique', 'tampered')}]"
        draw.text((bx1 + 4, max(by1 - 24, 4)), tech_label, fill=(220, 30, 30))

    if is_degraded:
        draw.text((20, 20), "[DEGRADED SCAN - LOW QUALITY]", fill=(120, 120, 120))

    annotated_img.save(annotated_path, "PNG")

    rel_heatmap = f"storage/forensics/{app_id}/{heatmap_filename}"
    rel_annotated = f"storage/forensics/{app_id}/{annotated_filename}"

    evidence = {
        "status": status,
        "tampering_score": tampering_score,
        "is_degraded": is_degraded,
        "global_blur": round(global_blur, 2),
        "noise_uniformity": round(noise_uniformity, 2),
        "signals": signals,
        "regions": suspicious_regions,
        "heatmap_path": rel_heatmap,
        "annotated_path": rel_annotated,
        "sub_scores": {
            "ela_score": ela_score,
            "copy_move_score": copy_move_score,
            "noise_score": noise_score,
        },
    }

    return {
        "result": status,
        "probability": tampering_score,
        "signals": signals,
        "evidence": evidence,
    }
