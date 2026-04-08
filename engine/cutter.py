"""
Cutter — Phase 2
Generates cut stamps from uploaded images using four cut types:
  - silhouette : follows subject mask contour with humanized wobble
  - tear       : organic blob shape biased toward subject region
  - geometric  : hard-edged shape (rect, strip, triangle, wedge)
  - raw        : simple rectangular crop, no masking

All functions return an RGBA PIL Image (transparent background = cut-away area).
"""

import math
import random
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import opensimplex
from PIL import Image


# ── Public API ─────────────────────────────────────────────────────────────────

def cut_stamp(
    image_path: str,
    meta: dict,
    cut_type: str,
    params: Optional[dict] = None,
    seed: Optional[int] = None,
) -> Image.Image:
    """
    Cut a stamp from an image. Returns RGBA PIL Image.

    cut_type: 'silhouette' | 'tear' | 'geometric' | 'raw'
    params:   dict of cut-specific parameters (see each function below)
    seed:     random seed for reproducibility
    """
    if params is None:
        params = {}
    if seed is None:
        seed = random.randint(0, 999_999)

    img_pil = Image.open(image_path).convert("RGBA")
    img_np  = np.array(img_pil)

    if   cut_type == "silhouette": return _silhouette_cut(img_pil, img_np, meta, params, seed)
    elif cut_type == "tear":       return _tear_cut      (img_pil, img_np, meta, params, seed)
    elif cut_type == "geometric":  return _geometric_cut (img_pil, img_np, meta, params, seed)
    elif cut_type == "raw":        return _raw_crop      (img_pil, img_np, meta, params, seed)
    else:
        raise ValueError(f"Unknown cut_type: {cut_type!r}")


# ── Silhouette cut ─────────────────────────────────────────────────────────────

