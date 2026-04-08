"""
Morpher — Phase 3
Applies geometric deformations to pre-cut RGBA stamps.

Public API:
    morph_stamp(stamp, params, seed) -> PIL.Image RGBA

Morph types:
    compress_x        — squeeze horizontally into a tall thin sliver
    stretch_x         — expand horizontally into a wide flat ribbon
    compress_y        — squeeze vertically into a flat pancake
    stretch_y         — expand vertically into a tall column
    rotate            — rotate by a seeded angle (20°–170°), canvas expands
    flip_h            — mirror horizontally
    flip_v            — mirror vertically
    diagonal_stretch  — rotate 45°, stretch one axis, rotate back → rhombus warp
    shear             — lean the image diagonally
    combined          — chain two distinct transforms at varied intensities

params:
    morph_type  : str   — one of the above, or omitted for seeded random
    intensity   : float 0.0–1.0  — how extreme the deformation (default 0.5)
"""

import math
import random
from typing import Optional

import cv2
import numpy as np
from PIL import Image


# ── Public API ─────────────────────────────────────────────────────────────────

def morph_stamp(
    stamp:  Image.Image,
    params: Optional[dict] = None,
    seed:   Optional[int]  = None,
) -> Image.Image:
    """
    Deform a pre-cut RGBA stamp. Returns RGBA PIL Image.
    """
    if params is None:
        params = {}
    if seed is None:
        seed = random.randint(0, 999_999)

    stamp     = stamp.convert("RGBA")
    intensity = float(max(0.0, min(1.0, params.get("intensity", 0.5))))

    morph_types = [
        "compress_x", "stretch_x", "compress_y", "stretch_y",
        "rotate", "flip_h", "flip_v", "diagonal_stretch", "shear", "combined",
    ]
    morph_type = params.get("morph_type") or random.Random(seed).choice(morph_types)

    return _apply(stamp, morph_type, intensity, seed)


# ── Dispatch ───────────────────────────────────────────────────────────────────

def _apply(stamp: Image.Image, morph_type: str, intensity: float, seed: int) -> Image.Image:
    if   morph_type == "compress_x":       return _scale(stamp, _compress(intensity), 1.0)
    elif morph_type == "stretch_x":        return _scale(stamp, _stretch(intensity),  1.0)
    elif morph_type == "compress_y":       return _scale(stamp, 1.0, _compress(intensity))
    elif morph_type == "stretch_y":        return _scale(stamp, 1.0, _stretch(intensity))
    elif morph_type == "rotate":           return _rotate(stamp, intensity, seed)
    elif morph_type == "flip_h":           return stamp.transpose(Image.FLIP_LEFT_RIGHT)
    elif morph_type == "flip_v":           return stamp.transpose(Image.FLIP_TOP_BOTTOM)
    elif morph_type == "diagonal_stretch": return _diagonal_stretch(stamp, intensity, seed)
    elif morph_type == "shear":            return _shear(stamp, intensity, seed)
    elif morph_type == "combined":         return _combined(stamp, intensity, seed)
    else:
        raise ValueError(f"Unknown morph_type: {morph_type!r}")


# ── Scale factor helpers ───────────────────────────────────────────────────────

def _compress(intensity: float) -> float:
    """0→1 maps scale 1.0→0.18 (very thin sliver at max)."""
    return 1.0 - intensity * 0.82

def _stretch(intensity: float) -> float:
    """0→1 maps scale 1.0→4.5 (very wide at max)."""
    return 1.0 + intensity * 3.5

def _scale(stamp: Image.Image, sx: float, sy: float) -> Image.Image:
    w, h  = stamp.size
    new_w = max(1, int(round(w * sx)))
    new_h = max(1, int(round(h * sy)))
    return stamp.resize((new_w, new_h), Image.LANCZOS)


# ── Rotate ─────────────────────────────────────────────────────────────────────

def _rotate(stamp: Image.Image, intensity: float, seed: int) -> Image.Image:
    """
    Rotate by a seeded angle. At low intensity: 20–45°. At full: up to 175°.
    Canvas expands so no content is clipped.
    """
    rng       = random.Random(seed)
    max_angle = 20.0 + intensity * 155.0          # 20° at 0 intensity, 175° at 1.0
    angle     = rng.uniform(max_angle * 0.4, max_angle) * rng.choice([-1, 1])
    return stamp.rotate(angle, expand=True, resample=Image.BICUBIC,
                        fillcolor=(0, 0, 0, 0))


# ── Diagonal stretch ───────────────────────────────────────────────────────────

