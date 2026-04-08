"""
Preprocessor — Phase 1
For each uploaded image, generates:
  - Subject mask (rembg)
  - Dominant color palette (k-means, 5 colors)
  - Variance map (local std dev — marks high-detail regions)
  - Edge map (Canny)
All outputs cached in cache/ as {hash}_*.png / {hash}_meta.json.
"""

import hashlib
import json
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


# ── Helpers ────────────────────────────────────────────────────────────────────

def compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()[:16]


# ── Main entry point ───────────────────────────────────────────────────────────

def preprocess_image(
    image_path: Path,
    cache_dir: Path,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """
    Preprocess one image. Returns the metadata dict.
    Skips work that is already cached.
    progress_cb(step, total_steps, message) is called at each stage.
    All heavy work (rembg, cv2) runs synchronously — caller should use
    asyncio.to_thread() to avoid blocking the event loop.
    """
    image_path = Path(image_path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(exist_ok=True)

    def progress(step: int, msg: str):
        if progress_cb:
            progress_cb(step, 5, msg)

    # 1. Hash ──────────────────────────────────────────────────────────────────
    progress(0, "hashing")
    file_hash = compute_file_hash(image_path)
    meta_path = cache_dir / f"{file_hash}_meta.json"

    # Return cached result if complete
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))

    # 2. Load ──────────────────────────────────────────────────────────────────
    progress(1, "loading image")
    img_pil = Image.open(image_path).convert("RGB")
    img_np = np.array(img_pil)
    img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    width, height = img_pil.size

    # 3. Subject mask (rembg) ──────────────────────────────────────────────────
    progress(2, "generating subject mask")
    mask_path = cache_dir / f"{file_hash}_mask.png"
    has_mask = False
    subject_bbox = {"x": 0, "y": 0, "w": width, "h": height}
    try:
        from rembg import remove as rembg_remove
        rgba = rembg_remove(img_pil)
        alpha = rgba.split()[-1]  # alpha channel = subject mask
        alpha.save(mask_path)
        has_mask = True
        mask_np = np.array(alpha)
        rows = np.any(mask_np > 10, axis=1)
        cols = np.any(mask_np > 10, axis=0)
        if rows.any() and cols.any():
            rmin, rmax = int(np.where(rows)[0][0]), int(np.where(rows)[0][-1])
            cmin, cmax = int(np.where(cols)[0][0]), int(np.where(cols)[0][-1])
            subject_bbox = {"x": cmin, "y": rmin, "w": cmax - cmin, "h": rmax - rmin}
    except BaseException as e:
        # rembg failure is non-fatal (catches SystemExit from missing onnxruntime too)
        print(f"[preprocessor] rembg unavailable for {image_path.name}: {e}")
        # Fallback: GrabCut-based mask using OpenCV
        has_mask, subject_bbox = _grabcut_mask(img_cv, mask_path, width, height)

    # 4. Dominant colors (k-means) ─────────────────────────────────────────────
    progress(3, "extracting dominant colors")
    dominant_colors = _dominant_colors(img_np, n_colors=5)
    mean_color = img_np.mean(axis=(0, 1))

    # 5. Variance map ─────────────────────────────────────────────────────────
    progress(4, "computing variance map")
    variance_path = cache_dir / f"{file_hash}_variance.png"
    _compute_variance_map(img_cv, variance_path, kernel=15)

    # 6. Edge map (Canny) ──────────────────────────────────────────────────────
    progress(5, "generating edge map")
    edges_path = cache_dir / f"{file_hash}_edges.png"
    _compute_edge_map(img_cv, edges_path)

    # 7. Write metadata ────────────────────────────────────────────────────────
    meta = {
        "hash": file_hash,
        "width": width,
        "height": height,
        "dominant_colors": dominant_colors,
        "mean_color": {
            "r": int(mean_color[0]),
            "g": int(mean_color[1]),
            "b": int(mean_color[2]),
        },
        "has_mask": has_mask,
        "subject_bbox": subject_bbox,
        "mask_path": str(mask_path) if has_mask else None,
        "edges_path": str(edges_path),
        "variance_path": str(variance_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return meta


# ── Internal helpers ───────────────────────────────────────────────────────────

def _dominant_colors(img_np: np.ndarray, n_colors: int = 5) -> list:
    """K-means dominant color extraction. Returns list of {r,g,b,weight} dicts."""
    pixels = img_np.reshape(-1, 3).astype(float)
    # Subsample — 6000 pixels is plenty for color clustering
    step = max(1, len(pixels) // 6000)
    sample = pixels[::step]
    try:
        km = KMeans(n_clusters=n_colors, n_init=3, random_state=42)
        km.fit(sample)
        centers = km.cluster_centers_.astype(int)
        weights = np.bincount(km.labels_) / len(km.labels_)
        # Sort by weight descending
        order = np.argsort(-weights)
        return [
            {
                "r": int(centers[i][0]),
                "g": int(centers[i][1]),
                "b": int(centers[i][2]),
                "weight": float(weights[i]),
            }
            for i in order
        ]
    except Exception:
        mean = img_np.mean(axis=(0, 1)).astype(int)
        return [{"r": int(mean[0]), "g": int(mean[1]), "b": int(mean[2]), "weight": 1.0}]


def _grabcut_mask(img_cv: np.ndarray, out_path: Path, width: int, height: int):
    """
    Fallback subject mask using OpenCV GrabCut.
    Less accurate than rembg but requires no extra dependencies.
    Returns (has_mask, subject_bbox).
    """
    try:
        mask = np.zeros(img_cv.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        # Use a central rect as the foreground hint (covers middle 60% of image)
        margin_x = int(width * 0.2)
        margin_y = int(height * 0.2)
        rect = (margin_x, margin_y, width - 2 * margin_x, height - 2 * margin_y)
        cv2.grabCut(img_cv, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        # Pixels marked as definite/probable foreground
        fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        # Save as PNG
        cv2.imwrite(str(out_path), fg_mask)
        rows = np.any(fg_mask > 10, axis=1)
        cols = np.any(fg_mask > 10, axis=0)
        if rows.any() and cols.any():
            rmin, rmax = int(np.where(rows)[0][0]), int(np.where(rows)[0][-1])
            cmin, cmax = int(np.where(cols)[0][0]), int(np.where(cols)[0][-1])
            bbox = {"x": cmin, "y": rmin, "w": cmax - cmin, "h": rmax - rmin}
        else:
            bbox = {"x": 0, "y": 0, "w": width, "h": height}
        return True, bbox
    except Exception as e:
        print(f"[preprocessor] GrabCut fallback failed: {e}")
        return False, {"x": 0, "y": 0, "w": width, "h": height}


def _compute_variance_map(img_cv: np.ndarray, out_path: Path, kernel: int = 15):
    """Local standard deviation map — high values = high-detail regions."""
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY).astype(float)
    mean = cv2.blur(gray, (kernel, kernel))
    mean_sq = cv2.blur(gray ** 2, (kernel, kernel))
    variance = np.sqrt(np.maximum(mean_sq - mean ** 2, 0))
    v_max = variance.max()
    if v_max > 0:
        out = (variance / v_max * 255).astype(np.uint8)
    else:
        out = np.zeros_like(gray, dtype=np.uint8)
    cv2.imwrite(str(out_path), out)


def _compute_edge_map(img_cv: np.ndarray, out_path: Path):
    """Canny edge map."""
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    cv2.imwrite(str(out_path), edges)
