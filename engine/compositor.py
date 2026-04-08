"""
Compositor — Phase 4
Orchestrates the full collage pipeline: rules → role assignment → cut →
morph → place → composite into a single PIL RGB Image.

Public API:
    compose(image_pool, sliders, seed, canvas_w, canvas_h) -> PIL.Image RGB
"""

import math
import random
from typing import List, Optional

import numpy as np
from PIL import Image

from engine import rules, placer
from engine.cutter  import cut_stamp
from engine.morpher import morph_stamp


# ── Public API — defined after helpers below ───────────────────────────────────


# ── Role list builder ──────────────────────────────────────────────────────────

def _build_role_list(image_pool: list, spec: dict, rng: random.Random) -> list:
    """
    Create one entry per stamp. Each entry carries role, source_idx,
    and (pre-set) cut_type/cut_params if role dictates it.
    """
    role_list = []
    n_images  = len(image_pool)
    rc        = spec["role_counts"]

    # Background (optional)
    if spec["bg_type"] == "photo":
        role_list.append({
            "role":       "background",
            "source_idx": rng.randint(0, n_images - 1),
            "cut_type":   "raw",
            "cut_params": {},
            "morph_type": None,
        })

    # Dominant
    for _ in range(rc["dominant"]):
        role_list.append({
            "role":       "dominant",
            "source_idx": rng.randint(0, n_images - 1),
            "cut_type":   None,
            "cut_params": {},
            "morph_type": None,
        })

    # Supporting
    for _ in range(rc["supporting"]):
        role_list.append({
            "role":       "supporting",
            "source_idx": rng.randint(0, n_images - 1),
            "cut_type":   None,
            "cut_params": {},
            "morph_type": None,
        })

    # Detail
    for _ in range(rc["detail"]):
        role_list.append({
            "role":       "detail",
            "source_idx": rng.randint(0, n_images - 1),
            "cut_type":   None,
            "cut_params": {},
            "morph_type": None,
        })

    # Strips
    for i in range(rc["strip"]):
        shape = "strip_h" if i % 2 == 0 else "strip_v"
        role_list.append({
            "role":       "strip",
            "source_idx": rng.randint(0, n_images - 1),
            "cut_type":   "geometric",
            "cut_params": {"shape": shape},
            "morph_type": None,
        })

    return role_list


# ── Background ─────────────────────────────────────────────────────────────────

def _make_background(
    image_pool: list,
    spec:       dict,
    canvas_w:   int,
    canvas_h:   int,
    rng:        random.Random,
) -> Image.Image:
    """Create the base canvas (RGBA so we can alpha-composite stamps onto it)."""
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (20, 18, 16, 255))

    if spec["bg_type"] == "color":
        # Sample a dominant color from a random pool image
        entry = rng.choice(image_pool)
        colors = entry["meta"].get("dominant_colors", [])
        if colors:
            c = rng.choice(colors[:3])
            # Darken slightly for better contrast
            r = max(0, int(c["r"] * 0.55))
            g = max(0, int(c["g"] * 0.55))
            b = max(0, int(c["b"] * 0.55))
            canvas.paste(Image.new("RGBA", (canvas_w, canvas_h), (r, g, b, 255)))

    elif spec["bg_type"] == "photo":
        # Full-bleed photo background — composited at z_order 0 by _paste_stamp
        pass

    # bg_type == "none": leave dark canvas

    return canvas



