"""
Placer — Phase 4
Assigns pixel-space positions, sizes, rotations and z-orders to stamps
based on the composition mode and spec from rules.py.

Public API:
    place_stamps(role_list, spec, canvas_w, canvas_h, seed) -> list[PlacementDict]

PlacementDict keys:
    role        : str   — dominant | supporting | detail | strip | background
    source_idx  : int   — index into image_pool
    cut_type    : str
    cut_params  : dict
    morph_type  : str | None
    px, py      : int   — top-left paste position on canvas
    pw, ph      : int   — target stamp size on canvas
    rotation    : float — degrees
    z_order     : int
    flip_h      : bool
"""

import math
import random
from typing import List, Tuple


# ── Public API ─────────────────────────────────────────────────────────────────

def place_stamps(
    role_list:  List[dict],   # [{role, source_idx, cut_type, cut_params, morph_type}]
    spec:       dict,
    canvas_w:   int,
    canvas_h:   int,
    seed:       int,
) -> List[dict]:
    """
    Assign position, size, rotation, z_order to each stamp entry.
    Returns the same list with px/py/pw/ph/rotation/z_order/flip_h added.
    """
    rng  = random.Random(seed)
    mode = spec["mode"]

    if   mode == "scenic":       placements = _scenic      (role_list, spec, canvas_w, canvas_h, rng)
    elif mode == "symmetric":    placements = _symmetric   (role_list, spec, canvas_w, canvas_h, rng)
    elif mode == "radial":       placements = _radial      (role_list, spec, canvas_w, canvas_h, rng)
    elif mode == "framed":       placements = _framed      (role_list, spec, canvas_w, canvas_h, rng)
    elif mode == "experimental": placements = _experimental(role_list, spec, canvas_w, canvas_h, rng)
    else:
        placements = _scenic(role_list, spec, canvas_w, canvas_h, rng)

    # Apply symmetry mirror if requested
    if spec.get("symmetry"):
        placements = _apply_symmetry(placements, canvas_w, rng)

    return placements


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rot(spec: dict, rng: random.Random, scale: float = 1.0) -> float:
    r = spec["rotation_range"] * scale
    return rng.uniform(-r, r)

def _bleed(v: int, dim: int, size: int, allow: bool, rng: random.Random) -> int:
    """Optionally push position slightly off-canvas."""
    if allow and rng.random() < 0.25:
        bleed = int(size * rng.uniform(0.05, 0.30))
        return v - bleed if rng.random() < 0.5 else v
    return v

def _pick_cut(role: str, spec: dict, rng: random.Random) -> tuple:
    """Pick a cut type for this role using cut_weights, respecting disabled cuts."""
    weights  = dict(spec["cut_weights"].get(role, spec["cut_weights"]["detail"]))
    disabled = spec.get("disabled_cut_types", set())
    for d in disabled:
        weights.pop(d, None)
    if not weights:
        weights = {"raw": 1.0}   # last-resort fallback
    types  = list(weights.keys())
    probs  = list(weights.values())
    cut    = rng.choices(types, weights=probs, k=1)[0]

    cut_params = {}
    if cut == "geometric":
        disabled_shapes = spec.get("disabled_geo_shapes", set())
        if role == "strip":
            available = [s for s in ["strip_h", "strip_v"] if s not in disabled_shapes]
            cut_params["shape"] = rng.choice(available or ["strip_h"])
        else:
            available = [s for s in ["rect", "triangle", "wedge"] if s not in disabled_shapes]
            cut_params["shape"] = rng.choice(available or ["rect"])

    return cut, cut_params

def _pick_morph(spec: dict, rng: random.Random) -> str | None:
    if rng.random() < spec["morph_prob"]:
        disabled  = spec.get("disabled_morph_types", set())
        available = [m for m in [
            "compress_x", "stretch_x", "compress_y", "stretch_y",
            "rotate", "diagonal_stretch", "combined",
        ] if m not in disabled]
        if not available:
            return None
        return rng.choice(available)
    return None

def _assign_cut_morph(entry: dict, role: str, spec: dict, rng: random.Random) -> dict:
    """Fill in cut_type/cut_params/morph_type if not already set.
    Merges per-image disabled cuts (from entry['_parsed_disabled']) with global spec."""
    parsed = entry.get("_parsed_disabled") or {}
    if parsed:
        local = dict(spec)
        local["disabled_cut_types"]  = spec.get("disabled_cut_types",  set()) | parsed.get("dct", set())
        local["disabled_geo_shapes"] = spec.get("disabled_geo_shapes", set()) | parsed.get("dgs", set())
        local["disabled_morph_types"]= spec.get("disabled_morph_types",set()) | parsed.get("dmt", set())
    else:
        local = spec
    if not entry.get("cut_type"):
        entry["cut_type"], entry["cut_params"] = _pick_cut(role, local, rng)
    if "morph_type" not in entry:
        entry["morph_type"] = _pick_morph(local, rng)
    return entry

