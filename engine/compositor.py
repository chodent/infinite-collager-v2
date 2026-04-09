"""
Compositor — Phase 4
Orchestrates the full collage pipeline: rules → role assignment → cut →
morph → place → composite into a single PIL RGB Image.

Public API:
    compose(image_pool, sliders, seed, canvas_w, canvas_h) -> PIL.Image RGB
"""

import math
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import numpy as np
from PIL import Image

from engine import rules, placer
from engine.cutter  import cut_stamp
from engine.morpher import morph_stamp


# ── Per-image cut preference parsing ──────────────────────────────────────────

def _parse_disabled_cuts(disabled_keys: list) -> dict:
    """Map a list of cut-key strings to typed sets for use in placer."""
    dct: set = set()   # disabled cut types
    dgs: set = set()   # disabled geometric shapes
    dmt: set = set()   # disabled morph types
    for key in disabled_keys:
        if key in ("silhouette", "tear", "raw"):
            dct.add(key)
        elif key == "geometric_rect":
            dgs.add("rect")
        elif key == "geometric_strip":
            dgs.update({"strip_h", "strip_v"})
        elif key == "geometric_triangle":
            dgs.add("triangle")
        elif key == "geometric_wedge":
            dgs.add("wedge")
        elif key.startswith("morph_"):
            dmt.add(key[6:])
    if {"rect", "triangle", "wedge"}.issubset(dgs):
        dct.add("geometric")
    return {"dct": dct, "dgs": dgs, "dmt": dmt}


# ── Public API — defined after helpers below ───────────────────────────────────


# ── Role list builder ──────────────────────────────────────────────────────────

def _build_role_list(image_pool: list, spec: dict, rng: random.Random,
                     image_weights: Optional[list] = None) -> list:
    """
    Create one entry per stamp. Each entry carries role, source_idx,
    and (pre-set) cut_type/cut_params if role dictates it.
    image_weights: optional list of floats (parallel to image_pool) for weighted pick.
    """
    role_list = []
    n_images  = len(image_pool)
    rc        = spec["role_counts"]

    indices = list(range(n_images))
    if image_weights and len(image_weights) == n_images:
        def pick_idx():
            return rng.choices(indices, weights=image_weights, k=1)[0]
    else:
        def pick_idx():
            return rng.randint(0, n_images - 1)

    def make_entry(role, cut_type, cut_params, morph_type):
        idx = pick_idx()
        return {
            "role":              role,
            "source_idx":        idx,
            "cut_type":          cut_type,
            "cut_params":        cut_params,
            "morph_type":        morph_type,
            "_parsed_disabled":  image_pool[idx].get("_parsed_disabled", {}),
        }

    # Background (optional)
    if spec["bg_type"] == "photo":
        role_list.append(make_entry("background", "raw", {}, None))

    # Dominant
    for _ in range(rc["dominant"]):
        role_list.append(make_entry("dominant", None, {}, None))

    # Supporting
    for _ in range(rc["supporting"]):
        role_list.append(make_entry("supporting", None, {}, None))

    # Detail
    for _ in range(rc["detail"]):
        role_list.append(make_entry("detail", None, {}, None))

    # Strips
    for i in range(rc["strip"]):
        shape = "strip_h" if i % 2 == 0 else "strip_v"
        role_list.append(make_entry("strip", "geometric", {"shape": shape}, None))

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
    canvas     = Image.new("RGBA", (canvas_w, canvas_h), (20, 18, 16, 255))
    tonal_hint = spec.get("tonal_hint")

    if spec["bg_type"] == "color":
        if tonal_hint:
            r = max(0, int(tonal_hint["r"] * 0.60))
            g = max(0, int(tonal_hint["g"] * 0.60))
            b = max(0, int(tonal_hint["b"] * 0.60))
        else:
            entry  = rng.choice(image_pool)
            colors = entry["meta"].get("dominant_colors", [])
            if colors:
                c = rng.choice(colors[:3])
                r = max(0, int(c["r"] * 0.55))
                g = max(0, int(c["g"] * 0.55))
                b = max(0, int(c["b"] * 0.55))
            else:
                r, g, b = 20, 18, 16
        canvas.paste(Image.new("RGBA", (canvas_w, canvas_h), (r, g, b, 255)))

    elif spec["bg_type"] == "photo":
        # Full-bleed: load a random pool image, resize to fill the canvas, paste directly
        entry = rng.choice(image_pool)
        try:
            bg      = Image.open(entry["path"]).convert("RGBA")
            bw, bh  = bg.size
            scale   = max(canvas_w / bw, canvas_h / bh)
            new_w   = int(bw * scale)
            new_h   = int(bh * scale)
            bg      = bg.resize((new_w, new_h), Image.LANCZOS)
            left    = (new_w - canvas_w) // 2
            top     = (new_h - canvas_h) // 2
            bg      = bg.crop((left, top, left + canvas_w, top + canvas_h))
            canvas.paste(bg, (0, 0))
        except Exception as e:
            print(f"[compositor] bg photo failed: {e}")
        if tonal_hint:
            tint = Image.new("RGBA", (canvas_w, canvas_h),
                             (int(tonal_hint["r"] * 0.25),
                              int(tonal_hint["g"] * 0.25),
                              int(tonal_hint["b"] * 0.25), 65))
            canvas.alpha_composite(tint)

    elif spec["bg_type"] == "none" and tonal_hint:
        r = max(0, int(tonal_hint["r"] * 0.18))
        g = max(0, int(tonal_hint["g"] * 0.18))
        b = max(0, int(tonal_hint["b"] * 0.18))
        canvas.paste(Image.new("RGBA", (canvas_w, canvas_h), (r, g, b, 255)))

    return canvas