def _paste_stamp_from_entry(
    canvas:      Image.Image,
    p:           dict,
    image_entry: dict,
    spec:        dict,
    stamp_seed:  int,
    canvas_w:    int,
    canvas_h:    int,
) -> None:
    """
    Generate stamp RGBA from image_entry, apply morph, resize to pw×ph,
    rotate, and alpha-composite onto canvas at (px, py).
    """
    pw, ph = max(1, p["pw"]), max(1, p["ph"])
    px, py = p["px"], p["py"]
    rot    = p.get("rotation", 0.0)

    # ── Cut ──
    try:
        stamp = cut_stamp(
            image_entry["path"],
            image_entry["meta"],
            p["cut_type"],
            p.get("cut_params", {}),
            seed=stamp_seed,
        )
    except Exception as e:
        print(f"[compositor] cut failed ({p['cut_type']}): {e}")
        return

    # ── Morph ──
    morph_type = p.get("morph_type")
    if morph_type:
        try:
            stamp = morph_stamp(
                stamp,
                {"morph_type": morph_type, "intensity": spec["morph_intensity"]},
                seed=stamp_seed + 1,
            )
        except Exception as e:
            print(f"[compositor] morph failed ({morph_type}): {e}")

    # ── Flip ──
    if p.get("flip_h"):
        stamp = stamp.transpose(Image.FLIP_LEFT_RIGHT)

    # ── Resize to target pw×ph ──
    stamp = stamp.convert("RGBA")
    sw, sh = stamp.size
    if sw < 1 or sh < 1:
        return

    # Preserve aspect ratio within pw×ph bounding box
    scale  = min(pw / sw, ph / sh)
    new_w  = max(1, int(sw * scale))
    new_h  = max(1, int(sh * scale))
    stamp  = stamp.resize((new_w, new_h), Image.LANCZOS)

    # ── Rotate ──
    if abs(rot) > 0.5:
        stamp = stamp.rotate(rot, expand=True, resample=Image.BICUBIC,
                             fillcolor=(0, 0, 0, 0))

    # ── Composite onto canvas ──
    sw2, sh2 = stamp.size
    # Center the (possibly rotated, expanded) stamp at the original center point
    center_x = px + pw // 2
    center_y = py + ph // 2
    paste_x  = center_x - sw2 // 2
    paste_y  = center_y - sh2 // 2

    # Create a full-canvas layer for this stamp (handles partial overlap cleanly)
    layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    # Clip stamp to layer bounds
    src_x1 = max(0, -paste_x)
    src_y1 = max(0, -paste_y)
    src_x2 = min(sw2, canvas_w - paste_x)
    src_y2 = min(sh2, canvas_h - paste_y)
    dst_x1 = max(0, paste_x)
    dst_y1 = max(0, paste_y)

    if src_x2 > src_x1 and src_y2 > src_y1:
        crop   = stamp.crop((src_x1, src_y1, src_x2, src_y2))
        layer.paste(crop, (dst_x1, dst_y1))
        canvas.alpha_composite(layer)


# ── Internal compose (patched to pass entries) ─────────────────────────────────

def compose(
    image_pool: List[dict],
    sliders:    dict,
    seed:       Optional[int] = None,
    canvas_w:   int = 1200,
    canvas_h:   int = 900,
) -> Image.Image:
    if not image_pool:
        return _blank_canvas(canvas_w, canvas_h)

    if seed is None:
        seed = random.randint(0, 999_999)

    rng  = random.Random(seed)
    spec = rules.interpret_sliders(sliders, seed)

    role_list = _build_role_list(image_pool, spec, rng)
    placed    = placer.place_stamps(role_list, spec, canvas_w, canvas_h, seed + 1)

    canvas = _make_background(image_pool, spec, canvas_w, canvas_h, rng)

    for i, p in enumerate(sorted(placed, key=lambda x: x.get("z_order", 5))):
        src_idx = p.get("source_idx", 0)
        if src_idx >= len(image_pool):
            src_idx = src_idx % len(image_pool)
        entry       = image_pool[src_idx]
        stamp_seed  = seed + 100 + i
        _paste_stamp_from_entry(canvas, p, entry, spec, stamp_seed, canvas_w, canvas_h)

    return canvas.convert("RGB")


# ── Utilities ──────────────────────────────────────────────────────────────────

def _blank_canvas(w: int, h: int) -> Image.Image:
    return Image.new("RGB", (w, h), (20, 18, 16))