def _detail_size(cw: int, ch: int, rng: random.Random) -> Tuple[int, int]:
    """
    Detail stamps: visible minimum 10% of shorter dimension, max 22%.
    Aspect ratio varies — can be rectangular, not just square.
    """
    min_dim  = min(cw, ch)
    base     = rng.uniform(0.10, 0.22) * min_dim
    aspect   = rng.uniform(0.5, 2.0)          # allow tall or wide fragments
    pw       = max(60, int(base * math.sqrt(aspect)))
    ph       = max(60, int(base / math.sqrt(aspect)))
    return pw, ph

def _make_clusters(n: int, cw: int, ch: int, rng: random.Random, n_clusters: int = 3) -> list:
    """
    Generate n (cx, cy) positions clustered around n_clusters seeded anchor points.
    Returns list of (px, py) top-left positions with a placeholder size.
    """
    anchors = [(rng.randint(int(cw * 0.1), int(cw * 0.9)),
                rng.randint(int(ch * 0.1), int(ch * 0.9)))
               for _ in range(n_clusters)]
    positions = []
    for i in range(n):
        ax, ay = anchors[i % n_clusters]
        spread = int(min(cw, ch) * 0.18)
        px = int(ax + rng.uniform(-spread, spread))
        py = int(ay + rng.uniform(-spread, spread))
        positions.append((px, py))
    return positions

def _shuffle_z(placements: list, rng: random.Random) -> list:
    """Assign z_orders: background=0, rest shuffled but with role bias."""
    role_base = {"background": 0, "strip": 1, "detail": 2, "supporting": 3, "dominant": 4}
    for i, p in enumerate(placements):
        base  = role_base.get(p["role"], 2)
        jitter = rng.randint(-1, 1)
        p["z_order"] = max(0, base * 10 + i + jitter)
    return placements


# ── Scenic ─────────────────────────────────────────────────────────────────────

def _scenic(role_list, spec, cw, ch, rng):
    placements  = []
    bleed       = spec["allow_bleed"]
    detail_list = [e for e in role_list if e["role"] == "detail"]
    cluster_pos = _make_clusters(len(detail_list), cw, ch, rng, n_clusters=3)
    detail_idx  = 0

    for entry in role_list:
        role = entry["role"]
        _assign_cut_morph(entry, role, spec, rng)
        p = dict(entry)
        p["flip_h"] = rng.random() < 0.3

        if role == "background":
            p.update(px=0, py=0, pw=cw, ph=ch, rotation=0.0, z_order=0)

        elif role == "dominant":
            pw = int(rng.uniform(0.40, 0.72) * cw)
            ph = int(rng.uniform(0.40, 0.72) * ch)
            px = int(rng.uniform(0.10, 0.50) * cw)
            py = int(rng.uniform(0.10, 0.50) * ch)
            px = _bleed(px, cw, pw, bleed, rng)
            py = _bleed(py, ch, ph, bleed, rng)
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.15))

        elif role == "supporting":
            pw = int(rng.uniform(0.18, 0.40) * cw)
            ph = int(rng.uniform(0.18, 0.40) * ch)
            px = rng.randint(0, max(1, cw - pw))
            py = rng.randint(0, max(1, ch - ph))
            px = _bleed(px, cw, pw, bleed, rng)
            py = _bleed(py, ch, ph, bleed, rng)
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.5))

        elif role == "detail":
            pw, ph = _detail_size(cw, ch, rng)
            cx_d, cy_d = cluster_pos[detail_idx]
            px = cx_d - pw // 2
            py = cy_d - ph // 2
            detail_idx += 1
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 1.0))

        elif role == "strip":
            if entry.get("cut_params", {}).get("shape") == "strip_v":
                pw = int(rng.uniform(0.02, 0.08) * cw)
                ph = ch
                px = rng.randint(0, max(1, cw - pw))
                py = 0
            else:
                pw = cw
                ph = int(rng.uniform(0.02, 0.08) * ch)
                px = 0
                py = rng.randint(0, max(1, ch - ph))
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.05))

        placements.append(p)

    return _shuffle_z(placements, rng)


# ── Symmetric ──────────────────────────────────────────────────────────────────