def _composite_stamp(
    canvas:   Image.Image,
    stamp:    Image.Image,
    p:        dict,
    spec:     dict,
    canvas_w: int,
    canvas_h: int,
) -> None:
    """
    Resize, rotate, and composite a pre-cut stamp onto the canvas.
    Uses direct bbox paste — no full-canvas layer allocation.
    """
    pw, ph = max(1, p["pw"]), max(1, p["ph"])
    px, py = p["px"], p["py"]
    rot    = p.get("rotation", 0.0)

    stamp = stamp.convert("RGBA")
    sw, sh = stamp.size
    if sw < 1 or sh < 1:
        return

    # Preserve aspect ratio within pw×ph bounding box
    scale = min(pw / sw, ph / sh)
    new_w = max(1, int(sw * scale))
    new_h = max(1, int(sh * scale))
    stamp = stamp.resize((new_w, new_h), Image.LANCZOS)

    if abs(rot) > 0.5:
        stamp = stamp.rotate(rot, expand=True, resample=Image.BICUBIC,
                             fillcolor=(0, 0, 0, 0))

    sw2, sh2 = stamp.size
    center_x = px + pw // 2
    center_y = py + ph // 2
    paste_x  = center_x - sw2 // 2
    paste_y  = center_y - sh2 // 2

    # Clip to canvas bounds
    src_x1 = max(0, -paste_x)
    src_y1 = max(0, -paste_y)
    src_x2 = min(sw2, canvas_w - paste_x)
    src_y2 = min(sh2, canvas_h - paste_y)
    dst_x1 = max(0, paste_x)
    dst_y1 = max(0, paste_y)

    if src_x2 <= src_x1 or src_y2 <= src_y1:
        return

    crop       = stamp.crop((src_x1, src_y1, src_x2, src_y2))
    blend_mode = p.get("blend_mode", "normal")

    if blend_mode == "normal":
        # Fast path: paste directly into the bbox region only
        canvas.alpha_composite(crop, dest=(dst_x1, dst_y1))
    else:
        # Blend path: extract canvas region, blend, paste back
        cw_crop = src_x2 - src_x1
        ch_crop = src_y2 - src_y1
        canvas_region = canvas.crop((dst_x1, dst_y1,
                                     dst_x1 + cw_crop, dst_y1 + ch_crop))
        blended = _apply_blend_region(canvas_region, crop, blend_mode)
        canvas.alpha_composite(blended, dest=(dst_x1, dst_y1))


# ── Internal compose (patched to pass entries) ─────────────────────────────────