def _diagonal_stretch(stamp: Image.Image, intensity: float, seed: int) -> Image.Image:
    """
    Rotate 45°, stretch one axis, rotate back. Produces a rhombus-like warp.
    """
    rng   = random.Random(seed)
    angle = rng.choice([45.0, -45.0, 30.0, -30.0, 60.0, -60.0])

    # Rotate into diagonal alignment
    rotated = stamp.rotate(angle, expand=True, resample=Image.BICUBIC,
                           fillcolor=(0, 0, 0, 0))

    # One axis stretches, the other may compress slightly
    sx = _stretch(intensity * rng.uniform(0.5, 1.0))
    sy = _compress(intensity * rng.uniform(0.2, 0.55))
    if rng.random() < 0.5:
        sx, sy = sy, sx          # swap so either axis can be the stretched one

    deformed = _scale(rotated, sx, sy)

    # Rotate back
    return deformed.rotate(-angle, expand=True, resample=Image.BICUBIC,
                           fillcolor=(0, 0, 0, 0))


# ── Irregular fragment ─────────────────────────────────────────────────────────

def _shear(stamp: Image.Image, intensity: float, seed: int) -> Image.Image:
    """
    Cuts an irregular polygon fragment out of the stamp — like a raw crop
    but with a random jagged/organic shape. Returns just that piece on a
    transparent background, cropped tight.

    intensity controls fragment size: small sliver at 0, larger chunk at 1.
    """
    rng  = random.Random(seed)
    w, h = stamp.size

    # Fragment center — wanders across the stamp so different seeds land differently
    cx = int(rng.uniform(0.2, 0.8) * w)
    cy = int(rng.uniform(0.2, 0.8) * h)

    # Base radius scales with intensity: captures 15–55% of the shorter dimension
    base_r = min(w, h) * (0.15 + intensity * 0.40)

    # 5–9 vertices at random angles, each with an independent random radius
    n_verts = rng.randint(5, 9)
    angles  = sorted(rng.uniform(0, 2 * math.pi) for _ in range(n_verts))

    pts = []
    for angle in angles:
        r = base_r * rng.uniform(0.35, 1.55)   # heavy variance → jagged edges
        x = int(np.clip(cx + r * math.cos(angle), 0, w - 1))
        y = int(np.clip(cy + r * math.sin(angle), 0, h - 1))
        pts.append([x, y])

    # Build mask
    mask     = np.zeros((h, w), dtype=np.uint8)
    pts_np   = np.array(pts, dtype=np.int32)
    cv2.fillPoly(mask, [pts_np], 255)

    # Apply mask to stamp alpha
    stamp_np         = np.array(stamp.convert("RGBA"))
    stamp_np[:, :, 3] = np.minimum(stamp_np[:, :, 3], mask)

    # Crop tight to the masked region
    rows = np.any(mask > 0, axis=1)
    cols = np.any(mask > 0, axis=0)
    if not (rows.any() and cols.any()):
        return stamp
    y1, y2 = int(np.where(rows)[0][0]),  int(np.where(rows)[0][-1])
    x1, x2 = int(np.where(cols)[0][0]),  int(np.where(cols)[0][-1])
    pad = 3
    y1 = max(0, y1 - pad);  y2 = min(h - 1, y2 + pad)
    x1 = max(0, x1 - pad);  x2 = min(w - 1, x2 + pad)

    return Image.fromarray(stamp_np[y1:y2+1, x1:x2+1], "RGBA")


# ── Combined ───────────────────────────────────────────────────────────────────

# Transforms eligible to be chained in combined (exclude combined itself and
# the trivially-identical flip pair to keep results interesting)
_CHAINABLE = [
    "compress_x", "stretch_x", "compress_y", "stretch_y",
    "rotate", "diagonal_stretch",
]

def _combined(stamp: Image.Image, intensity: float, seed: int) -> Image.Image:
    """
    Chain two distinct seeded transforms at varied intensities.
    The pair is chosen so neither is a near-identity at the given intensity,
    guaranteeing a result visually distinct from any single-transform output.
    """
    rng  = random.Random(seed)
    pair = rng.sample(_CHAINABLE, 2)

    # First transform at 65–95% of intensity, second at 45–75%
    i1 = intensity * rng.uniform(0.65, 0.95)
    i2 = intensity * rng.uniform(0.45, 0.75)

    result = _apply(stamp,  pair[0], i1, seed + 1)
    result = _apply(result, pair[1], i2, seed + 2)
    return result