def _symmetric(role_list, spec, cw, ch, rng):
    """
    Gravitational balance — stamps weighted toward the axis rather than hard pixel-mirror.
    Dominant stamps anchor the center axis. Others are placed with bilateral pull:
    their x-position is biased toward being equidistant from center, but not exact.
    """
    placements  = []
    axis_x      = cw // 2
    detail_list = [e for e in role_list if e["role"] == "detail"]
    # Clusters on left half only — mirroring doubles them
    cluster_pos = _make_clusters(len(detail_list), axis_x, ch, rng, n_clusters=2)
    detail_idx  = 0

    dominants = [e for e in role_list if e["role"] == "dominant"]
    others    = [e for e in role_list if e["role"] != "dominant"]

    # Dominant stamps anchor the center
    for entry in dominants:
        _assign_cut_morph(entry, "dominant", spec, rng)
        p = dict(entry)
        pw = int(rng.uniform(0.30, 0.60) * cw)
        ph = int(rng.uniform(0.35, 0.65) * ch)
        px = axis_x - pw // 2
        py = int(rng.uniform(0.15, 0.45) * ch)
        p.update(px=px, py=py, pw=pw, ph=ph,
                 rotation=_rot(spec, rng, 0.08), flip_h=False)
        placements.append(p)

    for entry in others:
        role = entry["role"]
        _assign_cut_morph(entry, role, spec, rng)
        p = dict(entry)
        p["flip_h"] = False

        if role == "background":
            p.update(px=0, py=0, pw=cw, ph=ch, rotation=0.0)
            placements.append(p)
            continue

        elif role == "detail":
            pw, ph = _detail_size(cw, ch, rng)
            cx_d, cy_d = cluster_pos[detail_idx % len(cluster_pos)]
            px  = cx_d - pw // 2
            py  = cy_d - ph // 2
            rot = _rot(spec, rng, 1.0)
            detail_idx += 1

        elif role == "supporting":
            pw = int(rng.uniform(0.18, 0.42) * cw)
            ph = int(rng.uniform(0.18, 0.42) * ch)
            # Bilateral pull: place left of axis with slight inward bias
            px = rng.randint(0, max(1, axis_x - pw // 2))
            py = rng.randint(0, max(1, ch - ph))
            rot = _rot(spec, rng, 0.6)

        elif role == "strip":
            pw = int(rng.uniform(0.02, 0.07) * cw)
            ph = ch
            px = rng.randint(0, max(1, axis_x - pw))
            py = 0
            rot = 0.0
        else:
            pw, ph, px, py, rot = 60, 60, 0, 0, 0.0

        p.update(px=px, py=py, pw=pw, ph=ph, rotation=rot)
        placements.append(p)

        # Mirror: small random offset from exact mirror for organic feel
        jitter   = int(rng.uniform(-0.03, 0.03) * cw)
        mirror   = dict(p)
        mirror["px"]     = cw - px - pw + jitter
        mirror["flip_h"] = True
        mirror["z_order"] = p.get("z_order", 5)
        placements.append(mirror)

    return _shuffle_z(placements, rng)


# ── Radial ─────────────────────────────────────────────────────────────────────

def _radial(role_list, spec, cw, ch, rng):
    """Dominant at center, supporters fan outward, details clustered at periphery."""
    placements   = []
    cx, cy       = cw // 2, ch // 2
    detail_list  = [e for e in role_list if e["role"] == "detail"]
    cluster_pos  = _make_clusters(len(detail_list), cw, ch, rng, n_clusters=3)
    detail_idx   = 0

    n_supporting = sum(1 for e in role_list if e["role"] == "supporting")
    sup_idx      = 0

    for entry in role_list:
        role = entry["role"]
        _assign_cut_morph(entry, role, spec, rng)
        p = dict(entry)
        p["flip_h"] = rng.random() < 0.3

        if role == "background":
            p.update(px=0, py=0, pw=cw, ph=ch, rotation=0.0)

        elif role == "dominant":
            pw = int(rng.uniform(0.30, 0.55) * cw)
            ph = int(rng.uniform(0.30, 0.55) * ch)
            px = cx - pw // 2 + rng.randint(-int(cw * 0.05), int(cw * 0.05))
            py = cy - ph // 2 + rng.randint(-int(ch * 0.05), int(ch * 0.05))
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.1))

        elif role == "supporting":
            angle = (sup_idx / max(1, n_supporting)) * 2 * math.pi + rng.uniform(-0.3, 0.3)
            dist  = rng.uniform(0.28, 0.48) * min(cw, ch)
            pw    = int(rng.uniform(0.18, 0.35) * cw)
            ph    = int(rng.uniform(0.18, 0.35) * ch)
            px    = int(cx + dist * math.cos(angle)) - pw // 2
            py    = int(cy + dist * math.sin(angle)) - ph // 2
            sup_idx += 1
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.5))

        elif role == "detail":
            pw, ph     = _detail_size(cw, ch, rng)
            cx_d, cy_d = cluster_pos[detail_idx]
            px = cx_d - pw // 2
            py = cy_d - ph // 2
            detail_idx += 1
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 1.0))

        elif role == "strip":
            angle = rng.uniform(0, 2 * math.pi)
            dist  = rng.uniform(0.1, 0.45) * min(cw, ch)
            pw    = int(rng.uniform(0.02, 0.07) * cw)
            ph    = int(rng.uniform(0.30, 0.70) * ch)
            px    = int(cx + dist * math.cos(angle)) - pw // 2
            py    = int(cy + dist * math.sin(angle)) - ph // 2
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=math.degrees(angle))

        placements.append(p)

    return _shuffle_z(placements, rng)