def _silhouette_cut(
    img_pil: Image.Image,
    img_np:  np.ndarray,
    meta:    dict,
    params:  dict,
    seed:    int,
) -> Image.Image:
    """
    Follows the subject mask contour with humanized wobble and occasional
    straight-line segments (where scissors changed direction).
    Each seed produces a distinctly different cut character.
    """
    width, height = img_pil.size
    min_dim = min(width, height)
    rng = np.random.default_rng(seed)

    # ── Load or synthesize mask ──
    mask_np = _load_mask(meta, width, height)

    # ── Find largest contour ──
    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return _raw_crop(img_pil, img_np, meta, params, seed)

    contour = max(contours, key=cv2.contourArea)
    pts = contour.reshape(-1, 2)

    # Resample to ~500 points for consistent wobble density regardless of image size
    pts = _resample_contour(pts, target_n=500)

    # ── Seeded variation in wobble character ──
    # Amplitude: from very tight to quite ragged
    amplitude = params.get("wobble_amplitude",
                           int(rng.integers(max(3, min_dim // 90), max(6, min_dim // 22) + 1)))
    # Frequency: from slow gentle waves to tight jitter
    frequency = params.get("wobble_frequency", float(rng.uniform(2.2, 9.0)))
    pts = _wobble_contour(pts, amplitude, frequency, seed)

    # Optional second wobble pass at higher frequency, lower amplitude (~40% of seeds)
    if rng.random() < 0.40:
        pts = _wobble_contour(pts, amplitude * 0.35, frequency * 2.8, seed + 77)

    # ── Straight segments — density and length vary per seed ──
    seg_prob    = float(rng.uniform(0.05, 0.22))
    seg_max_len = int(rng.integers(10, 42))
    pts = _add_straight_segments(pts, seed, prob=seg_prob, min_len=4, max_len=seg_max_len)

    # ── Render cut mask ──
    cut_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(cut_mask, [pts.astype(np.int32)], 255)

    # ── Apply mask & crop to subject bbox ──
    return _apply_mask_and_crop(img_np, cut_mask, meta, width, height, pad=amplitude * 2)


# ── Loose tear cut ─────────────────────────────────────────────────────────────

def _tear_cut(
    img_pil: Image.Image,
    img_np:  np.ndarray,
    meta:    dict,
    params:  dict,
    seed:    int,
) -> Image.Image:
    """
    Organic blob shape built in polar coordinates using opensimplex noise.
    rx and ry are modulated independently to avoid the leaf/elongation artifact.
    Center wanders by seed. Random spike perturbations add sudden jagged variation.
    """
    width, height = img_pil.size
    bbox = meta.get("subject_bbox", {"x": width // 4, "y": height // 4,
                                      "w": width // 2, "h": height // 2})

    rng = np.random.default_rng(seed)

    # Center wanders within ±18% of bbox dims
    cx_base = bbox["x"] + bbox["w"] // 2
    cy_base = bbox["y"] + bbox["h"] // 2
    cx = int(np.clip(cx_base + rng.uniform(-0.18, 0.18) * bbox["w"], 0, width  - 1))
    cy = int(np.clip(cy_base + rng.uniform(-0.18, 0.18) * bbox["h"], 0, height - 1))

    # Scale varies per seed for size diversity
    scale        = params.get("scale", float(rng.uniform(0.35, 0.65)))
    irregularity = params.get("irregularity", float(rng.uniform(0.45, 0.80)))
    base_rx = max(20, bbox["w"] * scale)
    base_ry = max(20, bbox["h"] * scale)

    # 4–7 random spike positions (sudden inward or outward jolts)
    n_spikes    = int(rng.integers(4, 8))
    spike_angles = rng.uniform(0, 2 * math.pi, n_spikes)
    spike_mags   = rng.uniform(-0.35, 0.55, n_spikes)   # negative = inward dent

    opensimplex.seed(seed)
    n_pts  = 160
    angles = np.linspace(0, 2 * math.pi, n_pts, endpoint=False)
    pts    = []

    for angle in angles:
        # Independent noise coordinates for rx and ry — breaks the leaf symmetry
        nx_r = math.cos(angle) * 1.7
        ny_r = math.sin(angle) * 1.7
        nx_x = math.cos(angle + 1.3) * 1.7   # phase-shifted for x
        ny_x = math.sin(angle + 1.3) * 1.7
        nx_y = math.cos(angle - 0.9) * 1.7   # different phase for y
        ny_y = math.sin(angle - 0.9) * 1.7

        # Base noise (two octaves)
        n1x = opensimplex.noise2(nx_x, ny_x)
        n2x = opensimplex.noise2(nx_x * 3.1 + 5, ny_x * 3.1 + 5) * 0.4
        n1y = opensimplex.noise2(nx_y + 11, ny_y + 11)
        n2y = opensimplex.noise2(nx_y * 3.1 + 13, ny_y * 3.1 + 13) * 0.4
        noise_x = (n1x + n2x) / 1.4
        noise_y = (n1y + n2y) / 1.4

        # Spike contribution: gaussian falloff around each spike angle
        spike_val = 0.0
        for sa, sm in zip(spike_angles, spike_mags):
            diff = abs(((angle - sa + math.pi) % (2 * math.pi)) - math.pi)
            spike_val += sm * math.exp(-diff * diff * 18.0)

        rx = base_rx * (1.0 + noise_x * irregularity + spike_val * 0.5)
        ry = base_ry * (1.0 + noise_y * irregularity + spike_val * 0.5)
        rx = max(2.0, rx)
        ry = max(2.0, ry)
        x  = cx + rx * math.cos(angle)
        y  = cy + ry * math.sin(angle)
        pts.append([int(np.clip(x, 0, width - 1)), int(np.clip(y, 0, height - 1))])

    pts_np = np.array(pts, dtype=np.int32)
    cut_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(cut_mask, [pts_np], 255)

    return _apply_mask_and_crop(img_np, cut_mask, meta, width, height, pad=0)


# ── Geometric cut ──────────────────────────────────────────────────────────────

def _geometric_cut(
    img_pil: Image.Image,
    img_np:  np.ndarray,
    meta:    dict,
    params:  dict,
    seed:    int,
) -> Image.Image:
    """
    Hard-edged shape imposed on the image regardless of content.
    shape: 'rect' | 'strip_h' | 'strip_v' | 'triangle' | 'wedge'
    If shape not specified, one is chosen randomly.
    """
    width, height = img_pil.size
    rng = np.random.default_rng(seed)

    shape_choices = ["rect", "strip_h", "strip_v", "triangle", "wedge"]
    shape = params.get("shape") or rng.choice(shape_choices)

    cut_mask = np.zeros((height, width), dtype=np.uint8)

    if shape == "rect":
        x = int(params.get("x", rng.integers(0, width  // 4)))
        y = int(params.get("y", rng.integers(0, height // 4)))
        w = int(params.get("w", rng.integers(width  // 3, int(width  * 0.75))))
        h = int(params.get("h", rng.integers(height // 3, int(height * 0.75))))
        pts = np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], dtype=np.int32)

    elif shape == "strip_h":
        strip_h = int(params.get("h", rng.integers(int(height * 0.06), int(height * 0.22))))
        y       = int(params.get("y", rng.integers(int(height * 0.1),  int(height * 0.75))))
        pts = np.array([[0, y], [width, y], [width, y+strip_h], [0, y+strip_h]], dtype=np.int32)

    elif shape == "strip_v":
        strip_w = int(params.get("w", rng.integers(int(width * 0.06), int(width * 0.22))))
        x       = int(params.get("x", rng.integers(int(width * 0.1),  int(width * 0.75))))
        pts = np.array([[x, 0], [x+strip_w, 0], [x+strip_w, height], [x, height]], dtype=np.int32)

    elif shape == "triangle":
        # Scalene triangle — 3 independently seeded points biased toward subject
        bbox = meta.get("subject_bbox", {"x": width // 4, "y": height // 4,
                                          "w": width // 2, "h": height // 2})
        bx, by, bw, bh = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        # Each vertex is a blend of a subject-biased position and a random image position
        # blend=0 → inside subject bbox, blend=1 → anywhere in image
        def _vertex(blend: float) -> list:
            sx = int(rng.integers(bx, bx + bw + 1))
            sy = int(rng.integers(by, by + bh + 1))
            rx_ = int(rng.integers(0, width))
            ry_ = int(rng.integers(0, height))
            return [int(sx * (1 - blend) + rx_ * blend),
                    int(sy * (1 - blend) + ry_ * blend)]
        v0 = _vertex(float(rng.uniform(0.0, 0.3)))   # near subject
        v1 = _vertex(float(rng.uniform(0.4, 0.9)))   # pulled outward
        v2 = _vertex(float(rng.uniform(0.4, 0.9)))   # pulled outward
        pts = np.array([v0, v1, v2], dtype=np.int32)

    elif shape == "wedge":
        # Pie-slice / fan — apex placed at or near an image edge or corner for drama
        edge = int(rng.integers(0, 4))  # 0=top-left, 1=top-right, 2=bottom-right, 3=bottom-left
        margin = int(min(width, height) * 0.08)
        edge_positions = [
            (rng.integers(0, width  // 3),         rng.integers(0, height // 3)),          # top-left
            (rng.integers(width * 2 // 3, width),   rng.integers(0, height // 3)),          # top-right
            (rng.integers(width * 2 // 3, width),   rng.integers(height * 2 // 3, height)), # bottom-right
            (rng.integers(0, width  // 3),          rng.integers(height * 2 // 3, height)), # bottom-left
        ]
        ep = edge_positions[edge]
        cx     = int(params.get("cx", int(ep[0])))
        cy     = int(params.get("cy", int(ep[1])))
        # Radius large enough to cut well into the image
        radius = int(params.get("radius", rng.integers(
            int(max(width, height) * 0.55), int(max(width, height) * 1.1) + 1)))
        # Sweep wider: between 60° and 200°
        sweep   = float(params.get("sweep", float(rng.uniform(math.pi * 0.33, math.pi * 1.11))))
        # Aim the fan roughly toward image center
        toward_cx = math.atan2(height // 2 - cy, width // 2 - cx)
        a_start = float(params.get("a_start", toward_cx - sweep / 2))
        n_arc   = 48
        arc_angles = np.linspace(a_start, a_start + sweep, n_arc)
        arc_pts = [[int(np.clip(cx + radius * math.cos(a), 0, width - 1)),
                    int(np.clip(cy + radius * math.sin(a), 0, height - 1))]
                   for a in arc_angles]
        pts = np.array([[cx, cy]] + arc_pts, dtype=np.int32)

    else:
        pts = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.int32)

    # Optional rotation for rect / strip shapes
    rotation = params.get("rotation")
    if rotation is not None and shape in ("rect", "strip_h", "strip_v"):
        pts = _rotate_pts(pts, rotation)

    cv2.fillPoly(cut_mask, [pts], 255)
    return _apply_mask_and_crop(img_np, cut_mask, meta, width, height, pad=0)


# ── Raw crop ───────────────────────────────────────────────────────────────────

def _raw_crop(
    img_pil: Image.Image,
    img_np:  np.ndarray,
    meta:    dict,
    params:  dict,
    seed:    int,
) -> Image.Image:
    """Simple rectangular window into the image. No mask applied."""
    width, height = img_pil.size
    rng = np.random.default_rng(seed)

    if "nx" in params:
        # Normalised coords
        x = int(params["nx"] * width)
        y = int(params["ny"] * height)
        w = int(params["nw"] * width)
        h = int(params["nh"] * height)
    else:
        x = int(params.get("x", rng.integers(0, width  // 3)))
        y = int(params.get("y", rng.integers(0, height // 3)))
        w = int(params.get("w", rng.integers(width  // 4, width  * 2 // 3)))
        h = int(params.get("h", rng.integers(height // 4, height * 2 // 3)))

    x = max(0, min(x, width  - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width  - x))
    h = max(1, min(h, height - y))

    return img_pil.crop((x, y, x + w, y + h)).convert("RGBA")


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_mask(meta: dict, width: int, height: int) -> np.ndarray:
    """Load cached subject mask, or synthesise a centre-oval fallback."""
    mask_path = meta.get("mask_path")
    if mask_path and Path(mask_path).exists():
        m = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if m is not None:
            # Threshold to clean binary mask
            _, m = cv2.threshold(m, 30, 255, cv2.THRESH_BINARY)
            return m
    # Fallback: filled ellipse covering the central 70% of the image
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(mask, (width // 2, height // 2),
                (int(width * 0.35), int(height * 0.4)), 0, 0, 360, 255, -1)
    return mask


def _resample_contour(pts: np.ndarray, target_n: int = 500) -> np.ndarray:
    """Resample contour to roughly target_n evenly-spaced points."""
    n = len(pts)
    if n < 4:
        return pts
    if n == target_n:
        return pts

    # Arc-length parameterisation
    diffs  = np.diff(pts.astype(float), axis=0)
    segs   = np.sqrt((diffs ** 2).sum(axis=1))
    cumlen = np.concatenate(([0], np.cumsum(segs)))
    total  = cumlen[-1]
    if total == 0:
        return pts

    sample_at = np.linspace(0, total, target_n, endpoint=False)
    new_pts   = np.zeros((target_n, 2))
    for i, s in enumerate(sample_at):
        idx = int(np.searchsorted(cumlen, s, side="right")) - 1
        idx = max(0, min(idx, n - 2))
        seg = segs[idx] if idx < len(segs) else 1.0
        if seg == 0:
            new_pts[i] = pts[idx]
        else:
            t = (s - cumlen[idx]) / seg
            new_pts[i] = pts[idx] * (1 - t) + pts[idx + 1] * t

    return new_pts.astype(np.int32)


def _wobble_contour(
    pts: np.ndarray,
    amplitude: float,
    frequency: float,
    seed: int,
) -> np.ndarray:
    """
    Displace each contour point along its normal by opensimplex noise.
    Uses two octaves for more natural, irregular feel.
    """
    opensimplex.seed(seed)
    n      = len(pts)
    result = pts.astype(float).copy()

    for i in range(n):
        t    = i / n
        prev = pts[(i - 1) % n].astype(float)
        nxt  = pts[(i + 1) % n].astype(float)
        tangent = nxt - prev
        length  = math.hypot(tangent[0], tangent[1])
        if length > 0:
            tangent /= length
        normal = np.array([-tangent[1], tangent[0]])

        # Two octaves
        n1 = opensimplex.noise2(t * frequency,       seed * 0.0007)
        n2 = opensimplex.noise2(t * frequency * 2.5, seed * 0.0013 + 3) * 0.45
        disp = (n1 + n2) / 1.45 * amplitude

        result[i] = pts[i] + normal * disp

    return result.astype(np.int32)


def _add_straight_segments(
    pts: np.ndarray,
    seed: int,
    prob: float = 0.12,
    min_len: int = 6,
    max_len: int = 22,
) -> np.ndarray:
    """
    Randomly replace short runs of points with linear interpolation —
    simulates the scissors snapping to a straight direction.
    """
    rng    = np.random.default_rng(seed + 1)
    result = pts.astype(float).copy()
    n      = len(pts)
    i      = 0
    while i < n:
        if rng.random() < prob:
            seg_len = int(rng.integers(min_len, max_len + 1))
            end     = min(i + seg_len, n - 1)
            p0      = pts[i].astype(float)
            p1      = pts[end].astype(float)
            for j in range(i, end + 1):
                t         = (j - i) / max(1, end - i)
                result[j] = p0 * (1 - t) + p1 * t
            i = end + 1
        else:
            i += 1
    return result.astype(np.int32)


def _apply_mask_and_crop(
    img_np:   np.ndarray,
    cut_mask: np.ndarray,
    meta:     dict,
    width:    int,
    height:   int,
    pad:      int = 0,
) -> Image.Image:
    """Apply a binary mask to the RGBA image and crop to the non-transparent area."""
    result = img_np.copy()
    # If source is RGB (3 channels), convert
    if result.shape[2] == 3:
        result = np.dstack([result, np.full(result.shape[:2], 255, dtype=np.uint8)])
    result[:, :, 3] = cut_mask

    # Crop to mask bounds + padding
    rows = np.any(cut_mask > 0, axis=1)
    cols = np.any(cut_mask > 0, axis=0)
    if not (rows.any() and cols.any()):
        return Image.fromarray(result, "RGBA")

    y1, y2 = int(np.where(rows)[0][0]),  int(np.where(rows)[0][-1])
    x1, x2 = int(np.where(cols)[0][0]),  int(np.where(cols)[0][-1])
    pad_i   = int(pad)
    y1 = max(0, y1 - pad_i);  y2 = min(height - 1, y2 + pad_i)
    x1 = max(0, x1 - pad_i);  x2 = min(width  - 1, x2 + pad_i)

    return Image.fromarray(result[y1:y2+1, x1:x2+1], "RGBA")


def _rotate_pts(pts: np.ndarray, angle: float) -> np.ndarray:
    """Rotate polygon points around their centroid."""
    cx = pts[:, 0].mean()
    cy = pts[:, 1].mean()
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rotated = np.zeros_like(pts, dtype=float)
    for i, (px, py) in enumerate(pts):
        dx, dy        = px - cx, py - cy
        rotated[i, 0] = cx + dx * cos_a - dy * sin_a
        rotated[i, 1] = cy + dx * sin_a + dy * cos_a
    return rotated.astype(np.int32)