def compose(
    image_pool:     List[dict],
    sliders:        dict,
    seed:           Optional[int] = None,
    canvas_w:       int = 1200,
    canvas_h:       int = 900,
    tonal_hint:     Optional[dict] = None,
    image_weights:  Optional[list] = None,
) -> Image.Image:
    if not image_pool:
        return _blank_canvas(canvas_w, canvas_h)

    if seed is None:
        seed = random.randint(0, 999_999)

    rng  = random.Random(seed)
    spec = rules.interpret_sliders(sliders, seed)
    if tonal_hint:
        spec["tonal_hint"] = tonal_hint

    # ── Pre-load all pool images once (use work_path for speed) ───────────────
    loaded_pool = []
    for entry in image_pool:
        load_path = entry["meta"].get("work_path") or entry["path"]
        try:
            img = Image.open(load_path).convert("RGBA")
        except Exception:
            img = Image.open(entry["path"]).convert("RGBA")
        # Scale meta subject_bbox to work image dimensions
        meta        = dict(entry["meta"])
        orig_w      = meta.get("width", img.width)
        orig_h      = meta.get("height", img.height)
        work_w, work_h = img.size
        if (work_w, work_h) != (orig_w, orig_h):
            sx = work_w / orig_w
            sy = work_h / orig_h
            sb = meta.get("subject_bbox", {})
            if sb:
                meta["subject_bbox"] = {
                    "x": int(sb["x"] * sx), "y": int(sb["y"] * sy),
                    "w": int(sb["w"] * sx), "h": int(sb["h"] * sy),
                }
            # mask_path still points to full-res mask — scale handled in _load_mask
        disabled = entry.get("disabled_cuts") or []
        loaded_pool.append({
            "path": entry["path"], "meta": meta, "img": img,
            "_parsed_disabled": _parse_disabled_cuts(disabled) if disabled else {},
        })

    role_list = _build_role_list(loaded_pool, spec, rng, image_weights=image_weights)
    placed    = placer.place_stamps(role_list, spec, canvas_w, canvas_h, seed + 1)

    canvas         = _make_background(loaded_pool, spec, canvas_w, canvas_h, rng)
    blend_strength = spec.get("morph_intensity", 0.0) * 0.7
    sorted_placed  = sorted(placed, key=lambda x: x.get("z_order", 5))

    # ── Generate all stamps in parallel, then composite in z-order ────────────
    def _gen_stamp(args):
        i, p = args
        src_idx = p.get("source_idx", 0) % len(loaded_pool)
        entry   = loaded_pool[src_idx]
        s_seed  = seed + 100 + i
        if "blend_mode" not in p:
            p["blend_mode"] = _pick_blend(p.get("role", "detail"), blend_strength, rng)
        try:
            stamp = cut_stamp(
                entry["path"], entry["meta"], p["cut_type"],
                p.get("cut_params", {}), seed=s_seed, img_pil=entry["img"],
            )
            morph_type = p.get("morph_type")
            if morph_type:
                stamp = morph_stamp(
                    stamp,
                    {"morph_type": morph_type, "intensity": spec["morph_intensity"]},
                    seed=s_seed + 1,
                )
            if p.get("flip_h"):
                stamp = stamp.transpose(Image.FLIP_LEFT_RIGHT)
            return i, p, stamp
        except Exception as e:
            print(f"[compositor] stamp {i} failed: {e}")
            return i, p, None

    stamp_results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_gen_stamp, (i, p)): i
                   for i, p in enumerate(sorted_placed)}
        for fut in as_completed(futures):
            i, p, stamp = fut.result()
            stamp_results[i] = (p, stamp)

    # Composite in z-order (sequential — canvas writes must be serial)
    for i, p in enumerate(sorted_placed):
        p, stamp = stamp_results.get(i, (p, None))
        if stamp is not None:
            _composite_stamp(canvas, stamp, p, spec, canvas_w, canvas_h)

    return canvas.convert("RGB")


# ── Blend modes (region-scoped — operates only on stamp bbox) ─────────────────

def _apply_blend_region(base_region: Image.Image, stamp: Image.Image, mode: str) -> Image.Image:
    """
    Blend stamp onto base_region (both same size, RGBA).
    Returns blended RGBA region — caller pastes back to canvas.
    """
    base_np  = np.array(base_region.convert("RGBA"), dtype=np.float32) / 255.0
    layer_np = np.array(stamp.convert("RGBA"),        dtype=np.float32) / 255.0

    b = base_np[:, :, :3]
    s = layer_np[:, :, :3]
    a = layer_np[:, :, 3:4]

    if mode == "multiply":
        blended = b * s
    elif mode == "screen":
        blended = 1.0 - (1.0 - b) * (1.0 - s)
    elif mode == "overlay":
        blended = np.where(b < 0.5, 2 * b * s, 1.0 - 2 * (1 - b) * (1 - s))
    elif mode == "soft_light":
        blended = np.where(
            s <= 0.5,
            b - (1 - 2 * s) * b * (1 - b),
            b + (2 * s - 1) * (_soft_light_d(b) - b),
        )
    else:
        return stamp

    out_rgb = blended * a + b * (1.0 - a)
    out_a   = np.maximum(base_np[:, :, 3:4], a)
    out     = np.clip(np.dstack([out_rgb, out_a]), 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")

def _soft_light_d(b: np.ndarray) -> np.ndarray:
    return np.where(b <= 0.25,
                    ((16 * b - 12) * b + 4) * b,
                    np.sqrt(b))


# ── Blend mode assignment ───────────────────────────────────────────────────────

_ROLE_BLEND_WEIGHTS = {
    # role: [(mode, weight), ...]
    "dominant":   [("normal", 0.55), ("soft_light", 0.25), ("overlay", 0.20)],
    "supporting": [("normal", 0.50), ("multiply",   0.25), ("screen",  0.25)],
    "detail":     [("normal", 0.35), ("screen",     0.35), ("multiply",0.30)],
    "strip":      [("normal", 0.40), ("multiply",   0.40), ("overlay", 0.20)],
    "background": [("normal", 1.00)],
}

def _pick_blend(role: str, blend_strength: float, rng: random.Random) -> str:
    """
    blend_strength 0→1: at 0 always normal, at 1 full probability of exotic modes.
    Derived from morph_intensity slider in the spec.
    """
    if blend_strength < 0.15 or rng.random() > blend_strength:
        return "normal"
    weights_list = _ROLE_BLEND_WEIGHTS.get(role, [("normal", 1.0)])
    modes   = [w[0] for w in weights_list]
    weights = [w[1] for w in weights_list]
    return rng.choices(modes, weights=weights, k=1)[0]


# ── Utilities ──────────────────────────────────────────────────────────────────

def _blank_canvas(w: int, h: int) -> Image.Image:
    return Image.new("RGB", (w, h), (20, 18, 16))