# ── Framed ─────────────────────────────────────────────────────────────────────

def _framed(role_list, spec, cw, ch, rng):
    """Dense border of small stamps; larger stamps in interior."""
    placements = []
    border     = int(min(cw, ch) * 0.18)   # border zone thickness

    def in_border(px, py, pw, ph):
        return (px < border or py < border or
                px + pw > cw - border or py + ph > ch - border)

    for entry in role_list:
        role = entry["role"]
        _assign_cut_morph(entry, role, spec, rng)
        p = dict(entry)
        p["flip_h"] = rng.random() < 0.35

        if role == "background":
            p.update(px=0, py=0, pw=cw, ph=ch, rotation=0.0)

        elif role == "dominant":
            pw = int(rng.uniform(0.28, 0.55) * cw)
            ph = int(rng.uniform(0.28, 0.55) * ch)
            px = rng.randint(border, max(border + 1, cw - pw - border))
            py = rng.randint(border, max(border + 1, ch - ph - border))
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.12))

        elif role == "supporting":
            pw = int(rng.uniform(0.15, 0.32) * cw)
            ph = int(rng.uniform(0.15, 0.32) * ch)
            if rng.random() < 0.5:
                # Interior
                px = rng.randint(border, max(border + 1, cw - pw - border))
                py = rng.randint(border, max(border + 1, ch - ph - border))
            else:
                px = rng.randint(0, max(1, cw - pw))
                py = rng.randint(0, max(1, ch - ph))
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.4))

        elif role == "detail":
            # Pack into border zone with guaranteed visible size
            pw, ph = _detail_size(cw, ch, rng)
            side = rng.randint(0, 3)
            def _ri(a, b): return rng.randint(min(a, b), max(a, b))
            if side == 0:   px, py = rng.randint(0, max(1, cw - pw)), rng.randint(0, max(1, border))
            elif side == 1: px, py = rng.randint(0, max(1, cw - pw)), _ri(max(0, ch - border), max(0, ch - ph))
            elif side == 2: px, py = rng.randint(0, max(1, border)),  rng.randint(0, max(1, ch - ph))
            else:           px, py = _ri(max(0, cw - border), max(0, cw - pw)), rng.randint(0, max(1, ch - ph))
            px = max(0, min(px, cw - 1))
            py = max(0, min(py, ch - 1))
            p.update(px=px, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 1.0))

        elif role == "strip":
            pw = cw
            ph = int(rng.uniform(0.015, 0.06) * ch)
            side = rng.choice([0, 1])
            py   = rng.randint(0, border // 2) if side == 0 else rng.randint(ch - border, ch - ph)
            p.update(px=0, py=py, pw=pw, ph=ph, rotation=_rot(spec, rng, 0.04))

        placements.append(p)

    return _shuffle_z(placements, rng)


# ── Experimental ───────────────────────────────────────────────────────────────

def _experimental(role_list, spec, cw, ch, rng):
    """Blend two modes: first half of stamps get mode A, second half get mode B."""
    modes = ["scenic", "radial", "framed", "symmetric"]
    rng.shuffle(modes)
    mode_a, mode_b = modes[0], modes[1]

    mid    = len(role_list) // 2
    half_a = role_list[:mid]
    half_b = role_list[mid:]

    spec_a = dict(spec, mode=mode_a)
    spec_b = dict(spec, mode=mode_b)

    fn = {"scenic": _scenic, "radial": _radial, "framed": _framed, "symmetric": _symmetric}
    placed_a = fn[mode_a](half_a, spec_a, cw, ch, rng)
    placed_b = fn[mode_b](half_b, spec_b, cw, ch, rng)

    return _shuffle_z(placed_a + placed_b, rng)


# ── Symmetry mirror ────────────────────────────────────────────────────────────

def _apply_symmetry(placements: list, canvas_w: int, rng: random.Random) -> list:
    """Mirror non-background, non-axis stamps across the vertical center."""
    axis_x = canvas_w // 2
    result = []
    for p in placements:
        result.append(p)
        if p["role"] in ("detail", "strip") and rng.random() < 0.6:
            mirror = dict(p)
            mirror["px"]     = canvas_w - p["px"] - p["pw"]
            mirror["flip_h"] = not p.get("flip_h", False)
            result.append(mirror)
    return result
